#!/usr/bin/env bash
# Run the ReXGlue civrev port headlessly in the toolchain container, emitting
# the same artifact shapes as the Xenia oracle (run.log, frames/*.png,
# result summary) so oracle/trace + compare tooling can diff them.
#
# Mirrors xenia_automation/oracle semantics deliberately:
#   - game tree mounted READ-ONLY at /game_data (host data never modified)
#   - intro .bik movies blanked by bind-mounting an empty file INSIDE the
#     container (same "Error reading Bink header -> skip" path as the oracle)
#   - SDL_AUDIODRIVER=dummy (no audio device in container; matches oracle)
#   - Xvfb :99 1280x720 + lavapipe (software Vulkan; deterministic)
#   - takes the harness GPU lock (serializes vs Xenia runs; PRD hard rule)
#
# Usage: run_port.sh [--out DIR] [--timeout SECS] [--keep] [--game-dir DIR]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_X360="$(cd "$HERE/.." && pwd)"
source "$REPO_X360/xenia_automation/oracle/shlib/gpu_lock.sh"

OUT_DIR="$HERE/port_output/run_$(date +%H%M%S)"
TIMEOUT_SECS=180
KEEP=0
GAME_DIR="$REPO_X360/xenon_recomp/work/extracted"
BIN="$HERE/civrev/out/build/linux-amd64-release/Release/civrev"
CONTAINER=civrev-port
IMAGE=rexglue-toolchain

while [ "$#" -gt 0 ]; do
    case "$1" in
        --out) OUT_DIR="$2"; shift 2 ;;
        --timeout) TIMEOUT_SECS="$2"; shift 2 ;;
        --keep) KEEP=1; shift ;;
        --game-dir) GAME_DIR="$2"; shift 2 ;;
        --bin) BIN="$2"; shift 2 ;;
        *) echo "unknown arg: $1" >&2; exit 2 ;;
    esac
done

[ -f "$BIN" ] || { echo "port binary not found: $BIN (build first)" >&2; exit 1; }
[ -d "$GAME_DIR" ] || { echo "game dir not found: $GAME_DIR" >&2; exit 1; }
mkdir -p "$OUT_DIR/frames"
BIN_DIR="$(dirname "$BIN")"
BIN_NAME="$(basename "$BIN")"

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

# Supervisor inside the container: blank movies, start Xvfb, run the port
# under a watchdog, snap a frame every 2 s.
SUPERVISOR='
set -e
if [ "${CIVREV_KEEP_MOVIES:-0}" != 1 ]; then
    : > /tmp/empty.bik
    for m in IntroMovie AttractMovie DawnOfMan; do
        f="/game_data/Resource/Common/Art/Movies/$m.bik"
        if [ -f "$f" ] && mount --bind /tmp/empty.bik "$f"; then echo "movie-skip: $m"; fi
    done
fi
export DISPLAY=:99
export VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.json
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
export LIBGL_ALWAYS_SOFTWARE=1
export SDL_AUDIODRIVER=dummy
export LD_LIBRARY_PATH=/sdk/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
Xvfb :99 -screen 0 1280x720x24 &
sleep 2
echo "starting port binary"
cd /output
/port/'"$BIN_NAME"' --log_level=trace --log_file=/output/run.log --game_data_root=/game_data --gpu_plugin=xenos \
    > /output/game.stdout 2>&1 &
GAME_PID=$!
echo "$GAME_PID" > /output/game.pid
i=0
while kill -0 "$GAME_PID" 2>/dev/null && [ "$i" -lt '"$TIMEOUT_SECS"' ]; do
    n=$(printf "%04d" "$i")
    import -window root "/output/frames/f$n.png" 2>/dev/null || true
    sleep 2; i=$((i+2))
done
if kill -0 "$GAME_PID" 2>/dev/null; then
    echo "watchdog: timeout after '"$TIMEOUT_SECS"'s, stopping game" | tee /output/watchdog.txt
    kill "$GAME_PID" 2>/dev/null || true
    sleep 2; kill -9 "$GAME_PID" 2>/dev/null || true
    echo timeout > /output/exit_reason.txt
else
    # wait returns the exit code; a non-zero code must not kill the
    # supervisor (set -e), it is exactly what we want to record.
    if wait "$GAME_PID"; then rc=0; else rc=$?; fi
    echo "game exited rc=$rc" | tee /output/exit_reason.txt
fi
import -window root /output/final.png 2>/dev/null || true
'

run_container() {
    docker run --name "$CONTAINER" \
        --privileged \
        --tmpfs /dev/shm:rw,nosuid,nodev,exec,size=1g \
        --security-opt seccomp=unconfined \
        -e CIVREV_KEEP_MOVIES="${CIVREV_KEEP_MOVIES:-0}" \
        -v "$GAME_DIR:/game_data:ro" \
        -v "$BIN_DIR:/port:ro" \
        -v "$HERE/rexglue-sdk/out/install/linux-amd64:/sdk:ro" \
        -v "$OUT_DIR:/output:rw" \
        "$IMAGE" bash -c "$SUPERVISOR"
    local rc=$?
    [ "$KEEP" = 1 ] || docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    return $rc
}

echo "[port] running $BIN_NAME (timeout ${TIMEOUT_SECS}s) -> $OUT_DIR"
with_gpu_lock run_container
echo "[port] done; artifacts in $OUT_DIR"
