# iter-182: slot 17 NOW POPULATED — combined clamp + slotData17 patches

**Date:** 2026-04-14

## The breakthrough

Combined iter-181's `goRight` clamp extension (4 bytes) with iter-178's
`slotData17` pool extension + setVariable block duplication (+43 bytes)
into a single `gfx_chooseciv.gfx` rebuild. Installed via `fpk.py`
repack of `Pregame.FPK`.

**Slot 17 now renders a populated cell** instead of iter-181's
`"undefined / undefined"`. The carousel displays `"RANDOM / Romans"`
at slot 17 with actual era bonuses visible:

```
Ancient:   1/2 Price Roads        (Romans' Ancient bonus)
Medieval:  1/2 Cost Wonders       (Romans' Medieval bonus)
Industrial: More Famous People    (Romans' Industrial bonus)
Modern:    New Cities have 3 Population  (Romans' Modern bonus)
```

The cell title is the unusual `"RANDOM / Romans"` combination — the
title's first line reads from the duplicated slotData17's metadata
(which was cloned from slotData16 = "Random"), and the second line
+ era bonuses pull from the game's civ data at index 0 (Romans) due
to `theActiveArray[17]` being undefined and falling back to index 0.

## M9 test result

- `korea_play 17 combined`: **PASS**
- `in_game_hud: true` — selecting slot 17 launches a playable game
- `select_ocr` shows `"Genghis Khan / Elizabeth English / Random
  Random"` at the left visible cells and `"RANDOM / Romans"` at
  the new slot 17 cell
- Yellow right-arrow indicator is still visible in the screenshot,
  suggesting the carousel still thinks there's more to scroll

## What this proves

1. **The strict-reading "18 cells" carousel is feasible.** A brand
   new 18th cell is now physically present, visible, selectable, and
   launches a game when chosen.
2. **iter-181's clamp patch + iter-178's slotData17 block are a
   compatible combination.** No crashes, no regressions, game plays
   through.
3. **The cell-data wrap is controlled by `theActiveArray`, not by
   `numOptions` or slotDataN.** When `theActiveArray[17]` is
   undefined, the carousel falls back to some default (apparently
   civ index 0 / Romans), so the new slot plays Romans but displays
   with slotData17's (Random's) title format.

## Composite patch summary (iter-182)

Two edits to `gfx_chooseciv.gfx`, rebuilt via `fpk.py`:

| # | File offset | Before | After | Purpose |
|---|---|---|---|---|
| 1 | `0x4e3f` (tag[184] len) | `2021` | `2064` | extend DoAction body |
| 2 | `0x4e43 + 3 + 980` | (nothing) | `"slotData17\0"` | pool string |
| 3 | `0x4e43 + 1` (pool_len) | `980` | `991` | pool length field |
| 4 | `0x4e43 + 3` (pool_count) | `96` | `97` | pool count field |
| 5 | tag[184] end-1 | (nothing) | slot16-block clone (32B) | setVariable |
| 6 | `0x748c` (tag[188] bc@0x28a) | `01 00 00 00` | `00 00 00 00` | i32(1)→i32(0) |
| 7 | `0x0004` (SWF file length) | `59646` | `59689` | header fixup |

All edits are in `gfx_chooseciv.gfx`. No EBOOT changes.
Pregame.FPK rebuilt via `fpk.py from_directory` (iter-177 unblock).

## Remaining work for a Korea-populated slot 17

The current slot 17 plays Romans (wrap to slot 0). To make it play
Korea:

1. **Find where `theActiveArray` gets its 17 elements** and extend
   it to 18. Candidates:
     - Scaleform AS2 loop in tag[184] that does
       `theActiveArray[i] = ...` for i in 0..16
     - EBOOT PPU code that loops over civs and calls
       `Scaleform.SetVariable("theActiveArray.N", ...)`
2. **Populate slot 17 with Korea's civ index.** The simplest path
   is probably pointing `theActiveArray[17]` at civ index 6 (China)
   so slot 17 plays as Chinese with Korean cosmetics, matching the
   v1.0 spec in §9.
3. **Inject Korea-specific strings into slotData17** (title,
   description, etc.) so the cell's display is Korean rather than
   cloned Random.

These are future-iteration steps. iter-182 shipping state unchanged
(test edits reverted by `korea_mod/install.sh`).
