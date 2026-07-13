# port_pad_lib.sh — drive the port's IN-GAME + menu input via the uinput virtpad
# (SDL gamepad path), which wakes the game's event-driven in-game loop where
# injected xdotool keyboard does not. Requires the port booted with
# CIVREV_VIRTPAD=1 (run_port.sh starts virtpad.py on the FIFO /tmp/virtpad.cmd).
# OCR helpers reuse the host tesseract path (ORACLE_DIR/ocr.py).
# shellcheck disable=SC2086
CONT="${CONT:-civrev-port}"

pad_log() { printf '[pad %s] %s\n' "$(date +%H:%M:%S)" "$*"; }
# send one virtpad command line to the FIFO in the container
pad() { docker exec "$CONT" bash -c "printf '%s\n' \"$*\" > /tmp/virtpad.cmd" 2>/dev/null; }

# At llvmpipe ~1fps the game coalesces quick presses; hold every input across a
# poll (>=1-2s) via explicit down/up.
pad_press() { pad "down ${1}"; sleep "${2:-2}"; pad "up ${1}"; pad_log "press $1"; }   # A B X Y LB RB START BACK LS RS
pad_dpad()  { pad "dpad ${1}"; sleep "${2:-1}"; pad "dpad center"; pad_log "dpad $1"; }
pad_rt()    { pad "trig r 255"; sleep "${1:-1.5}"; pad "trig r 0"; pad_log "RT (end turn)"; }   # right trigger
pad_lt()    { pad "trig l 255"; sleep "${1:-1.5}"; pad "trig l 0"; pad_log "LT"; }
pad_stick() { pad "stick l ${1} ${2}"; pad "sleep ${3:-0.4}"; pad "stick l 0 0"; pad_log "stick $1 $2"; }

# --- OCR (host tesseract), plain + thresh=200, optional crop ---
pocr() {
    local pattern="$1" crop="${2:-}"
    docker exec "$CONT" bash -c "DISPLAY=:99 import -window root /tmp/pocr.png" 2>/dev/null
    docker cp "$CONT:/tmp/pocr.png" "$PORT_OUT/.ocr.png" >/dev/null 2>&1 || return 1
    local ca=(); [ -n "$crop" ] && ca=(--crop "$crop")
    python3 "$ORACLE_DIR/ocr.py" "$PORT_OUT/.ocr.png" "$pattern" "${ca[@]}" && return 0
    python3 "$ORACLE_DIR/ocr.py" "$PORT_OUT/.ocr.png" "$pattern" "${ca[@]}" --thresh 200
}
pshot() { docker exec "$CONT" bash -c "DISPLAY=:99 import -window root /tmp/s.png" 2>/dev/null; docker cp "$CONT:/tmp/s.png" "$PORT_OUT/$1.png" >/dev/null 2>&1 && pad_log "shot $1"; }
pwait_text() {  # pattern timeout [crop] [savename]
    local p="$1" to="${2:-120}" crop="${3:-}" save="${4:-}" w=0
    while [ "$w" -lt "$to" ]; do
        if pocr "$p" "$crop" >/dev/null 2>&1; then pad_log "OCR matched '$p' (t=${w}s)"; [ -n "$save" ] && cp "$PORT_OUT/.ocr.png" "$PORT_OUT/$save.png" 2>/dev/null; return 0; fi
        sleep 3; w=$((w+3))
    done
    pad_log "WARN pwait_text '$p' timed out (${to}s)"; [ -n "$save" ] && cp "$PORT_OUT/.ocr.png" "$PORT_OUT/${save}_TIMEOUT.png" 2>/dev/null; return 1
}
# pfind_text <padfn> <arg...> ... — generic: caller passes an action callback.
pad_find() {  # <action-cmd> <max> <pattern> [crop]
    local action="$1" max="$2" pattern="$3" crop="${4:-}" i
    for ((i=0; i<=max; i++)); do
        if pocr "$pattern" "$crop" >/dev/null 2>&1; then pad_log "find matched '$pattern' after $i x [$action]"; return 0; fi
        [ "$i" -ge "$max" ] && break
        eval "$action"; sleep 1.4
    done
    pad_log "WARN find '$pattern' not found after $max x [$action]"; return 1
}
pad_ready() {  # wait until container up + virtpad FIFO exists
    local to="${1:-180}" i
    for ((i=0; i<to; i+=3)); do
        docker inspect -f '{{.State.Running}}' "$CONT" 2>/dev/null | grep -q true \
          && docker exec "$CONT" bash -c "[ -p /tmp/virtpad.cmd ]" 2>/dev/null \
          && { pad_log "virtpad FIFO ready"; return 0; }
        sleep 3
    done
    pad_log "ERROR virtpad not ready"; return 1
}
