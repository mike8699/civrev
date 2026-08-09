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
HEIGHT_SCALE = 3.6           # world units per full 16-bit height range
WATER_NORM = 0.335           # sea level in normalized height
SKY = (0.043, 0.075, 0.11)

LEVEL_DIR = Path(__file__).resolve().parent.parent / "Level"


@dataclass
class SceneData:
    """Everything the renderer needs. Texture payloads are DDS-exact."""

    heights: np.ndarray            # (512,512) uint16
    light_dxt1: bytes | None       # 4096x4096 DXT1 payload (no header)
    light_rgb: np.ndarray | None   # fallback (4096,4096,3) uint8
    blend_dxt1: bytes              # 2048x2048 DXT1 payload
    grid: bytes                    # 1024 display-order tile bytes
    albedo: np.ndarray | None = None   # (2048,2048,3) uint8 ground colors


# ── Ground albedo (game-style: tiled Level/ terrain textures) ───────────

ALBEDO_SIZE = 2048                 # 64 px per tile
_CELL = ALBEDO_SIZE // GRID

# terrain type -> (warm, temperate, cold) Level texture names
_BAND_TEX = {
    1: ("grass_warm.dds", "grass_temperate.dds", "grass_cold.dds"),
    2: ("plains_warm.dds", "plains_temperate.dds", "plains_cold.dds"),
    5: ("desert_warm.dds", "desert_temperate.dds", "desert_cold.dds"),
}
_FIXED_TEX = {
    0: "ocean.dds",
    3: "mountain2.dds",            # Hills use the rocky ground texture
    6: "hills1.dds",               # Mountains (blends overlay adds rock)
    7: "snow.dds",
}

_tiled_cache: dict = {}


