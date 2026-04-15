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


# The clean base EBOOT. iter-137 switched the base from
# `EBOOT_v130_clean.ELF` (a SELF→ELF extract that was missing the SCE
# loader's runtime fixups, causing a libnet-stub NULL deref at boot)
# to `EBOOT_v130_decrypted.ELF` produced by `rpcs3 --decrypt`. The
# decrypted ELF carries 8 program headers including PT_SCE_RELA and
# PT_TLS, and has the .data sprx slots (e.g. 0x18b5a08) properly
# populated, so RPCS3's plain-ELF loader path boots it cleanly.
#
# Hash-gate against the new base.
EXPECTED_BASE_SHA256 = (
    "318eab2c91c23ea08b56fb92f512f69a3404967e5e794384157b87ea4786ce96"
)


@dataclass
class Patch:
    """A single-site byte patch.

    `offset` is interpreted as a VIRTUAL ADDRESS, not a file offset.
    The patcher walks the ELF's PT_LOAD program headers to translate
    each vaddr to the corresponding file offset before reading or
    writing. This is necessary because the iter-137 decrypted ELF has
    `p_offset != p_vaddr` (file offset 0x0 for PT_LOAD #0 with vaddr
    0x10000), unlike the old `EBOOT_v130_clean.ELF` where they matched.

    The `expected_old` byte values are unchanged across both ELFs —
    only the file offsets where they live differ.
    """

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
    # iter-202: empirically verified these patches are ACTIVE (not
    # inert). Removing them and booting produced an RSX init hang,
    # which confirms the dispatcher at FUN_00a2ec54 IS called at
    # runtime (via function descriptor + bctrl, not a direct bl,
    # which is why Python's bl-scan found 0 callers and why iter-
    # 201's "dead code" hypothesis was wrong).
    #
    # iter-202 ALSO corrected the TOC base for this dispatcher from
    # 0x193a288 to 0x194a1f8 — the function descriptor at
    # 0x18f0380..0x18f038c holds `entry = 0xa2ec54, toc = 0x194a1f8`.
    # With the correct r2, all 8 name-file buffer-holder slots
    # resolve to writable .bss addresses at 0x1ac939c..0x1ac93b8
    # (the civs holder is at 0x1ac93b8 specifically).
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

    # ITER-198: bump the 14 downstream "li r8, 0x10" (=16) consumer
    # sites to li r8, 0x11 (=17). iter-197's Ghidra decompile of the
    # parser dispatcher (FUN_00a2ec54) and worker (FUN_00a2e640)
    # established that the parser is dynamic — it allocates
    # (count*12 + 4) bytes per name file and stores all entries
    # correctly. The "17-wide buffer" model from iter-7..72 was wrong.
    #
    # The actual cap on civnames visibility lives in two consumer
    # functions at 0x011679xx / 0x01167dxx that load each of the 7
    # name-file buffer-pointer TOC slots and call a vtable method
    # with `r8 = 0x10` as the iteration count. With li r8 at 0x10,
    # they iterate 16 entries (indices 0..15) — exactly the 16 stock
    # civs, skipping the internal "Barbarians" placeholder at index
    # 16. To make a 17th civ (Korea inserted at index 16, pushing
    # Barbarians to 17) visible, every one of these `li r8, 0x10`
    # sites must be bumped to `li r8, 0x11`.
    #
    # Encoding: `li r8, 0x10` = `addi r8, 0, 0x10` = `0x39000010`.
    # Bumped: `li r8, 0x11` = `0x39000011`. One byte change per site
    # (file offset +3: 0x10 → 0x11). Same-size, in-place.
    #
    # The 14 sites came from iter-197's exhaustive scan
    # (Iter197ParserWriteTarget.py output): every lwz of any of the
    # 7 name-file buffer-pointer TOC slots (r2 + 0x1404/0x1408/
    # 0x140c/0x1410/0x1414/0x1418/0x141c) sits within ±24 bytes of
    # one of these 14 li r8 instructions, in two consumer functions
    # that iterate all 7 name files in sequence.
    #
    # Per-site mapping (from iter-197 findings.md):
    #   consumer A (0x011676xx-0x01167900):  TECH FAMOUS CITIES
    #                                         WONDERS WONDERS_FEM
    #                                         RULERS CIVS
    #   consumer B (0x01167a00-0x01167dc8):  TECH FAMOUS CITIES
    #                                         WONDERS WONDERS_FEM
    #                                         RULERS CIVS
    # iter-210 SELECTIVE TEST RESULT: 2 CIVS-only sites are SAFE
    # (boot passes) but INERT. No shipping value alone.
    #
    # iter-211 BINARY SEARCH RESULT: all 7 of consumer A's
    # patches together are SAFE but INERT. boot passes, slot 16
    # still Random, slot 17 still clamped. So the iter-198
    # breakage is ENTIRELY in consumer B's 7 patches. But since
    # consumer A is inert, even bisecting consumer B further
    # has no carousel-rendering value.
    # Patch(0x011676dc, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A TECH"),
    # Patch(0x01167744, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A FAMOUS"),
    # Patch(0x011677ac, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A CITIES"),
    # Patch(0x01167814, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A WONDERS"),
    # Patch(0x0116787c, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A WONDERS_FEM"),
    # Patch(0x011678e4, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A RULERS"),
    # Patch(0x01167948, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "A CIVS"),
    # Consumer B sites stay disabled:
    # Patch(0x011676dc, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A TECH"),
    # Patch(0x01167744, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A FAMOUS"),
    # Patch(0x011677ac, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A CITIES"),
    # Patch(0x01167814, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A WONDERS"),
    # Patch(0x0116787c, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A WONDERS_FEM"),
    # Patch(0x011678e4, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer A RULERS"),
    # Patch(0x01167af4, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B TECH"),
    # Patch(0x01167b88, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B FAMOUS"),
    # Patch(0x01167c10, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B CITIES"),
    # Patch(0x01167ca0, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B WONDERS"),
    # Patch(0x01167d00, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B WONDERS_FEM"),
    # Patch(0x01167d64, b"\x39\x00\x00\x10", b"\x39\x00\x00\x11", "consumer B RULERS"),

    # iter-206 DIAGNOSTIC RESULT: b . traps at FUN_001dc0d8 and
    # FUN_0x111dd70 both PASSED. Romans M9 slot 0 runs clean with
    # both functions trapped. Conclusion: BOTH are off the
    # boot-to-civ-select-to-in-game path — joining iter-150
    # (FUN_001e49f0) and iter-154 (FUN_011675d8) on the "not the
    # carousel" list. Traps removed; diagnostic recorded.

    # iter-208 DIAGNOSTIC RESULT: b . at 0xf070a0 PASSED (Romans
    # M9 clean). 0xf070a0 is NOT on the civ-select path, so
    # iter-193's "ChooseCiv panel loader wrapper" hypothesis is
    # WRONG. Either the function is dead code, or the civ-select
    # panel is loaded under a different name / via a different
    # path entirely. Trap removed; diagnostic recorded.
    # Patch(
    #     offset=0x00f070a0,
    #     expected_old=b"\x80\x82\xd7\x78",
    #     new=b"\x48\x00\x00\x00",
    #     description="DIAG iter-208: b . trap at 0xf070a0",
    # ),

    # iter-209 DIAGNOSTIC RESULT: b . at FUN_001262a0 PASSED
    # (Romans M9 clean). FUN_001262a0 is the 5th candidate
    # consumer function ruled out (joining FUN_001e49f0,
    # FUN_011675d8, FUN_001dc0d8, FUN_0x111dd70). The CIV_*.dds
    # icon table iter-208 discovered IS used somewhere, but not
    # on the boot-to-civ-select-to-in-game path. Almost
    # certainly the civilopedia init.
    # Patch(
    #     offset=0x001262a0,
    #     expected_old=b"\xf8\x21\xff\x71",
    #     new=b"\x48\x00\x00\x00",
    #     description="DIAG iter-209: b . trap at FUN_001262a0 entry",
    # ),
    # Patch(
    #     offset=0x001dc0d8,
    #     expected_old=b"\xf8\x21\xff\x61",
    #     new=b"\x48\x00\x00\x00",
    #     description="DIAG iter-206: b . trap at FUN_001dc0d8 entry",
    # ),
    # Patch(
    #     offset=0x00111dd70,
    #     expected_old=b"\xf8\x21\xff\x71",
    #     new=b"\x48\x00\x00\x00",
    #     description="DIAG iter-206: b . trap at FUN_0x111dd70 entry",
    # ),

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

    # iter-144 BOTH patches REMOVED. Diagnostic test (Rome → China at
    # slot 0) had zero visible effect on the carousel — Caesar still
    # rendered. The LDR_*.dds table at 0x01937c44 is NOT the civ-select
    # carousel cell array. The carousel uses 3D leader-head models
    # (LH-* assets), not flat DDS portraits. The LDR table is for
    # diplomacy/pediainfo flat portrait fallbacks.

    # iter-145 DIAG patch REMOVED. Test (Caesar → Elizabeth at slot 0
    # in the LEADER table at 0x0194b434) had zero visible effect on
    # the carousel — Caesar still rendered with "Caesar / Romans"
    # labels. iter-4's PRD note was correct: this 16-entry LEADER
    # table is dead rodata. The carousel reads its display names
    # from somewhere else — possibly a runtime-allocated struct
    # populated from civnames/rulernames parser output, or yet
    # another table not yet located.

    # iter-150 DIAG patch REMOVED. Patched FUN_001e49f0 entry with
    # `b .` (infinite loop). Ran korea_play 0 romans — test PASSED
    # with M9 in_game_hud=true, slot 0 highlighted_ok=true. That
    # means FUN_001e49f0 is NEVER CALLED during the entire civ-select
    # render path — my iter-146 conclusion that this was the "per-cell
    # carousel data binder" was wrong. The function reads parser
    # TOC offsets for some OTHER purpose (probably in-game player-info
    # display, diplomacy panels, or pediainfo entries). The vtable at
    # 0x018c9ae0 is not the civ-select carousel cell class.

    # iter-154 DIAG patch REMOVED. Patched FUN_011675d8 entry with `b .`
    # and ran korea_play — test PASSED again. FUN_011675d8 is also never
    # called during civ-select. Combined with iter-150's FUN_001e49f0
    # disproof, **both static consumers of r2+0x141c outside the parser
    # writer area are NOT the carousel.**
    #
    # Conclusion: the carousel reads the civnames buffer via a CACHED
    # pointer, not via the TOC slot. The buffer pointer is stored in a
    # long-lived register or struct field after initial init, and
    # subsequent reads bypass r2+0x141c entirely. Static `lwz rN,
    # 0x141c(r2)` search cannot find such consumers.

    # iter-155 DIAG patch REMOVED. Patched FUN_001e489c (vtable[+0]
    # constructor) entry with `b .`. RPCS3 timed out at "Waiting for
    # RSX init" — the function is called VERY EARLY during boot, before
    # the title screen, before civ-select. The vtable class at
    # 0x018c9ae0 is part of the CORE BOOT PATH, probably a base UI
    # class that lots of game systems derive from. Hanging its
    # constructor breaks ALL of UI init, not just the carousel.

    # iter-156 DIAG: tested both EBOOT "Caesar" string locations
    # (0x16a38a8 and 0x0169dcb4). Neither patch (Caesar → Korean)
    # affected what the carousel displays — the slot 0 cell still
    # rendered "Caesar / Romans". This conclusively proves the
    # carousel reads its display text from RUNTIME PARSER OUTPUT
    # BUFFERS (heap memory populated from rulernames_enu.txt /
    # civnames_enu.txt at boot), NOT from static EBOOT strings.

    # ITER-176 REVERT: the iter-159..175 slot-16-repurpose patches
    # are removed because user directive (iter-176 PRD update)
    # tightened DoD item 1 to require Random remain selectable as
    # its own option. Those patches converted the Random cell's
    # visible text to "Korean Sejong" / era bonuses / Korean
    # description, which made Random unreachable. Reverting them
    # restores the stock Random cell at slot 16.
    #
    # iter-4 (ADJ_FLAT relocation) and iter-14 (parser count bumps)
    # stay — they're infrastructure for the future true-17th-civ
    # path, not part of the slot-16-repurpose workaround.
    #
    # Removed in this revert:
    #   - iter-159: 0x016a70e8 slot 16 description
    #   - iter-162: 0x0169d290 slot 16 title "Random" → "Korean"
    #   - iter-165: 0x017f4088 "Sejong"/"Korean Sejong" allocation
    #   - iter-165: 0x0193aca8 TOC redirect
    #   - iter-167: 0x016a70b9/c7/d7/e3 era bonus "???" fills
    #   - iter-175: extension of iter-165 to "Korean Sejong"
    #
    # All static-analysis findings from those iterations remain
    # valid and are preserved in the PRD Progress Log. Re-applying
    # any of them is a one-line addition to PATCHES below, so no
    # code is lost — just disabled.
]


