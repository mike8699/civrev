# iter-176 full M9 regression — 4/4 stock civs PASS

**Date:** 2026-04-14
**Scope:** Confirm the iter-176 revert to the 6-patch EBOOT set
does not regress any stock civ.

## Results

| Slot | Civ | Label | M9 PASS | in_game_hud |
|---|---|---|---|---|
| 0 | Romans | caesar | ✓ | true |
| 5 | Russians | catherine | ✓ | true |
| 6 | Chinese | mao | ✓ | true |
| 7 | Americans | lincoln | ✓ | true |
| 15 | Koreans (v0.9) | sejong | ✓ (M6) | true |
| 16 | Random | random | ✓ | true |

All 6 sampled slots load a playable in-game HUD under the iter-176
6-patch EBOOT set (iter-4 ADJ_FLAT + iter-14 parser count bumps)
and the v0.9 Pregame.FPK byte-patches (Elizabeth→Sejong,
English→Koreans, 16 English city names → Korean).

**Random cell is fully restored at slot 16.** The slot 15 Korea
and slot 16 Random are both independently selectable; neither
replaces the other.

## DoD §9 item 5 (regression check) — MET

The PRD explicitly samples slots 0, 5, 6, 7 for regression. All
four pass, plus slot 15 (the mod's primary Korea slot) and slot
16 (Random, newly required by the iter-176 directive). Six-way
confirmation that the 6-patch set is clean.

## Raw artifacts

- `korea_m9_caesar_result.json`
- `korea_m9_catherine_result.json`
- `korea_m9_mao_result.json`
- `korea_m9_lincoln_result.json`

The slot 15 (sejong) and slot 16 (random) runs from iter-176
are in the sibling `iter176_random_preserved/` directory.
