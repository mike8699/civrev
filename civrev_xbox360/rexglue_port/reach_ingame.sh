#!/usr/bin/env bash
# Boot the port and navigate to in-game (Play Now), leaving the container ALIVE
# (--keep, no teardown) so end-turn / gameplay input can be driven interactively
# afterward via `docker exec civrev-port ...`. Prints "REACHED_INGAME" when the
# unit HUD is up.
#   Usage: reach_ingame.sh [--out DIR] [--timeout SECS]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/ingame_session"; TIMEOUT=900
while [ "$#" -gt 0 ]; do case "$1" in
    --out) OUT="$2"; shift 2 ;; --timeout) TIMEOUT="$2"; shift 2 ;;
    *) echo "unknown arg $1" >&2; exit 2 ;; esac; done
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
source "$HERE/port_nav_lib.sh"
rm -rf "$OUT"; mkdir -p "$OUT"; cp "$HERE/nav_controls.toml" "$OUT/controls.toml"

CIVREV_LOG_LEVEL=info EXTRA_ARGS="--mnk_config=/output/controls.toml" \
    "$HERE/run_port.sh" --out "$OUT" --timeout "$TIMEOUT" --keep \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" > "$OUT/runner.log" 2>&1 &
# NOTE: no trap — deliberately leave civrev-port running for interaction.

nav_wait_ready 180 || { echo "FAIL: no window"; exit 1; }
pwait_text 'Press START' 300 '' 01_title || { echo "FAIL: no title"; exit 1; }
sleep 3
phold j            # START -> main menu
sleep "$SETTLE_SECS"
pwait_text 'Play Now' 60 '' 02_menu || nav_log "menu not confirmed"
sleep 2
phold Return       # A on Play Now
nav_log "pressed Play Now; walking to in-game"

DEADLINE=$((SECONDS + 700))
while [ "$SECONDS" -lt "$DEADLINE" ]; do
    if pocr '4000 BC' >/dev/null 2>&1 || pocr 'Wait One Turn|Found City|Defend City' >/dev/null 2>&1; then
        pshot ingame; nav_log "REACHED_INGAME"; echo "REACHED_INGAME"; exit 0
    fi
    txt="$(nav_ocr_dump 2>/dev/null || true)"
    nav_log "probe: ${txt:0:90}"
    case "$txt" in
        *Loading*) ;;
        *"begin the game"*|*"Select Your Civilization"*) phold Return ;;
        *"awaiting orders"*) phold d 2; phold Return ;;
        *REVOLUTION*|*Zimbabwe*|*Excellent*|*"tell me"*|*Tutorial*|*Welcome*) phold Return ;;
        *"Play Now"*) phold Return ;;
    esac
    sleep 8
done
echo "FAIL: never reached in-game"; exit 1
