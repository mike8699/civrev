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
    # Disc game (read-only, for booting)
    -v "$GAME_DISC_DIR:/game_disc:ro"
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
    # Share RPCS3 cache (PPU/SPU/shader) with host for fast boot
    -v "$HOME/.cache/rpcs3:/root/.cache/rpcs3:rw"
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
