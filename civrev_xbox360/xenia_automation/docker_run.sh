#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$SCRIPT_DIR/output"

mkdir -p "$OUTPUT_DIR"

# Game path: pass as first arg, or set GAME_PATH env var
GAME_PATH="${1:-${GAME_PATH:-}}"
if [ -z "$GAME_PATH" ]; then
    echo "Usage: $0 <path-to-xbla-or-iso>"
    echo "  e.g. $0 /path/to/CivRev/default.xex"
    echo "  e.g. $0 /path/to/XBLA_package_dir"
    exit 1
fi

# Resolve to absolute path
GAME_PATH="$(cd "$(dirname "$GAME_PATH")" && pwd)/$(basename "$GAME_PATH")"

if [ ! -e "$GAME_PATH" ]; then
    echo "Error: Game not found at: $GAME_PATH"
    exit 1
fi

echo "Building Docker image..."
docker build -t civrev-xbox360 "$SCRIPT_DIR"

echo "Launching Xenia with CivRev Xbox 360..."
echo "  Game: $GAME_PATH"
echo "  VNC: localhost:5900 (vncviewer localhost:5900)"
echo ""
echo "Display modes (set VULKAN_DISPLAY env var):"
echo "  lavapipe    - (default) Xvfb + lavapipe sw Vulkan, no DRI3 needed"
echo "  weston      - Weston VNC backend + Xwayland (DRI3, can use host GPU)"
echo "  xorg-dummy  - Xorg dummy driver + lavapipe"
echo ""

# Determine mount type: file or directory
if [ -d "$GAME_PATH" ]; then
    GAME_MOUNT=(-v "$GAME_PATH:/game_data:ro")
else
    GAME_MOUNT=(-v "$GAME_PATH:/game_data/$(basename "$GAME_PATH"):ro")
fi

docker run \
    --rm \
    --privileged \
    --tmpfs /dev/shm:rw,nosuid,nodev,exec,size=1g \
    --security-opt seccomp=unconfined \
    --device /dev/dri:/dev/dri \
    -p 5900:5900 \
    -e VULKAN_DISPLAY="${VULKAN_DISPLAY:-lavapipe}" \
    "${GAME_MOUNT[@]}" \
    -v "$OUTPUT_DIR:/output:rw" \
    civrev-xbox360
