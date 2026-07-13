#!/usr/bin/env bash
# Self-contained: boot the port with a uinput VIRTPAD (SDL gamepad path, no MnK)
# and a LONG watchdog, navigate golden_age (Golden Age / Deity / Russians) via
# the pad, reach gameplay, and END TURNS with RT — confirming the date plaque
# advances. The pad wakes the game's event-driven in-game loop (xdotool keyboard
# does not). Held presses (down/up >=2s) because llvmpipe polls ~1fps.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/golden_pad_full"
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
source "$HERE/port_pad_lib.sh"
rm -rf "$OUT"; mkdir -p "$OUT"

CIVREV_LOG_LEVEL=info CIVREV_VIRTPAD=1 EXTRA_ARGS="" \
    "$HERE/run_port.sh" --out "$OUT" --timeout 1800 --keep \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" > "$OUT/runner.log" 2>&1 &
# NO trap: keep the container alive after the test for manual end-turn iteration.

pad_ready 200 || { echo "FAIL: virtpad not ready"; exit 1; }
pwait_text 'Press START' 300 '' 01_title || { echo "FAIL: no title"; exit 1; }
sleep 3
pad_press START; sleep 6
pad_press B; sleep 5            # decline sign-in
pwait_text 'Play Now' 60 '' 02_main_menu || { echo "FAIL: no main menu"; exit 1; }

# main menu -> Single Player
pad_dpad down; sleep 1.5; pad_press A; sleep 4; pshot 03_single_player
# Single Player -> Play Scenario (down x3, A)
for i in 1 2 3; do pad_dpad down; sleep 1; done
pad_press A; sleep 4
pwait_text 'Golden|Beta|Centauri|Pacific|Chariots|Huns|Chariot' 30 '' 04_scenario_list || pad_log "scenario list unconfirmed"
sleep 2
# Golden Age
pad_find 'pad_dpad down' 12 'Golden Age' '0.54,0.21,0.82,0.33' || pad_log "Golden Age unconfirmed"
sleep 1; pshot 05_golden_selected
pad_press A; sleep 3
pwait_text 'Difficulty|Chieftain|Deity|Warlord|King|Prince' 20 '' 06_difficulty || pad_log "difficulty unconfirmed"
sleep 1
# Deity
pad_find 'pad_dpad down' 10 'De[il1]t|eity' '0.56,0.34,0.82,0.46' || pad_log "Deity unconfirmed"
sleep 1; pshot 07_deity_selected
pad_press A; sleep 3
pwait_text 'Civilization|Accept|Caesar|Cath|Roman|Aztec|Egypt|Monte' 25 '' 08_civ_select || pad_log "civ select unconfirmed"
sleep 2
# Russians: LEFT to Romans, then RIGHT to Russians
pad_find 'pad_dpad left' 30 'Caesar|Roman' '0.38,0.49,0.64,0.63' || pad_log "Romans unconfirmed"
sleep 1; pshot 09_at_romans
pad_find 'pad_dpad right' 20 'Cath|ussia' '0.38,0.49,0.64,0.63' || pad_log "Russians unconfirmed"
sleep 1; pshot 10_russians
# accept + load
pad_press A; sleep 2; pad_press A
pwait_text 'Loading|Galley|Ranger|Golden|Settlers' 60 '' 11_loading || pad_log "loading unconfirmed"
pad_log "waiting for load to finish (soft gate — in-game HUD text is garbled at 1fps)..."
# Best-effort OCR detect, but DO NOT hard-fail: the in-game HUD font renders as
# glyph soup under llvmpipe, so this rarely matches even though we're in-game.
pwait_text 'End Turn|Activate unit|Diplomacy|Wait One Turn|Found City' 180 '' 12_ingame \
    || pad_log "HUD OCR unconfirmed (expected); proceeding after settle"
sleep 60   # let the map fully render at ~1fps before touching the pad
pshot 12b_ingame_settled
pad_log "REACHED_GOLDEN_INGAME"; sleep 5

# ---- TURN-LOOP TEST ----
# read the date plaque (multi-threshold OCR of a wide crop)
read_date() {
  docker exec "$CONT" bash -c "DISPLAY=:99 import -window root /tmp/d.png" 2>/dev/null
  docker cp "$CONT:/tmp/d.png" "$OUT/.date.png" >/dev/null 2>&1 || return 1
  python3 - "$OUT/.date.png" <<'PY'
import sys,subprocess,tempfile,os
from PIL import Image, ImageOps
im=Image.open(sys.argv[1]).convert("L").crop((985,632,1195,685))
best=""
for th in (120,150,180,205):
    b=im.point(lambda p:255 if p>th else 0).resize((840,212))
    fd,t=tempfile.mkstemp(suffix=".png");os.close(fd);b.save(t)
    r=subprocess.run(["tesseract",t,"--psm","7","stdout"],capture_output=True,text=True);os.unlink(t)
    s=" ".join(r.stdout.split())
    if any(c.isdigit() for c in s) and len(s)>len(best): best=s
print(best)
PY
}
# date-region pixel signature (to detect a change even if OCR fails)
date_sig() { docker cp "$CONT:/tmp/d.png" "$OUT/.dsig.png" >/dev/null 2>&1; python3 -c "
import numpy as np; from PIL import Image
print(int(np.asarray(Image.open('$OUT/.dsig.png').convert('L').crop((985,632,1195,685))).astype(int).sum()))"; }

pshot t0_start
pad_log "date at start: [$(read_date)]  sig=$(date_sig)"
# Turn 1: found the city with the Settlers (Y = Found City) — the natural first
# move; consumes the Settlers so the turn can end.
pad_press Y; sleep 8; pshot t1_found_city
pad_log "after Found City: date=[$(read_date)] sig=$(date_sig)"
prev="$(date_sig)"
for n in $(seq 1 8); do
  pad_rt; sleep 6           # RT = End Turn
  pad_press A; sleep 3      # confirm 'end turn?' / next-unit / found-city prompts
  pad_press B; sleep 3      # dismiss popups
  pshot "turn_$n"
  cur="$(date_sig)"; dt="$(read_date)"
  changed="SAME"; [ "$cur" != "$prev" ] && changed="CHANGED"
  pad_log "after end-turn #$n: date=[$dt] sig=$cur  ($changed vs prev)"
  prev="$cur"
done
pad_log "TURN_LOOP_TEST_DONE (container kept alive)"
echo "TURN_LOOP_TEST_DONE"
