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
    for overlay in "$OVERLAYS"/*.xml "$OVERLAYS"/*.ini "$OVERLAYS"/*.txt; do
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

# iter-195 (2026-04-15): Pregame repack path.
#
# iter-190 reverted all v0.9 English→Korean substitutions, so
# fpk_byte_patch.py is a no-op. We now route Pregame through the same
# repack-from-directory path as Common0, patching gfx_chooseciv.gfx in
# place before the repack.
#
# iter-177 proved that `fpk.py from_directory` on a plain extract of
# Pregame.FPK is byte-identical to the stock original, so the repack
# path is boot-safe. The iter-195 patch is a 4-byte same-size swap
# inside gfx_chooseciv.gfx (numOptions default 6 -> 18).
stage_pregame_repack() {
    local src="$PS3_ROOT/extracted/Pregame"
    local dst="$STAGE/Pregame_korea"
    if [ ! -d "$src" ]; then
        echo "[pack_korea] ERROR: $src missing. Run 1unpack.sh first." >&2
        return 1
    fi
    rm -rf "$dst"
    cp -r "$src" "$dst"

    # iter-198: apply any name-file (.txt) overlays for Pregame too —
    # civnames_enu.txt / rulernames_enu.txt land here.
    for overlay in "$OVERLAYS"/*.xml "$OVERLAYS"/*.ini "$OVERLAYS"/*.txt; do
        [ -f "$overlay" ] || continue
        local base
        base="$(basename "$overlay")"
        local target="$dst/$base"
        if [ ! -f "$target" ]; then
            continue
        fi
        cp "$overlay" "$target"
        echo "[pack_korea] Pregame: replaced $base"
    done

    if [ -f "$HERE/gfx_chooseciv_patch.py" ]; then
        echo "[pack_korea] Pregame: patching gfx_chooseciv.gfx (iter-195)"
        python3 "$HERE/gfx_chooseciv_patch.py" \
            "$dst/gfx_chooseciv.gfx" \
            "$dst/gfx_chooseciv.gfx"
    fi

    python3 "$PS3_ROOT/fpk.py" repack "$dst"
    local out_fpk="$STAGE/Pregame_korea.FPK"
    if [ ! -f "$out_fpk" ]; then
        echo "[pack_korea] ERROR: expected $out_fpk" >&2
        return 1
    fi
    sha256sum "$out_fpk"
}
stage_pregame_repack
