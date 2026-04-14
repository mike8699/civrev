#!/usr/bin/env bash
# korea_mod/verify.sh — run the Korea mod verification suite.
#
# Tiers:
#   --tier=static  runs M0 only (<30s, no emulator): XML well-formedness,
#                  EBOOT dry-run patch, FPK round-trip hash (when implemented),
#                  string-key inventory.
#   --tier=fast    M0..M3 (<6 min): static + boot-time OCR checks.
#   --tier=full    M0..M7 + M9 (<45 min): static + boot + live memory + soak.
#
# Every milestone writes korea_mod/verification/<milestone>/result.json and
# a screenshot + rpcs3.log when applicable. verify.sh exits 0 iff every
# milestone in the requested tier is green.
#
# v1.0 status: only M0 is wired. Higher tiers short-circuit with a
# "not-implemented" result.json so the oracle artifact layout is stable from
# iteration 1.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VDIR="$HERE/verification"

TIER="static"
for arg in "$@"; do
    case "$arg" in
        --tier=*) TIER="${arg#--tier=}" ;;
        *) echo "unknown arg: $arg" >&2; exit 2 ;;
    esac
done

mkdir -p "$VDIR"

fail=0

write_result() {
    local milestone="$1"; shift
    local passed="$1"; shift
    local notes="$1"; shift
    local dir="$VDIR/$milestone"
    mkdir -p "$dir"
    python3 - "$dir/result.json" "$milestone" "$passed" "$notes" <<'PY'
import json, sys
path, milestone, passed, notes = sys.argv[1:]
json.dump(
    {
        "milestone": milestone,
        "pass": passed == "true",
        "notes": notes,
    },
    open(path, "w"),
    indent=2,
)
PY
}

# ---------- M0: static checks ----------
echo "[verify] M0 static checks"

m0_pass=true
m0_notes=""

# M0c — XML well-formedness on every overlay.
for f in "$HERE/xml_overlays"/*.xml; do
    if ! xmllint --noout "$f" 2>/dev/null; then
        m0_pass=false
        m0_notes="xmllint failed on $(basename "$f"); $m0_notes"
    fi
done

# M0a — EBOOT patch dry-run. Fallback when the patcher is not yet wired.
if [ -f "$HERE/eboot_patches.py" ]; then
    if ! python3 "$HERE/eboot_patches.py" --dry-run --in "$ROOT/EBOOT_v130_clean.ELF" > "$VDIR/M0/dry_run.log" 2>&1; then
        m0_pass=false
        m0_notes="eboot_patches.py --dry-run failed (see verification/M0/dry_run.log); $m0_notes"
    fi
else
    m0_notes="eboot_patches.py not implemented yet; $m0_notes"
fi

# M0b — FPK round-trip. Only attempted once build.sh actually repacks.
if [ -f "$HERE/_build/Common0_korea.FPK" ]; then
    echo "[verify] (M0b FPK round-trip not yet implemented)"
fi

# M0d — string-key inventory. Only when gfxtext.xml / pedia XMLs land.
:

if [ "$m0_pass" = true ]; then
    write_result M0 true "overlays well-formed${m0_notes:+; $m0_notes}"
else
    write_result M0 false "$m0_notes"
    fail=1
fi

# ---------- Emulator tiers (not yet wired) ----------
if [ "$TIER" != "static" ]; then
    for m in M1 M2 M3 M4 M5 M6 M7 M9; do
        write_result "$m" false "tier=$TIER requested but $m is not implemented yet"
    done
    fail=1
fi

if [ $fail -eq 0 ]; then
    echo "[verify] all requested milestones PASS"
    exit 0
else
    echo "[verify] one or more milestones FAILED" >&2
    exit 1
fi
