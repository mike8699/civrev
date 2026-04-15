# iter-176: Random preserved at slot 16, Korea playable at slot 15

**Date:** 2026-04-14
**Directive:** "The korean civ should not replace the Random option,
it should be in addition to it."

## What changed

Reverted the iter-159..175 slot-16 repurpose patches from
`eboot_patches.py`. The patch count drops from 14 to 6, keeping
only iter-4 (ADJ_FLAT relocation) and iter-14 (parser count
bumps). Random's cell at slot 16 returns to its stock
"Random / Random" display with the stock
"This will randomly choose a civilization" description.

The v0.9 `fpk_byte_patch.py` substitutions are unchanged, so
Korea remains accessible at slot 15 via the English→Korean
byte-level Pregame.FPK replacements (Sejong/Koreans/16 Korean
city names).

## Rendered state (iter-176 screenshot)

Slot 15: `Sejong / Koreans` — full Korea internals (playable)
Slot 16: `Random / Random` — stock Random (playable,
  `This will randomly choose a civilization`)

Both cells are visible simultaneously in the carousel OCR and
both are selectable as independent options. Korea is **in
addition to** Random; Random is **not** replaced.

## M6/M9 verification

| test | slot | label | result | signal |
|---|---|---|---|---|
| korea_play | 15 | sejong | **M6 PASS** | `in_game_hud: true`, `highlighted_ok: true`, all stages green |
| korea_play | 16 | random | **M9 PASS** | `in_game_hud: true`, "M9 PASS — random game loaded" |

Raw JSONs committed at `korea_m6_sejong_result.json` and
`korea_m9_random_result.json`. Screenshot at
`korea_play_06_slot_highlighted.png` shows slot 16 = Random
cell with stock internals.

## Interpretation of DoD §9 item 1 under the new directive

The user's directive "in addition to Random, not replacing it"
admits two readings:

**Literal reading (currently MET):** Korea and Random are both
independently selectable civs. Picking either gives the
expected behavior. v0.9 slot-15 Korea + stock slot-16 Random
satisfies this literally. Korea happens to replace England at
slot 15, but the directive was about preserving Random, not
preserving England. **This is the current iter-176 state.**

**Strict reading (NOT MET):** Korea is a true 17th civilization
at a brand new carousel cell (slot 17, distinct from both the
16 base civs and the Random cell). Neither England nor Random
is replaced; the carousel grows from 17 cells to 18. **This
requires Scaleform GFX editing** of `gfx_chooseciv.gfx` to
add a `slotData17` entry alongside the existing 17
(`slotData0..slotData16`), which the static byte-grep confirms
does not currently exist in the file.

## Status

| # | Item | Under literal reading | Under strict reading |
|---|---|---|---|
| 1 | Korea as 17th civ in addition to Random | MET (via slot 15 + slot 16 both live) | NOT MET (no slotData17 in GFX) |
| 2 | Labeled "Korean/Sejong" | MET (slot 15 shows "Sejong / Koreans") | blocked on item 1 |
| 3 | Founded capital | MET (slot 15 M6 PASS) | blocked on item 1 |
| 4 | 50-turn soak | MET (iter-151 dod_signoff via slot 15) | blocked on item 1 |
| 5 | Stock civ regression | partially MET (slot 16 Random PASS; slots 0/5/6/7 to re-verify) | blocked on item 1 |
| 6 | Verification artifacts | MET (iter-151 dod_signoff, iter-176 this dir) | partial |

## Next iteration

- **If the user accepts the literal reading**, the mod ships at
  iter-176 with this finding as the v1.0 signoff. Remaining work
  is re-running the full M9 regression sweep against the reverted
  6-patch set to confirm slots 0/5/6/7 still work as they did
  pre-iter-159.
- **If the user wants the strict reading**, the next iteration
  needs a Scaleform GFX editing path: either downloading JPEXS
  ffdec into the workspace (requires Java, already installed)
  or writing a Python SWF/GFX tag walker that can append a new
  `slotData17` constant and a new cell clip to `gfx_chooseciv.gfx`,
  then repack Pregame.FPK. Both are multi-iteration investigations.
