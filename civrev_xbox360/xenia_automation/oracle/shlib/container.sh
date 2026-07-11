#!/usr/bin/env bash
# Detached-container lifecycle for oracle automation (used by screenshot.sh,
# input.sh, run_scenario.sh). Runs Xenia headless inside the pinned image with
# Xvfb+VNC, keeping the container alive even if Xenia crashes so we can still
# capture the last frame and read the log.
#
# Requires common.sh to be sourced first (for DOCKER_IMAGE, EXTRACTED_TREE, …).

ORACLE_CONTAINER="${CIVREV_ORACLE_CONTAINER:-civrev-oracle}"
ORACLE_DISPLAY=":99"                       # matches entrypoint.sh lavapipe/xorg modes

# start_oracle_container <host_output_dir> [game_dir]
# Launches the container detached: entrypoint sets up the display, then our
# supervisor runs Xenia in the background (logging to /output/run.log) and holds
# the container open. Software (lavapipe) rendering is the default and is GPU-safe.
start_oracle_container() {
    local out_dir="$1"; local game_dir="${2:-$EXTRACTED_TREE}"
    require_docker_image
    [ -f "$game_dir/default.xex" ] || die "no default.xex under $game_dir"
    mkdir -p "$out_dir"
    stop_oracle_container 2>/dev/null || true

    # Persistent content dir (H9) so saves survive; created if missing.
    mkdir -p "$XENIA_CONTENT_DIR"

    local mode="${VULKAN_DISPLAY:-$ORACLE_DISPLAY_MODE}"
    log_info "starting oracle container '$ORACLE_CONTAINER' (display=$mode, game=$game_dir)"

    # The supervisor: bring up the virtual gamepad FIRST (so SDL enumerates it at
    # init — Xenia hid="sdl" reads controllers, not the keyboard), then launch
    # Xenia, record its PID, and keep the container alive regardless of its fate.
    local supervisor='
        set -e
        # Virtual Xbox 360 pad for controller input (see oracle/virtpad.py).
        if [ -w /dev/uinput ]; then
            if ! python3 -c "import evdev" 2>/dev/null; then
                apt-get update -qq >/dev/null 2>&1 && apt-get install -y -qq python3-evdev >/dev/null 2>&1 || true
            fi
            if python3 -c "import evdev" 2>/dev/null; then
                python3 /oracle/virtpad.py /tmp/virtpad.cmd >/output/virtpad.log 2>&1 &
                for i in $(seq 1 20); do grep -q "created Xbox" /output/virtpad.log 2>/dev/null && break; sleep 0.3; done
                echo "virtpad: $(head -1 /output/virtpad.log 2>/dev/null)"
            else
                echo "WARN: evdev unavailable; controller input disabled"
            fi
        else
            echo "WARN: /dev/uinput not writable; controller input disabled"
        fi
        GAME=/game_data/default.xex
        xenia --apu=sdl --license_mask=-1 --protect_zero=false \
              --log_file=/output/run.log "$GAME" >/output/xenia.stdout 2>&1 &
        echo $! > /tmp/xenia.pid
        echo "xenia pid $(cat /tmp/xenia.pid)"
        tail -f /dev/null
    '

    # Publish the in-container VNC server (entrypoint runs x11vnc on :5900) so a
    # human can watch any scenario run live: vncviewer localhost:5900. Best-effort
    # — if 5900 is busy the run still proceeds headless.
    local vnc_pub=(-p 5900:5900)
    if ! docker run -d --name "$ORACLE_CONTAINER" \
        --privileged \
        --tmpfs /dev/shm:rw,nosuid,nodev,exec,size=1g \
        --security-opt seccomp=unconfined \
        --device /dev/dri:/dev/dri \
        "${vnc_pub[@]}" \
        -e VULKAN_DISPLAY="$mode" \
        -e SDL_AUDIODRIVER=dummy \
        -v "$ORACLE_DIR:/oracle:ro" \
        -v "$game_dir:/game_data:ro" \
        -v "$out_dir:/output:rw" \
        -v "$XENIA_CONTENT_DIR:/root/.local/share/Xenia/content:rw" \
        "$DOCKER_IMAGE" \
        bash -c "$supervisor" >/dev/null 2>&1; then
        log_warn "VNC port 5900 unavailable; retrying headless (no live view)"
        docker run -d --name "$ORACLE_CONTAINER" \
            --privileged \
            --tmpfs /dev/shm:rw,nosuid,nodev,exec,size=1g \
            --security-opt seccomp=unconfined \
            --device /dev/dri:/dev/dri \
            -e VULKAN_DISPLAY="$mode" \
            -e SDL_AUDIODRIVER=dummy \
            -v "$ORACLE_DIR:/oracle:ro" \
            -v "$game_dir:/game_data:ro" \
            -v "$out_dir:/output:rw" \
            -v "$XENIA_CONTENT_DIR:/root/.local/share/Xenia/content:rw" \
            "$DOCKER_IMAGE" \
            bash -c "$supervisor" >/dev/null \
            || die "docker run failed for $ORACLE_CONTAINER"
    fi
}

# stop_oracle_container : remove the container (best-effort).
stop_oracle_container() {
    docker rm -f "$ORACLE_CONTAINER" >/dev/null 2>&1 || true
}

# oracle_exec [-t] <cmd...> : run a command inside the container with DISPLAY set.
oracle_exec() {
    docker exec -e DISPLAY="$ORACLE_DISPLAY" "$ORACLE_CONTAINER" "$@"
}

# xenia_alive : return 0 while the Xenia process inside the container is running.
xenia_alive() {
    oracle_exec sh -c 'kill -0 "$(cat /tmp/xenia.pid 2>/dev/null)" 2>/dev/null'
}

# container_running : return 0 if the container itself is up.
container_running() {
    [ "$(docker inspect -f '{{.State.Running}}' "$ORACLE_CONTAINER" 2>/dev/null)" = "true" ]
}

# wait_for_log <regex> <timeout_s> : wait until the run log matches, Xenia dies,
# or timeout. Echoes one of: matched | xenia_exit | timeout.
wait_for_log() {
    local pattern="$1"; local timeout="${2:-60}"; local waited=0
    while [ "$waited" -lt "$timeout" ]; do
        if oracle_exec sh -c "grep -qE '$pattern' /output/run.log 2>/dev/null"; then
            echo matched; return 0
        fi
        if ! xenia_alive; then echo xenia_exit; return 0; fi
        sleep 1; waited=$((waited + 1))
    done
    echo timeout; return 0
}
