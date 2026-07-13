#!/usr/bin/env bash
# Validate the virtpad path: boot the port with a uinput gamepad (no MnK), reach
# the title, press START via the virtpad, and confirm the main menu appears.
# Proves the SDL-gamepad input path works for the port (vs xdotool keyboard).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/validate_pad"
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
source "$HERE/port_pad_lib.sh"
rm -rf "$OUT"; mkdir -p "$OUT"

# NO --mnk_config: drive purely via the SDL virtpad.
CIVREV_LOG_LEVEL=info CIVREV_VIRTPAD=1 EXTRA_ARGS="" \
    "$HERE/run_port.sh" --out "$OUT" --timeout 240 --keep \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" > "$OUT/runner.log" 2>&1 &
# no trap: keep container for follow-up.

pad_ready 180 || { echo "FAIL: virtpad not ready"; exit 1; }
pwait_text 'Press START' 300 '' 01_title || { echo "FAIL: no title"; exit 1; }
sleep 3
pad_press START 0.3
sleep 6
pad_press B 0.3          # decline any sign-in
sleep 5
if pwait_text 'Play Now' 40 '' 02_menu; then
    echo "PAD_VALIDATE_PASS: virtpad START reached the main menu"
else
    pshot 02_after_start_FAIL
    echo "PAD_VALIDATE_FAIL: menu not reached via virtpad"
fi
