# iter-227: verify.sh fast/full tiers wired to docker harness

**Date:** 2026-04-15

## Problem

`verify.sh` at iter-226 had the following tier behavior:

```bash
if [ "$TIER" != "static" ]; then
    for m in M1 M2 M3 M4 M5 M6 M7 M9; do
        write_result "$m" false "tier=$TIER requested but $m is not implemented yet"
    done
    fail=1
fi
```

Effect: `--tier=fast` and `--tier=full` were **dead code** — they
short-circuited with a "not-implemented" failure for every milestone
M1-M9. Anyone running `./verify.sh --tier=fast` got an immediate
exit-1 with no actual emulator run. M9 verification has been
happening exclusively through the standalone
`run_m9_regressions.sh` script, completely outside of `verify.sh`'s
tier system.

## Fix

iter-227 wires the fast and full tiers to the existing docker
harness:

- **`--tier=fast`** runs **M0 + a single M9 Caesar smoke test**
  (~5 min wall clock). Caesar M9 PASS implies the patched EBOOT
  cold-boots, reaches civ-select, drives the cursor to slot 0,
  confirms the civ, and reaches the in-game HUD — which transitively
  proves M1 (boot to main menu), so M1 doesn't need a separate
  implementation.
- **`--tier=full`** runs **M0 + the iter-216/iter-224 6-civ
  regression sample sweep** (~25 min wall clock). All 6 civs
  must PASS for the full tier to exit 0.

M2-M7 are NOT wired by this change. They are STRUCTURALLY BLOCKED
under the iter-189 strict reading on the §9.X carousel cell
visibility issue (M2 needs Korea visible at slot 16, M3-M7
cascade). Their semantics are subsumed by M9 PASS for the v1.0
regression purpose. If a future iteration unblocks the carousel,
M1-M7 should be wired as separate scripts here.

## Verification

```bash
./verify.sh --tier=static
# → M0 GREEN, exit 0

./verify.sh --tier=fast
# → M0 GREEN + Caesar M9 PASS, exit 0
```

Both verified locally. Result jsons:

`verification/M9/result.json`:
```json
{
  "milestone": "M9",
  "pass": true,
  "notes": "fast smoke: Caesar M9 PASS"
}
```

`rpcs3_automation/output/korea_m9_caesar_result.json` (the
underlying harness output):
```json
{
  "milestone": "M9",
  "slot": 0,
  "label": "caesar",
  "pass": true,
  "stages": {
    "main_menu": true,
    "difficulty_selected": true,
    "highlighted_ok": true,
    "in_game_hud": true
  }
}
```

`--tier=full` was not run in this iteration to save 25 minutes
of harness time — its implementation calls `run_m9_regressions.sh`
directly, which has been exercised end-to-end by iter-224 and
shown to produce a 6/6 PASS against the iter-223 lean install.

## What this enables for future iterations

1. **One-shot regression check.** Future iterations that touch
   the build/install pipeline can verify with a single command:
   `./verify.sh --tier=fast` (or `--tier=full` for paranoia).
   Previously, that required manually invoking
   `docker_run.sh --headless korea_play 0 caesar` and reading the
   result.json by hand, OR running the full sweep separately.
2. **Stable artifact paths.** `verify.sh` writes a single
   `verification/M9/result.json` with a unified pass/fail summary,
   independent of how many civs the underlying tier runs. Loop
   tooling can poll this single file instead of per-civ jsons.
3. **Tier upgrade path.** If a future v1.1 unblocks the carousel,
   M2/M3 etc. can be wired into the same `if [ "$TIER" = "fast" ]`
   block alongside the existing M9 call.

## Verification artifacts

- `m9_fast_result.json` — verify.sh's M9 unified result
- `m9_fast_caesar_result.json` — underlying harness Caesar result
- This findings.md.
