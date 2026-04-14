# Verification artifacts

Durable test outputs for the Korea mod. Each subdir pins a specific
milestone's "greenest" known run: its `result.json` from the test
harness plus any screenshots worth keeping. Copy-paste from
`rpcs3_automation/output/*` when a new run produces a cleaner
baseline, don't overwrite in place.

## Layout

| Dir | Milestone | Contents |
|---|---|---|
| `M0/` | static checks | `result.json` (xmllint + FPK round-trip), `fpk_check.json` |
| `M1/` | first boot + world map | `ingame_spawn_screenshot.png`, `civ_select_screenshot.png`, `result.json` |
| `M2_iter6/` .. `M2_iter8/` | civ-select v0.9 GREEN path | progression of the "Sejong / Koreans" replacement attempt; iter-8 is the shipping form |
| `M6/` | 4000 BC start + found city | `civ_select_korea.png`, `in_game_settlers.png`, `result.json` |
| `M6_iter29/` | M6 re-verified with Korean city names | `korea_m6_korea_result.json` + screenshot (iter-29 city names PASS) |
| `M7/` | 50-turn soak (iter-10 baseline) | turn 20 / 50 screenshots, `result.json` and `result_50turn.json` |
| `M7_iter33/` | 50-turn soak post iter-29 city names | turn 5/30/35 screenshots, `result.json`, `notes.md` (flags the main-menu soft-exit oracle hole that iter-34 closed) |
| `M9/` | 4-civ stock regression (PRD §9 DoD 5) | Caesar slot 0, Catherine slot 5, Mao slot 6, Lincoln slot 7 — each with `<name>_result.json` + `<name>_slot<N>_civ_select.png` + `<name>_in_game.png` |
| `M2_iter12/` .. `M2_iter25_analysis.md` | failed 17-slot extension investigation | iter-12..25 summaries / RPCS3 logs / GDB dumps; none of these represent a shipping state, they document the §7.7 STOP research trail |

## Promotion protocol

When a docker run produces a new pass that should replace an older
baseline:

1. Inspect the new `result.json` in `civrev_ps3/rpcs3_automation/output/`.
2. Check `pass == true` AND (for M7) `stages.still_in_game_at_end
   == true` per the iter-34 tightened oracle.
3. Copy the result JSON + the relevant screenshots into this dir
   under either the canonical milestone subdir OR an `iter<N>/`
   subdir if you want to keep both (preferred when in doubt).
4. `git add -f` any `.png` — the repo-wide `.gitignore` rule
   `*.png` excludes them by default.
5. Commit with a message that references the iter number and what
   changed semantically about the run.

## Why not auto-promote

Runs can flake. The first iter-33 M7 run shipped `pass=true` despite
the game soft-exiting to the main menu between turn 30 and 35 — the
old oracle was too loose. Auto-overwriting would have silently
dropped the iter-10 baseline. Manual promotion keeps bad runs out.
