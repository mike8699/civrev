#!/usr/bin/env bash
# End-to-end test for the TOML keyboard/mouse controller mapping (MnK driver).
#
# Boots the port headlessly with a given controls.toml, waits for the title
# screen ("Press START to begin"), then injects X11 keyboard/mouse input via
# xdotool inside the container and checks whether the game ADVANCES past the
# title (START registered) — proving the binding path
# TOML -> MnK driver -> XamInputGetState -> game.
#
# Usage: test_controls.sh --toml FILE --inject "CMD [CMD...]" --out DIR
#                         [--expect advance|noadvance] [--timeout SECS]
#   CMD is an xdotool argument string, e.g. "key Return" or "click 1" or
#   "mousemove_relative -- 0 200".
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TOML=""; INJECT=(); OUT=""; EXPECT="advance"; TIMEOUT=240
while [ "$#" -gt 0 ]; do
    case "$1" in
        --toml) TOML="$2"; shift 2 ;;
        --inject) INJECT+=("$2"); shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --expect) EXPECT="$2"; shift 2 ;;
        --timeout) TIMEOUT="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done
[ -n "$TOML" ] && [ -n "$OUT" ] || { echo "need --toml and --out" >&2; exit 2; }
case "$OUT" in /*) ;; *) OUT="$PWD/$OUT" ;; esac

mkdir -p "$OUT"
cp "$TOML" "$OUT/controls.toml"

# Start the port (background) with the mapping under test.
EXTRA_ARGS="--mnk_config=/output/controls.toml" \
    "$HERE/run_port.sh" --out "$OUT" --timeout "$TIMEOUT" \
    --bin "$HERE/civrev/out/build/linux-amd64-release/civrev" \
    > "$OUT/runner.log" 2>&1 &
RUNNER_PID=$!

frame_brightpx() {  # count of pixels with any channel > 60 in the newest COMPLETE frame
    python3 - "$1" <<'EOF'
import glob, sys
import numpy as np
from PIL import Image
frames = sorted(glob.glob(sys.argv[1] + "/frames/f*.png"))
# Newest frames may still be mid-write (import writes in place); scan back to
# the first one that loads completely.
for f in reversed(frames):
    try:
        a = np.asarray(Image.open(f).convert("RGB"))
        print(int((a.max(axis=2) > 60).sum())); raise SystemExit
    except SystemExit:
        raise
    except Exception:
        continue
print(0)
EOF
}

# Newest frame that loads without truncation, copied to $2.
copy_last_good_frame() {
    python3 - "$1" "$2" <<'EOF'
import glob, sys, shutil
from PIL import Image
frames = sorted(glob.glob(sys.argv[1] + "/frames/f*.png"))
for f in reversed(frames):
    try:
        Image.open(f).convert("RGB").load()
        shutil.copy(f, sys.argv[2]); print(f); raise SystemExit
    except SystemExit:
        raise
    except Exception:
        continue
raise SystemExit("no complete frame")
EOF
}

# 1) Wait for the title screen: a huge amount of bright content (the 3D
#    panorama) vs the sparse text of the loading/legal screens.
echo "[test] waiting for title screen..."
TITLE_SEEN=0
for i in $(seq 1 "$TIMEOUT"); do
    sleep 1
    kill -0 "$RUNNER_PID" 2>/dev/null || { echo "[test] runner exited early" >&2; break; }
    px=$(frame_brightpx "$OUT")
    if [ "$px" -gt 400000 ]; then TITLE_SEEN=1; echo "[test] title screen up (brightpx=$px, t=${i}s)"; break; fi
done
if [ "$TITLE_SEEN" != 1 ]; then
    echo "RESULT: FAIL (title screen never appeared)"; kill "$RUNNER_PID" 2>/dev/null || true; exit 1
fi
sleep 3  # let the title settle
copy_last_good_frame "$OUT" "$OUT/before_inject.png"

# 2) Inject input via xdotool inside the container.
docker exec civrev-port bash -c \
    "command -v xdotool >/dev/null || (apt-get update -qq && apt-get install -y -qq xdotool) >/dev/null 2>&1; command -v xdotool" \
    >/dev/null || { echo "RESULT: FAIL (xdotool unavailable in container)"; exit 1; }
WIN=$(docker exec civrev-port bash -c "DISPLAY=:99 xdotool search --onlyvisible '.' 2>/dev/null | head -1")
[ -n "$WIN" ] || { echo "RESULT: FAIL (no X window found)"; exit 1; }
docker exec civrev-port bash -c "DISPLAY=:99 xdotool windowactivate $WIN 2>/dev/null; DISPLAY=:99 xdotool windowfocus $WIN" || true
for cmd in "${INJECT[@]}"; do
    echo "[test] inject: xdotool $cmd"
    docker exec civrev-port bash -c "DISPLAY=:99 xdotool $cmd"
    sleep 1
done

# 3) Did the game leave the title screen? Compare the injected-region screen
#    against the pre-injection one: pressing START opens the sign-in dialog
#    (large visual change in the center); no reaction leaves it ~identical
#    (only the animated water/clouds differ slightly).
sleep 6
copy_last_good_frame "$OUT" "$OUT/after_inject.png"
CHANGED=$(python3 - "$OUT" <<'EOF'
import sys
import numpy as np
from PIL import Image
out = sys.argv[1]
a = np.asarray(Image.open(out + "/before_inject.png").convert("RGB")).astype(int)
b = np.asarray(Image.open(out + "/after_inject.png").convert("RGB")).astype(int)
# Center band where the "Press START" banner / sign-in dialog lives.
ca = a[380:660, 300:980]; cb = b[380:660, 300:980]
diff = (np.abs(ca - cb).max(axis=2) > 40).sum()
print(diff)
EOF
)
echo "[test] center-band changed pixels: $CHANGED"

kill "$RUNNER_PID" 2>/dev/null || true
docker rm -f civrev-port >/dev/null 2>&1 || true
wait "$RUNNER_PID" 2>/dev/null || true

if [ "$EXPECT" = advance ]; then
    if [ "$CHANGED" -gt 20000 ]; then echo "RESULT: PASS (input registered, screen advanced)"; exit 0; fi
    echo "RESULT: FAIL (input did not advance the screen)"; exit 1
else
    if [ "$CHANGED" -le 20000 ]; then echo "RESULT: PASS (unbound input correctly ignored)"; exit 0; fi
    echo "RESULT: FAIL (screen advanced but input should have been unbound)"; exit 1
fi
