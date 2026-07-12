# port_nav_lib.sh — host-side navigation primitives for driving the ReXGlue
# civrev port running in the `civrev-port` container (started by run_port.sh).
#
# Mirrors the oracle run_scenario.sh primitives (wait_text / find_text / shot)
# but injects input as X11 KEY HOLDS via xdotool: the MnK driver synthesizes
# one VK_PAD_* keystroke per key-state TRANSITION (no auto-repeat), and on
# llvmpipe (~1 fps) the game's GetKeystroke poll is slow — a hold must straddle
# at least one poll, so taps are lost but a >=3 s hold is exactly one press.
#
# Requires: PORT_OUT (host artifact dir, same dir passed to run_port.sh --out),
# ORACLE_DIR (xenia_automation/oracle, for ocr.py). Uses host tesseract.
#
# shellcheck disable=SC2086

CONT="${CONT:-civrev-port}"
HOLD_SECS="${HOLD_SECS:-3}"      # key hold long enough to straddle a 1 fps poll
SETTLE_SECS="${SETTLE_SECS:-6}"  # UI animation settle at ~1 fps

nav_log() { printf '[nav %s] %s\n' "$(date +%H:%M:%S)" "$*"; }

pexec() { docker exec "$CONT" bash -c "DISPLAY=:99 $*"; }

# Wait for the container + X server + game window, then focus the window.
# Installs xdotool first if the image lacks it (the window search needs it).
nav_wait_ready() {
    local timeout="${1:-120}" i installed=0
    for ((i = 0; i < timeout; i += 2)); do
        if docker inspect -f '{{.State.Running}}' "$CONT" 2>/dev/null | grep -q true; then
            if [ "$installed" = 0 ]; then
                nav_ensure_xdotool || { sleep 2; continue; }
                installed=1
                nav_log "xdotool ready"
            fi
            local win
            win="$(pexec "xdotool search --onlyvisible '.' 2>/dev/null | head -1" 2>/dev/null || true)"
            if [ -n "$win" ]; then
                pexec "xdotool windowactivate $win; xdotool windowfocus $win" 2>/dev/null || true
                nav_log "window $win focused"
                return 0
            fi
        fi
        sleep 2
    done
    nav_log "ERROR: container/window never came up"; return 1
}

# Install xdotool in the container if the image lacks it (mirrors test_controls.sh).
nav_ensure_xdotool() {
    docker exec "$CONT" bash -c \
        "command -v xdotool >/dev/null || (apt-get update -qq && apt-get install -y -qq xdotool) >/dev/null 2>&1; command -v xdotool" \
        >/dev/null
}

# phold <X11-key> [secs] — one gamepad press (keydown, hold, keyup).
phold() {
    local key="$1" secs="${2:-$HOLD_SECS}"
    pexec "xdotool keydown $key" || nav_log "WARN keydown $key failed"
    sleep "$secs"
    pexec "xdotool keyup $key" || nav_log "WARN keyup $key failed"
    nav_log "pressed $key (${secs}s hold)"
}

# pshot <name> — screenshot of the container root window -> $PORT_OUT/<name>.png
pshot() {
    local name="$1"
    pexec "import -window root /tmp/pshot.png" 2>/dev/null
    docker cp "$CONT:/tmp/pshot.png" "$PORT_OUT/$name.png" >/dev/null 2>&1 \
        && nav_log "shot $name" || nav_log "WARN shot $name failed"
}

# pocr <pattern> [crop] — OCR the current screen (host tesseract). Exit 0 on
# match. Two passes: plain autocontrast (legal text, loading screens), then
# thresh=200 binarized (bright UI text over the busy 3D scene — main menu
# buttons, in-game HUD — which plain OCR reads as garbage).
pocr() {
    local pattern="$1" crop="${2:-}"
    pexec "import -window root /tmp/pocr.png" 2>/dev/null
    docker cp "$CONT:/tmp/pocr.png" "$PORT_OUT/.ocr.png" >/dev/null 2>&1 || return 1
    local cropargs=(); [ -n "$crop" ] && cropargs=(--crop "$crop")
    python3 "$ORACLE_DIR/ocr.py" "$PORT_OUT/.ocr.png" "$pattern" "${cropargs[@]}" && return 0
    python3 "$ORACLE_DIR/ocr.py" "$PORT_OUT/.ocr.png" "$pattern" "${cropargs[@]}" --thresh 200
}

