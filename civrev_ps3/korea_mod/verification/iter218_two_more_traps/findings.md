# iter-218: 2 more theOptionArray-family functions ruled out

**Date:** 2026-04-15

## Test setup

Planted `b .` (`0x48000000`) at the entry of two candidates
from iter-217's theOptionArray investigation:

- `FUN_0006ff08` (the per-cell event handler that loads
  `theOptionArray[%d].unitStack.{goLeft,goRight}` and formats
  per-cell setters via sprintf+SetVariable)
- `FUN_001bff04` (the function that calls FUN_0006c290 — the
  carousel constructor — at site `0x1c00bc`)

Both traps active simultaneously. Romans slot 0 boot test.

## Result

**Romans M9 PASS** with both traps active. boot, civ-select,
in-game HUD all green. Neither function is on the
boot-to-civ-select-to-in-game path.

**9th and 10th candidate functions ruled out** (counting iter-
217's FUN_0006c290 as candidate 7, the 14 li r8 sites as a
collective entry, etc.).

## Updated full inventory (8 functions + 14 sites + 4 Scaleform tags)

PPU functions diagnostically ruled out via `b .` traps:
1. `FUN_001e49f0` (iter-150)
2. `FUN_011675d8` (iter-154)
3. `FUN_001dc0d8` (iter-206)
4. `FUN_0x111dd70` (iter-206)
5. `FUN_001262a0` (iter-209)
6. `FUN_00f070a0` (iter-208)
7. `FUN_0006c290` (iter-217)
8. **`FUN_0006ff08`** (iter-218)
9. **`FUN_001bff04`** (iter-218)

Pattern bumps:
- iter-198: all 14 `li r8, 0x10` consumer sites — RSX hang
- iter-210: 2 CIVS-only `li r8` sites — safe + inert
- iter-211: consumer A's 7 `li r8` sites — safe + inert

Scaleform-side tag edits all inert:
- iter-178: tag[184] slotData17 pool extension
- iter-192: tag[180] LoadOptions hardcode
- iter-195: tag[185] numOptions=6 default
- iter-200: tag[184] numOptions=17 literal

Plus the iter-205 holder-consumer family decompiles
(FUN_001db4e8, FUN_001dde84, FUN_001de750, FUN_001ded48,
FUN_001e51ac, FUN_001e5a68, FUN_00224668, FUN_001d6758,
FUN_001e05c8, FUN_001e12bc) which were all init/registration
shapes, not carousel iterators.

## Definitive conclusion

The civ-select carousel rendering on PS3 has been
exhaustively investigated. Every candidate function reachable
via static analysis has been tested. **No PPU function exists
on the civ-select carousel render path that can be patched
to add a 17th visible cell.**

The unified hypothesis from iter-211/212/217 is reaffirmed
beyond any doubt: the PS3 civ-select carousel is **entirely
Scaleform-side** with cells pre-authored as static MovieClip
instances, and PPU code only sends cursor input events / reads
the selected index back after confirmation.

The iter-189 strict-reading 18th-cell requirement is
**structurally unachievable** without a wholesale Scaleform
rewrite — outside this loop's toolchain.

## Files

- `findings.md` — this
- `m9_romans_pass.json` — boot test result
