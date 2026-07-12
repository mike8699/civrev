#!/usr/bin/env bash
# m6_playnow.sh — drive the port from boot to IN-GAME via the shortest path:
#   title (Press START) -> [sign-in?] -> main menu (Play Now preselected) -> A
#   -> game loads -> terrain map on screen  (M6 first-part gate)
#
# Play Now starts a quick game immediately (random civ) — fewest input steps,
# so the llvmpipe ~1 fps poll loop has the fewest chances to bite. The
# deterministic golden_age parity run comes after this proves gameplay reaches
# the map at all.
#
# Usage: m6_playnow.sh [--out DIR] [--timeout SECS]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUT="$HERE/port_output/m6_playnow"
TIMEOUT=1500
while [ "$#" -gt 0 ]; do
    case "$1" in
        --out) OUT="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac

export PORT_OUT="$OUT"
export ORACLE_DIR="$HERE/../xenia_automation/oracle"
source "$HERE/port_nav_lib.sh"

rm -rf "$OUT"; mkdir -p "$OUT"
cp "$HERE/nav_controls.toml" "$OUT/controls.toml"

# Start the port (background); run_port.sh blanks intro movies, starts Xvfb,
# snaps a frame every second, and holds the GPU lock for the duration.
EXTRA_ARGS="--mnk_config=/output/controls.toml" \
    "$HERE/run_port.sh" --out "$OUT" --timeout "$TIMEOUT" \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" \
    > "$OUT/runner.log" 2>&1 &
RUNNER_PID=$!
trap 'kill $RUNNER_PID 2>/dev/null; docker rm -f civrev-port >/dev/null 2>&1' EXIT

nav_wait_ready 180 || exit 1

# --- 1. title screen -----------------------------------------------------------
pwait_text 'Press START' 300 '' 01_title || { nav_log 'FAIL: no title'; exit 1; }
sleep 3

# --- 2. START -> sign-in or main menu ------------------------------------------
phold j           # START
sleep "$SETTLE_SECS"
pshot 02_after_start

# Main menu shows "Play Now"; a sign-in dialog would not. Decline sign-in with
# B (Backspace) if we're not on the menu yet — mirrors the oracle's `input B`.
if ! pocr 'Play Now' >/dev/null 2>&1; then
    nav_log "not on main menu yet -> OCR: $(nav_ocr_dump || true)"
    phold BackSpace   # B: decline sign-in
    sleep "$SETTLE_SECS"
fi
pwait_text 'Play Now' 60 '' 03_main_menu || { nav_log 'FAIL: no main menu'; exit 1; }
sleep 2

# --- 3. A on Play Now -----------------------------------------------------------
phold Return      # A
nav_log "pressed A on Play Now; probing for game load"

# --- 4. probe until in-game ------------------------------------------------------
# In-game anchor: the era/date plaque "4000 BC". It is the ONLY HUD string the
# Loading screen's rotating gameplay hints can never contain (hints DO mention
# Diplomacy/units — 'Diplomacy' as an anchor false-positived on a hint).
DEADLINE=$((SECONDS + 900))
STATE=""
while [ "$SECONDS" -lt "$DEADLINE" ]; do
    if pocr '4000 BC' >/dev/null 2>&1; then
        STATE=ingame; break
    fi
    txt="$(nav_ocr_dump 2>/dev/null || true)"
    nav_log "probe: ${txt:0:120}"
    case "$txt" in
        *Loading*) ;;          # loading screen — just wait
        *"begin the game"*|*"Select Your Civilization"*)
            # Play Now rolls a random civ and presents it on the civ-select
            # carousel; A = Accept (sometimes needs a second press — the case
            # simply fires again on the next probe if the card is still up).
            pshot 04_civ_card; phold Return ;;
        *"Wait One Turn"*|*"Defend City"*|*"Found City"*|*"Wait Here"*)
            # In-game unit action panel visible (and NOT a Loading hint — hints
            # never render the action menu). This is the definitive in-game HUD.
            STATE=ingame; break ;;
        *"awaiting orders"*)
            # Play Now's unit-move tutorial prompt: it dismisses when the unit
            # actually moves. Nudge the left stick (D) then confirm (A). This
            # reaches the bare unit action panel -> caught next probe.
            phold d 2; phold Return ;;
        *"awaiting"*|*"REVOLUTION"*|*Zimbabwe*|*Excellent*|*"tell me"*|*Tutorial*)
            # Play Now enables the tutorial: a chain of advisor dialogs whose
            # top option (A) advances/acknowledges. Walk it.
            phold Return ;;
        *"Play Now"*)          # A didn't register — press again
            phold Return ;;
        *Difficulty*|*Chieftain*)   # unexpected difficulty prompt: accept default
            pshot 04_difficulty; phold Return ;;
        *"Press START"*)       # bounced back to title?!
            phold j ;;
    esac
    sleep 8
done

if [ "$STATE" != ingame ]; then
    nav_log "FAIL: never reached in-game HUD"; pshot 99_last; exit 1
fi
pshot 05_ingame_first
nav_log "IN-GAME detected; letting the map settle / shaders finish"
sleep 30
# Dismiss any start-of-game popup (B), then take the money shot.
phold BackSpace
sleep 10
pshot 06_ingame
nav_log "done"
