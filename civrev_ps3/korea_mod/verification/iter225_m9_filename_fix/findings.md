# iter-225: harness M9 filename uniformity fix

**Date:** 2026-04-15

## The flake (recap from iter-224)

`run_m9_regressions.sh` invokes `docker_run.sh --headless
korea_play <slot> <label>` for 6 civs. It then expects each
run to drop `korea_m9_<label>_result.json` in `output/`. But
slot 15 (Elizabeth) was producing `korea_m6_elizabeth_result.json`
instead, causing the iter-224 sweep tally to mistakenly flag
elizabeth as missing.

## Root cause

`rpcs3_automation/test_korea_play.py` line 61 had a historical
special-case:

```python
"milestone": "M6" if slot == 15 else "M9",
```

This dates from v0.9 when slot 15 was repurposed for Korea
(the Pregame.FPK byte-patch English→Korean substitution path).
M6 was the "Korea boots and plays" milestone in the original
verification plan. Under the iter-189 strict reading, slot 15
is Elizabeth/English again and the M6 routing is meaningless —
it just produces non-uniform filenames.

## Fix

Drop the `slot == 15` special case so every invocation reports
as M9:

```python
result = {
    "milestone": "M9",
    ...
}
```

Result.json filenames are now uniformly
`korea_m9_<label>_result.json` for every M9 sweep slot.

## Verification

```bash
rm -f output/korea_m9_elizabeth_result.json
./docker_run.sh --headless korea_play 15 elizabeth
```

Output:
```
M9 PASS — elizabeth game loaded
wrote /output/korea_m9_elizabeth_result.json; pass=True
```

```json
{
  "milestone": "M9",
  "slot": 15,
  "label": "elizabeth",
  "pass": true,
  "stages": {
    "main_menu": true,
    "difficulty_selected": true,
    "highlighted_ok": true,
    "in_game_hud": true
  }
}
```

The old `korea_m6_elizabeth_result.json` is no longer
produced. Future `run_m9_regressions.sh` invocations will
find elizabeth's result via the m9 glob without
special-casing.

## What's NOT changed

- The M6 milestone label still exists in the test_korea_play.py
  imports / utility code and in historical verification
  artifacts (under `verification/M6_iter29/`,
  `verification/iter176_random_preserved/` etc.). Those are
  archival and don't need updating.
- `run_m9_regressions.sh` itself is unchanged — the fix is
  upstream of where the script reads result.jsons.
- The PRD §7.1-§7.5 milestone definitions (M0–M9) are
  unchanged. M6 still semantically means "Korea boots and
  plays the game" — it's just that the harness no longer
  has a trigger for it under the iter-189 strict reading.

## Verification artifacts

- `korea_m9_elizabeth_result.json` (new naming, M9 milestone)
- This findings.md.
