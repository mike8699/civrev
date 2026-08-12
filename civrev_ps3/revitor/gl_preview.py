"""3D in-game-style map preview (OpenGL 4.1 core, no PyOpenGL needed).

Renders the map the way the game does: the generated 512x512 heights DDS
displaces a terrain mesh, the 4096x4096 lightmap is the painted ground
diffuse, the blends G channel mixes in the game's rock detail texture on
mountains, a translucent water plane sits at sea level over the painted
ocean floor, rivers run along flagged tile edges, and forest tiles get
conifer clusters. All texture payloads are the exact bytes a build writes.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from model import FOREST, GRID
from PyQt5.QtCore import QPoint, QSize, Qt
from PyQt5.QtGui import (
    QImage,
    QMatrix4x4,
    QOffscreenSurface,
    QOpenGLBuffer,
    QOpenGLContext,
    QOpenGLFramebufferObject,
    QOpenGLFramebufferObjectFormat,
    QOpenGLShader,
    QOpenGLShaderProgram,
    QOpenGLTexture,
    QOpenGLVersionProfile,
    QOpenGLVertexArrayObject,
    QSurfaceFormat,
    QVector3D,
)
from PyQt5.QtWidgets import QOpenGLWidget

# GL constants (core profile, no wrapper enums for these)
GL_FLOAT = 0x1406
GL_TRIANGLES = 0x0004
GL_UNSIGNED_INT = 0x1405
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_SRC_ALPHA = 0x0302
GL_ONE_MINUS_SRC_ALPHA = 0x0303
GL_COLOR_BUFFER_BIT = 0x4000
GL_DEPTH_BUFFER_BIT = 0x0100
GL_CULL_FACE = 0x0B44

H_TEX = 512
# Calibrated against RPCS3 captures: in-game mountains rise well under a
# tile-width — relief is much subtler than the heightfield range suggests
HEIGHT_SCALE = 1.55
WATER_NORM = 0.335           # sea level in normalized height
SKY = (0.235, 0.415, 0.78)   # the game's bright blue backdrop
CURVE = 0.0032               # CivRev's rolling world-curvature

from settings import PROJECT_ROOT as _PROJECT_ROOT
# The game's Level/ textures (canopies, rock detail) are OPTIONAL and
# loaded at runtime from the user's own extracted files — never bundled.
LEVEL_DIR = _PROJECT_ROOT / "Level"


@dataclass
class SceneData:
    """Everything the renderer needs. Texture payloads are DDS-exact."""

    heights: np.ndarray            # (512,512) uint16
    light_dxt1: bytes | None       # 4096x4096 DXT1 payload (no header)
    light_rgb: np.ndarray | None   # fallback (4096,4096,3) uint8
    blend_dxt1: bytes              # 2048x2048 DXT1 payload
    grid: bytes                    # 1024 display-order tile bytes
    veg: np.ndarray | None = None  # (2048,2048,4) RGBA vegetation splats


# ── Vegetation splats (game-style: colored overlays on the pale ground) ─

VEG_SIZE = 2048                    # 64 px per tile

# In-game colors sampled from RPCS3 captures (pristine UK/Earth maps)
GREEN_VEG = np.array([94, 162, 72], dtype=np.float32)      # grass/forest
GREEN_WARM = np.array([118, 176, 68], dtype=np.float32)
GREEN_COLD = np.array([84, 142, 74], dtype=np.float32)
PLAINS_GOLD = np.array([196, 186, 98], dtype=np.float32)
DESERT_GOLD = np.array([208, 186, 92], dtype=np.float32)
ICE_BLUE = np.array([170, 212, 232], dtype=np.float32)

_noise_cache: dict = {}


def _splat_noise(size: int, seed: int, blur: int) -> np.ndarray:
    """Smooth deterministic noise in [0,1] for organic splat edges."""
    key = (size, seed, blur)
    if key not in _noise_cache:
        from PIL import Image

        rng = np.random.default_rng(seed)
        small = rng.random((size // 8, size // 8)).astype(np.float32)
        img = Image.fromarray(small, "F").resize((size, size),
                                                 Image.BILINEAR)
        n = np.asarray(img)
        for _ in range(blur):
            p = np.pad(n, 1, mode="wrap")
            n = sum(p[dy:dy + size, dx:dx + size]
                    for dy in range(3) for dx in range(3)) / 9.0
        lo, hi = n.min(), n.max()
        _noise_cache[key] = (n - lo) / max(1e-6, hi - lo)
    return _noise_cache[key]


def _class_mask(idx_map: np.ndarray, noise: np.ndarray) -> np.ndarray:
    """32x32 bool map -> feathered organic 2048 alpha in [0,1].

    Splats cover their tiles fully and bleed slightly outward with noisy
    feathered borders (matching the game's transition masks).
    """
    from PIL import Image

    m = np.asarray(Image.fromarray(
        idx_map.astype(np.float32), "F").resize((VEG_SIZE, VEG_SIZE),
                                                Image.BILINEAR))
    return np.clip((m - 0.22) * 4.0 + (noise - 0.5) * 1.1, 0.0, 1.0)


def build_vegetation_overlay(grid: bytes) -> np.ndarray:
    """(2048,2048,4) RGBA: the game's colored vegetation splats.

    The painted lightmap is the base ground; grass/plains/desert/ice read
    as saturated color splats with feathered edges over it.
    """
    g = np.frombuffer(bytes(grid), dtype=np.uint8).reshape(GRID, GRID) & 0x07
    lat = np.abs(np.arange(GRID) - 15.5)

    green = (g == 1) | (g == FOREST)
    plains = g == 2
    desert = g == 5
    ice = g == 7

    n1 = _splat_noise(VEG_SIZE, 11, 1)
    n2 = _splat_noise(VEG_SIZE, 23, 0)

    out_rgb = np.zeros((VEG_SIZE, VEG_SIZE, 3), dtype=np.float32)
    out_a = np.zeros((VEG_SIZE, VEG_SIZE), dtype=np.float32)

    # Latitude-banded green color field
    band = np.select(
        [lat <= 5.5, lat <= 10.5], [0, 1], default=2)
    green_rows = np.stack([GREEN_WARM, GREEN_VEG, GREEN_COLD])[band]
    green_field = np.repeat(green_rows[:, None, :], GRID, axis=1)
    from PIL import Image

    green_big = np.stack([
        np.asarray(Image.fromarray(green_field[:, :, i], "F").resize(
            (VEG_SIZE, VEG_SIZE), Image.BILINEAR))
        for i in range(3)
    ], axis=-1)

    layers = [
        (green, green_big, 0.97),
        (plains, PLAINS_GOLD[None, None, :], 0.92),
        (desert, DESERT_GOLD[None, None, :], 0.92),
        (ice, ICE_BLUE[None, None, :], 0.85),
    ]
    for mask32, color, strength in layers:
        if not mask32.any():
            continue
        a = _class_mask(mask32, n1) * strength
        keep = a > out_a
        col = np.broadcast_to(color, (VEG_SIZE, VEG_SIZE, 3))
        out_rgb[keep] = col[keep]
        out_a = np.maximum(out_a, a)

    # Organic brightness variation + fine grass grain inside splats
    grain = _splat_noise(VEG_SIZE, 41, 0)
    out_rgb *= ((0.90 + 0.20 * n2) * (0.93 + 0.14 * grain))[:, :, None]

    # Darker rim just inside splat borders, like the game's outlined edges
    rim = np.clip((out_a - 0.15) * 5.0, 0, 1) * np.clip(
        (0.75 - out_a) * 4.0, 0, 1)
    out_rgb *= (1.0 - 0.22 * rim)[:, :, None]

    rgba = np.empty((VEG_SIZE, VEG_SIZE, 4), dtype=np.uint8)
    rgba[:, :, :3] = np.clip(out_rgb, 0, 255).astype(np.uint8)
    rgba[:, :, 3] = np.clip(out_a * 255, 0, 255).astype(np.uint8)
    return rgba


# Back-compat alias used by the scene worker
def build_ground_albedo(grid: bytes) -> np.ndarray:
    return build_vegetation_overlay(grid)


def default_surface_format() -> QSurfaceFormat:
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 1)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    return fmt


# ── Shaders ─────────────────────────────────────────────────────────────

CURVE_FN = """
uniform vec2 uEye;
uniform float uCurve;
vec3 curved(vec3 p) {
    vec2 d = p.xy - uEye;
    p.z -= uCurve * dot(d, d);
    return p;
}
"""

TERRAIN_VS = """
#version 150
in vec2 xy;
uniform sampler2D uHeights;
uniform float uHScale;
uniform mat4 uMvp;
out vec2 vUV;
""" + CURVE_FN + """
void main() {
    vUV = xy / 32.0;
    float h = texture(uHeights, vUV).r;
    gl_Position = uMvp * vec4(curved(vec3(xy, h * uHScale)), 1.0);
}
"""

TERRAIN_FS = """
#version 150
in vec2 vUV;
uniform sampler2D uHeights;
uniform sampler2D uLight;
uniform sampler2D uBlend;
uniform sampler2D uDetail;
uniform sampler2D uVeg;
uniform float uHScale;
uniform vec3 uLightDir;
out vec4 frag;
void main() {
    float texel = 1.0 / 512.0;
    float hl = texture(uHeights, vUV - vec2(texel, 0.0)).r;
    float hr = texture(uHeights, vUV + vec2(texel, 0.0)).r;
    float hd = texture(uHeights, vUV - vec2(0.0, texel)).r;
    float hu = texture(uHeights, vUV + vec2(0.0, texel)).r;
    float span = 2.0 * 32.0 / 512.0;
    vec3 n = normalize(vec3((hl - hr) * uHScale / span,
                            (hd - hu) * uHScale / span, 1.0));

    // The painted lightmap IS the ground (pale rock/sand with crevices),
    // warmed slightly toward the game's cream tone
    vec3 light = texture(uLight, vUV).rgb;
    vec3 base = light * vec3(1.16, 1.12, 1.02);

    // Warm sand ring just above the waterline
    float hh = texture(uHeights, vUV).r;
    float beach = (1.0 - smoothstep(0.345, 0.40, hh))
                * smoothstep(0.325, 0.34, hh);
    base *= mix(vec3(1.0), vec3(1.06, 1.0, 0.82), beach);

    // Saturated vegetation splats colorized over the full painted texture,
    // so the lightmap's mottled detail shows through the grass like in-game
    vec4 veg = texture(uVeg, vUV);
    vec3 vegcol = veg.rgb * (light * vec3(1.35, 1.32, 1.30));
    base = mix(base, vegcol, veg.a);

    // Rock texture on mountain mask (cool gray, light touch)
    float rock = texture(uBlend, vUV).g;
    vec3 detail = texture(uDetail, vUV * 40.0).rgb;
    vec3 rockcol = base * mix(vec3(1.0), detail * 1.7, 0.5)
                   * vec3(1.02, 0.98, 0.92);
    base = mix(base, rockcol, clamp(rock, 0.0, 1.0) * 0.55);

    // Snow only on the very highest peaks
    float h = texture(uHeights, vUV).r;
    float snow = smoothstep(0.85, 0.95, h);
    base = mix(base, vec3(0.93, 0.96, 1.0) * (0.7 + 0.45 * light.r), snow);

    float diff = max(dot(n, normalize(uLightDir)), 0.0);
    vec3 col = base * (0.86 + 0.30 * diff);
    // Gentle saturation push toward the game's vivid look
    float grey = dot(col, vec3(0.299, 0.587, 0.114));
    col = clamp(mix(vec3(grey), col, 1.10), 0.0, 1.0);
    frag = vec4(col, 1.0);
}
"""

FLAT_VS = """
#version 150
in vec3 pos;
uniform mat4 uMvp;
""" + CURVE_FN + """
void main() { gl_Position = uMvp * vec4(curved(pos), 1.0); }
"""

FLAT_FS = """
#version 150
uniform vec4 uColor;
out vec4 frag;
void main() { frag = uColor; }
"""

WATER_VS = """
#version 150
in vec3 pos;
uniform mat4 uMvp;
out vec2 vUV;
""" + CURVE_FN + """
void main() {
    vUV = pos.xy / 32.0;
    gl_Position = uMvp * vec4(curved(pos), 1.0);
}
"""

WATER_FS = """
#version 150
in vec2 vUV;
uniform sampler2D uHeights;
uniform sampler2D uLight;
uniform float uWaterNorm;
out vec4 frag;
void main() {
    // Beyond the map bounds: uniform deep ocean like the game's backdrop
    float inside = step(0.0, vUV.x) * step(vUV.x, 1.0)
                 * step(0.0, vUV.y) * step(vUV.y, 1.0);
    float floor_h = texture(uHeights, vUV).r;
    float depth = mix(1.0, clamp((uWaterNorm - floor_h) * 14.0, 0.0, 1.0),
                      inside);
    vec3 floorc = mix(vec3(0.72), texture(uLight, vUV).rgb, inside);
    // Soften the painted seafloor slightly (in-game reads silky)
    floorc = mix(floorc, vec3(0.74), 0.3);
    // Blue glass: teal shelf -> dark saturated deep
    vec3 tint = mix(vec3(0.50, 0.88, 0.96), vec3(0.13, 0.36, 0.74),
                    smoothstep(0.0, 0.5, depth));
    vec3 col = floorc * tint * 1.16;
    col = mix(col, vec3(0.10, 0.30, 0.58),
              smoothstep(0.3, 1.0, depth) * 0.62);
    float alpha = mix(0.35, 0.96, smoothstep(0.0, 0.35, depth));
    // White foam ring hugging the shoreline, with a wobbly outer edge
    float foamz = clamp((uWaterNorm - floor_h) * 60.0, 0.0, 1.0) * inside;
    float wob = sin(vUV.x * 260.0) * sin(vUV.y * 240.0) * 0.25;
    float foam = foamz * (1.0 - smoothstep(0.35 + wob, 0.9 + wob, foamz));
    col = mix(col, vec3(0.97, 1.0, 1.0), foam * 0.85);
    alpha = max(alpha, foam * 0.9);
    frag = vec4(col, mix(1.0, alpha, inside));
}
"""

RIVER_VS = """
#version 150
in vec3 pos;
in vec2 uv;
uniform mat4 uMvp;
out vec2 vUV;
""" + CURVE_FN + """
void main() {
    vUV = uv;
    gl_Position = uMvp * vec4(curved(pos), 1.0);
}
"""

RIVER_FS = """
#version 150
in vec2 vUV;                 // u = distance along (tiles), v = 0..1 across
uniform int uKind;           // 0 = sand bank, 1 = water channel
out vec4 frag;
void main() {
    float edge = min(vUV.y, 1.0 - vUV.y) * 2.0;   // 0 banks -> 1 center
    if (uKind == 0) {
        // Sand halo, soft outer edge, slight speckle
        vec3 sandc = vec3(0.93, 0.88, 0.72);
        float sp = fract(sin(dot(floor(vUV * vec2(14.0, 9.0)),
                                 vec2(12.9898, 78.233))) * 43758.5453);
        sandc *= 0.96 + 0.07 * sp;
        float a = smoothstep(0.0, 0.45, edge) * 0.85;
        frag = vec4(sandc, a);
    } else {
        // Milky cyan channel like the game's: pale rim, soft teal body
        vec3 rim = vec3(0.88, 0.98, 1.0);
        vec3 body = vec3(0.62, 0.86, 0.95);
        vec3 core = vec3(0.44, 0.74, 0.90);
        vec3 col = mix(rim, body, smoothstep(0.06, 0.45, edge));
        col = mix(col, core, smoothstep(0.55, 1.0, edge) * 0.5);
        // Gentle flow ripple
        col *= 1.0 + 0.03 * sin(vUV.x * 9.0 + vUV.y * 4.0);
        float a = smoothstep(0.0, 0.2, edge) * 0.88;
        frag = vec4(col, a);
    }
}
"""

TREE_VS = """
#version 150
in vec3 pos;
in vec2 uv;
in float shade;
uniform mat4 uMvp;
out vec2 vUV;
out float vShade;
""" + CURVE_FN + """
void main() {
    vUV = uv;
    vShade = shade;
    gl_Position = uMvp * vec4(curved(pos), 1.0);
}
"""

TREE_FS = """
#version 150
in vec2 vUV;
in float vShade;
uniform sampler2D uTex;
out vec4 frag;
void main() {
    vec4 c = texture(uTex, vUV);
    if (c.a < 0.5) discard;
    frag = vec4(c.rgb * vShade, 1.0);
}
"""


# ── CPU helpers ─────────────────────────────────────────────────────────


def _sample_height(heights: np.ndarray, wx: float, wy: float) -> float:
    """Bilinear height (normalized 0-1) at world coords (tile units)."""
    px = min(max(wx / 32.0 * H_TEX - 0.5, 0), H_TEX - 1.001)
    py = min(max(wy / 32.0 * H_TEX - 0.5, 0), H_TEX - 1.001)
    x0, y0 = int(px), int(py)
    fx, fy = px - x0, py - y0
    h = heights
    v = (h[y0, x0] * (1 - fx) * (1 - fy) + h[y0, x0 + 1] * fx * (1 - fy)
         + h[y0 + 1, x0] * (1 - fx) * fy + h[y0 + 1, x0 + 1] * fx * fy)
    return float(v) / 65535.0


def _tile_hash(r: int, c: int, k: int = 0) -> int:
    return ((r * 37 + c * 13 + k * 71 + 7) * 2654435761) & 0xFFFFFFFF


def _river_chains(grid: bytes) -> list:
    """Chain flagged tile edges into polylines over lattice points.

    A tile's west edge is the segment x=c from y=r to r+1, east is x=c+1,
    south is y=r+1. Adjacent tiles flagging the same physical line are
    deduplicated. Returns a list of point lists [(x, y), ...].
    """
    edges = set()
    for r in range(GRID):
        for c in range(GRID):
            v = grid[r * GRID + c]
            if v & 0x20:
                edges.add(((c, r), (c, r + 1)))
            if v & 0x40:
                edges.add(((c + 1, r), (c + 1, r + 1)))
            if v & 0x80:
                edges.add(((c, r + 1), (c + 1, r + 1)))

    adj = {}
    for a, b in edges:
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)

    unused = set(edges)
    chains = []
    # Prefer starting from endpoints (degree-1 nodes) for full runs
    starts = [n for n, ns in adj.items()
              if sum(1 for m in ns if _edge_free(unused, n, m)) == 1]
    for start in starts + list(adj.keys()):
        while any(_edge_free(unused, start, m) for m in adj.get(start, ())):
            chain = _walk_chain(start, adj, unused)
            if len(chain) > 1:
                chains.append([(float(x), float(y)) for x, y in chain])
    return chains


def _edge_free(unused: set, a, b) -> bool:
    return (a, b) in unused or (b, a) in unused


def _walk_chain(start, adj, unused) -> list:
    """One chain from `start`, preferring the straightest continuation."""
    chain = [start]
    cur, prev = start, None
    while True:
        cands = [m for m in adj.get(cur, ()) if _edge_free(unused, cur, m)]
        if not cands:
            return chain
        if prev is None:
            best = cands[0]
        else:
            dx0, dy0 = cur[0] - prev[0], cur[1] - prev[1]
            best = max(cands, key=lambda m: (
                (m[0] - cur[0]) * dx0 + (m[1] - cur[1]) * dy0))
        unused.discard((cur, best))
        unused.discard((best, cur))
        chain.append(best)
        prev, cur = cur, best


def _smooth_chain(pts: list, seed: int) -> list:
    """Jitter interior nodes, then Chaikin-smooth into a meander."""
    if len(pts) > 2:
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            px, py = pts[i - 1]
            nx_, ny_ = pts[i + 1]
            dx, dy = nx_ - px, ny_ - py
            ln = math.hypot(dx, dy) or 1.0
            h = _tile_hash(int(pts[i][1] * 7), int(pts[i][0] * 13), seed)
            amt = ((h % 200) / 100.0 - 1.0) * 0.14
            out.append((pts[i][0] + (-dy / ln) * amt,
                        pts[i][1] + (dx / ln) * amt))
        out.append(pts[-1])
        pts = out
    for _ in range(3):                     # Chaikin corner cutting
        if len(pts) < 3:
            break
        nxt = [pts[0]]
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            nxt.append((ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25))
            nxt.append((ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75))
        nxt.append(pts[-1])
        pts = nxt
    return pts


def _emit_ribbon(tris, pts, half_widths, heights, lift, u_scale=1.0):
    """Triangulate a ribbon along pts. Vertices: (x, y, z, u, v)."""
    prev = None
    u = 0.0
    for i, (cx, cy) in enumerate(pts):
        if i + 1 < len(pts):
            dx, dy = pts[i + 1][0] - cx, pts[i + 1][1] - cy
        else:
            dx, dy = cx - pts[i - 1][0], cy - pts[i - 1][1]
        ln = math.hypot(dx, dy) or 1.0
        nx_, ny_ = -dy / ln, dx / ln
        if i:
            u += math.hypot(cx - pts[i - 1][0], cy - pts[i - 1][1]) * u_scale
        w = half_widths[i]
        cz = _sample_height(heights, cx, cy) * HEIGHT_SCALE + lift
        cur = ((cx - nx_ * w, cy - ny_ * w, cz, u, 0.0),
               (cx + nx_ * w, cy + ny_ * w, cz, u, 1.0))
        if prev is not None:
            a, b = prev
            d, e = cur
            tris.extend([a, b, d, b, e, d])
        prev = cur


def _mouth_in_ocean(pt, grid) -> bool:
    """Does a chain endpoint touch an ocean tile?"""
    x, y = int(round(pt[0])), int(round(pt[1]))
    for dc, dr in ((0, 0), (-1, 0), (0, -1), (-1, -1)):
        c, r = x + dc, y + dr
        if 0 <= r < GRID and 0 <= c < GRID:
            if grid[r * GRID + c] & 0x07 == 0:
                return True
    return False


def _river_widths(n: int, h0: int, mouth0: bool, mouth1: bool) -> list:
    """Width envelope: thin source, breathing middle, widening mouth."""
    widths = []
    for i in range(n):
        t = i / max(1, n - 1)
        w = 0.065 * (0.85 + 0.3 * math.sin(t * math.pi * (2 + h0 % 3) + h0))
        if mouth1:
            w *= 1.0 + 1.1 * max(0.0, t - 0.82) / 0.18
        if mouth0:
            w *= 1.0 + 1.1 * max(0.0, 0.18 - t) / 0.18
        if not mouth0:
            w *= min(1.0, 0.45 + t * 2.2)
        if not mouth1:
            w *= min(1.0, 0.45 + (1 - t) * 2.2)
        widths.append(w)
    return widths


def _emit_braid(water, pts, heights):
    """Mid-run sandbar: split the channel around a lens-shaped island."""
    seg = pts[int(len(pts) * 0.38):int(len(pts) * 0.62)]
    if len(seg) < 2:
        return
    for side in (-1.0, 1.0):
        off_pts = []
        for j, (cx, cy) in enumerate(seg):
            k = j / max(1, len(seg) - 1)
            bulge = math.sin(k * math.pi) * 0.09
            if j + 1 < len(seg):
                dx, dy = seg[j + 1][0] - cx, seg[j + 1][1] - cy
            else:
                dx, dy = cx - seg[j - 1][0], cy - seg[j - 1][1]
            ln = math.hypot(dx, dy) or 1.0
            off_pts.append((cx - dy / ln * bulge * side,
                            cy + dx / ln * bulge * side))
        _emit_ribbon(water, off_pts, [0.05] * len(off_pts), heights, 0.078)


def _emit_delta(sand, water, end, prev, heights):
    """Curved two-channel delta fan at a beach-level ocean mouth."""
    if _sample_height(heights, *end) > WATER_NORM + 0.02:
        return                               # cliff mouth: no fan
    dx, dy = end[0] - prev[0], end[1] - prev[1]
    ln = math.hypot(dx, dy) or 1.0
    dx, dy = dx / ln, dy / ln
    for side in (-1.0, 1.0):
        fork = [end]
        fx, fy = dx, dy
        for _ in range(4):
            ang = side * 0.22                # curve outward gradually
            ca, sa = math.cos(ang), math.sin(ang)
            fx, fy = fx * ca - fy * sa, fx * sa + fy * ca
            lx, ly = fork[-1]
            fork.append((lx + fx * 0.14, ly + fy * 0.14))
        fw = [0.055, 0.045, 0.035, 0.025, 0.015]
        _emit_ribbon(sand, fork, [w * 1.9 + 0.035 for w in fw],
                     heights, 0.044)
        _emit_ribbon(water, fork, fw, heights, 0.074)


def build_river_geometry(grid: bytes, heights: np.ndarray) -> dict:
    """Game-style rivers: sand-bank halo under a cyan channel, smooth
    meanders, and braided deltas where a river meets the ocean.

    Returns {'sand': (N,5) float32, 'water': (M,5) float32}.
    """
    sand, water = [], []
    for ci, chain in enumerate(_river_chains(grid)):
        pts = _smooth_chain(chain, ci + 1)
        n = len(pts)
        if n < 2:
            continue
        h0 = _tile_hash(ci, len(chain), 5)
        mouth0 = _mouth_in_ocean(pts[0], grid)
        mouth1 = _mouth_in_ocean(pts[-1], grid)

        widths = _river_widths(n, h0, mouth0, mouth1)
        _emit_ribbon(sand, pts, [w * 1.9 + 0.045 for w in widths],
                     heights, 0.045)
        _emit_ribbon(water, pts, widths, heights, 0.075)

        if n >= 24 and (h0 >> 3) % 2 == 0:
            _emit_braid(water, pts, heights)
        if mouth1:
            _emit_delta(sand, water, pts[-1], pts[-2], heights)
        if mouth0:
            _emit_delta(sand, water, pts[0], pts[1], heights)

    def pack(v):
        if not v:
            return np.zeros((0, 5), dtype=np.float32)
        return np.array(v, dtype=np.float32)

    return {"sand": pack(sand), "water": pack(water)}


# Tier stacks per species: list of (scale, z offset in tile units)
_TIERS = {
    "pine": [(1.0, 0.05), (0.68, 0.15), (0.40, 0.25)],
    "broad": [(1.0, 0.06), (0.62, 0.15)],
    "palm": [(1.0, 0.30)],
}


def _emit_trunk(verts, tx, ty, gz, dia):
    """Crossed vertical bark quads under a palm canopy (atlas cell 7)."""
    top = gz + dia * 2.0 * _TIERS["palm"][0][1] + 0.02
    hw = dia * 0.16
    u0, v0, u1, v1 = _cell_uv(7)
    for ang in (0.0, math.pi / 2):
        dx, dy = math.cos(ang) * hw, math.sin(ang) * hw
        a = (tx - dx, ty - dy, gz - 0.02)
        b = (tx + dx, ty + dy, gz - 0.02)
        ta = (tx - dx, ty - dy, top)
        tb = (tx + dx, ty + dy, top)
        for p, (u, v) in ((a, (u0, v0)), (b, (u1, v0)), (ta, (u0, v1)),
                          (b, (u1, v0)), (tb, (u1, v1)), (ta, (u0, v1))):
            verts.append((*p, u, v, 0.9))


def _cell_uv(cell: int) -> tuple:
    u0 = (cell % 4) * 0.25
    v0 = (cell // 4) / ATLAS_ROWS
    return u0, v0, u0 + 0.25, v0 + 1.0 / ATLAS_ROWS


def _emit_canopy(verts, tx, ty, base_z, dia, cell, ang, shade):
    u0, v0, u1, v1 = _cell_uv(cell)
    ca, sa = math.cos(ang), math.sin(ang)
    s = dia / 2
    corners = []
    for dx, dy in ((-s, -s), (s, -s), (-s, s), (s, s)):
        corners.append((tx + dx * ca - dy * sa,
                        ty + dx * sa + dy * ca, base_z))
    a, b, d, e = corners
    for p, (u, v) in ((a, (u0, v0)), (b, (u1, v0)), (d, (u0, v1)),
                      (b, (u1, v0)), (e, (u1, v1)), (d, (u0, v1))):
        verts.append((*p, u, v, shade))


def _tree_species(band: float, hsh: int) -> tuple:
    """(species, [big cell, med cell]) for a latitude band."""
    if band <= 5.5:                            # warm: palms
        return "palm", [6, 6]
    if band > 10.5:                            # polar: snowy pines
        return "pine", [4, 5]
    if (hsh >> 5) & 1:
        return "pine", [0, 1]
    return "broad", [2, 3]


def _emit_tree(verts, tx, ty, big, band, hsh, heights):
    species, cells = _tree_species(band, hsh)
    cell = cells[0] if big else cells[1]
    dia = (0.36 + ((hsh >> 20) % 100) / 100.0 * 0.12 if big
           else 0.24 + ((hsh >> 20) % 100) / 100.0 * 0.08)
    if species == "palm":
        dia *= 0.8
    shade = 0.95 + ((hsh >> 8) % 100) / 100.0 * 0.28
    gz = _sample_height(heights, tx, ty) * HEIGHT_SCALE
    ang0 = ((hsh >> 3) % 628) / 100.0
    if species == "palm":
        _emit_trunk(verts, tx, ty, gz, dia)
    for ti, (scale, zoff) in enumerate(_TIERS[species]):
        _emit_canopy(verts, tx, ty, gz + zoff * (dia * 2.0),
                     dia * scale, cell, ang0 + ti * 0.9,
                     min(1.2, shade + ti * 0.08))


def build_tree_verts(grid: bytes, heights: np.ndarray) -> np.ndarray:
    """Stacked-tier canopy trees on forest tiles, like the game's models.

    Atlas cells (4x2): 0 pine-big, 1 pine-med, 2 broadleaf-big,
    3 broadleaf-med, 4 snowy-big, 5 snowy-med, 6 palm, 7 palm bark.
    (N,6): pos3 + uv2 + shade.
    """
    verts = []
    for r in range(GRID):
        for c in range(GRID):
            if grid[r * GRID + c] & 0x07 != FOREST:
                continue
            band = abs(r - 15.5)
            n = 7 + _tile_hash(r, c) % 3
            for k in range(n):
                hsh = _tile_hash(r, c, k + 1)
                tx = c + 0.10 + (hsh % 1000) / 1000.0 * 0.80
                ty = r + 0.10 + ((hsh >> 10) % 1000) / 1000.0 * 0.80
                _emit_tree(verts, tx, ty, k < 3, band, hsh, heights)
    if not verts:
        return np.zeros((0, 6), dtype=np.float32)
    return np.array(verts, dtype=np.float32)


def _emit_upright(verts, tx, ty, gz, width, height, cell, shade):
    """Crossed vertical quads (tufts, flags)."""
    u0, v0, u1, v1 = _cell_uv(cell)
    hw = width / 2
    for ang in (0.0, math.pi / 2):
        dx, dy = math.cos(ang) * hw, math.sin(ang) * hw
        a = (tx - dx, ty - dy, gz - 0.01)
        b = (tx + dx, ty + dy, gz - 0.01)
        ta = (tx - dx, ty - dy, gz + height)
        tb = (tx + dx, ty + dy, gz + height)
        for p, (u, v) in ((a, (u0, v0)), (b, (u1, v0)), (ta, (u0, v1)),
                          (b, (u1, v0)), (tb, (u1, v1)), (ta, (u0, v1))):
            verts.append((*p, u, v, shade))


def _emit_rocks(verts, r, c, hsh, water_z):
    for k in range(1 + hsh % 3):
        h2 = _tile_hash(r, c, 10 + k)
        px = c + 0.15 + (h2 % 1000) / 1000.0 * 0.7
        py = r + 0.15 + ((h2 >> 10) % 1000) / 1000.0 * 0.7
        size = 0.05 + ((h2 >> 20) % 100) / 100.0 * 0.05
        _emit_canopy(verts, px, py, water_z + 0.012,
                     size, 8, (h2 % 62) / 10.0, 1.0)


def _emit_tufts(verts, r, c, t, hsh, heights, water_z):
    for k in range(3 + hsh % 4):
        h2 = _tile_hash(r, c, 20 + k)
        px = c + 0.08 + (h2 % 1000) / 1000.0 * 0.84
        py = r + 0.08 + ((h2 >> 10) % 1000) / 1000.0 * 0.84
        gz = _sample_height(heights, px, py) * HEIGHT_SCALE
        if gz < water_z:
            continue
        shade = 0.9 if t == 1 else 1.1                 # olive on plains
        _emit_upright(verts, px, py, gz, 0.07, 0.075, 9, shade)


def build_prop_verts(grid: bytes, heights: np.ndarray) -> np.ndarray:
    """Map-data props: shore rocks, grass tufts, spawn-marker flags.

    Rocks scatter in coastal shallows and tufts on grass/plains like the
    game's ambient decals (positions are deterministic per tile, not the
    game's exact runtime scatter). Flags mark the map's 0x10 spawn bits —
    real landmarks for lining the view up with the editor.
    """
    verts = []
    water_z = WATER_NORM * HEIGHT_SCALE

    def land(r, c):
        return (0 <= r < GRID and 0 <= c < GRID
                and grid[r * GRID + c] & 0x07 not in (0, 7))

    for r in range(GRID):
        for c in range(GRID):
            v = grid[r * GRID + c]
            t = v & 0x07
            hsh = _tile_hash(r, c, 9)
            if t == 0 and any(land(r + dr, c + dc)
                              for dr, dc in ((1, 0), (-1, 0), (0, 1),
                                             (0, -1))):
                _emit_rocks(verts, r, c, hsh, water_z)
            elif t in (1, 2):
                _emit_tufts(verts, r, c, t, hsh, heights, water_z)
            if v & 0x10:                               # spawn-marker flag
                gz = _sample_height(heights, c + 0.5, r + 0.5) * HEIGHT_SCALE
                gz = max(gz, water_z)
                _emit_upright(verts, c + 0.5, r + 0.5, gz, 0.30, 0.48, 10,
                              1.0)
    if not verts:
        return np.zeros((0, 6), dtype=np.float32)
    return np.array(verts, dtype=np.float32)


def build_grid_lines(heights: np.ndarray) -> dict:
    """Draped tile-boundary lines. Every 4th line is emphasized so tiles
    can be counted when matching a view against the game."""
    minor, major = [], []
    for i in range(GRID + 1):
        for vertical in (True, False):
            pts = []
            for s in range(GRID * 2 + 1):
                t = s / 2.0
                x, y = (float(i), t) if vertical else (t, float(i))
                pts.append((x, y))
            target = major if i % 4 == 0 else minor
            _emit_ribbon(target, pts, [0.013] * len(pts), heights, 0.03)
    return {"minor": np.array(minor, dtype=np.float32),
            "major": np.array(major, dtype=np.float32)}


def build_marker_verts(row: int, col: int, heights: np.ndarray) -> np.ndarray:
    """Bright border ribbon around one tile (the tile selected in Design)."""
    verts = []
    ring = [(float(col), float(row)), (col + 1.0, float(row)),
            (col + 1.0, row + 1.0), (float(col), row + 1.0),
            (float(col), float(row))]
    dense = []
    for i in range(len(ring) - 1):
        for s in range(9):
            t = s / 8.0
            dense.append((ring[i][0] + (ring[i + 1][0] - ring[i][0]) * t,
                          ring[i][1] + (ring[i + 1][1] - ring[i][1]) * t))
    _emit_ribbon(verts, dense, [0.035] * len(dense), heights, 0.09)
    return np.array(verts, dtype=np.float32)


def build_skirt_verts(heights: np.ndarray) -> np.ndarray:
    """Dark side walls around the map so edges don't show through."""
    tris = []
    bottom = -0.6
    step = 32.0 / (H_TEX - 1)

    def wall(points):
        for i in range(len(points) - 1):
            x0, y0, z0 = points[i]
            x1, y1, z1 = points[i + 1]
            tris.extend([
                (x0, y0, z0), (x1, y1, z1), (x0, y0, bottom),
                (x1, y1, z1), (x1, y1, bottom), (x0, y0, bottom),
            ])

    hs = heights.astype(np.float32) / 65535.0 * HEIGHT_SCALE
    n = H_TEX
    edges = [
        [(i * step, 0.0, hs[0, i]) for i in range(n)],
        [(i * step, 32.0, hs[n - 1, i]) for i in range(n)],
        [(0.0, i * step, hs[i, 0]) for i in range(n)],
        [(32.0, i * step, hs[i, n - 1]) for i in range(n)],
    ]
    for e in edges:
        wall(e[::8])                # coarse walls are fine
    return np.array(tris, dtype=np.float32)


def _decode_level_rgba(name: str) -> np.ndarray:
    """Decode a Level DDS (DXT1 + 1-bit alpha) to (H,W,4) uint8."""
    import texgen

    raw = (LEVEL_DIR / name).read_bytes()
    w = struct.unpack_from("<I", raw, 16)[0]
    h = struct.unpack_from("<I", raw, 12)[0]
    blocks = np.frombuffer(raw, dtype=np.uint8, offset=128,
                           count=(w // 4) * (h // 4) * 8)
    return texgen.decode_dxt1_rgba(blocks.reshape(h // 4, w // 4, 8))


# Canopy sprite crops (x0, y0, x1, y1), centered on each canopy
_CANOPY_CROPS = [
    ("pinebranch.dds", (7, 57, 337, 387)),          # 0 pine big
    ("pinebranch.dds", (290, 12, 500, 212)),        # 1 pine med
    ("tree_temperate_diff.dds", (10, 288, 230, 504)),  # 2 temperate big
    ("tree_temperate_diff.dds", (237, 282, 457, 502)), # 3 temperate med
    ("pinebranchsnowy.dds", (7, 57, 337, 387)),     # 4 snowy big
    ("pinebranchsnowy.dds", (290, 12, 500, 212)),   # 5 snowy med
]


def _compose_palm_star() -> np.ndarray:
    """Radial palm canopy composed from the game's frond sprite."""
    from PIL import Image, ImageDraw

    palm = _decode_level_rgba("palm_tree_dds".replace("dds", "diff.dds"))
    frond = Image.fromarray(palm[140:196, 0:208])       # one frond
    canvas = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
    # Two layered rings of wide fronds for a full canopy
    for ring, (count, size, off) in enumerate(
            [(9, (118, 52), 0), (7, (86, 40), 20)]):
        fr = frond.resize(size)
        for i in range(count):
            layer = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
            layer.paste(fr, (118 - 6, 118 - size[1] // 2), fr)
            layer = layer.rotate(i * (360 / count) + off + ring * 8,
                                 center=(118, 118))
            canvas = Image.alpha_composite(canvas, layer)
    d = ImageDraw.Draw(canvas)
    d.ellipse([108, 108, 128, 128], fill=(96, 72, 44, 255))
    return np.asarray(canvas, dtype=np.uint8)


ATLAS_ROWS = 3


def _draw_rock_sprite() -> np.ndarray:
    """Shore-rock cluster sprite (236,236,4)."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    stones = [(70, 120, 60, 42, (225, 222, 212)),
              (130, 95, 48, 36, (238, 236, 228)),
              (150, 150, 38, 30, (214, 210, 198)),
              (95, 165, 30, 24, (230, 226, 216))]
    for cx, cy, rx, ry, col in stones:
        d.ellipse([cx - rx + 5, cy - ry + 6, cx + rx + 5, cy + ry + 6],
                  fill=(90, 100, 115, 110))          # soft shadow
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col + (255,))
        d.ellipse([cx - rx, cy - ry, cx + int(rx * 0.4), cy + int(ry * 0.4)],
                  fill=(250, 250, 246, 90))
    return np.asarray(img, dtype=np.uint8)


def _draw_tuft_sprite() -> np.ndarray:
    """Upright grass-tuft sprite (236,236,4), base at v=0."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    base_y = 230
    for i, (dx, h, w) in enumerate([(-60, 130, 16), (-30, 170, 18),
                                    (0, 200, 20), (30, 175, 18),
                                    (60, 135, 16), (-90, 100, 13),
                                    (90, 105, 13)]):
        col = (46, 110, 44, 255) if i % 2 else (64, 134, 52, 255)
        tip_x = 118 + dx + (8 if dx >= 0 else -8)
        d.polygon([(118 + dx - w, base_y), (118 + dx + w, base_y),
                   (tip_x, base_y - h)], fill=col)
    return np.asarray(img, dtype=np.uint8)[::-1].copy()


def _draw_flag_sprite() -> np.ndarray:
    """Spawn-marker flag sprite (236,236,4), pole base at v=0."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([112, 20, 124, 236], fill=(70, 58, 40, 255))       # pole
    d.polygon([(124, 24), (216, 52), (124, 84)],
              fill=(255, 204, 0, 255))                              # banner
    d.polygon([(124, 30), (196, 52), (124, 76)], fill=(255, 232, 90, 255))
    return np.asarray(img, dtype=np.uint8)[::-1].copy()


def make_tree_texture() -> np.ndarray:
    """Sprite atlas (768,1024,4): trees, palms, and map props.

    Row-major 256px cells: 0-5 canopies, 6 palm, 7 palm bark,
    8 shore rocks, 9 grass tuft, 10 spawn flag.
    """
    from PIL import Image

    atlas = np.zeros((256 * ATLAS_ROWS, 1024, 4), dtype=np.uint8)
    atlas[522:758, 10:246] = _draw_rock_sprite()      # cell 8
    atlas[522:758, 266:502] = _draw_tuft_sprite()     # cell 9
    atlas[522:758, 522:758] = _draw_flag_sprite()     # cell 10
    try:
        yy, xx = np.mgrid[0:236, 0:236].astype(np.float32)
        rad = np.hypot(xx - 117.5, yy - 117.5) / 118.0
        radial = np.clip((0.95 - rad) / 0.15, 0.0, 1.0)  # soft edge cutoff

        decoded = {}
        for i, (src, (x0, y0, x1, y1)) in enumerate(_CANOPY_CROPS):
            if src not in decoded:
                decoded[src] = _decode_level_rgba(src)
            crop = decoded[src][y0:y1, x0:x1]
            img = np.asarray(
                Image.fromarray(crop).resize((236, 236), Image.LANCZOS)
            ).copy()
            img[:, :, 3] = (img[:, :, 3].astype(np.float32) * radial
                            ).astype(np.uint8)
            cx = (i % 4) * 256 + 10
            cy = (i // 4) * 256 + 10
            atlas[cy:cy + 236, cx:cx + 236] = img

        # Cell 6: palm star composed from the frond sprite
        star = _compose_palm_star()
        atlas[266:502, 522:758] = star
        # Cell 7: palm bark for trunks (opaque strip from the same sheet)
        bark = decoded.get("palm_tree_diff.dds")
        if bark is None:
            bark = _decode_level_rgba("palm_tree_diff.dds")
        strip = np.asarray(Image.fromarray(
            bark[64:188, 208:250]).resize((236, 236))).astype(np.float32)
        strip[:, :, :3] *= np.array([0.72, 0.58, 0.42]) * 1.35
        atlas[266:502, 778:1014] = np.clip(strip, 0, 255).astype(np.uint8)
    except OSError:
        from PIL import ImageDraw

        img = Image.new("RGBA", (236, 236), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([20, 20, 216, 216], fill=(30, 86, 46, 255))
        for i in range(8):
            cy = (i // 4) * 256 + 10
            atlas[cy:cy + 236, (i % 4) * 256 + 10:(i % 4) * 256 + 246] = \
                np.asarray(img)
    return atlas


def load_detail_texture() -> tuple:
    """First mip of the game's Hills1.dds rock detail (DXT1)."""
    path = LEVEL_DIR / "hills1.dds"
    if not path.exists():
        return None, 0
    raw = path.read_bytes()
    w = struct.unpack_from("<I", raw, 16)[0]
    h = struct.unpack_from("<I", raw, 12)[0]
    size = (w // 4) * (h // 4) * 8
    return raw[128:128 + size], w


# ── Renderer core (shared by widget and offscreen harness) ──────────────


class SceneRenderer:
    def __init__(self):
        self.f = None
        self.vao = None
        self.scene: SceneData | None = None
        self._scene_dirty = False
        self._gl_ready = False
        self.programs = {}
        self.textures = {}
        self.buffers = {}
        self.counts = {"terrain": 0, "river_sand": 0, "river_water": 0,
                       "tree": 0, "skirt": 0, "water": 6, "prop": 0,
                       "grid_minor": 0, "grid_major": 0, "marker": 0}
        self.show_grid3d = False
        self.marker = None            # (row, col) selected in the editor
        self._marker_dirty = False
        # Camera — defaults match the game's close-in view
        self.yaw = 0.0
        self.pitch = 46.0
        self.dist = 11.0
        self.target = QVector3D(16.0, 17.0, 0.55)
        self._eye_xy = (16.0, 40.0)

    # ── Setup ───────────────────────────────────────────────

    def initialize(self, ctx: QOpenGLContext):
        vp = QOpenGLVersionProfile()
        vp.setVersion(4, 1)
        vp.setProfile(QSurfaceFormat.CoreProfile)
        self.f = ctx.versionFunctions(vp)
        if self.f is None:
            raise RuntimeError(
                "OpenGL 4.1 core functions unavailable "
                f"(context {ctx.format().majorVersion()}."
                f"{ctx.format().minorVersion()})")
        self.f.initializeOpenGLFunctions()
        self.vao = QOpenGLVertexArrayObject()
        self.vao.create()
        self.vao.bind()

        self.programs["terrain"] = self._program(TERRAIN_VS, TERRAIN_FS)
        self.programs["flat"] = self._program(FLAT_VS, FLAT_FS)
        self.programs["tree"] = self._program(TREE_VS, TREE_FS)
        self.programs["water"] = self._program(WATER_VS, WATER_FS)
        self.programs["river"] = self._program(RIVER_VS, RIVER_FS)

        self._build_terrain_grid()
        self._make_water()
        self._make_tree_texture()
        self._make_detail_texture()
        self._gl_ready = True
        if self.scene is not None:
            self._scene_dirty = True

    def _program(self, vs, fs) -> QOpenGLShaderProgram:
        prog = QOpenGLShaderProgram()
        if not prog.addShaderFromSourceCode(QOpenGLShader.Vertex, vs):
            raise RuntimeError("vertex shader: " + prog.log())
        if not prog.addShaderFromSourceCode(QOpenGLShader.Fragment, fs):
            raise RuntimeError("fragment shader: " + prog.log())
        if not prog.link():
            raise RuntimeError("link: " + prog.log())
        return prog

    def _vbo(self, name: str, data: np.ndarray) -> QOpenGLBuffer:
        buf = self.buffers.get(name)
        if buf is None:
            buf = QOpenGLBuffer(QOpenGLBuffer.VertexBuffer)
            buf.create()
            self.buffers[name] = buf
        buf.bind()
        buf.allocate(data.tobytes(), data.nbytes)
        return buf

    def _build_terrain_grid(self):
        n = H_TEX
        step = 32.0 / (n - 1)
        xs = np.arange(n, dtype=np.float32) * step
        xy = np.stack(np.meshgrid(xs, xs), axis=-1)          # (n,n,2) x,y
        self._vbo("terrain", xy.reshape(-1, 2))

        idx = np.arange(n * n, dtype=np.uint32).reshape(n, n)
        a = idx[:-1, :-1].ravel()
        b = idx[:-1, 1:].ravel()
        c = idx[1:, :-1].ravel()
        d = idx[1:, 1:].ravel()
        tris = np.stack([a, b, c, b, d, c], axis=1).ravel()
        ibo = QOpenGLBuffer(QOpenGLBuffer.IndexBuffer)
        ibo.create()
        ibo.bind()
        ibo.allocate(tris.tobytes(), tris.nbytes)
        self.buffers["terrain_idx"] = ibo
        self.counts["terrain"] = len(tris)

    def _make_water(self):
        # Tessellated so per-vertex world curvature tracks the terrain's
        z = WATER_NORM * HEIGHT_SCALE
        lo, hi, n = -8.0, 40.0, 48
        xs = np.linspace(lo, hi, n + 1, dtype=np.float32)
        tris = []
        for j in range(n):
            for i in range(n):
                x0, x1 = xs[i], xs[i + 1]
                y0, y1 = xs[j], xs[j + 1]
                tris.extend([
                    (x0, y0, z), (x1, y0, z), (x0, y1, z),
                    (x1, y0, z), (x1, y1, z), (x0, y1, z),
                ])
        quad = np.array(tris, dtype=np.float32)
        self._vbo("water", quad)
        self.counts["water"] = len(quad)

    def _make_tree_texture(self):
        arr = make_tree_texture()
        tex = QOpenGLTexture(QOpenGLTexture.Target2D)
        tex.setFormat(QOpenGLTexture.RGBA8_UNorm)
        tex.setSize(arr.shape[1], arr.shape[0])
        tex.setMipLevels(1)
        tex.allocateStorage()
        tex.setData(QOpenGLTexture.RGBA, QOpenGLTexture.UInt8, arr.tobytes())
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)
        self.textures["tree"] = tex

    def _make_detail_texture(self):
        payload, w = load_detail_texture()
        tex = QOpenGLTexture(QOpenGLTexture.Target2D)
        if payload:
            tex.setFormat(QOpenGLTexture.RGB_DXT1)
            tex.setSize(w, w)
            tex.setMipLevels(1)
            tex.allocateStorage()
            tex.setCompressedData(0, len(payload), payload)
        else:                        # neutral gray fallback
            tex.setFormat(QOpenGLTexture.RGBA8_UNorm)
            tex.setSize(1, 1)
            tex.setMipLevels(1)
            tex.allocateStorage()
            tex.setData(QOpenGLTexture.RGBA, QOpenGLTexture.UInt8,
                        bytes([128, 128, 128, 255]))
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.Repeat)
        self.textures["detail"] = tex

    # ── Scene upload ────────────────────────────────────────

    def set_scene(self, scene: SceneData):
        self.scene = scene
        self._scene_dirty = True

    def set_marker(self, row, col):
        self.marker = None if row is None else (row, col)
        self._marker_dirty = True

    def _texture(self, name: str) -> QOpenGLTexture:
        old = self.textures.pop(name, None)
        if old is not None:
            old.destroy()
        tex = QOpenGLTexture(QOpenGLTexture.Target2D)
        self.textures[name] = tex
        return tex

    def _apply_scene(self):
        s = self.scene
        self._scene_dirty = False

        tex = self._texture("heights")
        tex.setFormat(QOpenGLTexture.R16_UNorm)
        tex.setSize(H_TEX, H_TEX)
        tex.setMipLevels(1)
        tex.allocateStorage(QOpenGLTexture.Red, QOpenGLTexture.UInt16)
        tex.setData(QOpenGLTexture.Red, QOpenGLTexture.UInt16,
                    np.ascontiguousarray(s.heights).tobytes())
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)

        tex = self._texture("light")
        if s.light_dxt1 is not None:
            tex.setFormat(QOpenGLTexture.RGB_DXT1)
            tex.setSize(4096, 4096)
            tex.setMipLevels(1)
            tex.allocateStorage()
            tex.setCompressedData(0, len(s.light_dxt1), s.light_dxt1)
        else:
            rgb = np.ascontiguousarray(s.light_rgb)
            tex.setFormat(QOpenGLTexture.RGB8_UNorm)
            tex.setSize(rgb.shape[1], rgb.shape[0])
            tex.setMipLevels(1)
            tex.allocateStorage()
            tex.setData(QOpenGLTexture.RGB, QOpenGLTexture.UInt8, rgb.tobytes())
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)

        tex = self._texture("blend")
        tex.setFormat(QOpenGLTexture.RGB_DXT1)
        tex.setSize(2048, 2048)
        tex.setMipLevels(1)
        tex.allocateStorage()
        tex.setCompressedData(0, len(s.blend_dxt1), s.blend_dxt1)
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)

        veg = s.veg if s.veg is not None else build_vegetation_overlay(s.grid)
        veg = np.ascontiguousarray(veg)
        tex = self._texture("veg")
        tex.setFormat(QOpenGLTexture.RGBA8_UNorm)
        tex.setSize(veg.shape[1], veg.shape[0])
        tex.setMipLevels(1)
        tex.allocateStorage()
        tex.setData(QOpenGLTexture.RGBA, QOpenGLTexture.UInt8, veg.tobytes())
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)

        rivers = build_river_geometry(s.grid, s.heights)
        self._vbo("river_sand", rivers["sand"])
        self._vbo("river_water", rivers["water"])
        self.counts["river_sand"] = len(rivers["sand"])
        self.counts["river_water"] = len(rivers["water"])

        trees = build_tree_verts(s.grid, s.heights)
        self._vbo("tree", trees)
        self.counts["tree"] = len(trees)

        skirt = build_skirt_verts(s.heights)
        self._vbo("skirt", skirt)
        self.counts["skirt"] = len(skirt)

        props = build_prop_verts(s.grid, s.heights)
        self._vbo("prop", props)
        self.counts["prop"] = len(props)

        lines = build_grid_lines(s.heights)
        self._vbo("grid_minor", lines["minor"])
        self._vbo("grid_major", lines["major"])
        self.counts["grid_minor"] = len(lines["minor"])
        self.counts["grid_major"] = len(lines["major"])
        self._marker_dirty = True

    # ── Camera ──────────────────────────────────────────────

    def mvp(self, w: int, h: int) -> QMatrix4x4:
        aspect = w / max(1, h)
        proj = QMatrix4x4()
        proj.perspective(46.0, aspect, 0.3, 400.0)
        # World is col->+x, row->+y with z up (left-handed): mirror view-x
        # so the map reads like the game and the 2D canvas (east = right)
        proj.scale(-1.0, 1.0, 1.0)
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = self.target + QVector3D(
            math.sin(yaw) * math.cos(pitch) * self.dist,
            math.cos(yaw) * math.cos(pitch) * self.dist,
            math.sin(pitch) * self.dist,
        )
        self._eye_xy = (eye.x(), eye.y())
        view = QMatrix4x4()
        view.lookAt(eye, self.target, QVector3D(0, 0, 1))
        return proj * view

    def _set_common(self, prog, mvp):
        prog.setUniformValue("uMvp", mvp)
        prog.setUniformValue("uEye", float(self._eye_xy[0]),
                             float(self._eye_xy[1]))
        prog.setUniformValue("uCurve", float(CURVE))

    def orbit(self, dx: float, dy: float):
        self.yaw = (self.yaw + dx * 0.4) % 360
        self.pitch = min(88.0, max(15.0, self.pitch + dy * 0.3))

    def pan(self, dx: float, dy: float):
        yaw = math.radians(self.yaw)
        scale = self.dist * 0.0016
        rx = QVector3D(math.cos(yaw), -math.sin(yaw), 0) * (dx * scale)
        ry = QVector3D(math.sin(yaw), math.cos(yaw), 0) * (dy * scale)
        self.target += rx + ry
        self.target.setX(min(34.0, max(-2.0, self.target.x())))
        self.target.setY(min(34.0, max(-2.0, self.target.y())))

    def zoom(self, factor: float):
        # The game's zoom range is narrow (~4-12 tiles); allow a bit more
        # headroom for editing overview but keep the close-in feel
        self.dist = min(45.0, max(3.5, self.dist * factor))

    # ── Drawing ─────────────────────────────────────────────

    def _refresh_pending(self):
        if self._scene_dirty and self.scene is not None:
            self._apply_scene()
        if self._marker_dirty and self.scene is not None:
            self._marker_dirty = False
            if self.marker is not None:
                mk = build_marker_verts(self.marker[0], self.marker[1],
                                        self.scene.heights)
                self._vbo("marker", mk)
                self.counts["marker"] = len(mk)
            else:
                self.counts["marker"] = 0

    def _draw_rivers(self, f, mvp):
        if not (self.counts.get("river_water")
                or self.counts.get("river_sand")):
            return
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        rp = self.programs["river"]
        rp.bind()
        self._set_common(rp, mvp)
        stride = 5 * 4
        for kind, buf in ((0, "river_sand"), (1, "river_water")):
            if not self.counts.get(buf):
                continue
            rp.setUniformValue("uKind", kind)
            self.buffers[buf].bind()
            rp.enableAttributeArray("pos")
            rp.setAttributeBuffer("pos", GL_FLOAT, 0, 3, stride)
            rp.enableAttributeArray("uv")
            rp.setAttributeBuffer("uv", GL_FLOAT, 3 * 4, 2, stride)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts[buf])
        f.glDisable(GL_BLEND)

    def render(self, w: int, h: int):
        f = self.f
        self._refresh_pending()

        f.glViewport(0, 0, w, h)
        f.glClearColor(*SKY, 1.0)
        f.glEnable(GL_DEPTH_TEST)
        f.glDisable(GL_CULL_FACE)
        f.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self.scene is None or "heights" not in self.textures:
            return
        self.vao.bind()
        mvp = self.mvp(w, h)

        # Terrain
        prog = self.programs["terrain"]
        prog.bind()
        self._set_common(prog, mvp)
        prog.setUniformValue("uHScale", float(HEIGHT_SCALE))
        prog.setUniformValue("uLightDir", QVector3D(-0.45, -0.55, 0.75))
        for unit, (name, uni) in enumerate(
                [("heights", "uHeights"), ("light", "uLight"),
                 ("blend", "uBlend"), ("detail", "uDetail"),
                 ("veg", "uVeg")]):
            self.textures[name].bind(unit)
            prog.setUniformValue(uni, unit)
        self.buffers["terrain"].bind()
        prog.enableAttributeArray("xy")
        prog.setAttributeBuffer("xy", GL_FLOAT, 0, 2)
        self.buffers["terrain_idx"].bind()
        f.glDrawElements(GL_TRIANGLES, self.counts["terrain"],
                         GL_UNSIGNED_INT, None)
        self.buffers["terrain_idx"].release()

        # Skirt walls (fall away into the blue backdrop)
        flat = self.programs["flat"]
        flat.bind()
        self._set_common(flat, mvp)
        flat.setUniformValue("uColor", 0.16, 0.30, 0.58, 1.0)
        if self.counts["skirt"]:
            self.buffers["skirt"].bind()
            flat.enableAttributeArray("pos")
            flat.setAttributeBuffer("pos", GL_FLOAT, 0, 3)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts["skirt"])

        # Rivers: sand-bank halo, then the cyan channel over it
        self._draw_rivers(f, mvp)

        # Tile grid overlay (draped, counting-friendly)
        if self.show_grid3d:
            self._draw_grid(f, flat, mvp)

        # Trees
        self._draw_sprites(f, mvp, "tree")

        # Water (blue glass over the painted seafloor)
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        wp = self.programs["water"]
        wp.bind()
        self._set_common(wp, mvp)
        wp.setUniformValue("uWaterNorm", float(WATER_NORM))
        self.textures["heights"].bind(0)
        wp.setUniformValue("uHeights", 0)
        self.textures["light"].bind(1)
        wp.setUniformValue("uLight", 1)
        self.buffers["water"].bind()
        wp.enableAttributeArray("pos")
        wp.setAttributeBuffer("pos", GL_FLOAT, 0, 3)
        f.glDrawArrays(GL_TRIANGLES, 0, self.counts["water"])
        f.glDisable(GL_BLEND)

        # Props: shore rocks, tufts, spawn flags (crisp above the water)
        self._draw_sprites(f, mvp, "prop")

        # Selected-tile beacon (always on top of terrain)
        if self.counts.get("marker"):
            f.glEnable(GL_BLEND)
            f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            flat.bind()
            self._set_common(flat, mvp)
            flat.setUniformValue("uColor", 1.0, 0.92, 0.25, 0.95)
            self.buffers["marker"].bind()
            flat.enableAttributeArray("pos")
            flat.setAttributeBuffer("pos", GL_FLOAT, 0, 3, 5 * 4)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts["marker"])
            f.glDisable(GL_BLEND)

    def _draw_grid(self, f, flat, mvp):
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        flat.bind()
        self._set_common(flat, mvp)
        for buf, col in (("grid_minor", (0.05, 0.08, 0.12, 0.30)),
                         ("grid_major", (0.98, 0.98, 1.0, 0.42))):
            if not self.counts.get(buf):
                continue
            flat.setUniformValue("uColor", *col)
            self.buffers[buf].bind()
            flat.enableAttributeArray("pos")
            flat.setAttributeBuffer("pos", GL_FLOAT, 0, 3, 5 * 4)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts[buf])
        f.glDisable(GL_BLEND)

    def _draw_sprites(self, f, mvp, buf_name):
        if not self.counts.get(buf_name):
            return
        tp = self.programs["tree"]
        tp.bind()
        self._set_common(tp, mvp)
        self.textures["tree"].bind(0)
        tp.setUniformValue("uTex", 0)
        self.buffers[buf_name].bind()
        stride = 6 * 4
        tp.enableAttributeArray("pos")
        tp.setAttributeBuffer("pos", GL_FLOAT, 0, 3, stride)
        tp.enableAttributeArray("uv")
        tp.setAttributeBuffer("uv", GL_FLOAT, 3 * 4, 2, stride)
        tp.enableAttributeArray("shade")
        tp.setAttributeBuffer("shade", GL_FLOAT, 5 * 4, 1, stride)
        f.glDrawArrays(GL_TRIANGLES, 0, self.counts[buf_name])


