#!/usr/bin/env python3
"""iter-149: catch the carousel cell-init iterator via Z0 breakpoint.

Drives korea_play through to civ-select, attaches GDB, sets a Z0
software breakpoint at FUN_001e49f0 (0x1e49f0 — the per-cell
carousel data binder identified in iter-146), drives the cursor
(which forces re-render), and waits for the breakpoint to fire.

When (if) it fires, reads PC + LR + r3..r6 (PowerPC arg registers)
to identify the caller and the per-cell context object passed in.

If Z0 doesn't fire (RPCS3 may silently drop sw breakpoints in PPU
LLVM JIT mode), falls back to PC polling: pause every 50ms,
read PC, check if it's in 0x1e49f0..0x1e4a9c (FUN_001e49f0 body).
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import launch as L  # noqa: E402
from config import RPCS3_BIN, RPCS3_BOOT_TIMEOUT  # noqa: E402
from gdb_client import GDBClient  # noqa: E402

CAROUSEL_INIT = 0x001e49f0
CAROUSEL_INIT_END = 0x001e4a9c  # next vtable method


def _press(button, delay=0.5):
    L._send_ps3_button(button)
    time.sleep(delay)


def main() -> int:
    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 with {game_path}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    result = {
        "milestone": "iter-149",
        "carousel_init_addr": hex(CAROUSEL_INIT),
        "z0_set": False,
        "z0_fired": False,
        "polling_caught": False,
        "samples": [],
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

        # Drive to main menu, then ATTACH GDB AND SET BP before any civ-select navigation
        L._navigate_startup_to_main_menu(rpcs3)

        print("Setting Z0 at carousel cell-init BEFORE menu navigation...")
        try:
            with GDBClient("127.0.0.1", 2345, timeout=10) as gdb:
                gdb.pause()
                time.sleep(0.3)
                ok = gdb.set_breakpoint(CAROUSEL_INIT)
                result["z0_set"] = ok
                print(f"  Z0 at 0x{CAROUSEL_INIT:x}: {'OK' if ok else 'rejected'}")
                gdb.resume()
        except Exception as e:
            print(f"GDB attach (early) failed: {e}")
            result["gdb_early_error"] = str(e)

        # Drive to civ-select. The breakpoint should fire when the carousel
        # initializes its cells.
        _press("Down", 0.5)
        _press("X", 3)  # Single Player
        _press("Down", 0.5); _press("Down", 0.5); _press("Down", 0.5)
        _press("X", 3)  # Play Scenario
        for _ in range(15):
            t = L._ocr_screen()
            if "earth" in t.lower() or "scenario" in t.lower():
                break
            time.sleep(2)
        for _ in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                break
            _press("Down", 0.4)
        _press("X", 3)  # Earth
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 1)  # Difficulty → triggers carousel load

        print("Polling all threads for breakpoint hit on carousel cell-init...")
        try:

            # Poll all threads for breakpoint hit
            for poll in range(30):
                try:
                    with GDBClient("127.0.0.1", 2345, timeout=5) as gdb:
                        gdb.pause()
                        time.sleep(0.1)
                        threads = gdb.inspect_all_threads()
                        sample = {"poll": poll, "threads": []}
                        for t in threads:
                            tid = t.get("tid", "?")
                            pc = t.get("pc", 0)
                            lr = t.get("lr", 0)
                            in_carousel = CAROUSEL_INIT <= pc <= CAROUSEL_INIT_END
                            entry = {"tid": tid, "pc": hex(pc), "lr": hex(lr)}
                            if in_carousel:
                                entry["IN_CAROUSEL_INIT"] = True
                                result["polling_caught"] = True
                                print(f"  ★ poll {poll} tid={tid}: PC=0x{pc:x} LR=0x{lr:x}")
                            sample["threads"].append(entry)
                        result["samples"].append(sample)
                        # Show non-zero PCs
                        nonzero = [t for t in sample["threads"] if t["pc"] != "0x0"]
                        if nonzero and poll % 3 == 0:
                            print(f"  poll {poll}: {len(nonzero)} live threads, "
                                  f"first pc={nonzero[0]['pc']}")
                        gdb.resume()
                except Exception as e:
                    print(f"  poll {poll}: GDB error {e}")
                if result["polling_caught"]:
                    break
                _press("Right", 0.2)
                time.sleep(0.2)
        except Exception as e:
            print(f"GDB exception: {e}")
            result["gdb_error"] = str(e)
    finally:
        try:
            rpcs3.terminate()
            rpcs3.wait(timeout=5)
        except Exception:
            try:
                rpcs3.kill()
            except Exception:
                pass

    Path("/output/iter149_carousel_bp.json").write_text(json.dumps(result, indent=2))
    print(f"wrote /output/iter149_carousel_bp.json")
    return 0 if result.get("polling_caught") else 1


if __name__ == "__main__":
    sys.exit(main())
