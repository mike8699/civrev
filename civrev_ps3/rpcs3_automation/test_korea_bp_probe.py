#!/usr/bin/env python3
"""iter-108/109: Z-packet breakpoint infrastructure smoke test.

Drives the game through Main Menu -> Single Player -> Earth ->
Difficulty -> civ-select (no confirm yet), then attaches GDB,
sets a Z0 breakpoint at the name-file init dispatcher entry
(0x00a21ce8), then sends the civ-confirm X press and waits for
the breakpoint hit.

FUN_0002fb78 (the scenario init that calls the dispatcher via the
TOC stub at 0x10ef0) only runs AFTER civ confirmation — setting
the breakpoint at boot won't fire. This test parks the game at
civ-select, arms the breakpoint, then triggers the init.
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


DISPATCHER_ENTRY = 0x00a21ce8


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
        "milestone": "iter-109-bp-probe",
        "pass": False,
        "oracle": (
            f"drive game to civ-select, set Z0 at 0x{DISPATCHER_ENTRY:x}, "
            "confirm civ, wait for dispatcher breakpoint to fire"
        ),
        "stages": {
            "rpcs3_launched": True,
            "drove_to_civ_select": False,
            "gdb_attach": False,
            "bp_set": False,
            "bp_hit": False,
            "registers_read": False,
        },
        "hit": None,
    }

    try:
        time.sleep(2)
        if not L._is_rpcs3_alive(rpcs3):
            raise RuntimeError("RPCS3 exited")
        print("Waiting for RSX...")
        if not L._wait_for_rsx(
            rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time
        ):
            raise RuntimeError("RSX did not come up")

        # Drive through menu to civ-select (same sequence as
        # test_korea_play.py), but stop BEFORE the confirm press.
        L._navigate_startup_to_main_menu(rpcs3)
        _press("Down", 0.5)  # SP
        _press("X", 3)
        _press("Down", 0.5)  # Play Scenario (3 downs)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("X", 3)
        # Scroll to Earth
        for a in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                break
            _press("Down", 0.4)
        _press("X", 3)
        # Difficulty: 4 Down + X for Deity
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 5)
        # Normalize to leftmost (Romans)
        for _ in range(20):
            _press("Left", 0.25)
        time.sleep(0.5)
        print(f"[{int(time.time()-launch_time)}s] parked at civ-select")
        result["stages"]["drove_to_civ_select"] = True

        gdb = GDBClient("127.0.0.1", 2345, timeout=5)
        gdb.connect()
        print(f"[{int(time.time()-launch_time)}s] attached GDB stub")
        result["stages"]["gdb_attach"] = True

        # Pause the target.
        gdb.pause()
        time.sleep(0.3)

        # Set the breakpoint at the dispatcher entry.
        if not gdb.set_breakpoint(DISPATCHER_ENTRY, kind=4):
            raise RuntimeError("set_breakpoint returned False")
        print(f"set Z0 at 0x{DISPATCHER_ENTRY:x}")
        result["stages"]["bp_set"] = True

        # Resume and drive the civ-confirm press. Manually send 'c'
        # then drive input and wait for the stop reply — can't use
        # continue_until_stop() because it blocks before the input
        # can go out.
        checksum = sum(ord(c) for c in "c") & 0xFF
        gdb._send_raw(f"$c#{checksum:02x}".encode())
        time.sleep(0.3)
        print("sending civ-confirm press")
        _press("Return", 0.1)  # X = confirm

        print("waiting for breakpoint hit (up to 60s)...")
        try:
            payload = gdb._recv_packet(timeout=60)
        except Exception as e:
            raise TimeoutError(f"recv error after civ-confirm: {e}")
        if not payload:
            raise TimeoutError("empty stop reply")
        stop = gdb._parse_stop_reply(payload)
        result["hit"] = stop
        print(f"stop reply: {stop}")
        if stop.get("reason") in ("swbreak", "hwbreak"):
            result["stages"]["bp_hit"] = True

        # Read registers at the hit.
        threads = gdb.inspect_all_threads()
        regs = {}
        if threads:
            # Pick the thread whose PC is near the dispatcher
            # — if the stop reply gave us a specific thread, use it,
            # otherwise use thread 0.
            gdb.select_thread(threads[0]["tid"])
            for rn in range(3, 13):
                regs[f"r{rn}"] = hex(gdb.read_register(rn))
            regs["pc"] = hex(gdb.get_pc())
            regs["lr"] = hex(gdb.get_lr())
        result["regs"] = regs
        if regs:
            result["stages"]["registers_read"] = True

        # Dump iStack_84 + 0xcc0..0xcdc equivalents via the function
        # body: the dispatcher loads iStack_84 from some TOC slot.
        # For this smoke test we just prove we can read a few words
        # at the dispatcher's likely 'this' pointer.
        if regs.get("r3"):
            r3 = int(regs["r3"], 16) & 0xFFFFFFFF
            name_file_ptrs = {}
            for off in range(0xcc0, 0xce0, 4):
                try:
                    val = gdb.read_u32(r3 + off)
                except Exception:
                    val = 0
                name_file_ptrs[f"+0x{off:03x}"] = hex(val)
            result["name_file_param_ptrs"] = name_file_ptrs

        gdb.clear_breakpoint(DISPATCHER_ENTRY, kind=4)
        gdb.close()

        result["pass"] = all(
            result["stages"][k]
            for k in (
                "drove_to_civ_select",
                "gdb_attach",
                "bp_set",
                "bp_hit",
                "registers_read",
            )
        )
    except Exception as e:
        import traceback
        result["exception"] = str(e)
        result["traceback"] = traceback.format_exc()
        print(f"EXCEPTION: {e}")
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
    out = Path("/output/korea_bp_probe.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}; pass={result['pass']}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
