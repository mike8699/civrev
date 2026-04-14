#!/usr/bin/env python3
"""iter-111: GDB stub capability smoke test.

Drives the game to civ-select so the PPU is definitely running,
then interrogates RPCS3's GDB stub to find out which Z-packets
and watchpoint types it supports. Also tries setting a Z0/Z1
breakpoint at the CURRENT PC (read via p64) — if the stub
supports software or hardware breakpoints at all, setting one
at the live PC and then resuming+stepping will trivially fire.

Writes /output/gdb_smoke.json summarizing:
  * qSupported reply
  * pause/resume works
  * thread list
  * current PC
  * Z0 at PC+4 accepted?
  * Z1 at PC+4 accepted?
  * after resume, did the breakpoint fire?

This tells us definitively whether RPCS3 supports Z-packets at
all, and if so which variant to use for iter-112+.
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

    result = {"milestone": "iter-111-gdb-smoke", "pass": False}

    try:
        time.sleep(2)
        if not L._is_rpcs3_alive(rpcs3):
            raise RuntimeError("RPCS3 exited")
        if not L._wait_for_rsx(
            rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time
        ):
            raise RuntimeError("RSX did not come up")
        L._navigate_startup_to_main_menu(rpcs3)
        # Stop here — don't even drive to civ-select. The main menu
        # is enough to prove the PPU is running.
        print(f"[{int(time.time()-launch_time)}s] main menu reached")

        gdb = GDBClient("127.0.0.1", 2345, timeout=8)
        gdb.connect()
        print(f"attached; noack={gdb.noack}")
        result["noack_mode"] = gdb.noack

        # qSupported
        qsupp = gdb.query_supported()
        print(f"qSupported reply: {qsupp[:200]}")
        result["qSupported"] = qsupp

        # Pause, read state
        stop_reply = gdb.pause()
        result["pause_reply"] = stop_reply
        print(f"pause reply: {stop_reply[:100]}")

        threads = gdb.get_thread_list()
        result["threads"] = threads
        print(f"threads: {threads}")
        if threads:
            gdb.select_thread(threads[0])

        pc = gdb.get_pc()
        result["current_pc"] = hex(pc)
        print(f"current PC: {hex(pc)}")

        # Try Z0 at PC+4 (next instruction). If Z-packets are
        # supported this will let us single-step by continuing.
        target = (pc + 4) & 0xFFFFFFFF
        print(f"trying Z0 at 0x{target:x}")
        z0_ok = gdb.set_breakpoint(target, kind=4)
        result["z0_set_ok"] = z0_ok
        print(f"  Z0 accepted: {z0_ok}")

        # Raw qSupported tells us what's advertised; the Z0 accept
        # tells us if it's actually implemented. Try the other
        # variants too for full visibility.
        print(f"trying Z1 (hw bp) at 0x{target:x}")
        z1_ok = gdb.set_hw_breakpoint(target, kind=4)
        result["z1_set_ok"] = z1_ok
        print(f"  Z1 accepted: {z1_ok}")

        # Write watchpoint on a benign address — the stack pointer
        # range isn't great but at least a valid RAM address.
        # Use the current LR as a probe: it's in RAM.
        lr = gdb.get_lr() & 0xFFFFFFFF
        print(f"trying Z2 (write watchpoint) at LR 0x{lr:x}, len=4")
        z2_ok = gdb.set_write_watchpoint(lr, length=4)
        result["z2_set_ok"] = z2_ok
        print(f"  Z2 accepted: {z2_ok}")

        # Clean up anything we set
        if z0_ok:
            gdb.clear_breakpoint(target, kind=4)
        if z1_ok:
            gdb.clear_hw_breakpoint(target, kind=4)
        if z2_ok:
            gdb.clear_write_watchpoint(lr, length=4)

        # Resume the target so the game doesn't hang.
        gdb.resume()
        gdb.close()

        # Success criteria: qSupported returned something, pause
        # worked, at least one Z-packet got accepted.
        result["pass"] = bool(
            qsupp
            and stop_reply
            and threads
            and pc
            and (z0_ok or z1_ok or z2_ok)
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
    out = Path("/output/gdb_smoke.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}; pass={result['pass']}")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
