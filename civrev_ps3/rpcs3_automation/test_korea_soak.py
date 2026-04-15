#!/usr/bin/env python3
"""Korea mod M7 test — 50-turn end-turn soak as Korea (v0.9 form).

Reaches in-game state via the same flow as test_korea_play.py, founds
the capital (X on Settlers' 'Found City' action), then end-turns 50
times capturing screenshots every 5 turns. Pass criteria: RPCS3 stays
alive, no 'F .*' fatal lines in log, HUD text remains OCR-detectable.

50 turns is the PRD §7.4 M7 target. iter-9 proved 25 turns works
cleanly with year advance 4000 BC → 2400 BC; this scales to the
full target.
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


def _hold(key, dur):
    L._hold_key(key, dur)


def _shot(label):
    frame = L._capture_display()
    if frame is None:
        return
    out = Path(f"/output/korea_soak_{label}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.fromarray(frame).save(str(out))
    except Exception as e:
        print(f"  shot save fail: {e}")


TARGET_TURNS = 50


def main():
    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 with {game_path}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    result = {
        "milestone": "M7",
        "pass": False,
        "oracle": (
            f"end-turn {TARGET_TURNS}x without crash; HUD stays OCR-readable; "
            f"game is still on the world map at the end (not soft-exited to menu)"
        ),
        "target_turns": TARGET_TURNS,
        "stages": {},
        "snapshots": [],
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

        # Main menu → Single Player → Play Scenario
        _press("Down", 0.5); _press("X", 3)
        _press("Down", 0.5); _press("Down", 0.5); _press("Down", 0.5); _press("X", 3)

        # Wait for scenario list
        for _ in range(15):
            t = L._ocr_screen()
            if "choose" in t.lower() or "scenario" in t.lower():
                break
            time.sleep(2)

        # Scroll to Earth
        for _ in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                break
            _press("Down", 0.4)
        _press("X", 3)

        # Chieftain (easiest difficulty). iter-1186: switched from Deity
        # to Chieftain because the M7 soak run at iter-1186 had Korea
        # (playing as a Mao-stats clone per v1.0 §1.1) defeated by
        # Cleopatra via Domination around turn 30-35 on Deity. §9 DoD
        # item 4 asks for "50 end-turn cycles without the game crashing
        # or freezing" — the strict letter of item 4 doesn't require
        # surviving at the highest difficulty. The end-turn loop itself
        # (the crash/freeze check) is what we verify; a softer
        # difficulty lets the game simulate through 50 turns without
        # the civ being eliminated by AI play.
        _press("X", 5)
        _shot("01_difficulty")

        # Normalize to Romans, right 16 to Korea (iter-1185: Korea now
        # at slot 16 under the iter-189 strict reading, via the
        # LoadOptions Korea-synthesis prefix in gfx_chooseciv.gfx. The
        # old "right 15" was the v0.9 slot-15 England→Korea rename).
        for _ in range(20):
            _press("Left", 0.25)
        for _ in range(16):
            _press("Right", 0.3)
        _shot("02_korea_highlighted")

        _press("X", 15)
        _shot("03_after_confirm")

        # Dismiss intro
        for _ in range(4):
            _press("X", 3)

        # Wait for in-game HUD
        for poll in range(12):
            time.sleep(5)
            t = L._ocr_screen()
            if any(k in t for k in ("Turn", "Gold", "Science", "Sejong", "Koreans", "Seoul")):
                print(f"  HUD text detected on poll {poll}")
                result["stages"]["in_game"] = True
                break
        else:
            result["stages"]["in_game"] = False
            print("M7 precondition FAIL: no HUD after 60s")
            return 1

        _shot("04_spawn")

        # Found the capital: settler starts highlighted with "Found City" as
        # first action, so a single X press founds the city.
        print("Founding capital")
        _press("X", 3)
        _shot("05_after_found_city")

        # End-turn is the Circle (O) button on PS3, mapped to BackSpace by
        # the keyboard pad handler (key_map in launch.py). The in-game
        # help overlay we caught in the first iter-9 attempt explicitly
        # labels O as "Cancel / End turn".
        print(f"End-turn {TARGET_TURNS}x via O button (BackSpace)")
        end_turn_ok = True
        for i in range(TARGET_TURNS):
            _press("O", 2.5)  # Circle = End turn
            # Some turns fire a "units haven't moved" confirm — press O
            # again to confirm end-turn anyway.
            _press("O", 1.0)
            if (i + 1) % 5 == 0:
                _shot(f"turn_{i+1:02d}")
                # Sanity check: RPCS3 still alive?
                if not L._is_rpcs3_alive(rpcs3):
                    print(f"  RPCS3 died at turn {i+1}")
                    end_turn_ok = False
                    break
                t = L._ocr_screen()
                snap = " | ".join(s.strip() for s in t.splitlines() if s.strip())[:200]
                result["snapshots"].append({"turn": i + 1, "ocr": snap})
                print(f"  turn {i+1:02d}: {snap[:120]}")

        result["stages"]["end_turn_loop"] = end_turn_ok

        # Tightened oracle: the game must still be in an in-game state at
        # the end of the soak. A soft exit back to the main menu (from
        # civ elimination, accidental quit, etc.) would otherwise sneak
        # through the old "RPCS3 still alive" oracle. Check the last 3
        # snapshots for in-game HUD markers and flag a main-menu leak
        # if they're missing.
        in_game_markers = ("Turn", " BC", " AD", "Settlers", "Found City", "Science", "Gold")
        menu_markers = ("Play Now", "Single Player", "Multiplayer")
        tail_snaps = result["snapshots"][-3:] if result["snapshots"] else []
        last_ocrs = [s.get("ocr", "") for s in tail_snaps]
        any_in_game = any(
            any(m in ocr for m in in_game_markers) for ocr in last_ocrs
        )
        all_menu = all(
            any(m in ocr for m in menu_markers) for ocr in last_ocrs
        ) if last_ocrs else False
        result["stages"]["still_in_game_at_end"] = any_in_game and not all_menu
        result["pass"] = (
            end_turn_ok
            and L._is_rpcs3_alive(rpcs3)
            and result["stages"]["still_in_game_at_end"]
        )
        _shot("99_final")

    except Exception as e:
        print(f"test_korea_soak exception: {e}")
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
    out = Path("/output/korea_m7_result.json")
    out.write_text(json.dumps(result, indent=2))
    print(f"wrote {out}; pass={result['pass']}")
    if result.get("stages", {}).get("still_in_game_at_end") is False:
        print(
            "  M7 TIGHTEN-FAIL: last 3 snapshots do NOT show in-game HUD — "
            "game likely soft-exited to main menu (civ eliminated, "
            "accidental quit, etc.)"
        )
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
