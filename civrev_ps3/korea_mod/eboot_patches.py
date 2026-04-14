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


# Concrete patch list — empty until §5.1 lands. The structure is here
# so that future iterations can drop Patch(...) instances into this
# list without touching the rest of the file.
PATCHES: list[Patch] = []


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
