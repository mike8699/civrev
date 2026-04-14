#!/usr/bin/env bash
# korea_mod/install.sh — stage the Korea mod into civrev_ps3/modified/
# so the rpcs3_automation docker harness picks it up when it mounts
# /game_disc_src.
#
# This script is deliberately conservative:
#   1. It never touches the original stock FPKs under
#      civrev_ps3/extracted/ — those are the canonical source trees.
#   2. It never modifies civrev_ps3/Common0.FPK etc. at the repo root.
#   3. It only writes to civrev_ps3/modified/PS3_GAME/USRDIR/, which
#      is the docker-harness-mounted disc copy.
#
# v0.9 status: installs the modded Common0.FPK, Pregame.FPK (via
# in-place byte patches in fpk_byte_patch.py — civ/ruler/city names),
# and the patched EBOOT_korea.ELF (six harmless-on-v0.9 byte patches
# applied by eboot_patches.py). All three are produced by build.sh.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PS3_ROOT="$(cd "$HERE/.." && pwd)"
BUILD="$HERE/_build"
DISC_USRDIR="$PS3_ROOT/modified/PS3_GAME/USRDIR"
DISC_RESOURCE_COMMON="$DISC_USRDIR/Resource/Common"

if [ ! -d "$DISC_RESOURCE_COMMON" ]; then
    echo "[install] ERROR: $DISC_RESOURCE_COMMON missing — run the disc-extract step first" >&2
    exit 2
fi

# Build if needed
if [ ! -f "$BUILD/Common0_korea.FPK" ] || [ "$HERE/xml_overlays" -nt "$BUILD/Common0_korea.FPK" ]; then
    echo "[install] (re)building modded FPKs"
    "$HERE/build.sh"
fi

backup_once() {
    local src="$1"
    local bak="${src}.orig"
    if [ ! -f "$bak" ] && [ -f "$src" ]; then
        cp -a "$src" "$bak"
        echo "[install] backed up stock $(basename "$src") to $(basename "$bak")"
    fi
}

install_fpk() {
    local name="$1"
    local src="$BUILD/${name}_korea.FPK"
    local dst="$DISC_RESOURCE_COMMON/${name}.FPK"
    if [ ! -f "$src" ]; then
        echo "[install] skipping ${name}.FPK — $src not built"
        return 0
    fi
    backup_once "$dst"
    cp "$src" "$dst"
    echo "[install] installed $src -> $dst"
}

install_fpk Common0
install_fpk Pregame

# EBOOT patch install — only when the build step produced one.
if [ -f "$BUILD/EBOOT_korea.ELF" ]; then
    EBOOT_DST="$DISC_USRDIR/EBOOT.BIN"
    backup_once "$EBOOT_DST"
    cp "$BUILD/EBOOT_korea.ELF" "$EBOOT_DST"
    echo "[install] installed patched EBOOT"
else
    echo "[install] WARNING: no EBOOT_korea.ELF in _build/ — run ./build.sh first"
fi

echo "[install] done. Boot via civrev_ps3/rpcs3_automation/docker_run.sh"
