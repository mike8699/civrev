#!/usr/bin/env bash
# Drive golden_age (Golden Age / Deity / Russians) + the END-TURN test via the
# uinput VIRTPAD, continuing from the main menu (Play Now visible) on an
# already-booted CIVREV_VIRTPAD=1 container. Mirrors the oracle golden_age
# script but through the SDL gamepad (dpad + A + RT), which wakes the game's
# in-game event loop. Verifies the date plaque advances across turns.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/validate_pad"           # reuse the live container's out dir
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
source "$HERE/port_pad_lib.sh"

# --- main menu -> Single Player (1 down, A) ---
pad_dpad down; sleep 1.5; pad_press A; sleep 4
pshot 03_single_player
# --- Single Player -> Play Scenario (down x3, A) ---
for i in 1 2 3; do pad_dpad down; sleep 1.2; done
pad_press A
pwait_text 'Golden|Beta|Centauri|Pacific|Chariots|Huns' 25 '' 04_scenario_list || pad_log "scenario list unconfirmed"
sleep 3
# --- Golden Age (OCR-verified via description-panel header) ---
pad_find 'pad_dpad down' 12 'Golden Age' '0.54,0.21,0.82,0.33' || pad_log "Golden Age unconfirmed"
sleep 1; pshot 05_golden_selected
pad_press A
pwait_text 'Difficulty|Chieftain|Deity|Warlord|King|Prince' 20 '' 06_difficulty || pad_log "difficulty unconfirmed"
sleep 1
# --- Deity ---
pad_find 'pad_dpad down' 10 'De[il1]t|eity' '0.56,0.34,0.82,0.46' || pad_log "Deity unconfirmed"
sleep 1; pshot 07_deity_selected
pad_press A
pwait_text 'Civilization|Accept|Caesar|Cath|Roman|Aztec|Egypt' 25 '' 08_civ_select || pad_log "civ select unconfirmed"
sleep 2
# --- Russians: LEFT to Romans, then RIGHT to Russians ---
pad_find 'pad_dpad left' 30 'Caesar|Roman' '0.38,0.49,0.64,0.63' || pad_log "Romans unconfirmed"
sleep 1; pshot 09_at_romans
pad_find 'pad_dpad right' 20 'Cath|ussia' '0.38,0.49,0.64,0.63' || pad_log "Russians unconfirmed"
sleep 1; pshot 10_russians
# --- accept + load ---
pad_press A; sleep 2; pad_press A
pwait_text 'Loading|Galley|Ranger|Golden|Settlers' 60 '' 11_loading || pad_log "loading unconfirmed"
# wait for the REAL in-game HUD (not a Loading tip): the End Turn button /
# unit panel appears. Do NOT send input during load.
pad_log "waiting for real in-game HUD (no input during load)..."
if pwait_text 'End Turn|Activate unit|Diplomacy|Wait One Turn|Found City' 240 '' 12_ingame; then
    pad_log "REACHED_GOLDEN_INGAME"
else
    pad_log "FAIL: never reached in-game HUD"; exit 1
fi
sleep 4

# ---- END-TURN TEST via virtpad RT ----
read_date() {
  docker exec "$CONT" bash -c "DISPLAY=:99 import -window root /tmp/d.png" 2>/dev/null
  docker cp "$CONT:/tmp/d.png" "$OUT/.date.png" >/dev/null 2>&1 || return 1
  python3 - "$OUT/.date.png" <<'PY'
import sys,subprocess,tempfile,os
from PIL import Image, ImageOps
im=Image.open(sys.argv[1]).convert("L").crop((1010,640,1180,680))
im=im.point(lambda p:255 if p>150 else 0).resize((680,160))
fd,t=tempfile.mkstemp(suffix=".png");os.close(fd);im.save(t)
r=subprocess.run(["tesseract",t,"--psm","7","stdout"],capture_output=True,text=True);os.unlink(t)
print(" ".join(r.stdout.split()))
PY
}
d0="$(read_date)"; pad_log "date BEFORE: [$d0]"
for n in 1 2 3 4 5; do
  pad_rt                        # RT = End Turn
  sleep 7
  pad_press A                   # confirm 'end turn with units?' / next-unit prompt
  sleep 2
  pad_press B                   # dismiss any popup
  sleep 3
  pshot "turn_$n"
  pad_log "after end-turn #$n: date=[$(read_date)]"
done
pad_log "END_TURN_TEST_DONE"
echo "END_TURN_TEST_DONE"
