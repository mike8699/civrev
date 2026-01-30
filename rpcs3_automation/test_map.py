#!/usr/bin/env python3
"""
End-to-end map testing: pack DLC, launch RPCS3, capture screenshot.

Usage:
    python test_map.py                  # Pack + launch + screenshot
    python test_map.py --pack-only      # Just pack and install, don't launch
    python test_map.py --wait 120       # Max wait before timeout
    python test_map.py --generate-textures  # Regenerate DDS textures first
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from config import PAK9_DIR, PROJECT_ROOT, VENV_PYTHON


def generate_textures():
    """Regenerate DDS textures for all .map files in Pak9/."""
    gen_script = PROJECT_ROOT / "generate_map_textures.py"
    if not gen_script.exists():
        print(f"Error: {gen_script} not found", file=sys.stderr)
        sys.exit(1)

    map_files = list(PAK9_DIR.glob("*.map"))
    for mf in map_files:
        print(f"\nGenerating textures for {mf.name}...")
        result = subprocess.run(
            [str(VENV_PYTHON), str(gen_script), str(mf)],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(
                f"Texture generation failed for {mf.name}:\n{result.stderr}",
                file=sys.stderr,
            )
        else:
            print(result.stdout)


def main():
    parser = argparse.ArgumentParser(description="Test map changes in RPCS3")
    parser.add_argument(
        "--pack-only",
        action="store_true",
        help="Only pack and install, don't launch RPCS3",
    )
    parser.add_argument(
        "--generate-textures",
        "-g",
        action="store_true",
        help="Regenerate DDS textures before packing",
    )
    parser.add_argument(
        "--wait",
        "-w",
        type=int,
        default=None,
        help="Max seconds to wait for game to load",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="/output/screenshot.png",
        help="Save screenshot to this path",
    )
    args = parser.parse_args()

    if args.generate_textures:
        generate_textures()

    from pack import pack_and_install

    pack_and_install()

    if args.pack_only:
        print("Pack-only mode: done.")
        return

    from launch import launch_and_screenshot

    screenshot = launch_and_screenshot(max_wait=args.wait)

    if screenshot and args.output:
        out = Path(args.output)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = out.parent / f"{out.stem}_{timestamp}{out.suffix}"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(screenshot), str(dest))
        print(f"Screenshot copied to {dest}")

    if screenshot:
        print(f"\nResult screenshot: {screenshot}")
    else:
        print("\nNo screenshot was captured.")


if __name__ == "__main__":
    main()
