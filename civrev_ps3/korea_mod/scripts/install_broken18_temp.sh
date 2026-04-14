#!/usr/bin/env bash
# install_broken18_temp.sh — temporarily install the diagnostic
# broken-18 Pregame.FPK alongside the iter-14 patched EBOOT so
# RPCS3 boots into the crash state. Always backs up the current
# v0.9 Pregame to Pregame_v09.FPK.bak and restores it on cleanup.
#
# Usage:
#   install_broken18_temp.sh install     # stage broken Pregame
#   install_broken18_temp.sh restore     # put v0.9 back
#
# Do NOT leave the broken Pregame installed. Always restore.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$(cd "$HERE/.." && pwd)"
PS3="$(cd "$MOD/.." && pwd)"
BUILD="$MOD/_build"
DISC="$PS3/modified/PS3_GAME/USRDIR/Resource/Common"

BROKEN="$BUILD/Pregame_broken18.FPK"
V09="$BUILD/Pregame_korea.FPK"
INSTALLED="$DISC/Pregame.FPK"
BAK_BROKEN="$DISC/Pregame.FPK.broken18_bak"

case "${1:-}" in
    install)
        [ -f "$BROKEN" ] || { echo "$BROKEN not built" >&2; exit 1; }
        if [ ! -f "$BAK_BROKEN" ]; then
            cp "$INSTALLED" "$BAK_BROKEN"
            echo "backed up current Pregame.FPK -> $(basename "$BAK_BROKEN")"
        fi
        cp "$BROKEN" "$INSTALLED"
        sha256sum "$INSTALLED"
        echo "INSTALLED broken_18 Pregame (remember to restore)"
        ;;
    restore)
        if [ -f "$BAK_BROKEN" ]; then
            cp "$BAK_BROKEN" "$INSTALLED"
            rm -f "$BAK_BROKEN"
            echo "RESTORED Pregame.FPK from broken18_bak"
        else
            [ -f "$V09" ] || { echo "no v0.9 Pregame to restore" >&2; exit 1; }
            cp "$V09" "$INSTALLED"
            echo "RESTORED v0.9 Pregame_korea.FPK"
        fi
        sha256sum "$INSTALLED"
        ;;
    *)
        echo "usage: $0 {install|restore}" >&2
        exit 2
        ;;
esac
