#!/usr/bin/env bash
# Common paths, config, and logging helpers for the CivRev Xenia oracle harness.
# Source this from any oracle script: `source "$(dirname "$0")/shlib/common.sh"`
#
# All oracle scripts are designed to run FROM THE HOST (driving Docker), not from
# inside the container. Paths below are host paths unless noted.

# --- Resolve locations relative to this file (robust to symlinks / cwd) --------
_COMMON_SH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../oracle/shlib
ORACLE_DIR="$(dirname "$_COMMON_SH")"                 # .../xenia_automation/oracle
HARNESS_DIR="$(dirname "$ORACLE_DIR")"                # .../xenia_automation
XBOX360_DIR="$(dirname "$HARNESS_DIR")"               # .../civrev_xbox360
REPO_ROOT="$(dirname "$XBOX360_DIR")"                 # .../civrev  (git root)

# --- Key data locations --------------------------------------------------------
# The extracted game tree (default.xex + Resource/ + shaders/). This is both the
# oracle's mount and the port's game_data_root, so both consume identical bytes.
EXTRACTED_TREE="${CIVREV_EXTRACTED_TREE:-$XBOX360_DIR/xenon_recomp/work/extracted}"
# NB: the ISO filename contains an apostrophe. A lone ' inside "${VAR:-default}"
# re-opens quote parsing and breaks the script, so set the default separately.
GAME_ISO="${CIVREV_ISO:-}"
if [ -z "$GAME_ISO" ]; then
    GAME_ISO="$XBOX360_DIR/Sid Meier's Civilization Revolution (USA) (En,Fr,De,Es,It).iso"
fi

# Output / references / fixtures (host-writable, produced by the harness)
OUTPUT_DIR="${CIVREV_OUTPUT_DIR:-$HARNESS_DIR/output}"
REFERENCES_DIR="${CIVREV_REFERENCES_DIR:-$HARNESS_DIR/references}"
FIXTURES_DIR="${CIVREV_FIXTURES_DIR:-$HARNESS_DIR/fixtures}"
SCENARIOS_DIR="$ORACLE_DIR/scenarios"

# Persistent Xenia content root (save games survive runs) — see H9.
XENIA_CONTENT_DIR="${CIVREV_XENIA_CONTENT_DIR:-$FIXTURES_DIR/xenia_content}"

# --- Pinned configuration (H2) -------------------------------------------------
# The Docker image itself pins the xenia-edge build; these are recorded here too
# so host scripts and docs agree on the known-good configuration.
XENIA_EDGE_TAG="d158580"
XENIA_EDGE_SHA256="6b1b958a1d336e79d8e2a9403e0fc2c86285e89ee3b9b3938f5e30a01faccd2d"
DOCKER_IMAGE="${CIVREV_DOCKER_IMAGE:-civrev-xbox360}"
TITLE_ID="545407E5"

# Default display mode for reference capture. Overridable via VULKAN_DISPLAY.
# lavapipe = software Vulkan (deterministic, no host GPU); weston = host GPU.
ORACLE_DISPLAY_MODE="${VULKAN_DISPLAY:-lavapipe}"

# --- Logging -------------------------------------------------------------------
# Colorized when stderr is a TTY; plain otherwise (so logs/pipes stay clean).
if [ -t 2 ]; then
    _C_RED=$'\033[31m'; _C_YEL=$'\033[33m'; _C_GRN=$'\033[32m'; _C_DIM=$'\033[2m'; _C_RST=$'\033[0m'
else
    _C_RED=''; _C_YEL=''; _C_GRN=''; _C_DIM=''; _C_RST=''
fi
log_info() { printf '%s[oracle]%s %s\n' "$_C_DIM" "$_C_RST" "$*" >&2; }
log_ok()   { printf '%s[oracle] OK%s %s\n' "$_C_GRN" "$_C_RST" "$*" >&2; }
log_warn() { printf '%s[oracle] WARN%s %s\n' "$_C_YEL" "$_C_RST" "$*" >&2; }
log_err()  { printf '%s[oracle] ERROR%s %s\n' "$_C_RED" "$_C_RST" "$*" >&2; }
die()      { log_err "$*"; exit 1; }

# --- Small shared helpers ------------------------------------------------------
# Verify the extracted game tree looks sane (fail fast with a clear message).
require_extracted_tree() {
    [ -f "$EXTRACTED_TREE/default.xex" ] || die \
        "Extracted game tree missing default.xex at: $EXTRACTED_TREE
   Expected the XenonRecomp extraction (xenon_recomp/work/extracted/).
   Override with CIVREV_EXTRACTED_TREE=<path>."
}

# Verify the Docker image exists (built via docker_run.sh / build).
require_docker_image() {
    docker image inspect "$DOCKER_IMAGE" >/dev/null 2>&1 || die \
        "Docker image '$DOCKER_IMAGE' not found. Build it first:
   (cd '$HARNESS_DIR' && docker build -t $DOCKER_IMAGE .)"
}
