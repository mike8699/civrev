#!/usr/bin/env python3
"""In-place byte patcher for FPKs.

Applies simple fixed-length byte replacements to a copy of a source FPK
WITHOUT decoding or repacking the archive. Only bytes at the specified
file offsets are changed; everything else — including the FPK's internal
alignment padding — is preserved byte-for-byte.

This was originally the safe alternative to `fpk.py repack` based on a
stale iter-8 claim that the repacker "strips alignment padding and
breaks Pregame.FPK boot." iter-177 (2026-04-14) empirically disproved
that: `fpk.py from_directory` on a plain extract of Pregame.FPK produces
a byte-identical output (same SHA-256 as the original), and a Pregame.FPK
rebuilt with a surgically-modified `gfx_chooseciv.gfx` boots cleanly in
RPCS3 (slot 15 sejong M6 PASS, slot 16 random M9 PASS). The "breaks boot"
claim was a hallucination or a bug in an earlier fpk.py revision; it no
longer applies. Keeping this byte-patcher for its minimal patch surface
when only small in-place edits are needed, but the repacker IS available
as a path for patches that need to change file sizes.

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
    # iter-190 (2026-04-15): ALL v0.9 substitutions REMOVED.
    #
    # Per iter-189's STRICT reading directive, Korea must be a brand-new
    # 17th civ at its own slot, not a rename of England at slot 15. The
    # v0.9 substitutions (Elizabeth→Sejong, English→Koreans, 16 English
    # city names → Korean city names) are a REJECTED approach — they
    # silently overwrite Elizabeth/England and cause §9 item 5 (stock civ
    # regression must include Elizabeth at slot 15) to fail.
    #
    # This function now returns an empty patch list, so the output FPK
    # is byte-identical to the stock Pregame.FPK. That keeps England
    # fully intact as Elizabeth/English at slot 15.
    #
    # Korea-specific data for the future 18th carousel cell must come
    # from Scaleform gfx_chooseciv.gfx edits plus PPU SetVariable calls,
    # not from in-place English→Korean byte substitution. See PRD §9
    # item 2 and iter-189 progress log entry for the 6-step plan.
    #
    # The file parsing code above is still kept intact in case any
    # future caller wants to do real byte-surgery on Pregame.FPK via
    # this module's `BytePatch` mechanism, but the patch list is
    # currently empty.
    _ = src_bytes  # unused — no patches derived from the input anymore
    return []

    # iter-160 attempted: gfx_chooseciv.gfx has a hardcoded
    # slotData16 fallback string "RANDOM" at FPK offset 0x117010c.
    # I patched it to "Korean" (both 6 bytes), and the file content
    # did change. But the carousel slot 16 cell title still rendered
    # "Random / Random" with no visible difference. The "RANDOM"
    # string in .gfx is NOT the displayed text — it's probably a
    # slot identifier/key used by the Scaleform script for internal
    # bookkeeping. The displayed title comes from yet another source.

    # iter-161 attempted: gfx_chooseciv.gfx per-slot table at 0x296f
    # has slot 16 → "barbarian" tag. Replaced with "korean\0\0\0"
    # (preserving 9-byte length). Carousel slot 16 cell title still
    # displayed "Random / Random" — no visible effect. The .gfx
    # constant pool only has TWO "Random" occurrences ("RANDOM"
    # slotData16 identifier at 0x5204 and "random" in "Math.random"
    # at 0x573f) — neither is the displayed title source. The
    # title is runtime-constructed by PPU code, not anywhere in
    # the .gfx or stringdatabase.gsd.
    # iter-161 patch reverted.

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
