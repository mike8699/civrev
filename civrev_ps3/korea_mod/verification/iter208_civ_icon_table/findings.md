# iter-208: 0xf070a0 is NOT the ChooseCiv entry; civ icon table + `FUN_001262a0` found

**Date:** 2026-04-15

## iter-193 invalidated: `0xf070a0` is NOT on the civ-select path

Planted `b .` (0x48000000) at `0xf070a0` — the instruction
`lwz r4, -0x2888(r2)` that iter-193 identified as the
ChooseCiv-panel-name string load in the panel loader wrapper
chain.

**Result**: Romans slot 0 M9 **PASS**. Boot → main menu →
scenario → difficulty → civ-select → Romans highlighted → game
started → in-game HUD. **Not reached.**

**iter-193's "ChooseCiv panel loader wrapper at 0xf070a0" is
wrong.** Either it's dead code or the civ-select panel is
loaded via a completely different mechanism.

Python scan confirms: exactly 1 site in the entire binary does
`lwz r4, -0x2888(r2)` (= 0x8082d778), and it's `0xf070a0`. No
other code uses this address/offset pattern. So the "ChooseCiv"
name string at `0x169f438` is never loaded at runtime by any
call path that reaches civ-select.

## `GFX_ChooseCiv.gfx` filename + CIV icon table

Searching rodata found:
- `0x169f438` — bare `"ChooseCiv"` (the string iter-193 chased)
- `0x169f94c` — `"GFX_ChooseCiv_LockIcon.dds"` (texture)
- `0x169fc8c` — `"GFX_ChooseCiv.gfx"` (the Scaleform filename)
- `0x169fcf8..0x169fe28` — **CIV_*.dds icon filename table**

Each `CIV_*.dds` string is referenced exactly ONCE from a
4-byte pointer at `0x1937d38..0x1937d7c`. That's an 18-slot
**pointer table** in the main TOC (reachable via
`r2=0x193a288` at offsets `-0x2550..-0x250c`).

| TOC slot | r2+offset | filename |
|---|---|---|
| 0x1937d38 | r2+-0x2550 | CIV_Spain.dds |
| 0x1937d3c | r2+-0x254c | CIV_Russia.dds |
| 0x1937d40 | r2+-0x2548 | CIV_Rome.dds |
| 0x1937d44 | r2+-0x2544 | CIV_Random.dds |
| 0x1937d48 | r2+-0x2540 | CIV_Mongolia.dds |
| 0x1937d4c | r2+-0x253c | CIV_Japan.dds |
| 0x1937d50 | r2+-0x2538 | CIV_India.dds |
| 0x1937d54 | r2+-0x2534 | CIV_Greece.dds |
| 0x1937d58 | r2+-0x2530 | CIV_Germany.dds |
| 0x1937d5c | r2+-0x252c | CIV_France.dds |
| 0x1937d60 | r2+-0x2528 | CIV_England.dds |
| 0x1937d64 | r2+-0x2524 | CIV_Egypt.dds |
| 0x1937d68 | r2+-0x2520 | CIV_China.dds |
| 0x1937d6c | r2+-0x251c | CIV_Barbairan.dds (sic — typo in binary) |
| 0x1937d70 | r2+-0x2518 | CIV_Aztec.dds |
| 0x1937d74 | r2+-0x2514 | CIV_Arabia.dds |
| 0x1937d78 | r2+-0x2510 | CIV_America.dds |
| 0x1937d7c | r2+-0x250c | CIV_Africa.dds |

**18 entries**: 17 civs + Random. Barbarian is also present as
entry 13 but is MISSPELLED in the binary as `CIV_Barbairan.dds`.
(This has nothing to do with the parser buffer layout — it's a
separate 18-entry array of icon-filename pointers.)

## Readers: **three** accessing all 18 slots sequentially

Python scan finds each TOC slot is read at 3-6 call sites across
3 consistent code regions:

1. `0x12672x` range — **21 sequential unrolled calls**
   (`0x126680..0x126790`)
2. `0x94adxx` range — **18 sequential unrolled calls**
   (`0x94aedc..0x94ad8c`)
3. `0xf1axxx..0xf1daxx` range — **18 scattered individual calls**
   each in its own function

Regions 1 and 2 are **unrolled loops inside a single function**.
Region 3 is 18 separate functions, each loading one specific
icon — likely "per-civ info panel" functions.

## `FUN_001262a0` (region 1) is the strongest carousel candidate

Disassembly of region 1:

```
0x00126680  lwz r3, 0x60(r29)       ; r3 = panel_handle = r29->[0x60]
0x00126684  lwz r4, -0x2558(r2)     ; pre-civs icon (Barbarians?)
0x00126688  bl 0x126124              ; register icon with panel
0x0012668c  lwz r3, 0x60(r29)
0x00126690  lwz r4, -0x2554(r2)
0x00126694  bl 0x126124
0x00126698  mr r4, r28               ; dynamic filename
0x0012669c  lwz r3, 0x60(r29)
0x001266a0  bl 0x126124
0x001266a4  lwz r3, 0x60(r29)
0x001266a8  lwz r4, -0x2550(r2)     ; Spain
0x001266ac  bl 0x126124
...                                   ; 18+ more calls, covering all 18 civs
0x00126788  lwz r3, 0x60(r29)
0x0012678c  lwz r4, -0x2504(r2)     ; post-civs (more icons)
```

This is a **fully unrolled "register every icon with the panel"
loop**. The helper `bl 0x126124` (inside `FUN_001260bc`) is the
per-icon register function. The panel handle is read from
`r29->[0x60]` — a class field.

**This is almost certainly either the civ-select carousel
init or the pedia (civilopedia) init.** It operates on a panel
handle stored at instance offset +0x60.

**Function bounds:** `FUN_001262a0` (entry at `0x1262a0`,
next function at `0x1269fc` — 1884 bytes, no direct bl callers
= invoked indirectly like all the other panel-owner functions).

## iter-209 plan

1. **Plant `b .` at `0x1262a0`** (the function entry). If boot
   hangs before civ-select, we've confirmed this is the
   carousel init. If it passes, this is the pedia init
   (runs only in pedia, not civ-select).
2. If civ-select hangs at this function, decompile
   `FUN_001262a0` in full to understand its entry point and
   how it reads the civs buffer (if at all). Find the "loop
   bound" equivalent and figure out how to add a 19th icon
   (for Korea).
3. If it's pedia (civ-select passes), the icon table is STILL
   useful as a lead — the carousel might access the same icon
   table via a different code path with a runtime index
   computation.
4. Alternate dynamic path: set Z0 at `FUN_001262a0` entry via
   `test_civs_z0_probe.py` and poll during civ-select opening
   to capture the hit time.

## iter-208 changes

Diagnostic trap at `0xf070a0` applied and reverted; shipping
state back to iter-198 baseline.

## Files

- `findings.md` — this
- Python scan scripts embedded in iteration output
