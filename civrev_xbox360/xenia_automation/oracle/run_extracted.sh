#!/usr/bin/env bash
# H1 — launch Xenia from the EXTRACTED game tree (not the ISO), so the oracle
# and the ReXGlue port consume byte-identical assets from the same directory
# (xenon_recomp/work/extracted/, i.e. the port's game_data_root).
#
# This is a thin, interactive convenience wrapper (foreground, VNC on :5900) for
# a human to eyeball the game or verify the input map. For automated,
# machine-checked runs use run_scenario.sh instead.
#
# Usage:
#   run_extracted.sh                 # lavapipe (software Vulkan), VNC :5900
#   VULKAN_DISPLAY=weston run_extracted.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/shlib/common.sh"

require_docker_image
require_extracted_tree
mkdir -p "$OUTPUT_DIR" "$XENIA_CONTENT_DIR"

mode="${VULKAN_DISPLAY:-$ORACLE_DISPLAY_MODE}"
log_info "launching Xenia from extracted tree: $EXTRACTED_TREE"
log_info "display mode: $mode   VNC: localhost:5900   (vncviewer localhost:5900)"
log_info "assets are the same bytes the ReXGlue port will use as game_data_root"

# Reuse the image's entrypoint game-discovery: it prefers /game_data/default.xex.
exec docker run --rm -it \
    --privileged \
    --tmpfs /dev/shm:rw,nosuid,nodev,exec,size=1g \
    --security-opt seccomp=unconfined \
    --device /dev/dri:/dev/dri \
    -p 5900:5900 \
    -e VULKAN_DISPLAY="$mode" \
    -v "$EXTRACTED_TREE:/game_data:ro" \
    -v "$OUTPUT_DIR:/output:rw" \
    -v "$XENIA_CONTENT_DIR:/root/.local/share/Xenia/content:rw" \
    "$DOCKER_IMAGE"
