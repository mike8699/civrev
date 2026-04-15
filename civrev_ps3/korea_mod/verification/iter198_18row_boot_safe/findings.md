# iter-198: 18-row civnames/rulernames overlay BOOTS CLEAN — iter-14 finding 4 disproved

**Date:** 2026-04-15
**Dependencies:** iter-197 Ghidra decompile breakthrough.

## What shipped this iteration

1. **`civrev_ps3/korea_mod/xml_overlays/civnames_enu.txt`** — 18-row
   civnames file. Inserts `"Koreans, MP"` between `"English, MP"`
   and `"Barbarians, MP"`. All 16 stock entries at indices 0..15
   unchanged. Index 16 = Korea (NEW). Index 17 = Barbarians (was 16).
2. **`civrev_ps3/korea_mod/xml_overlays/rulernames_enu.txt`** — 18-row
   rulernames file. Inserts `"Sejong, M"` between `"Elizabeth, F"`
   and `"Grey Wolf, M"`.
3. **`pack_korea.sh`** — extended to apply `.txt` overlays (not
   just `.xml`/`.ini`), and the Pregame repack path now runs the
   overlay loop before calling `fpk.py repack`.
4. **No new `eboot_patches.py` patches land this iteration.** The
   iter-14 `li r5, 0x11 → 0x12` parser-count patches at
   `0xa2ee38`/`0xa2ee7c` stay (they were already shipping).

## Test matrix

| Probe | Slot | Label       | Expected | Result |
|-------|------|-------------|----------|--------|
| M9    | 0    | romans      | boot+HUD | **PASS** |
| M6    | 15   | elizabeth   | boot+HUD | **PASS** (`highlighted_ok=true`) |
| M9    | 16   | slot16_probe| boot+HUD | **PASS** but carousel still shows "Random/Random" |

Full result JSONs archived in this directory.

## The iter-14 misdiagnosis

iter-14 finding 4 (2026-03-28) said:
> "Extended `civnames_enu.txt` / `rulernames_enu.txt` to 18 entries
> via `fpk.py` repack, rebuilt with the `li r5, 18` patches,
> installed, and boot-tested. **Still timed out at RSX init.**"
> "[The crash] is likely a downstream 17-wide buffer..."

**That was a misdiagnosis.** iter-197's Ghidra decompile of
`real_parser_worker` (`FUN_00a2e640`) showed the parser is fully
dynamic: it allocates `(count * 0xc + 4)` bytes via
`thunk_FUN_00c4ff00`, stores the count as a header word, and writes
exactly one 12-byte entry per non-comment line in the file. There
is no 17-wide pre-allocated buffer anywhere in the parser.

iter-198 empirically confirms this: with the same patches iter-14
had active (parser-count `0x11→0x12` at `0xa2ee38`/`0xa2ee7c`) plus
fresh 18-row `civnames_enu.txt` / `rulernames_enu.txt` overlays,
the game boots cleanly, title screen loads, civ-select opens, and
Romans at slot 0 / Elizabeth at slot 15 are both playable with
in-game HUD confirmed by OCR.

iter-14's "Still timed out at RSX init" was most likely from:
- Stale FPK from a botched repack
- Wrong overlay path
- A transient emulator issue
- Or the EBOOT being copied to the wrong location (iter-133 later
  discovered the HDD/disc EBOOT dual-path requirement, which was
  not yet in place during iter-14)

Either way, the iter-7..72 "17-wide buffer OOB" hypothesis that
drove two and a half months of deep-RE is **structurally ruled
out**. The parser path is unconditionally safe at count=18.

## What the 14 `li r8, 0x10` consumer sites actually are

iter-198 also tested bumping the 14 `li r8, 0x10 → 0x11`
downstream consumer sites identified in iter-197 (the pattern
where a function loads any of the 7 name-file buffer-pointer TOC
slots and passes `r8 = 16` as count to a vtable method). When all
14 patches are active together with the 18-row overlay, the game
**hangs at RSX init** (audio Pause() Cubeb spin, no VM violation
logged, no progress past RSX bring-up). Removing just the 14
patches (overlay kept) brings boot back to green.

So the 14 `li r8, 0x10` consumers are **not the civ-select render
path** — they're some other system (most likely save-game /
serialization / session restore) that expects exactly 16 entries
and breaks at init if fed 17. iter-150/154 had already ruled out
two other candidate "16-wide consumer" functions as not being on
the carousel; iter-198 extends that: the `li r8, 0x10` pattern is
not the carousel either.

The `li r8, 0x10` patches are commented out in `eboot_patches.py`,
not deleted — they're kept as a recorded failed hypothesis.

## Slot 16 at civ-select still renders "Random / Random"

The `slot16_probe` OCR capture shows the cursor locked on the
Random cell with the "Random / Random" title and `???` era bonuses
— exactly the stock appearance. Korea at civnames index 16 is
present in the dynamically-allocated parser buffer, but whatever
code renders the civ-select carousel is reading from a different
source. Known disproofs (from iter-150..156):
- Not `FUN_001e49f0` (tested via `b .` diagnostic)
- Not `FUN_011675d8` (tested via `b .` diagnostic)
- Not the EBOOT "Caesar" / "Elizabeth" rodata string sites
- Not the static 16-entry LEADER / LDR_TAG / CIV_TAG / ADJ_PAIR
  rodata arrays (iter-4 dead-rodata finding + iter-144/145 tests)
- Not the 14 `li r8, 0x10` consumers (iter-198)

The carousel render path is **elsewhere**. iter-197 hinted at it
with the decompile of `FUN_00a2e640`'s post-parse loop (the
`FUN_009bf5a0` post-process block at lines 115-127) — that block
writes per-entry data via `FUN_009f1c80(iVar7*0xc + iVar8, uStack_c0)`.
Whoever reads that downstream data is the next target.

## Net PRD state

**§9 DoD item 1 blocker (M2 RSX-init crash on 18-row civnames)
is RESOLVED.** This has been open since iter-7 (2026-03-19).
iter-7..iter-72's entire effort was chasing a buffer that didn't
exist. The actual crash — if there ever was one — came from the
test environment, not from the binary.

**§9 DoD item 2 (Korea as a brand-new 17th civ at a new 18th
carousel cell, all 16 original civs + Korea + Random selectable)**
is still not met. Korea is now in the civnames/rulernames buffer
at index 16 but no UI element renders her.

**iter-199 plan:** trace the civ-select carousel render path from
the parsed buffer to the on-screen cells. Starting points:
1. Function `FUN_00a2e640` post-parse block at lines 115-127,
   which calls `FUN_009bf5a0` with the buffer offset + 8 and
   `FUN_009f1c80` with the buffer offset directly. Find
   `FUN_009f1c80`'s purpose — is it writing into a separate
   destination struct that's the actual carousel source?
2. The `theOptionArray` AS2 variable in `gfx_chooseciv.gfx`
   tag[185] — the PPU must be populating this array at panel-init
   time via Scaleform Invoke. Find the EBOOT code that writes to
   it. Iter-197 hypothesis: this happens near the
   `FUN_009bf5a0` / `FUN_009f1c80` calls, since those run right
   after the civnames parse completes.
3. Z-packet watchpoint via `gdb_client.py` extension on the
   civnames buffer after parse completes, during civ-select panel
   load. Whatever reads it first is the render path.

## Files

- `findings.md` (this)
- `m9_romans_result.json`
- `m6_elizabeth_result.json`
- `m9_slot16_probe_result.json`
- `slot16_06_still_random.png` (visual proof slot 16 is still Random)
