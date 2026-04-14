#!/usr/bin/env bash
# korea_mod/pack_korea.sh — build modded Common0.FPK / Pregame.FPK.
#
# For every XML in xml_overlays/, copy the source Common0 or Pregame
# directory into a staging tree, drop the overlaid XML in place of the
# original, then repack via civrev_ps3/fpk.py.
#
# This script is strictly REPLACE-only — it never adds a new entry to an
# FPK, because prior map-mod work confirmed that adding entries crashes
# the game (see CLAUDE memory for context). If an overlay XML has no
# matching file in the source tree we refuse to ship.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PS3_ROOT="$(cd "$HERE/.." && pwd)"
STAGE="${1:-$HERE/_build}"
OVERLAYS="$HERE/xml_overlays"

mkdir -p "$STAGE"

stage_fpk() {
    local name="$1"
    local src="$PS3_ROOT/extracted/$name"
    local dst="$STAGE/${name}_korea"

    if [ ! -d "$src" ]; then
        echo "[pack_korea] ERROR: source extract dir $src missing. Run 1unpack.sh first." >&2
        return 1
    fi

    rm -rf "$dst"
    cp -r "$src" "$dst"

    local applied=0
    for overlay in "$OVERLAYS"/*.xml "$OVERLAYS"/*.ini; do
        [ -f "$overlay" ] || continue
        local base
        base="$(basename "$overlay")"
        local target="$dst/$base"
        if [ ! -f "$target" ]; then
            continue
        fi
        cp "$overlay" "$target"
        applied=$((applied + 1))
        echo "[pack_korea] $name: replaced $base"
    done

    if [ "$applied" -eq 0 ]; then
        echo "[pack_korea] $name: no overlays applied, skipping repack"
        rm -rf "$dst"
        return 0
    fi

    python3 "$PS3_ROOT/fpk.py" repack "$dst"
    local out_fpk="$STAGE/${name}_korea.FPK"
    if [ ! -f "$out_fpk" ]; then
        echo "[pack_korea] ERROR: expected repacked FPK at $out_fpk" >&2
        return 1
    fi
    sha256sum "$out_fpk"
}

stage_fpk Common0
# iter-14 revert: bumping InitGenderedNames count 17→18 at the call
# site is NOT sufficient to unblock civnames+rulernames extension —
# the boot still crashes (see verification/M2_iter14). There must be
# a downstream 17-wide buffer (pre-allocated, not sized by the r5
# count arg) that still OOBs on the 18th entry. Reverting to the
# v0.9 byte-patch path for Pregame. The eboot_patches.py li-17→18
# patches at 0xa2ee38 / 0xa2ee7c are LEFT IN PLACE (harmless when
# civnames/rulernames only have 17 entries each — they just cause
# the loop to run one extra iteration with no data to write).
if [ -f "$HERE/fpk_byte_patch.py" ]; then
    echo "[pack_korea] Pregame: running in-place byte patcher (v0.9)"
    python3 "$HERE/fpk_byte_patch.py" \
        "$PS3_ROOT/Pregame.FPK" \
        "$STAGE/Pregame_korea.FPK"
    sha256sum "$STAGE/Pregame_korea.FPK"
fi
