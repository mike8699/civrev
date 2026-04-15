#!/usr/bin/env python3
"""Korea mod M6/M7 test — select Korea, enter game, end-turn loop.

v0.9 form: Korea currently lives at civ slot 15 (as a replacement for
Elizabeth/England, patched via fpk_byte_patch.py). This test mirrors
launch.py's Russians flow but selects slot 15 instead.
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


def _press(button, delay=0.5):
    L._send_ps3_button(button)
    time.sleep(delay)


def _shot(label):
    frame = L._capture_display()
    if frame is None:
        return
    out = Path(f"/output/korea_play_{label}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.fromarray(frame).save(str(out))
    except Exception as e:
        print(f"  shot save fail: {e}")


def main():
    # Optional arg: slot number to select (default 15 for Korea).
    # Iter-11 reuses this script for M9 regression by passing slot=6 (Mao).
    slot = 15
    label = "korea"
    if len(sys.argv) > 1:
        try:
            slot = int(sys.argv[1])
            label = sys.argv[2] if len(sys.argv) > 2 else f"slot{slot}"
        except ValueError:
            pass

    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 with {game_path}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    # iter-225: dropped the historical `slot == 15 -> M6` special case.
    # When this script was written under v0.9 (England→Korea slot-15
    # replacement), slot 15 was Korea and M6 was the "Korea boots" milestone.
    # Under the iter-189 strict reading, slot 15 is Elizabeth/English again
    # and M6's semantics no longer apply — the harness should report every
    # invocation as M9 (regression sweep) so result.json filenames are
    # uniform under `korea_m9_<label>_result.json`. Without this fix,
    # `run_m9_regressions.sh` misses the elizabeth result via its m9-only
    # glob (see iter-224 findings).
    result = {
        "milestone": "M9",
        "slot": slot,
        "label": label,
        "pass": False,
        "oracle": f"OCR in-game HUD after selecting slot {slot} ({label})",
        "stages": {},
    }

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
        result["stages"]["main_menu"] = True

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
                print(f"  scenario list ready on attempt {a}")
                break
            time.sleep(2)

        # iter-1188: user manually picked a DLC scenario during
        # their local test session, so the game remembered the
        # cursor position. On a fresh harness run the Choose
        # Scenario list now opens with the cursor on a DLC entry
        # ("Attack of the Huns") and Earth is above the visible
        # viewport. Original code only scrolled Down; now scroll
        # Up first then Down as fallback.
        print("  searching Earth scenario...")
        found = False
        for a in range(40):
            t = L._ocr_screen()
            if "earth" in t.lower():
                print(f"  found Earth up-scrolling at {a}")
                found = True
                break
            _press("Up", 0.4)
        if not found:
            for a in range(40):
                t = L._ocr_screen()
                if "earth" in t.lower():
                    print(f"  found Earth down-scrolling at {a}")
                    found = True
                    break
                _press("Down", 0.4)
        _press("X", 3)
        _shot("03_after_earth_select")

        # Difficulty: 4 Down + X for Deity
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 5)
        _shot("04_after_difficulty")
        result["stages"]["difficulty_selected"] = True

        # Civ-select: 20 Lefts to normalize to Romans (slot 0),
        # then N Rights to the target slot.
        print("  Normalizing to leftmost (Romans)")
        for _ in range(20):
            _press("Left", 0.25)
        _shot("05_romans_normalized")

        print(f"  Scrolling right {slot} to {label} (slot {slot})")
        for _ in range(slot):
            _press("Right", 0.3)
        _shot("06_slot_highlighted")

        # OCR the current selection to confirm
        text = L._ocr_screen(region=(0.0, 0.3, 1.0, 0.85))
        target_keywords = {
            0: ("Caesar", "Romans", "Roman"),
            1: ("Cleopatra", "Egyptians", "Egypt"),
            2: ("Alexander", "Greeks", "Greek"),
            3: ("Isabella", "Spanish", "Spain"),
            4: ("Bismarck", "Germans", "German"),
            5: ("Catherine", "Russians", "Russia"),
            6: ("Mao", "Chinese", "China"),
            7: ("Lincoln", "Americans", "America"),
            8: ("Tokugawa", "Japanese", "Japan"),
            9: ("Napoleon", "French", "France"),
            10: ("Gandhi", "Indians", "India"),
            11: ("Saladin", "Arabs", "Arabia"),
            12: ("Montezuma", "Aztecs", "Aztec"),
            13: ("Shaka", "Zulu", "African"),
            14: ("Genghis", "Mongols", "Mongolia"),
            15: ("Elizabeth", "English", "England"),
            16: ("Random",),
            # Under the iter-189 strict reading, slot 17 is the
            # brand-new Korea 18th-cell. It doesn't yet exist —
            # future iterations will add it via gfx_chooseciv.gfx
            # carousel extension. Keyword set is added here now so
            # the test harness can OCR-verify reachability once
            # the cell lands.
            17: ("Sejong", "Korean", "Korea", "KOREA18"),
        }.get(slot, ())
        target_on_screen = any(k in text for k in target_keywords)
        result["stages"]["highlighted_ok"] = target_on_screen
        result["select_ocr"] = (
            " | ".join(s.strip() for s in text.splitlines() if s.strip())[:200]
        )
        if target_on_screen:
            print(f"  *** {label} confirmed on civ-select before confirm ***")
        else:
            print(f"  WARNING: {label} keyword not detected; OCR: {text[:200]!r}")

        # Confirm selection
        _press("X", 15)
        _shot("07_after_confirm")

        # Intro cutscenes — press X multiple times
        print("  Dismissing intro cutscene")
        for _ in range(4):
            _press("X", 3)
        _shot("08_post_intro")

        # Wait up to 60s for in-game HUD. Poll OCR every 5s for HUD text.
        print("  Waiting for in-game HUD")
        hud_seen = False
        hud_markers = ("Turn", "Gold", "Science", "Found City", "Settlers", "BC")
        for poll in range(12):
            time.sleep(5)
            t = L._ocr_screen()
            if any(k in t for k in hud_markers):
                hud_seen = True
                print(f"  HUD text detected on poll {poll}")
                break
        _shot("09_in_game")
        result["stages"]["in_game_hud"] = hud_seen

        if hud_seen:
            result["pass"] = True
            print(f"  {result['milestone']} PASS — {label} game loaded")
        else:
            print(f"  {result['milestone']} FAIL — no HUD text after 60s")

    except Exception as e:
        print(f"test_korea_play exception: {e}")
        import traceback
        traceback.print_exc()
        result["exception"] = str(e)
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
    out = Path(f"/output/korea_{result['milestone'].lower()}_{label}_result.json")
    out.write_text(json.dumps(result, indent=2))
    print(f"wrote {out}; pass={result['pass']}")

    # iter-1188: copy RPCS3.log into /output so the host can inspect
    # fscommand traces and validate the slot-16→6 remap behavior.
    try:
        import shutil as _sh, subprocess as _sub
        # RPCS3 writes its log to a variety of locations depending on
        # build/flavor. Search broadly.
        result_cmd = _sub.run(
            ["find", "/root", "/tmp", "/opt", "/var",
             "-maxdepth", "6", "-iname", "*RPCS3*.log*", "-print"],
            capture_output=True, text=True, timeout=10,
        )
        hits = [l for l in result_cmd.stdout.splitlines() if l.strip()]
        print(f"rpcs3 log candidates: {hits}")
        for src_str in hits:
            src = Path(src_str)
            if src.is_file():
                dst = Path(f"/output/rpcs3_{label}_{src.name}")
                _sh.copy(src, dst)
                print(f"copied {src} -> {dst}")
    except Exception as e:
        print(f"rpcs3 log copy failed: {e}")
        import traceback
        traceback.print_exc()

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
