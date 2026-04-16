#!/usr/bin/env python3
"""Extract Sejong leader portrait from CivRev2 Unity asset bundles.

Reads the Kor_Sejong_DIFF texture atlas from the CivRev2 Android OBB,
crops the face region, masks the black UV background to transparent,
and outputs ldr_korea.dds + ldr_lrg_korea.dds in the PS3 portrait
format (uncompressed 32-bit BGRA DDS, 128x128 and 272x288).

Usage:
    extract_cr2_sejong.py [--cr2-data <dir>] [--out <dir>]

Defaults:
    --cr2-data: civrev2/main.19.com.t2kgames.civrev2/assets/bin/Data
    --out:      korea_mod/_build/portraits
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

SEJONG_DIFF_BUNDLE = "0384035ce88066041b0472c1c6e88c91"
SEJONG_DIFF_NAME = "Kor_Sejong_DIFF"

FACE_CROP = (540, 55, 790, 300)
CANVAS_SIZE = 280
BLACK_THRESHOLD = 20

SMALL_SIZE = (128, 128)
LARGE_SIZE = (272, 288)


def write_dds_bgra(path: Path, img: Image.Image) -> None:
    """Write an uncompressed 32-bit BGRA DDS file matching PS3 LDR format."""
    w, h = img.size
    rgba = img.convert("RGBA")
    r, g, b, a = rgba.split()
    bgra = Image.merge("RGBA", (b, g, r, a))
    pixels = bgra.tobytes()

    hdr = bytearray(128)
    struct.pack_into("<4s", hdr, 0, b"DDS ")
    struct.pack_into("<I", hdr, 4, 124)        # dwSize
    struct.pack_into("<I", hdr, 8, 0x1007)     # dwFlags (CAPS|HEIGHT|WIDTH|PIXELFORMAT)
    struct.pack_into("<I", hdr, 12, h)         # dwHeight
    struct.pack_into("<I", hdr, 16, w)         # dwWidth
    struct.pack_into("<I", hdr, 20, 0)         # dwPitchOrLinearSize
    struct.pack_into("<I", hdr, 76, 32)        # ddspf.dwSize
    struct.pack_into("<I", hdr, 80, 0x41)      # ddspf.dwFlags (RGB|ALPHAPIXELS)
    struct.pack_into("<I", hdr, 88, 32)        # ddspf.dwRGBBitCount
    struct.pack_into("<I", hdr, 92, 0x00FF0000)  # R mask
    struct.pack_into("<I", hdr, 96, 0x0000FF00)  # G mask
    struct.pack_into("<I", hdr, 100, 0x000000FF) # B mask
    struct.pack_into("<I", hdr, 104, 0xFF000000) # A mask
    struct.pack_into("<I", hdr, 108, 0x1000)   # dwCaps (TEXTURE)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(hdr) + pixels)
    print(f"  wrote {path} ({w}x{h}, {len(pixels)+128} bytes)")


def extract_sejong_diff(cr2_data: Path) -> Image.Image:
    """Extract the Sejong diffuse texture from CivRev2 Unity bundles."""
    try:
        import UnityPy
    except ImportError:
        sys.exit("UnityPy not installed: pip install UnityPy")

    bundle_path = cr2_data / SEJONG_DIFF_BUNDLE
    if not bundle_path.is_file():
        sys.exit(f"CivRev2 bundle not found: {bundle_path}")

    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            name = getattr(data, "m_Name", "") or getattr(data, "name", "")
            if name == SEJONG_DIFF_NAME:
                return data.image

    sys.exit(f"{SEJONG_DIFF_NAME} not found in {bundle_path.name}")


def make_portrait(diff_img: Image.Image) -> Image.Image:
    """Crop Sejong's face from the UV atlas and mask background."""
    face = diff_img.crop(FACE_CROP)
    px = np.array(face.convert("RGBA"))
    mask = (
        (px[:, :, 0] < BLACK_THRESHOLD)
        & (px[:, :, 1] < BLACK_THRESHOLD)
        & (px[:, :, 2] < BLACK_THRESHOLD)
    )
    px[mask] = [0, 0, 0, 0]

    canvas = Image.new("RGBA", (CANVAS_SIZE, CANVAS_SIZE), (0, 0, 0, 0))
    face_clean = Image.fromarray(px)
    fw, fh = face_clean.size
    canvas.paste(face_clean, ((CANVAS_SIZE - fw) // 2, (CANVAS_SIZE - fh) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    default_cr2 = here.parent.parent / "civrev2" / "main.19.com.t2kgames.civrev2" / "assets" / "bin" / "Data"
    parser.add_argument("--cr2-data", type=Path, default=default_cr2)
    parser.add_argument("--out", type=Path, default=here / "_build" / "portraits")
    args = parser.parse_args()

    print(f"Extracting {SEJONG_DIFF_NAME} from {args.cr2_data.name}/...")
    diff_img = extract_sejong_diff(args.cr2_data)
    print(f"  texture: {diff_img.size[0]}x{diff_img.size[1]}")

    portrait = make_portrait(diff_img)
    print(f"  portrait canvas: {portrait.size[0]}x{portrait.size[1]}")

    small = portrait.resize(SMALL_SIZE, Image.LANCZOS)
    large = portrait.resize(LARGE_SIZE, Image.LANCZOS)

    write_dds_bgra(args.out / "ldr_korea.dds", small)
    write_dds_bgra(args.out / "ldr_lrg_korea.dds", large)

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