def _load_level_tile(name: str) -> np.ndarray:
    """(64,64,3) float32 from a Level DDS first mip."""
    import texgen
    from PIL import Image

    path = LEVEL_DIR / name
    raw = path.read_bytes()
    w = struct.unpack_from("<I", raw, 16)[0]
    h = struct.unpack_from("<I", raw, 12)[0]
    blocks = np.frombuffer(raw, dtype=np.uint8, offset=128,
                           count=(w // 4) * (h // 4) * 8)
    rgb = texgen.decode_dxt1(blocks.reshape(h // 4, w // 4, 8))
    img = Image.fromarray(rgb, "RGB").resize((_CELL, _CELL), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32)
    # Flatten strong features toward the mean so per-tile repetition
    # doesn't read as a lattice at map scale
    mean = arr.reshape(-1, 3).mean(axis=0)
    return mean + (arr - mean) * 0.55


def _tiled(choice: str, dark: float = 1.0) -> np.ndarray:
    """Full-map (2048,2048,3) float32, texture repeating twice per tile."""
    key = (choice, dark)
    if key not in _tiled_cache:
        from PIL import Image

        tile = _load_level_tile(choice) * dark
        half = np.asarray(Image.fromarray(
            tile.astype(np.uint8), "RGB").resize(
            (_CELL // 2, _CELL // 2), Image.BILINEAR), dtype=np.float32)
        _tiled_cache[key] = np.tile(half, (GRID * 2, GRID * 2, 1))
    return _tiled_cache[key]


def _tile_choice(t: int, row: int) -> tuple:
    """(texture name, darken) for a tile, using latitude bands like the game."""
    if t in _FIXED_TEX:
        return _FIXED_TEX[t], 1.0
    band_dist = abs(row - 15.5)
    idx = 0 if band_dist <= 5.5 else (1 if band_dist <= 10.5 else 2)
    if t == FOREST:
        return _BAND_TEX[1][idx], 0.8      # darkened grass forest floor
    return _BAND_TEX.get(t, _BAND_TEX[1])[idx], 1.0


def build_ground_albedo(grid: bytes) -> np.ndarray:
    """Blend tiled per-terrain textures with soft transitions between tiles."""
    from PIL import Image

    choices: dict = {}
    idx_map = np.zeros((GRID, GRID), dtype=np.int32)
    for r in range(GRID):
        for c in range(GRID):
            key = _tile_choice(grid[r * GRID + c] & 0x07, r)
            if key not in choices:
                choices[key] = len(choices)
            idx_map[r, c] = choices[key]

    acc = np.zeros((ALBEDO_SIZE, ALBEDO_SIZE, 3), dtype=np.float32)
    for key, ci in choices.items():
        mask32 = (idx_map == ci).astype(np.float32)
        mask = np.asarray(Image.fromarray(mask32, "F").resize(
            (ALBEDO_SIZE, ALBEDO_SIZE), Image.BILINEAR))
        acc += mask[:, :, None] * _tiled(*key)
    return np.clip(acc, 0, 255).astype(np.uint8)


def default_surface_format() -> QSurfaceFormat:
    fmt = QSurfaceFormat()
    fmt.setVersion(4, 1)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setSamples(4)
    return fmt


# ── Shaders ─────────────────────────────────────────────────────────────

TERRAIN_VS = """
#version 150
in vec2 xy;
uniform sampler2D uHeights;
uniform float uHScale;
uniform mat4 uMvp;
out vec2 vUV;
void main() {
    vUV = xy / 32.0;
    float h = texture(uHeights, vUV).r;
    gl_Position = uMvp * vec4(xy, h * uHScale, 1.0);
}
"""

TERRAIN_FS = """
#version 150
in vec2 vUV;
uniform sampler2D uHeights;
uniform sampler2D uLight;
uniform sampler2D uBlend;
uniform sampler2D uDetail;
uniform sampler2D uAlbedo;
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
    // Ground color = tiled terrain textures modulated by the painted
    // lightmap (the game's approach: the lightmap is light/tint, not albedo)
    vec3 albedo = texture(uAlbedo, vUV).rgb;
    // Neutralize the lightmap's lavender average so land hues stay true
    vec3 light = texture(uLight, vUV).rgb * vec3(1.30, 1.32, 1.22);
    vec3 base = albedo * light;
    float rock = texture(uBlend, vUV).g;
    vec3 detail = texture(uDetail, vUV * 40.0).rgb;
    base = mix(base, base * detail * 2.0, clamp(rock, 0.0, 1.0) * 0.45);
    // Altitude snow, like the game's Snow.dds pass
    float h = texture(uHeights, vUV).r;
    float snow = smoothstep(0.60, 0.74, h);
    base = mix(base, vec3(0.90, 0.93, 0.97) * light, snow * 0.9);
    float diff = max(dot(n, normalize(uLightDir)), 0.0);
    frag = vec4(base * (0.62 + 0.5 * diff), 1.0);
}
"""

FLAT_VS = """
#version 150
in vec3 pos;
uniform mat4 uMvp;
void main() { gl_Position = uMvp * vec4(pos, 1.0); }
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
void main() { vUV = pos.xy / 32.0; gl_Position = uMvp * vec4(pos, 1.0); }
"""

WATER_FS = """
#version 150
in vec2 vUV;
uniform sampler2D uHeights;
uniform float uWaterNorm;
out vec4 frag;
void main() {
    float floor_h = texture(uHeights, vUV).r;
    float depth = clamp((uWaterNorm - floor_h) * 9.0, 0.0, 1.0);
    vec3 shallow = vec3(0.36, 0.78, 0.82);
    vec3 deep = vec3(0.07, 0.27, 0.55);
    float alpha = mix(0.22, 0.58, depth);
    frag = vec4(mix(shallow, deep, depth), alpha);
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
void main() { vUV = uv; vShade = shade; gl_Position = uMvp * vec4(pos, 1.0); }
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


def build_river_verts(grid: bytes, heights: np.ndarray) -> np.ndarray:
    """Triangle strip quads along flagged tile edges. (N,3) float32."""
    tris = []
    hw = 0.07                       # half width in tile units
    lift = 0.065

    def edge_strip(x0, y0, x1, y1):
        segs = 10
        dx, dy = x1 - x0, y1 - y0
        # Perpendicular in the ground plane
        ln = math.hypot(dx, dy) or 1.0
        px, py = -dy / ln * hw, dx / ln * hw
        for s in range(segs):
            t0, t1 = s / segs, (s + 1) / segs
            ax, ay = x0 + dx * t0, y0 + dy * t0
            bx, by = x0 + dx * t1, y0 + dy * t1
            az = _sample_height(heights, ax, ay) * HEIGHT_SCALE + lift
            bz = _sample_height(heights, bx, by) * HEIGHT_SCALE + lift
            quad = [
                (ax - px, ay - py, az), (ax + px, ay + py, az),
                (bx - px, by - py, bz),
                (ax + px, ay + py, az), (bx + px, by + py, bz),
                (bx - px, by - py, bz),
            ]
            tris.extend(quad)

    for r in range(GRID):
        for c in range(GRID):
            v = grid[r * GRID + c]
            if v & 0x20:
                edge_strip(c, float(r), c, r + 1.0)
            if v & 0x40:
                edge_strip(c + 1, float(r), c + 1, r + 1.0)
            if v & 0x80:
                edge_strip(float(c), r + 1, c + 1.0, r + 1)
    if not tris:
        return np.zeros((0, 3), dtype=np.float32)
    return np.array(tris, dtype=np.float32)


def build_tree_verts(grid: bytes, heights: np.ndarray) -> np.ndarray:
    """Crossed billboard quads on forest tiles. (N,6): pos3 + uv2 + shade."""
    verts = []
    for r in range(GRID):
        for c in range(GRID):
            if grid[r * GRID + c] & 0x07 != FOREST:
                continue
            n = 5 + _tile_hash(r, c) % 3
            for k in range(n):
                hsh = _tile_hash(r, c, k + 1)
                tx = c + 0.15 + (hsh % 1000) / 1000.0 * 0.7
                ty = r + 0.15 + ((hsh >> 10) % 1000) / 1000.0 * 0.7
                size = 0.34 + ((hsh >> 20) % 100) / 100.0 * 0.22
                shade = 0.75 + ((hsh >> 8) % 100) / 100.0 * 0.35
                tz = _sample_height(heights, tx, ty) * HEIGHT_SCALE - 0.02
                s = size / 2
                for ang in (0.0, math.pi / 2):
                    dx, dy = math.cos(ang) * s, math.sin(ang) * s
                    a = (tx - dx, ty - dy, tz)
                    b = (tx + dx, ty + dy, tz)
                    top_a = (tx - dx, ty - dy, tz + size * 1.5)
                    top_b = (tx + dx, ty + dy, tz + size * 1.5)
                    for p, (u, w) in ((a, (0, 0)), (b, (1, 0)), (top_a, (0, 1)),
                                      (b, (1, 0)), (top_b, (1, 1)),
                                      (top_a, (0, 1))):
                        verts.append((*p, u, w, shade))
    if not verts:
        return np.zeros((0, 6), dtype=np.float32)
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


def make_tree_texture() -> np.ndarray:
    """Procedural conifer billboard, (128,128,4) uint8 RGBA."""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([58, 8, 70, 30], fill=(70, 50, 28, 255))          # trunk
    for base_y, half, top_y in [(52, 52, 20), (78, 42, 44), (100, 32, 68),
                                (118, 22, 92)]:
        d.polygon([(64 - half, 128 - base_y + 30), (64 + half, 128 - base_y + 30),
                   (64, 128 - top_y - 30)], fill=(16, 62, 30, 255))
    for base_y, half, top_y in [(50, 44, 22), (76, 35, 46), (98, 26, 70),
                                (116, 17, 94)]:
        d.polygon([(64 - half, 128 - base_y + 30), (64 + half, 128 - base_y + 30),
                   (64, 128 - top_y - 30)], fill=(28, 84, 44, 255))
    arr = np.asarray(img, dtype=np.uint8)
    return arr[::-1].copy()          # v=0 at bottom of tree


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
        self.counts = {"terrain": 0, "river": 0, "tree": 0, "skirt": 0,
                       "water": 6}
        # Camera
        self.yaw = 0.0
        self.pitch = 54.0
        self.dist = 30.0
        self.target = QVector3D(16.0, 17.0, 1.3)

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
        z = WATER_NORM * HEIGHT_SCALE
        quad = np.array([
            (0, 0, z), (32, 0, z), (0, 32, z),
            (32, 0, z), (32, 32, z), (0, 32, z),
        ], dtype=np.float32)
        self._vbo("water", quad)

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

        albedo = s.albedo if s.albedo is not None else build_ground_albedo(
            s.grid)
        albedo = np.ascontiguousarray(albedo)
        tex = self._texture("albedo")
        tex.setFormat(QOpenGLTexture.RGB8_UNorm)
        tex.setSize(albedo.shape[1], albedo.shape[0])
        tex.setMipLevels(1)
        tex.allocateStorage()
        tex.setData(QOpenGLTexture.RGB, QOpenGLTexture.UInt8, albedo.tobytes())
        tex.setMinMagFilters(QOpenGLTexture.Linear, QOpenGLTexture.Linear)
        tex.setWrapMode(QOpenGLTexture.ClampToEdge)

        rivers = build_river_verts(s.grid, s.heights)
        self._vbo("river", rivers)
        self.counts["river"] = len(rivers)

        trees = build_tree_verts(s.grid, s.heights)
        self._vbo("tree", trees)
        self.counts["tree"] = len(trees)

        skirt = build_skirt_verts(s.heights)
        self._vbo("skirt", skirt)
        self.counts["skirt"] = len(skirt)

    # ── Camera ──────────────────────────────────────────────

    def mvp(self, w: int, h: int) -> QMatrix4x4:
        aspect = w / max(1, h)
        proj = QMatrix4x4()
        proj.perspective(46.0, aspect, 0.3, 400.0)
        yaw = math.radians(self.yaw)
        pitch = math.radians(self.pitch)
        eye = self.target + QVector3D(
            math.sin(yaw) * math.cos(pitch) * self.dist,
            math.cos(yaw) * math.cos(pitch) * self.dist,
            math.sin(pitch) * self.dist,
        )
        view = QMatrix4x4()
        view.lookAt(eye, self.target, QVector3D(0, 0, 1))
        return proj * view

    def orbit(self, dx: float, dy: float):
        self.yaw = (self.yaw + dx * 0.4) % 360
        self.pitch = min(88.0, max(15.0, self.pitch + dy * 0.3))

    def pan(self, dx: float, dy: float):
        yaw = math.radians(self.yaw)
        scale = self.dist * 0.0016
        rx = QVector3D(math.cos(yaw), -math.sin(yaw), 0) * (-dx * scale)
        ry = QVector3D(math.sin(yaw), math.cos(yaw), 0) * (dy * scale)
        self.target += rx + ry
        self.target.setX(min(34.0, max(-2.0, self.target.x())))
        self.target.setY(min(34.0, max(-2.0, self.target.y())))

    def zoom(self, factor: float):
        self.dist = min(80.0, max(4.0, self.dist * factor))

    # ── Drawing ─────────────────────────────────────────────

    def render(self, w: int, h: int):
        f = self.f
        if self._scene_dirty and self.scene is not None:
            self._apply_scene()

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
        prog.setUniformValue("uMvp", mvp)
        prog.setUniformValue("uHScale", float(HEIGHT_SCALE))
        prog.setUniformValue("uLightDir", QVector3D(-0.45, -0.55, 0.75))
        for unit, (name, uni) in enumerate(
                [("heights", "uHeights"), ("light", "uLight"),
                 ("blend", "uBlend"), ("detail", "uDetail"),
                 ("albedo", "uAlbedo")]):
            self.textures[name].bind(unit)
            prog.setUniformValue(uni, unit)
        self.buffers["terrain"].bind()
        prog.enableAttributeArray("xy")
        prog.setAttributeBuffer("xy", GL_FLOAT, 0, 2)
        self.buffers["terrain_idx"].bind()
        f.glDrawElements(GL_TRIANGLES, self.counts["terrain"],
                         GL_UNSIGNED_INT, None)
        self.buffers["terrain_idx"].release()

        # Skirt walls
        flat = self.programs["flat"]
        flat.bind()
        flat.setUniformValue("uMvp", mvp)
        flat.setUniformValue("uColor", 0.06, 0.09, 0.13, 1.0)
        if self.counts["skirt"]:
            self.buffers["skirt"].bind()
            flat.enableAttributeArray("pos")
            flat.setAttributeBuffer("pos", GL_FLOAT, 0, 3)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts["skirt"])

        # Rivers
        if self.counts["river"]:
            f.glEnable(GL_BLEND)
            f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            flat.setUniformValue("uColor", 0.30, 0.62, 0.90, 0.85)
            self.buffers["river"].bind()
            flat.enableAttributeArray("pos")
            flat.setAttributeBuffer("pos", GL_FLOAT, 0, 3)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts["river"])
            f.glDisable(GL_BLEND)

        # Trees
        if self.counts["tree"]:
            tp = self.programs["tree"]
            tp.bind()
            tp.setUniformValue("uMvp", mvp)
            self.textures["tree"].bind(0)
            tp.setUniformValue("uTex", 0)
            self.buffers["tree"].bind()
            stride = 6 * 4
            tp.enableAttributeArray("pos")
            tp.setAttributeBuffer("pos", GL_FLOAT, 0, 3, stride)
            tp.enableAttributeArray("uv")
            tp.setAttributeBuffer("uv", GL_FLOAT, 3 * 4, 2, stride)
            tp.enableAttributeArray("shade")
            tp.setAttributeBuffer("shade", GL_FLOAT, 5 * 4, 1, stride)
            f.glDrawArrays(GL_TRIANGLES, 0, self.counts["tree"])

        # Water (depth-graded: cyan shallows, navy deeps)
        f.glEnable(GL_BLEND)
        f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        wp = self.programs["water"]
        wp.bind()
        wp.setUniformValue("uMvp", mvp)
        wp.setUniformValue("uWaterNorm", float(WATER_NORM))
        self.textures["heights"].bind(0)
        wp.setUniformValue("uHeights", 0)
        self.buffers["water"].bind()
        wp.enableAttributeArray("pos")
        wp.setAttributeBuffer("pos", GL_FLOAT, 0, 3)
        f.glDrawArrays(GL_TRIANGLES, 0, self.counts["water"])
        f.glDisable(GL_BLEND)


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

    def reset_camera(self):
        r = self.renderer
        r.yaw, r.pitch, r.dist = 0.0, 54.0, 30.0
        r.target = QVector3D(16.0, 17.0, 1.3)
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
            self.renderer.orbit(-d.x(), d.y())
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
