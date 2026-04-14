#!/usr/bin/env bash
# install_eboot.sh — install the patched EBOOT_korea.ELF to BOTH
# locations RPCS3 needs:
#   1. civrev_ps3/modified/PS3_GAME/USRDIR/EBOOT.BIN  (disc image,
#      tracked in git via the modified/ tree)
#   2. ~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN
#      (HDD update path — this is the one RPCS3 actually boots
#      from; see iter-133 finding for the discovery)
#
# Without writing to BOTH paths, every patch verification is
# silently meaningless because RPCS3 reads the unpatched HDD copy.
# Iter-7..iter-132 all suffered this bug.
#
# Always backs up the original HDD EBOOT (the encrypted SCE SELF)
# to EBOOT.BIN.iter133_sce_bak the first time, so it can be
# restored later if needed.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$(cd "$HERE/.." && pwd)"
PS3="$(cd "$MOD/.." && pwd)"
BUILD="$MOD/_build"
PATCHED="$BUILD/EBOOT_korea.ELF"

DISC_DEST="$PS3/modified/PS3_GAME/USRDIR/EBOOT.BIN"
HDD_DEST="$HOME/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN"
HDD_BAK="$HDD_DEST.iter133_sce_bak"

if [ ! -f "$PATCHED" ]; then
    echo "ERROR: $PATCHED not built. Run ./build.sh first." >&2
    exit 1
fi

# Back up the encrypted SCE if not already done.
if [ ! -f "$HDD_BAK" ] && [ -f "$HDD_DEST" ]; then
    MAGIC=$(head -c4 "$HDD_DEST" | od -A n -t x1 | tr -d ' ')
    if [ "$MAGIC" = "53434500" ]; then
        cp "$HDD_DEST" "$HDD_BAK"
        echo "backed up encrypted SCE EBOOT -> $(basename "$HDD_BAK")"
    fi
fi

cp "$PATCHED" "$DISC_DEST"
cp "$PATCHED" "$HDD_DEST"

echo "installed patched EBOOT to:"
sha256sum "$DISC_DEST" "$HDD_DEST"
