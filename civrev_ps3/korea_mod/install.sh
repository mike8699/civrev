#!/usr/bin/env bash
# korea_mod/install.sh — stage the Korea mod into civrev_ps3/modified/
# and the RPCS3 HDD game directory.
#
# Writes to two locations:
#   1. civrev_ps3/modified/PS3_GAME/USRDIR/ — the docker-harness-
#      mounted disc copy (tracked in git).
#   2. ~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN
#      — the path RPCS3 actually boots from (per the iter-133
#      finding). Dual-path EBOOT install is mandatory.
#
# Never touches the original stock FPKs under civrev_ps3/extracted/
# or civrev_ps3/Common0.FPK — those are canonical sources.
#
# v1.0 shipping state (current as of iter-223):
#
#  EBOOT_korea.ELF: 6 static byte patches via eboot_patches.py
#    - iter-4 ADJ_FLAT pointer-table extension (16->17 entries with
#      a Korean adjective slot) — 4 patches
#    - iter-14 parser-count bumps (li r5, 0x11 -> 0x12 at 0xa2ee38
#      and 0xa2ee7c, for RulerNames_ and CivNames_ init counts) —
#      2 patches
#
#  Pregame_korea.FPK: 2 .txt overlays via fpk.py repack
#    - civnames_enu.txt — Koreans at row 17 (iter-198)
#    - rulernames_enu.txt — Sejong at row 17 (iter-198)
#
#  Common0.FPK: NOT modified (iter-223). iter-222 proved Common0.FPK
#  is never opened at runtime by the BLUS-30130 PS3 build, so the
#  iter-176/214 leaderheads.xml + 2 pediainfo XML overlays were
#  structurally inert. They're archived under
#  korea_mod/xml_overlays/dead_iter222/.
#
# All patches/overlays in the iter-159..175 series (slot-16 cell
# repurpose: title/description/era bonuses/Sejong TOC redirect)
# were REVERTED in iter-176 and are not part of v1.0 shipping
# under the iter-189 strict reading. The carousel cell rendering
# remains structurally blocked per iter-212 (PRD §9.X). See
# PRD §10 Progress Log for the full iteration history.

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

# iter-223: Common0_korea.FPK is no longer produced or installed.
# iter-222 proved Common0.FPK is never opened at runtime by the
# BLUS-30130 PS3 build. The 3 Common0 overlays (leaderheads.xml +
# 2 pediainfo XMLs) were structurally inert — they shipped in the
# FPK but couldn't reach the runtime. They're archived under
# korea_mod/xml_overlays/dead_iter222/ for documentation. The disc
# Common0.FPK is left as the stock file (we restore from .orig if
# a previous iteration's modded version is present).
restore_common0_to_stock() {
    local cur="$DISC_RESOURCE_COMMON/Common0.FPK"
    local orig="$DISC_RESOURCE_COMMON/Common0.FPK.orig"
    if [ -f "$orig" ] && [ -f "$cur" ] && ! cmp -s "$cur" "$orig"; then
        cp "$orig" "$cur"
        echo "[install] restored stock Common0.FPK from .orig (iter-223 cleanup)"
    fi
}
restore_common0_to_stock
install_fpk Pregame

# EBOOT patch install — delegate to install_eboot.sh for the
# dual-path install (modified/ + dev_hdd0/). install_eboot.sh also
# handles backing up the original encrypted SCE EBOOT the first
# time it runs.
if [ -f "$BUILD/EBOOT_korea.ELF" ]; then
    "$HERE/scripts/install_eboot.sh"
else
    echo "[install] WARNING: no EBOOT_korea.ELF in _build/ — run ./build.sh first"
fi

echo "[install] done. Boot via civrev_ps3/rpcs3_automation/docker_run.sh"
