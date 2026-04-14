#!/usr/bin/env python3
"""Korea mod M2 test — drive civ-select and scan for Korea / Sejong.

Replicates the main-menu → Single Player → Play Scenario → Earth →
Deity → civ-select flow from launch.py's _navigate_to_scenario, then
instead of committing to a civ, scrolls right across all slots and
OCRs each one looking for Korea / Korean / Sejong.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import launch as L
from config import RPCS3_BIN, RPCS3_BOOT_TIMEOUT
from PIL import Image
import numpy as np


def _press(button, delay=0.5):
    L._send_ps3_button(button)
    time.sleep(delay)


def _shot(label):
    frame = L._capture_display()
    if frame is None:
        return
    out = Path(f"/output/korea_{label}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.fromarray(frame).save(str(out))
    except Exception as e:
        print(f"  shot save fail: {e}")


def main():
    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 with {game_path}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    observed = []
    korea_seen = False
    korea_at_slot = None

    try:
        time.sleep(2)
        if not L._is_rpcs3_alive(rpcs3):
            print("RPCS3 failed to start")
            return 2
        print("Waiting for RSX...")
        if not L._wait_for_rsx(rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time):
            print("RSX did not come up")
            return 3

        L._navigate_startup_to_main_menu(rpcs3)
        _shot("00_main_menu")

        # Main menu -> Single Player (1 Down + X)
        _press("Down", 0.5)
        _press("X", 3)
        _shot("01_single_player")

        # Single Player -> Play Scenario (3 Down + X)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("X", 3)
        _shot("02_scenario_menu")

        # Wait for "Choose Scenario"
        for a in range(15):
            t = L._ocr_screen()
            if "choose" in t.lower() or "scenario" in t.lower():
                print(f"  scenario list on attempt {a}")
                break
            time.sleep(2)

        # Scroll down until Earth is found
        print("  searching Earth scenario...")
        for a in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                print(f"  found Earth at {a}")
                break
            _press("Down", 0.4)
        _press("X", 3)
        _shot("03_after_earth_select")

        # Difficulty: 4 Down + X for Deity
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 5)
        _shot("04_after_difficulty")

        # Civ-select: scroll RIGHT 25 times, capturing+OCR each
        # We don't normalize to leftmost first because that risks infinite
        # loop on a 17-civ list; instead we start wherever the cursor lands
        # and sweep right. 25 > 17 guarantees we visit every slot.
        print("Sweeping civ-select with 25 rights")
        for i in range(25):
            _press("Right", 0.35)
            _shot(f"slot_{i:02d}")
            try:
                text = L._ocr_screen(region=(0.0, 0.3, 1.0, 0.9))
            except Exception as e:
                text = f"<OCR FAIL: {e}>"
            text_clean = " | ".join(
                line.strip() for line in text.splitlines() if line.strip()
            )[:200]
            observed.append({"i": i, "text": text_clean})
            print(f"  slot[{i:02d}] {text_clean}")
            if any(kw in text for kw in ("Korea", "Korean", "Sejong")):
                korea_seen = True
                if korea_at_slot is None:
                    korea_at_slot = i
                print(f"  *** KOREA KEYWORD DETECTED at slot {i} ***")
    except Exception as e:
        print(f"test_korea exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            rpcs3.terminate()
            rpcs3.wait(timeout=5)
        except Exception:
            try:
                rpcs3.kill()
            except Exception:
                pass

    Path("/output").mkdir(exist_ok=True)
    result = {
        "milestone": "M2",
        "pass": korea_seen,
        "oracle": "OCR {'Korea','Korean','Sejong'} on civ-select carousel during a 25-right sweep",
        "observations": observed,
        "korea_seen": korea_seen,
        "korea_at_slot": korea_at_slot,
    }
    out = Path("/output/korea_m2_result.json")
    out.write_text(json.dumps(result, indent=2))
    print(f"wrote {out}; korea_seen={korea_seen} slot={korea_at_slot}")
    return 0 if korea_seen else 1


if __name__ == "__main__":
    sys.exit(main())
