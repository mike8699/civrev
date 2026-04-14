#!/usr/bin/env bash
# build_civ18_only_pregame.sh — build a diagnostic Pregame with
# civnames_enu.txt = 18 entries but rulernames_enu.txt = stock
# (17 entries). Isolates whether the crash requires BOTH files
# to be oversized or only one.
#
# Usage: build_civ18_only_pregame.sh
# Output: korea_mod/_build/Pregame_civ18only.FPK

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$(cd "$HERE/.." && pwd)"
PS3="$(cd "$MOD/.." && pwd)"
BUILD="$MOD/_build"
STAGE="$BUILD/Pregame_civ18only"

mkdir -p "$BUILD"
rm -rf "$STAGE"
cp -r "$PS3/extracted/Pregame" "$STAGE"

python3 - "$STAGE/civnames_enu.txt" "Koreans, MP" <<'PY'
import sys
path, new_line = sys.argv[1], sys.argv[2]
with open(path, "rb") as f:
    raw = f.read()
needle = b"Barbarians, MP\r\n"
idx = raw.find(needle)
if idx < 0:
    raise SystemExit("Barbarians line not found")
insertion = (new_line + "\r\n").encode("ascii")
out = raw[:idx] + insertion + raw[idx:]
with open(path, "wb") as f:
    f.write(out)
print(f"civnames_enu.txt: inserted '{new_line}'")
PY

# rulernames stays untouched.

python3 "$PS3/fpk.py" repack "$STAGE"
produced="$BUILD/Pregame_civ18only.FPK"
if [ ! -f "$produced" ]; then
    echo "ERROR: expected $produced" >&2
    exit 1
fi
sha256sum "$produced"
