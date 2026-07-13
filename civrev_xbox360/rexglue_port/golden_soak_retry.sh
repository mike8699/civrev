#!/usr/bin/env bash
# Wrapper around golden_soak.sh that tolerates the INTERMITTENT boot-time GPU-hang
# deadlock (guest D3D "GPU is hung" + tw/td trap that occasionally fails to
# recover). Detects a boot deadlock early — run.log stops growing before the
# title appears — kills the attempt, and retries. Once booted to the title, it
# lets the soak run its 20 turns and reports the outcome.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONT=civrev-port
NTURNS="${1:-20}"
MAXATT="${2:-5}"
DRV="$HERE/port_output/golden_soak_driver.log"

boot_reached() { grep -qE "Press START|Play Now|REACHED_GOLDEN_INGAME" "$DRV" 2>/dev/null; }
soak_done()    { grep -qE "SOAK_PASS|SOAK_FAIL|crashed at turn|game process DIED" "$DRV" 2>/dev/null; }
lllog() { docker exec "$CONT" bash -c 'wc -l < /output/run.log 2>/dev/null' 2>/dev/null | tr -d ' '; }

for att in $(seq 1 "$MAXATT"); do
  echo "===== SOAK ATTEMPT $att/$MAXATT ====="
  docker rm -f "$CONT" >/dev/null 2>&1
  : > "$DRV"
  nohup bash "$HERE/golden_soak.sh" "$NTURNS" > "$DRV" 2>&1 &
  # ---- boot watchdog: wait until title reached, or run.log stalls (deadlock) ----
  last=-1; stall=0; booted=0
  for t in $(seq 1 140); do    # ~7 min max boot window
    if boot_reached; then booted=1; echo "[att $att] boot OK (title/menu reached) after ~$((t*3))s"; break; fi
    if soak_done; then break; fi
    ll="$(lllog)"; ll="${ll:-0}"
    if [ "$ll" = "$last" ]; then stall=$((stall+3)); else stall=0; last="$ll"; fi
    # deadlock if the log froze for 75s and we saw the GPU-hang trap
    if [ "$stall" -ge 75 ]; then
      if docker exec "$CONT" bash -c "grep -q 'tw/td trap' /output/run.log" 2>/dev/null; then
        echo "[att $att] BOOT DEADLOCK: run.log frozen at $ll lines for ${stall}s after GPU-hang trap -> retry"
      else
        echo "[att $att] BOOT STALL: run.log frozen at $ll lines for ${stall}s -> retry"
      fi
      break
    fi
    sleep 3
  done
  if [ "$booted" != 1 ]; then
    # kill this attempt's soak driver + container, then retry
    pkill -f "golden_soak.sh $NTURNS" 2>/dev/null
    docker rm -f "$CONT" >/dev/null 2>&1
    sleep 2
    continue
  fi
  # ---- booted: let the soak run to completion ----
  echo "[att $att] booted; letting soak drive $NTURNS turns..."
  for t in $(seq 1 600); do   # up to 50 min
    if soak_done; then break; fi
    sleep 5
  done
  echo "===== SOAK ATTEMPT $att RESULT ====="
  grep -E "SOAK_PASS|SOAK_FAIL|crashed at turn|game process DIED|SOAK_DONE" "$DRV" | tail -4
  # if the soak itself succeeded or crashed mid-turns (a real turn-level result), stop retrying
  if grep -qE "SOAK_PASS|crashed at turn|game process DIED" "$DRV"; then exit 0; fi
  # a non-boot SOAK_FAIL (e.g. lost nav) -> retry
  echo "[att $att] soak did not pass; retrying"
  docker rm -f "$CONT" >/dev/null 2>&1; sleep 2
done
echo "SOAK_RETRY_EXHAUSTED after $MAXATT attempts"
exit 3
