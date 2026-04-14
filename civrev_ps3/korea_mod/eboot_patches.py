#!/usr/bin/env python3
"""
korea_mod/eboot_patches.py — apply the Korea civ mod's byte patches to
EBOOT_v130_clean.ELF, producing EBOOT_korea.ELF.

Run with --dry-run to print every planned patch site, read the current
bytes at each site, and verify that the expected-old-bytes match.
This is M0a in the verification plan; it must exit 0 before any
emulator-backed milestones run.

v1.0 status: the PATCH LIST IS EMPTY. Investigation §5.1 has not yet
located the `_NCIV` initializer (the single instruction that writes
the initial civ-count integer), so we have nothing to patch. The
script still runs end-to-end — M0a passes trivially because there are
zero planned sites to mismatch — but the output EBOOT is byte-
identical to the input. This is intentional scaffolding: once §5.1
lands in a future iteration, adding entries to the PATCHES list is
the only change needed to make this script productive.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path


# The clean base EBOOT. All file offsets in PATCHES are against this
# specific file. Hash-gate to catch accidental base drift.
EXPECTED_BASE_SHA256 = (
    # Computed from civrev_ps3/EBOOT_v130_clean.ELF when this script
    # was first wired. If the hash ever changes, regenerate PATCHES
    # against the new base and bump this constant.
)


@dataclass
class Patch:
    """A single-site byte patch against EBOOT_v130_clean.ELF."""

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


# ---------------------------------------------------------------------------
# v1.0 patch list — extends the live civ-adjective pointer table from 16 to
# 17 entries by:
#
#   1. Allocating the null-terminated string "Korean\0" in the large
#      zero-fill padding region at file offset 0x017f4038 (inside a
#      ~144 KB zero run at 0x017f4036..0x01818036).
#   2. Writing a new 17-entry pointer table at 0x017f4040 (4-byte
#      aligned, immediately after the Korean string). Entries 0..15
#      duplicate the original ADJ_FLAT table; entry 16 points at the
#      new "Korean" string.
#   3. Updating the two TOC entries at 0x01938354 and 0x019398b0 —
#      which both currently hold 0x0195fe28 — to point at the new
#      table base 0x017f4040.
#
# This relocates ADJ_FLAT without touching the original table's bytes,
# so any stray reader (e.g. a function we haven't yet cataloged) that
# still sees 0x0195fe28 will read the unchanged 16-entry data.
#
# The static 0x194bxxx tables (LDR_TAG, CIV_TAG, ADJ_PAIR, LEADER_NAMES)
# are confirmed dead rodata (§5.1) and intentionally NOT patched.
# ---------------------------------------------------------------------------

import struct as _struct

# Original ADJ_FLAT entries (virtual addresses of the 16 adjective strings).
_ORIG_ADJ_ENTRIES = [
    0x016a49f8,  # Roman
    0x016a4a00,  # Egyptian
    0x016a4a10,  # Greek
    0x016a4a18,  # Spanish
    0x016a4a20,  # German
    0x016a4a28,  # Russian
    0x016a4a30,  # Chinese
    0x016a4a38,  # American
    0x016a4a48,  # Japanese
    0x016a4a58,  # French
    0x016a4a60,  # Indian
    0x016a4a68,  # Arab
    0x016a4a70,  # Aztec
    0x016a4a78,  # African
    0x016a4a80,  # Mongolian
    0x01692b00,  # English
]

_KOREAN_STRING_VA  = 0x017f4038   # 8 bytes: "Korean\0\0"
_NEW_TABLE_VA      = 0x017f4040   # 68 bytes: 17 × 4-byte pointers
_NEW_ENTRY_KOREAN  = _KOREAN_STRING_VA

# Byte encodings
_NEW_TABLE_BYTES = b"".join(_struct.pack(">I", p) for p in _ORIG_ADJ_ENTRIES + [_NEW_ENTRY_KOREAN])
_KOREAN_BYTES    = b"Korean\0\0"

# 32-bit BE pointer encodings of the old and new table base
_OLD_BASE_BE = _struct.pack(">I", 0x0195fe28)
_NEW_BASE_BE = _struct.pack(">I", _NEW_TABLE_VA)

PATCHES: list[Patch] = [
    # (1) Write "Korean\0\0" into the padding region.
    Patch(
        offset=_KOREAN_STRING_VA,
        expected_old=b"\0" * len(_KOREAN_BYTES),
        new=_KOREAN_BYTES,
        description='allocate "Korean\\0" string in .rodata padding',
    ),
    # (2) Write the 17-entry pointer table.
    Patch(
        offset=_NEW_TABLE_VA,
        expected_old=b"\0" * len(_NEW_TABLE_BYTES),
        new=_NEW_TABLE_BYTES,
        description="write extended ADJ_FLAT (17 entries) to .rodata padding",
    ),
    # (3a) Redirect TOC entry at 0x01938354 (r2-0x1f34).
    Patch(
        offset=0x01938354,
        expected_old=_OLD_BASE_BE,
        new=_NEW_BASE_BE,
        description="redirect TOC entry r2-0x1f34 → new ADJ_FLAT base",
    ),
    # (3b) Redirect TOC entry at 0x019398b0 (r2-0x9d8).
    Patch(
        offset=0x019398b0,
        expected_old=_OLD_BASE_BE,
        new=_NEW_BASE_BE,
        description="redirect TOC entry r2-0x9d8 → new ADJ_FLAT base",
    ),
]


def apply_patches(
    base: Path, dest: Path | None, dry_run: bool
) -> int:
    raw = base.read_bytes()
    out = bytearray(raw)

    if EXPECTED_BASE_SHA256:
        actual = hashlib.sha256(raw).hexdigest()
        if actual != EXPECTED_BASE_SHA256:
            print(
                f"[FATAL] base hash mismatch: {actual} != {EXPECTED_BASE_SHA256}",
                file=sys.stderr,
            )
            return 2

    mismatches = 0
    applied = 0
    for p in PATCHES:
        current = bytes(raw[p.offset : p.offset + len(p.expected_old)])
        status = "ok" if current == p.expected_old else "MISMATCH"
        print(
            f"  {p.offset:#010x}  "
            f"old={p.expected_old.hex()} "
            f"new={p.new.hex()}  {status}  # {p.description}"
        )
        if current != p.expected_old:
            mismatches += 1
            continue
        if not dry_run:
            out[p.offset : p.offset + len(p.new)] = p.new
            applied += 1

    print(f"[eboot_patches] {len(PATCHES)} planned, {mismatches} mismatch, {applied} applied")

    if mismatches:
        return 1

    if not dry_run and dest is not None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bytes(out))
        print(f"[eboot_patches] wrote {dest}")

    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=None, required=False)
    ap.add_argument("--out", dest="dest", default=None, required=False)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    src = Path(args.src) if args.src else here.parent / "EBOOT_v130_clean.ELF"
    dest = Path(args.dest) if args.dest else here / "_build" / "EBOOT_korea.ELF"

    if not src.exists():
        print(f"[FATAL] base EBOOT missing: {src}", file=sys.stderr)
        return 2

    return apply_patches(src, dest, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