# pwait_text <pattern> <timeout> [crop] [save_name] — poll OCR until match.
# Saves the matched frame as <save_name>.png when given.
pwait_text() {
    local pattern="$1" timeout="${2:-120}" crop="${3:-}" save="${4:-}" waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if pocr "$pattern" "$crop" >/dev/null 2>&1; then
            nav_log "OCR matched '$pattern' (t=${waited}s)"
            [ -n "$save" ] && cp "$PORT_OUT/.ocr.png" "$PORT_OUT/$save.png" 2>/dev/null
            return 0
        fi
        sleep 3; waited=$((waited + 3))
    done
    nav_log "WARN pwait_text '$pattern' timed out (${timeout}s)"
    [ -n "$save" ] && cp "$PORT_OUT/.ocr.png" "$PORT_OUT/${save}_TIMEOUT.png" 2>/dev/null
    return 1
}

# pfind_text <key> <max> <pattern> [crop] — OCR; if no match press <key> and
# retry (checks BEFORE each press and once after the last, like the oracle).
pfind_text() {
    local key="$1" max="$2" pattern="$3" crop="${4:-}" i
    for ((i = 0; i <= max; i++)); do
        if pocr "$pattern" "$crop" >/dev/null 2>&1; then
            nav_log "find_text matched '$pattern' after $i x $key"
            return 0
        fi
        [ "$i" -ge "$max" ] && break
        phold "$key"
        sleep "$SETTLE_SECS"
    done
    nav_log "WARN find_text '$pattern' not found after $max x $key"
    return 1
}

# pwait_log <regex> <timeout> — wait for a pattern in the port's run.log
# (the /output mount makes it visible on the host at $PORT_OUT/run.log).
pwait_log() {
    local pattern="$1" timeout="${2:-120}" waited=0
    while [ "$waited" -lt "$timeout" ]; do
        grep -qE "$pattern" "$PORT_OUT/run.log" 2>/dev/null && { nav_log "log matched '$pattern' (t=${waited}s)"; return 0; }
        sleep 2; waited=$((waited + 2))
    done
    nav_log "WARN pwait_log '$pattern' timed out"; return 1
}

# nav_ocr_dump [crop] — print current-screen OCR text (for exploration/debug).
nav_ocr_dump() {
    local crop="${1:-}"
    pexec "import -window root /tmp/pocr.png" 2>/dev/null
    docker cp "$CONT:/tmp/pocr.png" "$PORT_OUT/.ocr.png" >/dev/null 2>&1 || return 1
    python3 - "$PORT_OUT/.ocr.png" "$crop" <<'EOF'
import subprocess, sys, tempfile, os
from PIL import Image, ImageOps
src = Image.open(sys.argv[1]).convert("L")
if len(sys.argv) > 2 and sys.argv[2]:
    c = [float(v) for v in sys.argv[2].split(",")]
    w, h = src.size
    src = src.crop((int(c[0]*w), int(c[1]*h), int(c[2]*w), int(c[3]*h)))
out = []
for thresh in (None, 200):
    im = src.point(lambda p: 255 if p > thresh else 0) if thresh else src
    im = ImageOps.autocontrast(im.resize((im.width*2, im.height*2)))
    fd, tmp = tempfile.mkstemp(suffix=".png"); os.close(fd)
    im.save(tmp)
    r = subprocess.run(["tesseract", tmp, "stdout"], capture_output=True, text=True, timeout=30)
    os.unlink(tmp)
    out.append(" ".join(r.stdout.split()))
print(" /THR/ ".join(out))
EOF
}
