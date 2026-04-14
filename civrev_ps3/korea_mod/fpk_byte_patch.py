#!/usr/bin/env python3
"""In-place byte patcher for FPKs.

Applies simple fixed-length byte replacements to a copy of a source FPK
WITHOUT decoding or repacking the archive. Only bytes at the specified
file offsets are changed; everything else — including the FPK's internal
alignment padding — is preserved byte-for-byte.

This is the safe alternative to `fpk.py repack`, which re-emits the whole
archive and strips the original's alignment padding (empirically fine for
Common0.FPK but breaks Pregame.FPK boot).

Usage: fpk_byte_patch.py <src.FPK> <dst.FPK>

The patch list is hardcoded below. Every patch asserts expected_old
matches before writing, so if the base FPK drifts we bail out.
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BytePatch:
    offset: int
    expected_old: bytes
    new: bytes
    description: str

    def __post_init__(self) -> None:
        if len(self.expected_old) != len(self.new):
            raise ValueError(
                f"patch at {self.offset:#x}: old/new length mismatch "
                f"({len(self.expected_old)} vs {len(self.new)})"
            )


# File offsets inside the stock PS3 Pregame.FPK (SHA-confirmed by
# iter-3's baseline). Every patch below is an in-place replacement
# within a single extracted file's slot.
#
# rulernames_enu.txt lives at FPK offset 0x14af8, size 0xe2.
# civnames_enu.txt   lives at FPK offset 0x14bda, size 0xe9.
#
# v0.9 (iter-8): REPLACE England with Korea.
#
# PRD §9 DoD asks for Korea as the **17th** civ, not a replacement. This
# patch is an interim — it ships Korea as a renamed England at slot 15
# (i.e., Korea takes England's portrait, color, bonuses, and unique
# unit list). Strictly this is NOT v1.0 DoD-compliant; iter-9+ will
# either extend civnames/rulernames to 18 entries or land a real
# 17-slot extension.
#
# Why a replacement first: the civ-select cursor clamps at a hardcoded
# 17 slots (16 civs + Random), so even if we added a 17th entry to
# civnames_enu.txt / rulernames_enu.txt, the cursor can't reach it
# without an EBOOT patch to the cursor-bound constant — which is a
# separate iteration of work. Shipping Korea as a replacement lets us
# verify M6/M7 gameplay soak end-to-end first.
#
# The offsets below are computed from the iter-8 raw dump of Pregame.FPK.

PATCHES: list[BytePatch] = [
    # rulernames_enu.txt: "Elizabeth" appears once at gsd-local offset 0xc2
    # → absolute FPK offset 0x14af8 + 0xc2 = 0x14bba.
    # Actually let's compute it at runtime for safety via the search below.
]


def _build_patches(src_bytes: bytes) -> list[BytePatch]:
    patches: list[BytePatch] = []

    # rulernames_enu.txt region
    ruler_off = 0x14af8
    ruler_sz = 0xe2
    ruler = src_bytes[ruler_off : ruler_off + ruler_sz]
    eliz_rel = ruler.find(b"Elizabeth")
    if eliz_rel < 0:
        raise RuntimeError("Elizabeth not found in rulernames_enu.txt slot")
    # "Sejong" is 6 chars; pad with 3 trailing spaces to match "Elizabeth"'s
    # 9-char slot so we don't shift the rest of the file. The text parser
    # trims trailing whitespace inside a field, so the displayed name is
    # still "Sejong". Verified by iter-8 boot with "SejongTst" (9 chars).
    patches.append(
        BytePatch(
            offset=ruler_off + eliz_rel,
            expected_old=b"Elizabeth",
            new=b"Sejong   ",
            description='rulernames_enu: "Elizabeth" → "Sejong   " (9 bytes)',
        )
    )

    # civnames_enu.txt region
    civ_off = 0x14bda
    civ_sz = 0xe9
    civ = src_bytes[civ_off : civ_off + civ_sz]
    eng_rel = civ.find(b"English")
    if eng_rel < 0:
        raise RuntimeError("English not found in civnames_enu.txt slot")
    patches.append(
        BytePatch(
            offset=civ_off + eng_rel,
            expected_old=b"English",
            new=b"Koreans",
            description='civnames_enu: "English" → "Koreans" (7 bytes)',
        )
    )

    return patches


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} <src.FPK> <dst.FPK>", file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    raw = src.read_bytes()
    out = bytearray(raw)

    patches = _build_patches(raw)

    for p in patches:
        current = bytes(out[p.offset : p.offset + len(p.expected_old)])
        if current != p.expected_old:
            print(
                f"[FATAL] {p.offset:#x}: expected {p.expected_old!r} got {current!r}",
                file=sys.stderr,
            )
            return 3
        out[p.offset : p.offset + len(p.new)] = p.new
        print(f"  {p.offset:#010x}  {p.description}  [OK]")

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(out))
    print(f"wrote {dst} ({len(out)} bytes, {len(patches)} patches applied)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
