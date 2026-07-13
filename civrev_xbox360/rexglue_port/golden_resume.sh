#!/usr/bin/env bash
# Resume golden_age nav from the "Choose Scenario" screen with Golden Age
# already selected, through Deity/Russians into gameplay, then END A TURN with
# RT and confirm the date plaque advances. Assumes civrev-port is UP at the
# scenario list.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/port_output/golden_reach"
export PORT_OUT="$OUT" ORACLE_DIR="$HERE/../xenia_automation/oracle"
export HOLD_SECS=2 SETTLE_SECS=3
source "$HERE/port_nav_lib.sh"
WIN="$(pexec "xdotool search --onlyvisible '.' 2>/dev/null | head -1" 2>/dev/null || true)"
refocus() { pexec "xdotool windowfocus $WIN" 2>/dev/null || true; }

# Golden Age is selected -> A to pick it, wait for difficulty screen
refocus; phold Return
pwait_text 'Difficulty|Chieftain|Deity|Warlord|King|Prince' 25 '' 06_difficulty || nav_log "difficulty not confirmed"
sleep 1
# Deity difficulty (OCR-verified via description-panel header)
pfind_text s 10 'De[il1]t|eity' '0.56,0.34,0.82,0.46' || nav_log "Deity not confirmed"
sleep 1; pshot 07_deity_selected
refocus; phold Return
pwait_text 'Civilization|Accept|Caesar|Cath|Roman' 25 '' 08_civ_select || nav_log "civ select not confirmed"
sleep 2
# Russians: scroll LEFT to Romans (leftmost), then RIGHT to Russians (Catherine)
pfind_text a 30 'Caesar|Roman' '0.38,0.49,0.64,0.63' || nav_log "Romans not confirmed"
sleep 1; pshot 09_at_romans
pfind_text d 20 'Cath|ussia' '0.38,0.49,0.64,0.63' || nav_log "Russians not confirmed"
sleep 1; pshot 10_russians
# accept and load
refocus; phold Return; sleep 2; refocus; phold Return
pwait_text 'Loading|Galley|Ranger|Golden|Settlers|Deity' 60 '' 11_loading || nav_log "loading not confirmed"
sleep 22
refocus; phold BackSpace   # dismiss any start popup
sleep 4
pshot 12_gameplay
nav_log "REACHED_GOLDEN_INGAME"

# ---- END-TURN TEST ----
# Read the date plaque (bottom-right), press RT (End Turn = PageUp) a few times,
# confirm the date advances (turn loop works).
read_date() {
  pexec "import -window root /tmp/d.png" 2>/dev/null
  docker cp civrev-port:/tmp/d.png "$OUT/.date.png" >/dev/null 2>&1 || return 1
  python3 - "$OUT/.date.png" <<'PY'
import sys,subprocess,tempfile,os
from PIL import Image, ImageOps
im=Image.open(sys.argv[1]).convert("L").crop((940,615,1280,705))
im=ImageOps.autocontrast(im.resize((im.width*3,im.height*3)))
fd,t=tempfile.mkstemp(suffix=".png");os.close(fd);im.save(t)
r=subprocess.run(["tesseract",t,"stdout"],capture_output=True,text=True);os.unlink(t)
print(" ".join(r.stdout.split()))
PY
}
nav_log "date before end-turn: [$(read_date)]"
for n in 1 2 3 4 5; do
  refocus; phold Prior 2        # RT = PageUp = End Turn
  sleep 6
  refocus; phold Return         # dismiss any 'next turn' / unit prompt
  sleep 2
  refocus; phold BackSpace      # dismiss any popup
  sleep 3
  pshot "turn_$n"
  nav_log "after end-turn #$n: date=[$(read_date)]"
done
nav_log "END_TURN_TEST_DONE"
echo "END_TURN_TEST_DONE"
