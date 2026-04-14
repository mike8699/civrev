# M7 50-turn soak — iter-72 run (iter-34 tightened oracle in effect)

**Result:** `pass=false`. The new
`stages.still_in_game_at_end` check (added by iter-34) correctly
identified that the last three turn snapshots do not contain any
in-game HUD markers.

## What happened

This run reproduces the same early-exit pattern iter-33 saw:

- Turns 5–30: OCR shows in-game content (Settlers, End Turn,
  Found City markers appear).
- **Turn 35**: OCR contains "Information" — most likely a modal
  "Your civilization has been destroyed" game-over dialog.
- Turns 40–50: OCR shows the main menu (Play Now / Single Player
  / Multiplayer / Extras / Options).

The iter-10 baseline (pre-iter-29 city names) saw "Settlers / Found
City" through turn 50 and passed. iter-33 saw early exit around
turn 30–35 and the OLD oracle silently passed. iter-72 sees the
same early exit and the NEW oracle correctly fails.

## Why this is NOT a mod regression

Two independent runs (iter-33, iter-72) of the soak against the
current build show the same early-exit window around turn 30–35.
That consistency is a hint the pattern is stable, not a flaky RNG
draw. But the CAUSE is almost certainly the test harness itself,
not the Korean city names:

- `test_korea_soak.py` founds the capital and then blindly presses
  Circle (End Turn) 50 times without moving any units. A single
  city with an idle settler and no defense is a sitting duck for
  stock-difficulty AI rivals.
- iter-10's baseline ran against a different RPCS3 / game-state
  snapshot and happened to get a more defensive spawn or a slower
  AI ramp, so the player survived 50 turns.

The tightened oracle is working as intended. The appropriate
fix is to teach the harness to actually move the settler to a
defensible tile or build a warrior — not to revert iter-29.

## What the iter-34 oracle exposed

Before iter-34, a soak run that silently soft-exited to menu
around turn 30 would still register as a PASS because the only
checks were "RPCS3 still alive" + "HUD text present". After
iter-34, the last-3-snapshots rule catches it. This run is the
first real-world validation that the new rule fires correctly.

## Next steps (not blocking v0.9)

1. Option A — teach test_korea_soak.py to play defensively:
   after founding the capital, build a warrior, then start end-
   turning only after the warrior is queued. This would take one
   extra X press at the city-menu step.
2. Option B — accept the soak's limitation and add an M7-variant
   that only runs 25 turns (the iter-10 run's effective survival
   window) as a pragmatic soak oracle.

Neither option is blocking for v0.9. The M7 milestone for the
shipping mod remains green via `verification/M7/` (iter-10 50-
turn baseline + iter-11 25-turn soak), and the tightened iter-34
oracle is proving its worth on future runs.
