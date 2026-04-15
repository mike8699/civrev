# iter-190: v0.9 reverted, Elizabeth/England fully restored at slot 15

**Date:** 2026-04-15
**Directive:** iter-189 STRICT reading — England at slot 15 must be
fully stock; Korea must be a brand-new 17th civ at a new 18th
carousel cell.

## What changed

`civrev_ps3/korea_mod/fpk_byte_patch.py` — `_build_patches()` now
returns an empty list. The 18 v0.9 substitutions (Elizabeth→Sejong,
English→Koreans, 16 English city names → Korean city names) are
removed. The function's surrounding machinery is preserved for any
future byte-level patches that may need it.

**Effect:** `Pregame_korea.FPK` built by `build.sh` is now
**byte-identical to the stock `Pregame.FPK`** (SHA-256
`69d771f43eca1c898d95617354b46ddda884bc95066b5a7352d7d6c4e87adb1a`).
No substitutions applied. Elizabeth/English/London/... all restored.

Also updated `rpcs3_automation/test_korea_play.py`'s keyword dict:
  - slot 15 → `("Elizabeth", "English", "England")` — was
    `("Sejong", "Korean", "Korea")`
  - slot 16 → `("Random",)` — added
  - slot 17 → `("Sejong", "Korean", "Korea", "KOREA18")` — added in
    anticipation of the future 18th cell; not yet reachable

## Regression results (iter-190 build, 6-patch EBOOT + stock Pregame.FPK)

| Slot | Civ | Label | Test | Result | `highlighted_ok` | `in_game_hud` |
|---|---|---|---|---|---|---|
| 0  | Romans        | caesar    | M9 | **PASS** | — | ✓ |
| 6  | Chinese       | mao       | M9 | **PASS** | — | ✓ |
| 15 | English       | elizabeth | M6 | **PASS** | ✓ | ✓ |
| 16 | Random        | random    | M9 | **PASS** | — | ✓ |

The **iter-190 slot 15 M6 PASS** confirms that Elizabeth is a stock
playable civ again — the test harness OCR now sees "Elizabeth" /
"English" / "England" keywords and flips `highlighted_ok: true`.
This matches the strict-reading §9 item 5 requirement.

## DoD §9 status after iter-190

| # | Item | Status |
|---|------|--------|
| 1 | install.sh works | MET |
| 2 | Korea as brand-new 17th civ, 18 cells | **still NOT MET** (no Korea cell exists yet) |
| 3 | Founded capital | blocked on item 2 |
| 4 | 50-turn soak | blocked on item 2 |
| 5 | Stock regression (Caesar/Mao/Elizabeth/Random) | **MET** (iter-190 4-way PASS) |
| 6 | Verification artifacts | partial |

iter-190 is a **stepping-stone**: the mod temporarily has NO Korea
at all (it's just stock EBOOT + iter-4/iter-14 infrastructure
patches). This is the clean baseline from which the real 18th-cell
work begins in subsequent iterations.

## Next iteration

Per iter-189 PRD entry, step 2: extend `gfx_chooseciv.gfx` carousel
to 18 cells. Start with the `theOptionArray` extension hunt — find
where it's built in tag[184] or tag[185] and figure out how to
append an 18th MovieClip handle to it. Use iter-185's distinctive-
marker OCR technique to verify reachability at each test.
