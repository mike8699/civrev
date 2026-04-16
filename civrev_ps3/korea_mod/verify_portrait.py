#!/usr/bin/env python3
"""Verify the Sejong portrait is correctly wired in the built mod.

Runs three checks against the built Pregame FPK staging directory:

1. ldr_korea.dds exists and has correct size (128x128 BGRA = 65664 bytes)
2. JPEXS re-export of gfx_chooseciv.gfx shows GetImageName routes "16" → "korea"
3. JPEXS re-export shows SetUpUnits saves/restores myDataArray[0] for slot 16

Usage:
    verify_portrait.py [--stage <dir>] [--ffdec <jar>]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path


def check_dds(stage: Path) -> bool:
    """Check ldr_korea.dds is present and correctly sized."""
    dds = stage / "ldr_korea.dds"
    if not dds.is_file():
        print(f"  FAIL: {dds} not found")
        return False
    size = dds.stat().st_size
    if size != 65664:
        print(f"  FAIL: ldr_korea.dds is {size} bytes (expected 65664)")
        return False
    print(f"  PASS: ldr_korea.dds present ({size} bytes)")
    return True


def check_scripts(stage: Path, ffdec: Path) -> tuple[bool, bool]:
    """Re-export scripts from built GFX and verify patches."""
    gfx = stage / "gfx_chooseciv.gfx"
    if not gfx.is_file():
        print(f"  FAIL: {gfx} not found")
        return False, False

    with tempfile.TemporaryDirectory(prefix="verify_portrait_") as tmp:
        tmp_path = Path(tmp)
        result = subprocess.run(
            ["java", "-jar", str(ffdec), "-export", "script",
             str(tmp_path / "scripts"), str(gfx)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(f"  FAIL: JPEXS export failed: {result.stderr[:200]}")
            return False, False

        # Check GetImageName
        chooseciv = tmp_path / "scripts" / "scripts" / "DefineSprite_96_ChooseCivLeader" / "frame_1" / "DoAction.as"
        getimage_ok = False
        if chooseciv.is_file():
            src = chooseciv.read_text()
            if '"korea"' in src and 'case "16"' in src:
                print('  PASS: GetImageName routes "16" → "korea"')
                getimage_ok = True
            else:
                print('  FAIL: GetImageName does not contain Korea case')
        else:
            print(f"  FAIL: ChooseCivLeader DoAction.as not found")

        # Check SetUpUnits save/restore
        setupunits = tmp_path / "scripts" / "scripts" / "frame_1" / "DoAction_4.as"
        setupunits_ok = False
        if setupunits.is_file():
            src = setupunits.read_text()
            if 'j == 16' in src and 'myDataArray[0] = "16"' in src:
                print("  PASS: SetUpUnits has Korea portrait save/restore")
                setupunits_ok = True
            else:
                print("  FAIL: SetUpUnits missing Korea portrait patch")
        else:
            print(f"  FAIL: DoAction_4.as not found")

    return getimage_ok, setupunits_ok


def main() -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, default=here / "_build" / "Pregame_korea")
    parser.add_argument("--ffdec", type=Path, default=here.parent / "tools" / "ffdec" / "ffdec.jar")
    args = parser.parse_args()

    print("=== Sejong Portrait Verification ===")
    print()

    dds_ok = check_dds(args.stage)
    getimage_ok, setupunits_ok = check_scripts(args.stage, args.ffdec)

    print()
    all_ok = dds_ok and getimage_ok and setupunits_ok
    if all_ok:
        print("ALL CHECKS PASSED — Sejong portrait pipeline is wired correctly")
    else:
        print("SOME CHECKS FAILED — see above")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
