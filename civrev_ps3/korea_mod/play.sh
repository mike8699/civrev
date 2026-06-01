#!/usr/bin/env bash
# korea_mod/play.sh — launch the Korea mod in NATIVE RPCS3 on the host.
#
# Boots the modded disc copy (modified/PS3_GAME), which contains BOTH the
# patched EBOOT (gameplay: Korea = real civ 16) and the patched Pregame.FPK
# (carousel: Korea at slot 16 + Sejong portrait + the slot-16->civ-16 wiring).
# RPCS3 uses the dual-installed dev_hdd0 EBOOT and reads Pregame.FPK from the
# disc, so this single boot gives the full mod.
#
# Usage:
#   ./play.sh            # (re)build+install, then launch
#   ./play.sh --no-build # just launch what's already installed
#   RPCS3_APPIMAGE=/path/to/rpcs3.AppImage ./play.sh   # override the AppImage
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PS3_ROOT="$(cd "$HERE/.." && pwd)"
DISC_EBOOT="$PS3_ROOT/modified/PS3_GAME/USRDIR/EBOOT.BIN"

APP="${RPCS3_APPIMAGE:-}"
if [ -z "$APP" ]; then
    APP="$(ls -t "$HOME"/Desktop/rpcs3-*linux64.AppImage 2>/dev/null | head -1 || true)"
fi
if [ -z "$APP" ] || [ ! -f "$APP" ]; then
    echo "ERROR: RPCS3 AppImage not found. Set RPCS3_APPIMAGE=/path/to/rpcs3.AppImage" >&2
    exit 2
fi
chmod +x "$APP" 2>/dev/null || true

if [ "${1:-}" != "--no-build" ]; then
    echo "[play] (re)building + installing the mod..."
    "$HERE/install.sh"
fi

if [ ! -f "$DISC_EBOOT" ]; then
    echo "ERROR: modded disc EBOOT not found at $DISC_EBOOT — run install.sh." >&2
    exit 2
fi

echo "[play] launching native RPCS3 with the modded disc..."
echo "       (in-game: Single Player -> New Game -> pick difficulty ->"
echo "        scroll RIGHT to 'Sejong / Koreans' at slot 16 -> select)"
# --appimage-extract-and-run avoids needing FUSE on the host.
exec "$APP" --appimage-extract-and-run --no-gui "$DISC_EBOOT"
