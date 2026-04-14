#!/usr/bin/env bash
# build_broken_18_pregame.sh — build a Pregame_broken18.FPK with an
# 18th civ entry appended to civnames_enu.txt and rulernames_enu.txt.
#
# This is the deliberately-broken artifact for iter-109+ runtime
# debugging via GDB Z-packet watchpoints. The file triggers the
# deterministic memory corruption at 0xc26a98 / 0x2a12c during boot.
# The EBOOT patches from iter-14 (li r5, 0x11 → 0x12) are REQUIRED
# for the parser to actually read the 18th line — without them, it
# stops at 17.
#
# Usage: build_broken_18_pregame.sh
# Output: korea_mod/_build/Pregame_broken18.FPK
#
# Do NOT install this artifact. It is diagnostic-only.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
MOD="$(cd "$HERE/.." && pwd)"
PS3="$(cd "$MOD/.." && pwd)"
BUILD="$MOD/_build"
STAGE="$BUILD/Pregame_broken18"

mkdir -p "$BUILD"
rm -rf "$STAGE"
cp -r "$PS3/extracted/Pregame" "$STAGE"

# Append "Koreans, MP" as the 18th civ entry, right AFTER the 16
# civs and BEFORE "Barbarians, MP" (preserves Barbarians at its
# original index 16). iter-106 confirmed the parser reads 17 rows
# in the stock file: 16 civs + Barbarians. Inserting Korea before
# Barbarians makes Korea index 16 and pushes Barbarians to index
# 17. With the iter-14 li r5 bump to 0x12, the parser will then
# read 18 rows.
python3 - "$STAGE/civnames_enu.txt" "Koreans, MP" <<'PY'
import sys
path, new_line = sys.argv[1], sys.argv[2]
with open(path, "rb") as f:
    raw = f.read()
# The file uses CRLF. Find the Barbarians line and insert before it.
needle = b"Barbarians, MP\r\n"
idx = raw.find(needle)
if idx < 0:
    raise SystemExit("Barbarians line not found in civnames_enu.txt")
insertion = (new_line + "\r\n").encode("ascii")
out = raw[:idx] + insertion + raw[idx:]
with open(path, "wb") as f:
    f.write(out)
print(f"civnames_enu.txt: inserted '{new_line}' (added {len(insertion)} bytes)")
PY

python3 - "$STAGE/rulernames_enu.txt" "Sejong   " <<'PY'
import sys
path, new_line = sys.argv[1], sys.argv[2]
with open(path, "rb") as f:
    raw = f.read()
needle = b"Grey Wolf"
idx = raw.find(needle)
if idx < 0:
    # Stock may name the barbarian ruler differently — fall back to
    # inserting before the last entry.
    raw_lines = raw.split(b"\r\n")
    non_empty = [i for i, ln in enumerate(raw_lines) if ln and not ln.startswith(b";")]
    idx_last = non_empty[-1] if non_empty else len(raw_lines) - 2
    prefix = b"\r\n".join(raw_lines[:idx_last]) + b"\r\n"
    suffix = b"\r\n".join(raw_lines[idx_last:])
    out = prefix + (new_line + "\r\n").encode("ascii") + suffix
else:
    # Insert before the line containing "Grey Wolf".
    line_start = raw.rfind(b"\r\n", 0, idx) + 2
    out = raw[:line_start] + (new_line + "\r\n").encode("ascii") + raw[line_start:]
with open(path, "wb") as f:
    f.write(out)
print(f"rulernames_enu.txt: inserted '{new_line}'")
PY

# Repack via fpk.py. iter-24 confirmed this is deterministic for
# Pregame — crashes are content-driven, not packer-driven.
python3 "$PS3/fpk.py" repack "$STAGE"

out_fpk="$BUILD/Pregame_broken18.FPK"
# fpk.py drops the FPK alongside the stage directory with name
# "<stem>.FPK".
produced="$BUILD/Pregame_broken18.FPK"
if [ ! -f "$produced" ]; then
    echo "ERROR: expected $produced after fpk.py repack" >&2
    ls "$BUILD"
    exit 1
fi
sha256sum "$produced"
echo "broken-18 Pregame at $produced"
