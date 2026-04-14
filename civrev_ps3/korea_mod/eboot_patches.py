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
from dataclasses import dataclass
from pathlib import Path


# The clean base EBOOT. All file offsets in PATCHES are against this
# specific file. Hash-gate to catch accidental base drift.
EXPECTED_BASE_SHA256 = (
    "f69b4e4ed8cd5e7fa668bb65ea1d19f87b6fb17d3ada122183a3f3e6054a06ce"
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
    # ITER-14: bump InitGenderedNames entry-count from 17 → 18 for
    # RulerNames and CivNames. The parser allocates a 17-wide buffer
    # when called with count=0x11; feeding civnames_enu.txt or
    # rulernames_enu.txt a 18th line currently OOB-writes that buffer
    # and crashes boot (see verification/M2_iter12/summary.md).
    #
    # These are the ONLY two call sites in the binary that pass
    # count=17 to the name-file init function (FUN_0xa21ce8 in the
    # Ghidra EBOOT, equivalent sequence at 0x00a2ed6c..0x00a2ee80 in
    # EBOOT_v130_clean.ELF). Located via Ghidra headless analysis in
    # iter-14 by matching the full count-arg sequence
    # (0x101, 0x42, 0x80, 0x11, 0x11) inside a single function.
    #
    # Each instruction is `li r5, 0x11` (opcode 14, encoded as
    # 0x38a00011). Bumping to `li r5, 0x12` = 0x38a00012. One byte
    # change per site: low byte (file offset +3) goes from 0x11 to
    # 0x12.
    Patch(
        offset=0x00a2ee38,
        expected_old=b"\x38\xa0\x00\x11",
        new=b"\x38\xa0\x00\x12",
        description="li r5,17 → li r5,18 (RulerNames_ init count)",
    ),
    Patch(
        offset=0x00a2ee7c,
        expected_old=b"\x38\xa0\x00\x11",
        new=b"\x38\xa0\x00\x12",
        description="li r5,17 → li r5,18 (CivNames_ init count)",
    ),

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

    # ITER-133: HDD EBOOT path discovery, and revert of iter-131/132.
    #
    # Critical finding: RPCS3 boots from
    # `~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN`,
    # NOT from `civrev_ps3/modified/PS3_GAME/USRDIR/EBOOT.BIN`. The
    # disc EBOOT in the modified/ tree is read by entrypoint.sh but
    # only copied over the disc copy if the DLC EBOOT magic is `7fELF`
    # — the stock DLC EBOOT is an encrypted SCE SELF, so the copy
    # is skipped, and RPCS3 prefers the dev_hdd0 EBOOT (the actual
    # update path) over the disc one anyway.
    #
    # Result: every iteration from iter-7 through iter-132 was
    # patching civrev_ps3/modified/...EBOOT.BIN and verifying nothing.
    # All "fault silenced / fault returns" results were actually
    # against a stable, never-modified encrypted SCE EBOOT in
    # dev_hdd0. The fact that the iter-127 broken_18 fault and the
    # iter-132 "civ18-only fix" both showed identical crash signatures
    # was because they were running the SAME unmodified binary.
    #
    # iter-133 fix: the build pipeline must install the patched ELF
    # to BOTH locations (modified/ for git tracking, dev_hdd0/ for
    # actual RPCS3 boot). The `install_eboot.sh` helper added in
    # this iteration writes both.
    #
    # Re-tested iter-132's `cmpwi cr7, r0, 0` patch with the proper
    # HDD path: it DOES silence the iter-127 0xc26a00 fault for both
    # civ18-only and broken_18, BUT also breaks v0.9 booting. v0.9
    # crashes at 0x0141fa4c (sys_prx libnet stub) reading 0x0,
    # which means the function `FUN_00c26a00` is NOT a NULL-safe
    # noop — it's a lazy-init or in-place allocator for unset
    # FStringAs. Skipping it leaves downstream FStringAs uninitialized
    # and a later libnet thunk dereferences NULL.
    #
    # Conclusion: iter-132 patch reverted. The real fix needs to
    # let FUN_00c26a00 RUN even when buf == NULL (so it allocates
    # a buf properly). That requires either:
    #   (a) understanding the function's allocation path and
    #       triggering it correctly for the 18th entry slot, or
    #   (b) chasing the upstream that fails to allocate the
    #       18th slot's FStringA in the first place.
    # Both require deeper static analysis of the parser and
    # the FStringA lifecycle.
    #
    # ITER-132: null-guard at FUN_00c26a00 (replaces iter-131 wrapper
    # which was aimed at the wrong fault site).
    #
    # iter-131 placed a null-guard wrapper around FUN_00c25f8c
    # (FStringA::SetLength) on the theory that the civ18-only
    # crash happened inside SetLength. But re-testing with the
    # wrapper installed reproduced the SAME fault at PC 0xc26a00
    # reading 0xfffffff8 — the wrapper was catching the NULL and
    # SetLength was never entered, yet the crash persisted.
    #
    # Re-reading FUN_00c26a00's full disassembly (0xc26a00..0xc26ac4)
    # shows the real fault is in the function's TAIL, not in
    # SetLength:
    #
    #   0xc26a7c: lwz  r11, 0(r30)          ; r11 = *param_1 = buf
    #   0xc26a80: addi r9, r11, -16          ; r9 = buf - 16
    #   0xc26a84: clrldi r9, r9, 32          ; r9 = r9 & 0xffffffff
    #   0xc26a88: lwz  r0, 12(r9)            ; r0 = length        ★
    #   0xc26a8c: add  r11, r11, r0          ; r11 = buf + length
    #   0xc26a90: li   r0, 0
    #   0xc26a94: clrldi r11, r11, 32
    #   0xc26a98: stb  r0, 0(r11)            ; *(buf+length) = 0  ★★
    #   0xc26a9c: b    0xc26aa8              ; epilogue
    #
    # With buf == NULL: r11 = 0, r9 = 0xfffffff0, the lwz at
    # 0xc26a88 reads 0xfffffffc (civ18-only), and the stb at
    # 0xc26a98 writes 0x2a12c when buf was corrupted to 0x2a120
    # (both-18). Both faults live in the SAME tail block — they
    # just differ in which of the two memory ops trips first.
    #
    # Clean fix: hijack the existing early-exit at 0xc26a44/48.
    #
    #   Original:
    #     0xc26a3c: lwz   r0, 0(r30)      ; r0 = *param_1 (buf)
    #     0xc26a40: clrldi r9, r3, 32
    #     0xc26a44: cmpw  cr7, r5, r0     ; cr7 = (param_3 == buf)
    #     0xc26a48: beq   cr7, 0xc26aa8   ; skip tail if equal
    #
    # The `param_3 == *param_1` comparison is an oddball
    # optimization — comparing an int arg to a pointer value is
    # semantically weird and only fires by coincidence. It's a
    # safe instruction to repurpose.
    #
    #   Patched:
    #     0xc26a3c: lwz   r0, 0(r30)      ; r0 = *param_1 (unchanged)
    #     0xc26a40: clrldi r9, r3, 32     ; (unchanged)
    #     0xc26a44: cmpwi cr7, r0, 0      ; NEW: cr7 = (buf == 0)
    #     0xc26a48: beq   cr7, 0xc26aa8   ; NEW meaning: skip if NULL
    #
    # One-word in-place patch. cmpwi cr7, r0, 0 = 0x2f800000.
    # The existing beq cr7, +0x60 at 0xc26a48 is unchanged —
    # we're just changing what cr7 means when we reach it.
    #
    # Silences both the civ18-only NULL read AND the both-18 RO
    # write case, since both come from the same tail block that
    # this early-exit skips entirely.
    # iter-132 cmpwi patch REMOVED in iter-133: it broke v0.9 booting
    # because skipping FUN_00c26a00 on NULL-buf prevents the legitimate
    # buf-allocation path (FUN_00c26a00 is the lazy-init for an unset
    # FStringA, not a NULL-safe noop).
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
