#!/usr/bin/env bash
# korea_mod/build.sh — assemble the patched EBOOT + overlaid FPKs.
#
# v1.0 status: scaffold. The EBOOT patcher is not implemented yet — this
# script currently only validates that the XML overlays are well-formed and
# copies them into a staging tree. It will grow into the full
# patch→pack→install pipeline as §6.2 lands.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
STAGE="$HERE/_build"

rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[build] validating XML overlays"
shopt -s nullglob
xml_files=( "$HERE/xml_overlays"/*.xml )
shopt -u nullglob
for f in "${xml_files[@]}"; do
    xmllint --noout "$f"
    echo "  ok  $(basename "$f")"
done
if [ "${#xml_files[@]}" -eq 0 ]; then
    echo "  (no top-level .xml overlays — iter-223 archived the dead Common0 XMLs)"
fi

echo "[build] staging XML overlays into $STAGE/xml_overlays"
mkdir -p "$STAGE/xml_overlays"
if [ "${#xml_files[@]}" -gt 0 ]; then
    cp "${xml_files[@]}" "$STAGE/xml_overlays/"
fi

# EBOOT patch step: dry-run first (M0a gate), then apply for real.
if [ -f "$HERE/eboot_patches.py" ]; then
    echo "[build] eboot_patches.py --dry-run (M0a)"
    python3 "$HERE/eboot_patches.py" --dry-run --in "$ROOT/EBOOT_v130_decrypted.ELF" --out "$STAGE/EBOOT_korea.ELF"
    echo "[build] eboot_patches.py apply"
    python3 "$HERE/eboot_patches.py" --in "$ROOT/EBOOT_v130_decrypted.ELF" --out "$STAGE/EBOOT_korea.ELF"
fi

# Sejong portrait extraction (PRD §9.AA part A). Pull Kor_Sejong_DIFF from
# the CivRev2 Unity bundle, crop the face, and emit ldr_korea.dds in the
# stock LDR portrait format. Runs via `uv run` so UnityPy/numpy/Pillow are
# provisioned in an ephemeral env without touching system Python. The DDS
# lands in $STAGE/portraits where pack_korea.sh picks it up for the FPK.
CR2_DATA="$ROOT/../civrev2/main.19.com.t2kgames.civrev2/assets/bin/Data"
if [ -f "$HERE/extract_cr2_sejong.py" ] && [ -d "$CR2_DATA" ]; then
    echo "[build] extracting Sejong portrait from CivRev2 (uv run + UnityPy)"
    uv run --with UnityPy --with numpy --with Pillow \
        python3 "$HERE/extract_cr2_sejong.py" \
        --cr2-data "$CR2_DATA" --out "$STAGE/portraits"
elif [ -f "$HERE/extract_cr2_sejong.py" ]; then
    echo "[build] WARNING: CivRev2 data dir absent ($CR2_DATA);"
    echo "         skipping Sejong portrait — carousel ships without ldr_korea.dds"
fi

# FPK repack step.
if [ -f "$HERE/pack_korea.sh" ]; then
    echo "[build] running pack_korea.sh"
    "$HERE/pack_korea.sh" "$STAGE"
else
    echo "[build] pack_korea.sh not present yet — skipping FPK repack step"
fi

echo "[build] done"