# ── Interactive widget ──────────────────────────────────────────────────


class Preview3DWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFormat(default_surface_format())
        self.renderer = SceneRenderer()
        self.gl_error = None
        self._last_pos = QPoint()
        self.setMinimumSize(QSize(400, 300))
        self.setFocusPolicy(Qt.StrongFocus)

    def set_scene(self, scene: SceneData):
        self.renderer.set_scene(scene)
        self.update()

    def set_marker(self, row, col):
        self.renderer.set_marker(row, col)
        self.update()

    def set_grid_visible(self, on: bool):
        self.renderer.show_grid3d = on
        self.update()

    def reset_camera(self):
        r = self.renderer
        r.yaw, r.pitch, r.dist = 0.0, 46.0, 11.0
        r.target = QVector3D(16.0, 17.0, 0.55)
        self.update()

    def initializeGL(self):
        try:
            self.renderer.initialize(self.context())
        except RuntimeError as e:
            self.gl_error = str(e)

    def paintGL(self):
        if self.gl_error:
            return
        ratio = self.devicePixelRatioF()
        self.renderer.render(int(self.width() * ratio),
                             int(self.height() * ratio))

    def mousePressEvent(self, event):
        self._last_pos = event.pos()

    def mouseMoveEvent(self, event):
        d = event.pos() - self._last_pos
        self._last_pos = event.pos()
        if event.buttons() & Qt.LeftButton and not (
                event.modifiers() & Qt.ShiftModifier):
            self.renderer.orbit(d.x(), d.y())
        elif event.buttons() & (Qt.MiddleButton | Qt.RightButton) or (
                event.buttons() & Qt.LeftButton):
            self.renderer.pan(d.x() * self.renderer.dist,
                              d.y() * self.renderer.dist)
        self.update()

    def wheelEvent(self, event):
        self.renderer.zoom(0.88 if event.angleDelta().y() > 0 else 1.14)
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.reset_camera()


# ── Headless render harness (tests) ─────────────────────────────────────


def render_offscreen(scene: SceneData, width: int, height: int,
                     yaw=0.0, pitch=54.0, dist=30.0) -> QImage:
    """Render a scene to a QImage without a window (needs a QApplication)."""
    ctx = QOpenGLContext()
    ctx.setFormat(default_surface_format())
    if not ctx.create():
        raise RuntimeError("no GL context")
    surf = QOffscreenSurface()
    surf.setFormat(default_surface_format())
    surf.create()
    if not ctx.makeCurrent(surf):
        raise RuntimeError("makeCurrent failed")

    renderer = SceneRenderer()
    renderer.initialize(ctx)
    renderer.set_scene(scene)
    renderer.yaw, renderer.pitch, renderer.dist = yaw, pitch, dist

    fmt = QOpenGLFramebufferObjectFormat()
    fmt.setAttachment(QOpenGLFramebufferObject.Depth)
    fmt.setSamples(4)
    fbo = QOpenGLFramebufferObject(QSize(width, height), fmt)
    fbo.bind()
    renderer.render(width, height)
    img = fbo.toImage()
    fbo.release()
    ctx.doneCurrent()
    return img
