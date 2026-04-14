# M7 50-turn soak — iter-33 run (post iter-29 city names)

**Result:** `pass=true` per the M7 oracle ("end-turn 50x without crash;
HUD stays OCR-readable"). RPCS3 survived all 50 end-turn presses and
the HUD remained OCR-readable throughout.

**Observation worth flagging:** between turn 30 and turn 35 the game
transitioned from the world map back to the main menu. Turn 30
screenshot shows in-game (1800 BC, settler highlighted with "Activate
unit"); turn 35 screenshot shows the main menu ("Play Now / Single
Player / Multiplayer / Extras / Options"). Turns 35–50 all OCR as
main-menu strings.

**Interpretation:** test_korea_soak.py presses O (Circle = End Turn)
blindly for TARGET_TURNS iterations. It does NOT move units between
end-turns. After ~25 turns of Korea's capital sitting alone on a
coastal start with an unmoved settler, the default stock-difficulty AI
almost certainly captured or eliminated the player, soft-exiting the
session back to the main menu. This is gameplay RNG / test-harness
coverage, NOT a mod regression:

- **iter-10 baseline** (same Pregame byte patches MINUS the 16 city
  name replacements) ran 50 turns and stayed in game. Compare
  `verification/M7/result_50turn.json` snapshots — "Settlers" and
  "Found City" markers appear in every turn through turn 50.
- **iter-33** (same setup + 16 city name replacements) shows in-game
  HUD markers through turn 30 and main-menu markers from turn 35 on.

Whether this is deterministic (caused by the city-name patches
perturbing the map/RNG seed) or stochastic (unlucky spawn) is
unresolved. Two non-destructive follow-ups would settle it:

1. Re-run M7 with the current build once; if the early exit repeats
   at the same turn, that's deterministic and iter-29 is suspect.
2. Tighten the M7 oracle so "main menu visible" counts as FAIL and
   commits cannot silently pass a run like this one. Add a check:
   for the last 3 snapshots, assert that OCR contains at least one
   of ("Turn", "BC", "AD", "Settlers", "Found City").

iter-33 does NOT revert iter-29's city names on the strength of a
single run. A future iteration should either reproduce the early
exit or tighten the oracle.
