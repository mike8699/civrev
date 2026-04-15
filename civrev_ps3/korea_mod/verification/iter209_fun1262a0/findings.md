# iter-209: `FUN_001262a0` is the 5th candidate ruled out

**Date:** 2026-04-15

## Diagnostic test

Planted `b .` (`0x48000000`) at `0x1262a0` (`FUN_001262a0`
entry — the function iter-208 found that unrolls
`bl 0x126124(panel, icon_filename)` for all 18 `CIV_*.dds`
strings).

Original bytes: `0xf821ff71` (stdu r1, -0x8f(r1) prologue).

**Result**: Romans slot 0 M9 **PASS**. Boot → main menu →
scenario → difficulty → civ-select → Romans highlighted →
in-game HUD detected by OCR. The function is NOT called on
the boot-to-civ-select-to-in-game path.

**`FUN_001262a0` is the civilopedia init**, NOT the
civ-select carousel init. The CIV_*.dds icon table at
`0x1937d38..0x1937d7c` is consumed by the civilopedia for its
per-civ pedia pages.

## Cumulative "ruled out" list

Five candidate consumer functions have now been
diagnostically tested with `b .` traps and all PASS the
korea_play boot test, meaning none of them is on the
carousel render path:

| iter | function | discovery context |
|---|---|---|
| 150 | FUN_001e49f0 | "per-cell carousel binder" hypothesis |
| 154 | FUN_011675d8 | second 16-count consumer |
| 206 | FUN_001dc0d8 | second .data holder struct unrolled reader |
| 206 | FUN_0x111dd70 | class destructor that holds civs holder ptr |
| 209 | FUN_001262a0 | unrolled CIV_*.dds icon registration |

All are name-file or icon CONSUMERS in some sense — but
none is on the civ-select carousel path. The carousel
render path remains unidentified.

## Diminishing returns observation

Static analysis has identified ~50 functions that touch
civnames-related data structures. Each one decompiled and
diagnostically tested has been negative. The pattern suggests
the carousel render is **not driven by PPU code reading
the civnames buffer or icon table at runtime**.

Possible alternative architectures:
1. **Carousel data is purely Scaleform-side.** The
   `gfx_chooseciv.gfx` Scaleform file has the cell layout
   pre-authored as `slotData0..slotData16` constants. The PPU
   only sends the cursor position and key events; the AS2
   bytecode reads its own constants. iter-178/192/195/200
   already explored extending these and found them inert.
2. **Carousel cells are loaded by name, not by pointer.** If
   the PPU calls Scaleform's `Loader.loadClip("CIV_Spain.dds")`
   per cell, the loaders would not appear as TOC pointer reads
   to the icon table — they'd be string-formatted via
   `sprintf("CIV_%s.dds", civname)` at runtime.
3. **The civ-select carousel uses a hardcoded 16-cell array
   with no index lookup at all**, with each cell rendering
   a fixed civ assigned at compile time.

If hypothesis 3 is true, the carousel CANNOT be extended
without rewriting the Scaleform AS2 carousel from scratch —
which is outside our toolchain capability.

## Net state

Korea is in the parser buffer at index 16 (verified iter-203).
The carousel still renders Random at slot 16. No additional
code path has been found that would surface Korea visually.

The iter-189 strict-reading directive (Korea as a brand-new
17th civ at a brand-new 18th carousel cell) may not be
achievable with the static-patching toolchain available in
this loop. The most we can ship under iter-189 is the
iter-198 partial state: Korea present in the parser buffer
but invisible in the UI.

## iter-210 plan options

Three remaining tactics, in order of cost:

1. **Selective `li r8, 0x10 → 0x11` patching.** iter-198
   tested all 14 `li r8, 0x10` consumer-A/B patches at once,
   and boot hung. Test SUBSETS — first the 2 CIVS-only sites
   (`0x01167948` and `0x01167dc8`), then RULERS, etc. — to
   isolate which patch breaks boot. If only some patches
   break, the others might be safe and reveal a 17-entry
   path.

2. **Look at the OTHER 18-row table.** iter-208 found the
   icon table is 18 entries. The civnames buffer is 18
   entries. Maybe there's a THIRD parallel 18-entry array
   (per-civ adjective, leader-portrait, civ-tag) that the
   carousel actually reads. Search for any 18-pointer table
   in the binary.

3. **Pivot to documenting the iter-189 limitation.** Update
   the PRD §9 DoD to acknowledge the strict-reading 18th-cell
   requirement is structurally blocked by the Scaleform
   carousel architecture, and ship the iter-198 partial
   state with a documented caveat.

iter-210 should pursue option 1 (cheapest, may unblock).
Option 2 is more thorough static. Option 3 is the
acceptance-of-limitation path.

## Files

- `findings.md` — this
- `m9_romans_pass.json` — diagnostic boot test result
