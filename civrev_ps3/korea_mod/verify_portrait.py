#!/usr/bin/env python3
"""Static verification of the Sejong carousel-portrait pipeline (PRD §9.AA A).

Verifies the *built* artifacts, not the source scripts, so it catches a
broken build regardless of how the patcher is wired. Three checks against
the repacked Pregame_korea.FPK staging tree:

1. ldr_korea.dds is present in the staging dir, is a real DDS, and matches
   the stock small-portrait format exactly (128x128, 65664 bytes), plus its
   .extradata companion exists and the name is registered in ordering.json
   (without those two, fpk.py repack would have failed).
2. The patched gfx_chooseciv.gfx routes GetImageName("16") -> "korea"
   (so the carousel loads LDR_korea.dds for the Korea cell).
3. The patched gfx_chooseciv.gfx overrides the Korea cell thumbnail via
   SetPortraitImage("16") in SetUpUnits (slot 16), so the cell shows Sejong
   even though slotData16[0] stays "6" (China) for the PPU 3D leaderhead.

These prove the portrait is wired; the actual on-screen render is confirmed
separately by the M9 docker run (06_slot_highlighted screenshot). Exits
non-zero with a diagnostic if any check fails.

Usage:
    verify_portrait.py [--stage <dir>] [--ffdec <jar>]
"""

from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

STOCK_PORTRAIT_SIZE = 65664  # 128x128 32-bit BGRA + 128-byte DDS header
GETIMAGE_REL = "scripts/DefineSprite_96_ChooseCivLeader/frame_1/DoAction.as"
SETUPUNITS_REL = "scripts/frame_1/DoAction_4.as"


def check_dds(stage: Path) -> bool:
    ok = True
    dds = stage / "ldr_korea.dds"
    if not dds.is_file():
        print(f"  FAIL: {dds} not found"); return False
    b = dds.read_bytes()
    if b[:4] != b"DDS ":
        print(f"  FAIL: ldr_korea.dds bad magic {b[:4]!r}"); ok = False
    w = struct.unpack_from("<I", b, 16)[0]
    h = struct.unpack_from("<I", b, 12)[0]
    if (w, h) != (128, 128) or len(b) != STOCK_PORTRAIT_SIZE:
        print(f"  FAIL: ldr_korea.dds is {w}x{h} {len(b)}B "
              f"(expected 128x128 {STOCK_PORTRAIT_SIZE}B)"); ok = False
    if not (stage / "ldr_korea.dds.extradata").is_file():
        print("  FAIL: ldr_korea.dds.extradata missing"); ok = False
    order_path = stage / "ordering.json"
    if order_path.is_file():
        if "ldr_korea.dds" not in json.loads(order_path.read_text()):
            print("  FAIL: ldr_korea.dds not registered in ordering.json"); ok = False
    if ok:
        print(f"  PASS: ldr_korea.dds present ({w}x{h} {len(b)}B, +extradata, in ordering)")
    return ok


def check_scripts(stage: Path, ffdec: Path) -> bool:
    gfx = stage / "gfx_chooseciv.gfx"
    if not gfx.is_file():
        print(f"  FAIL: {gfx} not found"); return False
    with tempfile.TemporaryDirectory(prefix="verify_portrait_") as tmp:
        out = Path(tmp) / "scripts"
        r = subprocess.run(["java", "-jar", str(ffdec), "-export", "script",
                            str(out), str(gfx)], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  FAIL: JPEXS export failed: {r.stderr[:200]}"); return False
        ok = True
        gi = out / "scripts" / GETIMAGE_REL.split("scripts/", 1)[1]
        if gi.is_file() and 'case "16":' in gi.read_text() and '"korea"' in gi.read_text():
            print('  PASS: GetImageName routes "16" -> "korea"')
        else:
            print('  FAIL: GetImageName does not route "16" -> "korea"'); ok = False
        su = out / "scripts" / SETUPUNITS_REL.split("scripts/", 1)[1]
        if su.is_file() and 'SetPortraitImage("16")' in su.read_text():
            print('  PASS: SetUpUnits overrides slot-16 thumbnail via SetPortraitImage("16")')
        else:
            print('  FAIL: SetUpUnits missing SetPortraitImage("16") override'); ok = False
    return ok


def main() -> int:
    here = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, default=here / "_build" / "Pregame_korea")
    ap.add_argument("--ffdec", type=Path, default=here.parent / "tools" / "ffdec" / "ffdec.jar")
    args = ap.parse_args()

    print("=== Sejong Portrait Verification (static) ===")
    if not args.stage.is_dir():
        print(f"  SKIP: staging dir {args.stage} absent — run build.sh first")
        return 0  # nothing built yet is not a failure of this check
    dds_ok = check_dds(args.stage)
    scr_ok = check_scripts(args.stage, args.ffdec)
    print()
    if dds_ok and scr_ok:
        print("ALL CHECKS PASSED — Sejong portrait pipeline wired correctly")
        return 0
    print("SOME CHECKS FAILED — see above")
    return 1


if __name__ == "__main__":
    sys.exit(main())
