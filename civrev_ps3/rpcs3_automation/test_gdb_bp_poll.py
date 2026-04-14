#!/usr/bin/env python3
"""iter-113: Poll-based Z0 verification.

iter-112 confirmed the RPCS3 GDB stub accepts Z0 packets but
doesn't send stop-reply T-packets on pause, so
continue_until_stop() can't block until a breakpoint fires. This
test drives a poll-based loop instead:

  1. Boot to main menu.
  2. Attach GDB, pause, read main_thread PC.
  3. Set Z0 at the name-file dispatcher entry (0xa21ce8) and at
     a known-idle PC from the smoke test (as a sanity check
     address that should get re-executed).
  4. Resume.
  5. Drive main-menu -> scenario -> civ-select -> confirm inputs
     so the dispatcher runs.
  6. Poll every 300ms: pause, read PC of each thread, resume.
  7. Record whether the dispatcher PC was ever observed as the
     current PC of any thread.

If we see the dispatcher PC in a poll sample, Z0 actually breaks
execution (the thread was halted at the breakpoint). If we never
see it, Z0 is a no-op / ignored by the JIT.
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
# A few addresses near dispatcher body in case JIT basic-block
# boundaries put the actual halt PC slightly offset.
BP_TARGETS = [
    DISPATCHER_ENTRY,
    DISPATCHER_ENTRY + 4,
    DISPATCHER_ENTRY + 8,
    0x00a216d4,  # parser worker entry
]


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
        "milestone": "iter-113-bp-poll",
        "pass": False,
        "oracle": (
            "set Z0 at dispatcher, drive civ-confirm, poll PC of all "
            "threads every 300ms for up to 40s — success means the "
            "dispatcher PC was observed at least once"
        ),
        "stages": {"drove_to_civ_select": False, "gdb_attach": False,
                   "bp_set": False, "dispatcher_observed": False},
        "bp_targets": [hex(a) for a in BP_TARGETS],
        "pc_samples": [],
    }

    try:
        time.sleep(2)
        if not L._wait_for_rsx(
            rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time
        ):
            raise RuntimeError("RSX did not come up")
        L._navigate_startup_to_main_menu(rpcs3)
        _press("Down", 0.5)
        _press("X", 3)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("X", 3)
        for a in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                break
            _press("Down", 0.4)
        _press("X", 3)
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 5)
        for _ in range(20):
            _press("Left", 0.25)
        time.sleep(0.5)
        print(f"[{int(time.time()-launch_time)}s] parked at civ-select")
        result["stages"]["drove_to_civ_select"] = True

        gdb = GDBClient("127.0.0.1", 2345, timeout=5)
        gdb.connect()
        result["stages"]["gdb_attach"] = True

        gdb.pause()
        time.sleep(0.2)

        set_any = False
        for target in BP_TARGETS:
            ok = gdb.set_breakpoint(target, kind=4)
            print(f"  Z0 at 0x{target:x}: {ok}")
            if ok:
                set_any = True
        result["stages"]["bp_set"] = set_any
        if not set_any:
            raise RuntimeError("no Z0 accepted")

        gdb.resume()
        time.sleep(0.3)

        # Drive civ-confirm.
        _press("Return", 0.2)

        # Poll loop. Every 300ms, pause + read every thread's PC +
        # resume. Stop as soon as we observe a BP_TARGETS PC.
        start = time.time()
        poll_budget_s = 40
        hit_sample = None
        while time.time() - start < poll_budget_s:
            time.sleep(0.3)
            try:
                gdb.pause()
                time.sleep(0.1)
                threads = gdb.get_thread_list()
                sample = {"t": round(time.time() - start, 2), "threads": []}
                for tid in threads:
                    gdb.select_thread(tid)
                    pc = gdb.get_pc()
                    sample["threads"].append({"tid": tid, "pc": hex(pc)})
                    if pc in BP_TARGETS:
                        hit_sample = sample
                result["pc_samples"].append(sample)
                gdb.resume()
                time.sleep(0.05)
                if hit_sample is not None:
                    break
            except Exception as e:
                result["pc_samples"].append({"error": str(e)[:120]})
                try:
                    gdb.resume()
                except Exception:
                    pass

        if hit_sample:
            result["stages"]["dispatcher_observed"] = True
            result["hit_sample"] = hit_sample
            print(f"HIT: dispatcher PC observed at t={hit_sample['t']}s")
        else:
            print(f"NO HIT in {poll_budget_s}s of polling")

        # Cleanup
        for target in BP_TARGETS:
            gdb.clear_breakpoint(target, kind=4)
        gdb.close()

        result["pass"] = result["stages"]["dispatcher_observed"]
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
    out = Path("/output/gdb_bp_poll.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}; pass={result['pass']}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
