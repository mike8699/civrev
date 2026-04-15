# iter-224: 6-civ M9 sweep against the lean iter-223 install

**Date:** 2026-04-15

## Goal

Refresh the §9 DoD item 5 regression sweep against the iter-223
shipping state (5-overlay → 2-overlay reduction, Common0_korea.FPK
removed from the install pipeline). iter-216's M9 sweep was against
the bloated pre-iter-223 install with the inert Common0 overlays
still present; iter-224 re-verifies that the lean shipping state is
regression-free.

## Method

```bash
cd civrev_ps3/korea_mod
./run_m9_regressions.sh
```

The script serializes 6 docker_run.sh invocations covering the
PRD §9 item 5 sample set: Caesar (slot 0), Catherine (slot 5),
Mao (slot 6), Lincoln (slot 7), Elizabeth (slot 15), Random
(slot 16).

## Results

| civ | slot | milestone | result | notes |
|---|---|---|---|---|
| Caesar | 0 | M9 | **PASS** | clean run |
| Catherine | 5 | M9 | **PASS** | re-run separately after I prematurely killed the in-sweep run at the scenario picker (mistook a normal mid-navigation state for a hang) |
| Mao | 6 | M9 | **PASS** | clean run; canary for asset reuse (Korea reuses Mao's leaderhead binding) |
| Lincoln | 7 | M9 | **PASS** | clean run |
| Elizabeth | 15 | M6 | **PASS** | re-run separately. Slot 15 routes through the harness's M6 reporter, not M9, so the in-sweep result landed in `korea_m6_elizabeth_result.json` and was missed by the m9-glob check until the second run |
| Random | 16 | M9 | **PASS** | clean run |

**Net: 6/6 PASS** against the iter-223 lean install. No
regressions from removing the Common0 overlays + restoring stock
Common0.FPK.

All result.json files in this directory.

## Operator lessons learned

1. **Don't kill a docker_run.sh that's only 2 minutes in** — the
   civ-select navigation step takes 1-2 min for civs at slot 5+
   because the harness has to step the cursor across the whole
   carousel. The scenario-picker / navigation-mid screenshot is
   not a hang signal. Wait at least 5 minutes before assuming
   stuck.
2. **The harness reports Elizabeth's milestone as M6, not M9.**
   `run_m9_regressions.sh` doesn't know this and produces a
   `korea_m6_elizabeth_result.json` for slot 15 instead of an m9
   variant. A grep-by-name verification will appear to show
   elizabeth missing unless the m6 path is checked too. Future
   iterations should either (a) update `run_m9_regressions.sh` to
   dual-check both filenames, or (b) update the harness to always
   emit m9_<civ>_result.json regardless of internal milestone
   routing.

## Cumulative §9 DoD status (unchanged from iter-223)

| # | item | status |
|---|------|--------|
| 1 | install.sh works | **MET** (iter-223 + iter-224 verified) |
| 2 | Korea visible at slot 16 in carousel | **OPEN — STRUCTURALLY BLOCKED** (§9.X) |
| 3 | Found capital with Korea | **BLOCKED on item 2** |
| 4 | 50-turn soak as Korea | **BLOCKED on item 2** |
| 5 | Stock regression (6 civs) | **MET** (iter-216 6/6 + iter-224 6/6) |
| 6 | Verification artifacts committed | **MET** |

## What's not in this run

- M7 50-turn soak was not re-run (cascaded blocker on item 2;
  the iter-9 M7 PASS still stands as the soak baseline for stock
  civs since iter-223 made no changes to the gameplay code path).
- Korea-as-Korea play-through was not attempted (the PRD §9.X
  structural blocker means there's no UI path to select Korea
  even though the data is in the parser buffers per iter-203).

## Verification artifacts

- `korea_m9_caesar_result.json`
- `korea_m9_catherine_result.json`
- `korea_m9_mao_result.json`
- `korea_m9_lincoln_result.json`
- `korea_m6_elizabeth_result.json` (note: m6 not m9)
- `korea_m9_random_result.json`
- This findings.md.
