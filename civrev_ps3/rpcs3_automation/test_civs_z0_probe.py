#!/usr/bin/env python3
"""iter-202: Z0 code breakpoint at the civs BL site 0xa2ee80.

iter-201 established that RPCS3's GDB stub rejects Z2/Z3/Z4 data
watchpoints. Z0 software breakpoints should still work.

This probe sets a Z0 on 0xa2ee80 (the `bl 0xa2e640` just after
`lwz r4, 0x141c(r2)` in the parser dispatcher at FUN_00a2ec54).
It's the second name-file parser call (civs, count=0x11=17 stock
or 0x12=18 with iter-14 patch).

When the breakpoint fires:
  - Read r2 (GPR2) — the runtime TOC base at this call
  - Read r4 (GPR4) — the actual value being passed as param_2
    to the parser worker. Compare against the ELF file value at
    (r2 + 0x141c) to see if they match.
  - Read r3 (the FStringA path ptr), r5 (count)

If r4 is in .bss/.data (writable), that's the real civs buffer
holder and the parser path works. If r4 is in rodata (like the
static 0x1695660), something else is going on.

The breakpoint must be set BEFORE the dispatcher runs — i.e.,
before boot completes. Set Z0 early (before RSX init completes)
and then poll for hits. Boot-time parser calls happen very early,
so we'll connect to the GDB stub within the first few seconds.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import launch as L  # noqa: E402
from config import RPCS3_BIN, RPCS3_BOOT_TIMEOUT  # noqa: E402
from gdb_client import GDBClient  # noqa: E402


# Rulers BL, civs BL, and the dispatcher entry (for early Z0).
RULERS_BL = 0xa2ee3c
CIVS_BL = 0xa2ee80
DISPATCHER_ENTRY = 0xa2ec54


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
        "iteration": "iter-202",
        "rulers_bl": hex(RULERS_BL),
        "civs_bl": hex(CIVS_BL),
        "dispatcher_entry": hex(DISPATCHER_ENTRY),
        "z0_rulers_ok": False,
        "z0_civs_ok": False,
        "z0_dispatcher_ok": False,
        "hits": [],
        "error": None,
    }

    try:
        time.sleep(2)
        if not L._is_rpcs3_alive(rpcs3):
            print("RPCS3 failed to start")
            return 2

        # Poll the GDB stub every 0.5s looking for it to come up.
        # Once available, pause and set all three Z0 breakpoints BEFORE
        # the parser runs.
        print("Waiting for GDB stub to accept connections...")
        connected = False
        t0 = time.time()
        while time.time() - t0 < 30:
            try:
                with GDBClient("127.0.0.1", 2345, timeout=2) as gdb:
                    gdb.pause()
                    time.sleep(0.2)
                    print("  Stub connected, installing Z0s...")
                    r = gdb.set_breakpoint(DISPATCHER_ENTRY)
                    result["z0_dispatcher_ok"] = r
                    print(f"  Z0 @ {DISPATCHER_ENTRY:#x} (dispatcher entry): {'OK' if r else 'FAIL'}")
                    r = gdb.set_breakpoint(RULERS_BL)
                    result["z0_rulers_ok"] = r
                    print(f"  Z0 @ {RULERS_BL:#x} (rulers BL): {'OK' if r else 'FAIL'}")
                    r = gdb.set_breakpoint(CIVS_BL)
                    result["z0_civs_ok"] = r
                    print(f"  Z0 @ {CIVS_BL:#x} (civs BL): {'OK' if r else 'FAIL'}")
                    gdb.resume()
                    connected = True
                    break
            except Exception as e:
                print(f"  attempt: {e}")
                time.sleep(0.5)
        if not connected:
            result["error"] = "GDB stub never accepted connection"
            return 3

        # Wait for main menu — during boot the dispatcher will run and
        # hit our breakpoints. Poll every 1s for hits.
        print("Polling for Z0 hits during boot...")
        for poll in range(60):
            time.sleep(1)
            try:
                with GDBClient("127.0.0.1", 2345, timeout=3) as gdb:
                    gdb.pause()
                    time.sleep(0.1)
                    threads = gdb.inspect_all_threads()
                    for t in threads:
                        tid = t.get("tid", "?")
                        pc = t.get("pc", 0)
                        lr = t.get("lr", 0)
                        if pc in (DISPATCHER_ENTRY, RULERS_BL, CIVS_BL):
                            # Hit! Capture GPRs
                            gdb.select_thread(tid)
                            r2 = gdb.read_register(2)
                            r3 = gdb.read_register(3)
                            r4 = gdb.read_register(4)
                            r5 = gdb.read_register(5)
                            # Follow r4 if it's non-zero
                            deref_r4 = gdb.read_u32(r4) if r4 else 0
                            # Also read the buffer at *r4 if non-NULL
                            deref_r4_plus = None
                            if deref_r4:
                                db = gdb.read_memory(deref_r4, 16)
                                deref_r4_plus = db.hex()
                            hit = {
                                "poll": poll,
                                "tid": tid,
                                "pc": hex(pc),
                                "lr": hex(lr),
                                "r2": hex(r2),
                                "r3": hex(r3),
                                "r4": hex(r4),
                                "r5": hex(r5),
                                "deref_r4": hex(deref_r4),
                                "deref_r4_bytes": deref_r4_plus,
                            }
                            result["hits"].append(hit)
                            name = {
                                DISPATCHER_ENTRY: "DISPATCHER_ENTRY",
                                RULERS_BL: "RULERS_BL",
                                CIVS_BL: "CIVS_BL",
                            }[pc]
                            print(f"  ★ HIT {name} poll={poll} tid={tid}")
                            print(f"      r2={r2:#x}  r3={r3:#x}  r4={r4:#x}  r5={r5:#x}")
                            print(f"      *r4={deref_r4:#x}  bytes[16]={deref_r4_plus}")
                            # Clear and continue past
                            gdb.clear_breakpoint(pc)
                    gdb.resume()
            except Exception as e:
                print(f"  poll {poll}: {e}")

    except Exception as e:
        print(f"exception: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
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
    out = Path("/output/iter202_civs_z0_result.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}")
    return 0 if result.get("hits") else 1


if __name__ == "__main__":
    sys.exit(main())