def _build_vaddr_to_file_offset(raw: bytes):
    """Build a (vaddr_lo, vaddr_hi, p_offset) table from PT_LOAD headers."""
    e_phoff = _struct.unpack(">Q", raw[0x20:0x28])[0]
    e_phnum = _struct.unpack(">H", raw[0x38:0x3a])[0]
    segments: list[tuple[int, int, int]] = []
    for i in range(e_phnum):
        off = e_phoff + i * 56
        p_type = _struct.unpack(">I", raw[off : off + 4])[0]
        if p_type != 1:
            continue
        p_offset = _struct.unpack(">Q", raw[off + 8 : off + 16])[0]
        p_vaddr = _struct.unpack(">Q", raw[off + 16 : off + 24])[0]
        p_filesz = _struct.unpack(">Q", raw[off + 32 : off + 40])[0]
        if p_filesz == 0:
            continue
        segments.append((p_vaddr, p_vaddr + p_filesz, p_offset))
    return segments


def _vaddr_to_file(segments, vaddr: int) -> int | None:
    for lo, hi, p_offset in segments:
        if lo <= vaddr < hi:
            return vaddr - lo + p_offset
    return None


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

    segments = _build_vaddr_to_file_offset(raw)

    mismatches = 0
    applied = 0
    for p in PATCHES:
        file_off = _vaddr_to_file(segments, p.offset)
        if file_off is None:
            print(
                f"  {p.offset:#010x}  vaddr not in any PT_LOAD segment  "
                f"# {p.description}"
            )
            mismatches += 1
            continue
        current = bytes(raw[file_off : file_off + len(p.expected_old)])
        status = "ok" if current == p.expected_old else "MISMATCH"
        print(
            f"  vaddr {p.offset:#010x}  file_off {file_off:#010x}  "
            f"old={p.expected_old.hex()} "
            f"new={p.new.hex()}  {status}  # {p.description}"
        )
        if current != p.expected_old:
            mismatches += 1
            continue
        if not dry_run:
            out[file_off : file_off + len(p.new)] = p.new
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
    src = Path(args.src) if args.src else here.parent / "EBOOT_v130_decrypted.ELF"
    dest = Path(args.dest) if args.dest else here / "_build" / "EBOOT_korea.ELF"

    if not src.exists():
        print(f"[FATAL] base EBOOT missing: {src}", file=sys.stderr)
        return 2

    return apply_patches(src, dest, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
