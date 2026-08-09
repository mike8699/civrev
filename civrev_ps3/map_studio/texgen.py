"""DDS texture generation for CivRev DLC maps (numpy-accelerated).

Every map needs three textures (formats verified against all 281 shipped sets):
  map<tag>_heights.dds               512x512  L16 uncompressed, no mips
  map<tag>_lightmap.dds             4096x4096 DXT1, no mips
  map<tag>_mountainhill_blends.dds  2048x2048 DXT1, no mips

Per 32x32 tile that is 16 px (heights), 128 px = 32x32 DXT1 blocks (lightmap),
and 64 px = 16x16 DXT1 blocks (blends). DDS pixel x = display column,
y = display row.

Two generation modes:

* SMART PATCH (default): start from the target slot's pristine textures and
  replace only the cells of tiles whose terrain changed. Replacement cells are
  harvested from a donor corpus built from all four original DLC maps —
  the donor is a tile of the same terrain type with the closest neighborhood
  (ocean/ice/land pattern), so coastlines get coastal art and interiors get
  interior art. Unchanged tiles keep their original art byte-for-byte.

* FULL SYNTH: procedural fallback used when originals are unavailable —
  per-terrain height profiles, flat lightmap colors, and authentic blend
  block sets extracted from the Firaxis originals.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np
from model import GRID, ICE, MOUNTAINS, OCEAN, MapModel, file_to_display
from PIL import Image

ASSETS = Path(__file__).resolve().parent / "assets"

H_SIZE = 512      # heights px
L_SIZE = 4096     # lightmap px
B_SIZE = 2048     # blends px
H_PPT = H_SIZE // GRID          # 16 px per tile
L_BPT = L_SIZE // 4 // GRID     # 32 blocks per tile
B_BPT = B_SIZE // 4 // GRID     # 16 blocks per tile

DDS_HEADER_LEN = 128

# ── DDS headers (byte-for-byte from original DLC files) ─────────────────


def _dds_header(width: int, height: int, fourcc: bytes | None) -> bytes:
    """Build the exact 128-byte header the originals use."""
    h = bytearray(DDS_HEADER_LEN)
    h[0:4] = b"DDS "
    struct.pack_into("<I", h, 4, 124)
    struct.pack_into("<I", h, 8, 0x1007)          # CAPS|HEIGHT|WIDTH|PIXELFORMAT
    struct.pack_into("<I", h, 12, height)
    struct.pack_into("<I", h, 16, width)
    struct.pack_into("<I", h, 76, 32)             # pixel-format struct size
    if fourcc:
        struct.pack_into("<I", h, 80, 0x4)        # DDPF_FOURCC
        h[84:88] = fourcc
    else:
        struct.pack_into("<I", h, 80, 0x20000)    # DDPF_LUMINANCE
        struct.pack_into("<I", h, 88, 16)         # bpp
        struct.pack_into("<I", h, 92, 0xFFFF)     # luminance mask
    struct.pack_into("<I", h, 108, 0x1000)        # DDSCAPS_TEXTURE
    return bytes(h)


HEIGHTS_HEADER = _dds_header(H_SIZE, H_SIZE, None)
LIGHTMAP_HEADER = _dds_header(L_SIZE, L_SIZE, b"DXT1")
BLENDS_HEADER = _dds_header(B_SIZE, B_SIZE, b"DXT1")

# ── Synthetic per-terrain tables (correct mapping: 3=Hills, 6=Mountains) ─

# (base_height, peak_amplitude, gaussian sharpness)
HEIGHT_PROFILE = {
    0: (14000, 0, 0.0),        # Ocean
    1: (29000, 1500, 1.5),     # Grassland
    2: (29000, 1500, 1.5),     # Plains
    3: (32000, 6000, 2.0),     # Hills
    4: (30000, 5000, 1.5),     # Forest
    5: (29000, 1500, 1.5),     # Desert
    6: (35000, 30000, 2.0),    # Mountains
    7: (32000, 0, 0.0),        # Ice
}

# Flat lightmap colors measured from originals (per terrain type)
LIGHTMAP_COLOR = [
    (188, 187, 198),  # Ocean
    (204, 202, 212),  # Grassland
    (207, 205, 215),  # Plains
    (156, 153, 170),  # Hills
    (203, 201, 212),  # Forest
    (204, 202, 212),  # Desert
    (205, 203, 213),  # Mountains
    (166, 163, 180),  # Ice
]


def _tile_hash(r: int, c: int) -> int:
    return ((r * 37 + c * 13 + 7) * 2654435761) & 0xFFFFFFFF


# ── DXT1 encode / decode (vectorized) ───────────────────────────────────


def _pack_565(px: np.ndarray) -> np.ndarray:
    """(N,3) uint8 -> (N,) uint16 RGB565."""
    p = px.astype(np.uint16)
    return ((p[:, 0] >> 3) << 11) | ((p[:, 1] >> 2) << 5) | (p[:, 2] >> 3)


def _unpack_565(v: np.ndarray) -> np.ndarray:
    """(N,) uint16 -> (N,3) uint8, matching the game's expansion."""
    v = v.astype(np.uint32)
    r = ((v >> 11) & 0x1F) * 255 // 31
    g = ((v >> 5) & 0x3F) * 255 // 63
    b = (v & 0x1F) * 255 // 31
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def encode_dxt1(img: np.ndarray, progress=None) -> np.ndarray:
    """(H,W,3) uint8 -> (H//4, W//4, 8) uint8 DXT1 blocks."""
    h, w, _ = img.shape
    hb, wb = h // 4, w // 4
    out = np.empty((hb, wb, 8), dtype=np.uint8)
    chunk = max(1, (1 << 21) // max(1, w))   # ~2M px per chunk
    shifts = (np.arange(16, dtype=np.uint32) * 2)[None, :]

    for y0 in range(0, hb, chunk):
        y1 = min(hb, y0 + chunk)
        sub = img[y0 * 4:y1 * 4]
        n = (y1 - y0) * wb
        # -> (N, 16, 3) pixel blocks
        px = (sub.reshape(y1 - y0, 4, wb, 4, 3)
                 .transpose(0, 2, 1, 3, 4)
                 .reshape(n, 16, 3))
        lum = (px.astype(np.int32) * np.array([2, 5, 1])).sum(axis=2)
        imax = lum.argmax(axis=1)
        imin = lum.argmin(axis=1)
        ar = np.arange(n)
        c0 = _pack_565(px[ar, imax])
        c1 = _pack_565(px[ar, imin])
        swap = c0 < c1
        c0s, c1s = c0.copy(), c1.copy()
        c0s[swap], c1s[swap] = c1[swap], c0[swap]

        e0 = _unpack_565(c0s).astype(np.int32)
        e1 = _unpack_565(c1s).astype(np.int32)
        pal = np.stack(
            [e0, e1, (2 * e0 + e1) // 3, (e0 + 2 * e1) // 3], axis=1
        )  # (N,4,3)
        d = ((px.astype(np.int32)[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(
            axis=3
        )  # (N,16,4)
        codes = d.argmin(axis=2).astype(np.uint32)          # (N,16)
        idx = np.bitwise_or.reduce(codes << shifts, axis=1)  # (N,)
        idx[c0s == c1s] = 0

        blk = np.empty((n, 8), dtype=np.uint8)
        blk[:, 0] = c0s & 0xFF
        blk[:, 1] = c0s >> 8
        blk[:, 2] = c1s & 0xFF
        blk[:, 3] = c1s >> 8
        blk[:, 4] = idx & 0xFF
        blk[:, 5] = (idx >> 8) & 0xFF
        blk[:, 6] = (idx >> 16) & 0xFF
        blk[:, 7] = (idx >> 24) & 0xFF
        out[y0:y1] = blk.reshape(y1 - y0, wb, 8)
        if progress:
            progress(y1 / hb)
    return out


def decode_dxt1(blocks: np.ndarray) -> np.ndarray:
    """(Hb,Wb,8) uint8 DXT1 blocks -> (Hb*4, Wb*4, 3) uint8."""
    hb, wb, _ = blocks.shape
    n = hb * wb
    b = blocks.reshape(n, 8).astype(np.uint32)
    c0 = b[:, 0] | (b[:, 1] << 8)
    c1 = b[:, 2] | (b[:, 3] << 8)
    e0 = _unpack_565(c0).astype(np.int32)
    e1 = _unpack_565(c1).astype(np.int32)
    four = c0 > c1
    p2 = np.where(four[:, None], (2 * e0 + e1) // 3, (e0 + e1) // 2)
    p3 = np.where(four[:, None], (e0 + 2 * e1) // 3, 0)
    pal = np.stack([e0, e1, p2, p3], axis=1).astype(np.uint8)  # (N,4,3)
    idx = b[:, 4] | (b[:, 5] << 8) | (b[:, 6] << 16) | (b[:, 7] << 24)
    codes = (idx[:, None] >> (np.arange(16, dtype=np.uint32) * 2)) & 0x3  # (N,16)
    px = pal[np.arange(n)[:, None], codes]                    # (N,16,3)
    return (px.reshape(hb, wb, 4, 4, 3)
              .transpose(0, 2, 1, 3, 4)
              .reshape(hb * 4, wb * 4, 3))


def decode_dxt1_rgba(blocks: np.ndarray) -> np.ndarray:
    """DXT1 decode with 1-bit alpha (3-color-mode index 3 = transparent).

    (Hb,Wb,8) uint8 -> (Hb*4, Wb*4, 4) uint8 RGBA.
    """
    hb, wb, _ = blocks.shape
    n = hb * wb
    b = blocks.reshape(n, 8).astype(np.uint32)
    c0 = b[:, 0] | (b[:, 1] << 8)
    c1 = b[:, 2] | (b[:, 3] << 8)
    e0 = _unpack_565(c0).astype(np.int32)
    e1 = _unpack_565(c1).astype(np.int32)
    four = c0 > c1
    p2 = np.where(four[:, None], (2 * e0 + e1) // 3, (e0 + e1) // 2)
    p3 = np.where(four[:, None], (e0 + 2 * e1) // 3, 0)
    pal = np.stack([e0, e1, p2, p3], axis=1).astype(np.uint8)
    apal = np.stack([
        np.full(n, 255), np.full(n, 255), np.full(n, 255),
        np.where(four, 255, 0),
    ], axis=1).astype(np.uint8)
    idx = b[:, 4] | (b[:, 5] << 8) | (b[:, 6] << 16) | (b[:, 7] << 24)
    codes = (idx[:, None] >> (np.arange(16, dtype=np.uint32) * 2)) & 0x3
    px = pal[np.arange(n)[:, None], codes]
    pa = apal[np.arange(n)[:, None], codes]
    rgb = (px.reshape(hb, wb, 4, 4, 3).transpose(0, 2, 1, 3, 4)
             .reshape(hb * 4, wb * 4, 3))
    a = (pa.reshape(hb, wb, 4, 4).transpose(0, 2, 1, 3)
           .reshape(hb * 4, wb * 4))
    return np.dstack([rgb, a])


def solid_dxt1_block(rgb: tuple) -> np.ndarray:
    """A single uniform-color DXT1 block, (8,) uint8."""
    c = _pack_565(np.array([rgb], dtype=np.uint8))[0]
    return np.array(
        [c & 0xFF, c >> 8, c & 0xFF, c >> 8, 0, 0, 0, 0], dtype=np.uint8
    )


# ── Blend reference blocks (authentic Firaxis block sets) ───────────────


def load_blend_refs() -> dict:
    """terrain type -> list of (16,16,8) uint8 block cells."""
    refs = {}
    ref_dir = ASSETS / "blend_refs"
    for t in range(8):
        variants = []
        for f in sorted(ref_dir.glob(f"terrain_{t}_*.bin")):
            data = f.read_bytes()
            if len(data) == B_BPT * B_BPT * 8:
                variants.append(
                    np.frombuffer(data, dtype=np.uint8).reshape(B_BPT, B_BPT, 8)
                )
        if variants:
            refs[t] = variants
    return refs


# ── Original map sets (the donor corpus) ────────────────────────────────


class OriginalSet:
    """A pristine DLC map: tile grid + its three decoded texture arrays."""

    def __init__(self, tag: str, grid: bytes, heights: np.ndarray,
                 light_blocks: np.ndarray, blend_blocks: np.ndarray):
        self.tag = tag
        self.grid = grid                    # display-order tile bytes
        self.heights = heights              # (512,512) uint16
        self.light_blocks = light_blocks    # (1024,1024,8) uint8
        self.blend_blocks = blend_blocks    # (512,512,8) uint8

    def terrain(self, r: int, c: int) -> int:
        return self.grid[r * GRID + c] & 0x07


def load_original_set(pak9_original: Path, slot: dict) -> OriginalSet | None:
    tag = slot["tag"].lower()
    try:
        grid = bytes(file_to_display(
            (pak9_original / slot["file"]).read_bytes()))
        h_raw = (pak9_original / f"map{tag}_heights.dds").read_bytes()
        l_raw = (pak9_original / f"map{tag}_lightmap.dds").read_bytes()
        b_raw = (pak9_original / f"map{tag}_mountainhill_blends.dds").read_bytes()
    except OSError:
        return None
    heights = np.frombuffer(
        h_raw, dtype="<u2", offset=DDS_HEADER_LEN
    ).reshape(H_SIZE, H_SIZE).copy()
    light = np.frombuffer(
        l_raw, dtype=np.uint8, offset=DDS_HEADER_LEN
    ).reshape(L_SIZE // 4, L_SIZE // 4, 8).copy()
    blend = np.frombuffer(
        b_raw, dtype=np.uint8, offset=DDS_HEADER_LEN
    ).reshape(B_SIZE // 4, B_SIZE // 4, 8).copy()
    return OriginalSet(tag, grid, heights, light, blend)


def load_corpus(pak9_original: Path) -> list:
    from model import DLC_SLOTS

    out = []
    for slot in DLC_SLOTS:
        s = load_original_set(pak9_original, slot)
        if s:
            out.append(s)
    return out


# ── Donor selection ─────────────────────────────────────────────────────


def _klass(t: int) -> int:
    """Coarse terrain class for neighborhood matching."""
    if t == OCEAN:
        return 0
    if t == ICE:
        return 1
    return 2


def _signature(grid_terrain, r: int, c: int) -> tuple:
    """Ocean/ice/land pattern of the four neighbors (out of bounds = ice)."""
    sig = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < GRID and 0 <= nc < GRID:
            sig.append(_klass(grid_terrain(nr, nc)))
        else:
            sig.append(1)
    return tuple(sig)


def build_donor_index(corpus: list) -> dict:
    """terrain type -> list of (set_idx, r, c, signature)."""
    index = {t: [] for t in range(8)}
    for si, s in enumerate(corpus):
        for r in range(GRID):
            for c in range(GRID):
                t = s.terrain(r, c)
                index[t].append((si, r, c, _signature(s.terrain, r, c)))
    return index


def pick_donor(index: dict, terrain: int, sig: tuple, seed: int):
    """Best-matching donor tile, deterministic tie-break."""
    cands = index.get(terrain)
    if not cands:
        return None
    best_score = -1
    best = []
    for cand in cands:
        score = sum(1 for a, b in zip(sig, cand[3], strict=True) if a == b)
        if score > best_score:
            best_score = score
            best = [cand]
        elif score == best_score:
            best.append(cand)
    return best[seed % len(best)]


# ── Full-synth generators ───────────────────────────────────────────────


def synth_heights(model: MapModel) -> np.ndarray:
    """(512,512) uint16 from per-terrain profiles."""
    base = np.zeros((GRID, GRID), dtype=np.float32)
    for r in range(GRID):
        for c in range(GRID):
            t = model.get_terrain(r, c)
            h = HEIGHT_PROFILE[t][0]
            if t == MOUNTAINS:
                h = 32000 + (_tile_hash(r, c) % 1000) / 1000.0 * 8000
            base[r, c] = h
    smooth = np.asarray(
        Image.fromarray(base, mode="F").resize((H_SIZE, H_SIZE), Image.BILINEAR)
    )

    # Peak overlay: per-tile gaussian bumps
    yy, xx = np.mgrid[0:H_PPT, 0:H_PPT].astype(np.float32)
    half = H_PPT / 2 - 0.5
    nx = np.abs(xx - half) / half
    ny = np.abs(yy - half) / half
    dist_sq = nx * nx + ny * ny
    kernels = {
        sharp: np.exp(-sharp * dist_sq)
        for sharp in {p[2] for p in HEIGHT_PROFILE.values() if p[1] > 0}
    }

    overlay = np.zeros((H_SIZE, H_SIZE), dtype=np.float32)
    for r in range(GRID):
        for c in range(GRID):
            t = model.get_terrain(r, c)
            _, amp, sharp = HEIGHT_PROFILE[t]
            if amp == 0:
                continue
            if t == MOUNTAINS:
                amp = amp * (0.2 + 0.8 * (_tile_hash(r, c) % 1000) / 1000.0)
            overlay[r * H_PPT:(r + 1) * H_PPT,
                    c * H_PPT:(c + 1) * H_PPT] = amp * kernels[sharp]

    return np.clip(smooth + overlay, 0, 65535).astype(np.uint16)


def synth_lightmap_rgb(model: MapModel) -> np.ndarray:
    """(4096,4096,3) uint8 flat-color lightmap, bilinear tile transitions."""
    base = np.zeros((GRID, GRID, 3), dtype=np.uint8)
    for r in range(GRID):
        for c in range(GRID):
            base[r, c] = LIGHTMAP_COLOR[model.get_terrain(r, c)]
    img = Image.fromarray(base, mode="RGB").resize((L_SIZE, L_SIZE),
                                                   Image.BILINEAR)
    return np.asarray(img)


def synth_blend_blocks(model: MapModel, refs: dict) -> np.ndarray:
    """(512,512,8) uint8 blend blocks from authentic reference cells."""
    nb = B_SIZE // 4
    out = np.zeros((nb, nb, 8), dtype=np.uint8)
    for r in range(GRID):
        for c in range(GRID):
            t = model.get_terrain(r, c)
            variants = refs.get(t)
            if not variants:
                continue
            cell = variants[_tile_hash(r, c) % len(variants)]
            out[r * B_BPT:(r + 1) * B_BPT, c * B_BPT:(c + 1) * B_BPT] = cell
    return out


# ── Smart patch ─────────────────────────────────────────────────────────


def _feather_heights(heights: np.ndarray, cells: list):
    """Soften 4px-wide seams around patched tile cells with a 3x3 mean."""
    if not cells:
        return heights
    f = heights.astype(np.float32)
    padded = np.pad(f, 1, mode="edge")
    blurred = np.zeros_like(f)
    for dy in range(3):
        for dx in range(3):
            blurred += padded[dy:dy + H_SIZE, dx:dx + H_SIZE]
    blurred /= 9.0

    mask = np.zeros((H_SIZE, H_SIZE), dtype=bool)
    for r, c in cells:
        y0, x0 = r * H_PPT, c * H_PPT
        y1, x1 = y0 + H_PPT, x0 + H_PPT
        ol0, ol1 = 2, 2   # 2px outside, 2px inside each seam
        ys = slice(max(0, y0 - ol0), min(H_SIZE, y1 + ol0))
        xs = slice(max(0, x0 - ol0), min(H_SIZE, x1 + ol0))
        mask[ys, max(0, x0 - ol0):min(H_SIZE, x0 + ol1)] = True   # left band
        mask[ys, max(0, x1 - ol1):min(H_SIZE, x1 + ol0)] = True   # right band
        mask[max(0, y0 - ol0):min(H_SIZE, y0 + ol1), xs] = True   # top band
        mask[max(0, y1 - ol1):min(H_SIZE, y1 + ol0), xs] = True   # bottom band

    out = f.copy()
    out[mask] = blurred[mask]
    return np.clip(out, 0, 65535).astype(np.uint16)


def patch_textures(model: MapModel, target: OriginalSet, corpus: list,
                   refs: dict, progress=None) -> tuple:
    """Smart-patch mode. Returns (heights u16, light_blocks, blend_blocks)."""
    heights = target.heights.copy()
    light = target.light_blocks.copy()
    blend = target.blend_blocks.copy()

    changed = model.changed_tiles(target.grid)
    if not changed:
        return heights, light, blend

    index = build_donor_index(corpus)
    patched_cells = []

    for i, (r, c) in enumerate(changed):
        t = model.get_terrain(r, c)
        sig = _signature(model.get_terrain, r, c)
        donor = pick_donor(index, t, sig, _tile_hash(r, c))
        if donor:
            si, dr, dc, _ = donor
            src = corpus[si]
            heights[r * H_PPT:(r + 1) * H_PPT, c * H_PPT:(c + 1) * H_PPT] = \
                src.heights[dr * H_PPT:(dr + 1) * H_PPT,
                            dc * H_PPT:(dc + 1) * H_PPT]
            light[r * L_BPT:(r + 1) * L_BPT, c * L_BPT:(c + 1) * L_BPT] = \
                src.light_blocks[dr * L_BPT:(dr + 1) * L_BPT,
                                 dc * L_BPT:(dc + 1) * L_BPT]
            blend[r * B_BPT:(r + 1) * B_BPT, c * B_BPT:(c + 1) * B_BPT] = \
                src.blend_blocks[dr * B_BPT:(dr + 1) * B_BPT,
                                 dc * B_BPT:(dc + 1) * B_BPT]
        else:
            # No donor anywhere in the corpus — synthetic cell
            base, amp, sharp = HEIGHT_PROFILE[t]
            cell = np.full((H_PPT, H_PPT), base, dtype=np.float32)
            if amp:
                yy, xx = np.mgrid[0:H_PPT, 0:H_PPT].astype(np.float32)
                half = H_PPT / 2 - 0.5
                d2 = (np.abs(xx - half) / half) ** 2 + \
                     (np.abs(yy - half) / half) ** 2
                cell += amp * np.exp(-sharp * d2)
            heights[r * H_PPT:(r + 1) * H_PPT, c * H_PPT:(c + 1) * H_PPT] = \
                np.clip(cell, 0, 65535).astype(np.uint16)
            light[r * L_BPT:(r + 1) * L_BPT, c * L_BPT:(c + 1) * L_BPT] = \
                solid_dxt1_block(LIGHTMAP_COLOR[t])
            variants = refs.get(t)
            if variants:
                blend[r * B_BPT:(r + 1) * B_BPT,
                      c * B_BPT:(c + 1) * B_BPT] = \
                    variants[_tile_hash(r, c) % len(variants)]
            else:
                blend[r * B_BPT:(r + 1) * B_BPT,
                      c * B_BPT:(c + 1) * B_BPT] = 0
        patched_cells.append((r, c))
        if progress:
            progress((i + 1) / len(changed))

    heights = _feather_heights(heights, patched_cells)
    return heights, light, blend


# ── Top-level API ───────────────────────────────────────────────────────


def heights_to_dds(heights: np.ndarray) -> bytes:
    return HEIGHTS_HEADER + heights.astype("<u2").tobytes()


def light_blocks_to_dds(blocks: np.ndarray) -> bytes:
    return LIGHTMAP_HEADER + blocks.tobytes()


def blend_blocks_to_dds(blocks: np.ndarray) -> bytes:
    return BLENDS_HEADER + blocks.tobytes()


def generate_textures(model: MapModel, target: OriginalSet | None,
                      corpus: list, refs: dict,
                      progress=None) -> dict:
    """Produce the three DDS payloads.

    Uses smart patch when a target original is available, full synth otherwise.
    progress: callable(step_label, fraction 0-1).
    """
    def report(label, frac):
        if progress:
            progress(label, frac)

    if target is not None:
        report("Patching textures from originals", 0.0)
        heights, light, blend = patch_textures(
            model, target, corpus, refs,
            progress=lambda f: report("Patching textures from originals", f))
        report("Encoding", 1.0)
        return {
            "heights": heights_to_dds(heights),
            "lightmap": light_blocks_to_dds(light),
            "blends": blend_blocks_to_dds(blend),
            "mode": "smart-patch",
        }

    report("Generating heights", 0.0)
    heights = synth_heights(model)
    report("Generating lightmap", 0.2)
    rgb = synth_lightmap_rgb(model)
    light = encode_dxt1(
        rgb, progress=lambda f: report("Encoding lightmap (DXT1)", 0.2 + f * 0.6))
    report("Generating blends", 0.9)
    blend = synth_blend_blocks(model, refs)
    report("Done", 1.0)
    return {
        "heights": heights_to_dds(heights),
        "lightmap": light_blocks_to_dds(light),
        "blends": blend_blocks_to_dds(blend),
        "mode": "full-synth",
    }


# ── Preview helpers (for the GUI) ───────────────────────────────────────


def hillshade(heights: np.ndarray) -> np.ndarray:
    """(H,W) uint16 -> (H,W,3) uint8 shaded-relief rendering."""
    f = heights.astype(np.float32) / 256.0
    gy, gx = np.gradient(f)
    # Light from the northwest
    shade = 0.5 + (gx * -0.35 + gy * -0.35) / 8.0
    base = f / 255.0 * 0.55 + 0.25
    v = np.clip((base * shade * 2.0) * 255, 0, 255).astype(np.uint8)
    return np.stack([v, v, v], axis=-1)
