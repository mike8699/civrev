#!/usr/bin/env bash
# korea_mod/run_m9_regressions.sh — run the PRD §9 DoD item 5 M9
# regression sample set in sequence.
#
# Hits slot 0 (Caesar), slot 5 (Catherine), slot 6 (Mao), slot 7
# (Lincoln). Each invocation takes ~3 minutes, so the full sweep is
# ~12-15 minutes wall-clock. Two containers can't run in parallel
# on the same host (they'd fight over /tmp/.X11-unix) so this loop
# intentionally serializes them.
#
# Result JSONs land in civrev_ps3/rpcs3_automation/output/ and are
# NOT auto-copied to korea_mod/verification/M9/. Move them manually
# after inspecting the pass flag so a flaky run doesn't overwrite
# a known-good baseline.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PS3_ROOT="$(cd "$HERE/.." && pwd)"
RPCS3_DIR="$PS3_ROOT/rpcs3_automation"

SAMPLES=(
    "0 caesar"
    "5 catherine"
    "6 mao"
    "7 lincoln"
    "15 elizabeth"
    "16 random"
)

cd "$RPCS3_DIR"

for sample in "${SAMPLES[@]}"; do
    read -r slot label <<< "$sample"
    echo
    echo "=============================================="
    echo "M9 regression: slot $slot / $label"
    echo "=============================================="
    if ! ./docker_run.sh --headless korea_play "$slot" "$label"; then
        echo "[run_m9_regressions] slot $slot $label FAILED — continuing"
    fi
    echo "[run_m9_regressions] slot $slot $label completed"
done

echo
echo "=============================================="
echo "M9 regression sweep done. Results in:"
echo "  $RPCS3_DIR/output/korea_m9_*_result.json"
echo "Inspect pass flags, then copy the keepers to:"
echo "  $HERE/verification/M9/"
echo "=============================================="
