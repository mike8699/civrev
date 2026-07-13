#!/usr/bin/env bash
# Reach the tutorial-free golden_age scenario (Golden Age / Deity / Russians) on
# the port, then END A TURN with RT and confirm the date plaque advances. Mirrors
# xenia_automation/oracle/scenarios/golden_age/script.txt but uses the port's
# MnK menu input: the port menus navigate with the LEFT STICK (W/A/S/D), not the
# dpad (dpad is inert in these menus by game design). Selection is OCR-verified
# via find_text crops over the description panel.
#
# Leaves the container ALIVE (--keep) at the end for the end-turn test.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/golden_reach"; TIMEOUT=1500
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
# Menu nav is more forgiving than unit movement — use shorter holds/settles.
export HOLD_SECS=2 SETTLE_SECS=3
source "$HERE/port_nav_lib.sh"
rm -rf "$OUT"; mkdir -p "$OUT"; cp "$HERE/nav_controls.toml" "$OUT/controls.toml"

CIVREV_LOG_LEVEL=info EXTRA_ARGS="--mnk_config=/output/controls.toml" \
    "$HERE/run_port.sh" --out "$OUT" --timeout "$TIMEOUT" --keep \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" > "$OUT/runner.log" 2>&1 &
# no trap: keep the container for the end-turn test.

nav_wait_ready 180 || { echo "FAIL: no window"; exit 1; }
WIN="$(pexec "xdotool search --onlyvisible '.' 2>/dev/null | head -1" 2>/dev/null || true)"
refocus() { pexec "xdotool windowfocus $WIN" 2>/dev/null || true; }

pwait_text 'Press START' 300 '' 01_title || { echo "FAIL: no title"; exit 1; }
sleep 3
refocus; phold j            # START
sleep "$SETTLE_SECS"
refocus; phold BackSpace    # decline any sign-in (harmless if none)
sleep "$SETTLE_SECS"
pwait_text 'Play Now' 60 '' 02_main_menu || { echo "FAIL: no main menu"; exit 1; }

# main menu -> Single Player (1 down, A)
refocus; phold s
sleep "$SETTLE_SECS"
refocus; phold Return
sleep "$SETTLE_SECS"
pshot 03_single_player
# Single Player -> Play Scenario (down x3, A), verify scenario list
for i in 1 2 3; do refocus; phold s; sleep 1.5; done
refocus; phold Return
pwait_text 'Choose|Scenario|Golden|Beta|Pacific' 25 '' 04_scenario_list || nav_log "scenario list not confirmed (continuing)"
sleep 3

# select Golden Age (OCR-verified via description-panel header)
pfind_text s 12 'Golden Age' '0.54,0.21,0.82,0.33' || nav_log "Golden Age not confirmed"
sleep 1; pshot 05_golden_selected
refocus; phold Return
pwait_text 'Difficulty|Chieftain|Deity|Warlord' 20 '' 06_difficulty || nav_log "difficulty not confirmed"
sleep 1

# Deity difficulty
pfind_text s 10 'De[il1]t|eity' '0.56,0.34,0.82,0.46' || nav_log "Deity not confirmed"
sleep 1; pshot 07_deity_selected
refocus; phold Return
pwait_text 'Civilization|Accept|Caesar|Cath' 25 '' 08_civ_select || nav_log "civ select not confirmed"
sleep 2

# Russians: scroll LEFT to Romans (leftmost), then RIGHT to Russians (Catherine)
pfind_text a 30 'Caesar|Roman' '0.38,0.49,0.64,0.63' || nav_log "Romans not confirmed"
sleep 1; pshot 09_at_romans
pfind_text d 20 'Cath|ussia' '0.38,0.49,0.64,0.63' || nav_log "Russians not confirmed"
sleep 1; pshot 10_russians

# accept and load
refocus; phold Return; sleep 2; refocus; phold Return
pwait_text 'Loading|Galley|Ranger|Golden|Settlers' 60 '' 11_loading || nav_log "loading not confirmed"
sleep 20
refocus; phold BackSpace    # dismiss any start-of-game popup
sleep 4
pshot 12_gameplay
nav_log "REACHED_GOLDEN_INGAME"
echo "REACHED_GOLDEN_INGAME"
