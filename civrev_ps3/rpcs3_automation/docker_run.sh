#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
RPCS3_CONFIG="$HOME/.config/rpcs3"
GAME_DISC_DIR="$PROJECT_DIR/modified"
GAME_DLC_DIR="$RPCS3_CONFIG/dev_hdd0/game/BLUS30130"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Parse --headless flag (pass remaining args to container)
HEADLESS=0
ARGS=()
for arg in "$@"; do
    if [ "$arg" = "--headless" ]; then
        HEADLESS=1
    else
        ARGS+=("$arg")
    fi
done

mkdir -p "$OUTPUT_DIR"

echo "Building Docker image..."
docker build -t civrev-test "$SCRIPT_DIR"

DOCKER_ARGS=(
    --rm
    # GPU passthrough for hardware rendering
    --device /dev/dri:/dev/dri
    # Disc game (read-only source, writable copy made by entrypoint for patching)
    -v "$GAME_DISC_DIR:/game_disc_src:ro"
    # DLC/game data (read-only, copied to writable location by entrypoint)
    -v "$GAME_DLC_DIR:/game_dlc:ro"
    # DLC exdata (license files + additional DLC packs like Pak1, Pak6)
    -v "$RPCS3_CONFIG/dev_hdd0/home/00000001/exdata:/game_exdata:ro"
    # PS3 firmware (read-only)
    -v "$RPCS3_CONFIG/dev_flash:/root/.config/rpcs3/dev_flash:ro"
    -v "$RPCS3_CONFIG/dev_flash2:/root/.config/rpcs3/dev_flash2:ro"
    -v "$RPCS3_CONFIG/dev_flash3:/root/.config/rpcs3/dev_flash3:ro"
    # Project (read-only)
    -v "$PROJECT_DIR:/civrev:ro"
    # RPCS3 PPU/SPU JIT cache is DELIBERATELY NOT BIND-MOUNTED. Prior
    # revisions shared $HOME/.cache/rpcs3/{cache,spu_progs,ppu_progs}
    # with the container to speed up repeated boots, but that created
    # two problems:
    #   1. The container runs rpcs3 as root, so cache files written
    #      through the bind mount were owned by root on the host.
    #      Host-side rpcs3 (running as the user) then couldn't
    #      overwrite them and ended up reading a mix of stale Docker-
    #      written and partially-updated host files. The result was
    #      a nasty SPU segfault at boot ("writing location 0x818 at
    #      0x75ee00000000") whenever a user tried to play locally
    #      after a harness run — iter-1187 repro on 2026-04-15.
    #   2. If the Docker image's RPCS3 version drifted out of sync
    #      with the host's RPCS3, the two would write incompatible
    #      JIT metadata into the same cache files, yielding the same
    #      segfault pattern even for root-owned reads.
    # Dropping the bind mount means each container run gets an
    # ephemeral cache and recompiles PPU/SPU code on first use
    # (~20-30s added to cold boot). That's the price of cross-
    # version / cross-user isolation, and it's cheap compared to
    # losing an afternoon debugging a stale-cache segfault.
    # If you want to restore the cache share for performance, ALSO
    # add `--user $(id -u):$(id -g)` to DOCKER_ARGS below so the
    # container writes cache files as the host user, not root.
    # RPCS3 screenshots dir + writable output (same location)
    -v "$OUTPUT_DIR:/root/.config/rpcs3/screenshots:rw"
    -v "$OUTPUT_DIR:/output:rw"
)

if [ "$HEADLESS" = "0" ]; then
    echo "GUI mode: watch via VNC at localhost:5900"
    echo "  (e.g., vncviewer localhost:5900)"
    DOCKER_ARGS+=(
        -e DISPLAY="$DISPLAY"
        -p 5900:5900
    )
else
    echo "Headless mode: using Xvfb"
fi

echo "Running test..."
docker run "${DOCKER_ARGS[@]}" civrev-test "${ARGS[@]}"

echo ""
echo "Output screenshot: $OUTPUT_DIR/screenshot.png"
