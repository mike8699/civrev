#!/usr/bin/env python3
"""iter-108: Z-packet breakpoint infrastructure smoke test.

Boots RPCS3 with the CURRENT v0.9 Pregame (known-good 17-entry
state) and exercises the iter-105 Z-packet helpers by:

  1. Attaching the GDB stub at 127.0.0.1:2345.
  2. Setting a Z0 (software breakpoint) at the name-file init
     dispatcher entry 0x00a21ce8 — called once during game boot,
     so the breakpoint should fire exactly once.
  3. Resuming and waiting for the hit via continue_until_stop().
  4. Reading r3 (this pointer / iStack_84) and the 8 name-file
     param struct pointers at *(r3 + 0xcc0..0xcdc).
  5. Writing the results as JSON to /output/korea_bp_probe.json.

Success criteria:
  * stages.gdb_attach is True
  * stages.bp_set is True
  * stages.bp_hit is True
  * stages.registers_read is True
  * result_json has the 8 name-file pointer values

If all four stages are green, the iter-105 Z-packet path works
end-to-end and iter-109 can use it to set a breakpoint at the
real fault site 0xc26a98 against a broken 18-entry Pregame.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import launch as L  # noqa: E402
from config import RPCS3_BIN  # noqa: E402
from gdb_client import GDBClient  # noqa: E402


DISPATCHER_ENTRY = 0x00a21ce8


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
        "milestone": "iter-108-bp-probe",
        "pass": False,
        "oracle": (
            f"set Z0 at 0x{DISPATCHER_ENTRY:x}, resume, confirm the "
            "breakpoint fires once and r3 points at the name-file "
            "manager state struct"
        ),
        "stages": {
            "rpcs3_launched": True,
            "gdb_attach": False,
            "bp_set": False,
            "bp_hit": False,
            "registers_read": False,
        },
        "hit": None,
    }

    try:
        # Wait for RPCS3 to boot the PPU enough that the GDB stub
        # is accepting connections.
        for attempt in range(30):
            time.sleep(1)
            try:
                gdb = GDBClient("127.0.0.1", 2345, timeout=5)
                gdb.connect()
                break
            except OSError:
                if attempt == 29:
                    raise
                continue
        else:
            raise RuntimeError("gdb stub never came up")
        print(f"[{int(time.time()-launch_time)}s] attached GDB stub")
        result["stages"]["gdb_attach"] = True

        # Pause the target. The stub may need a moment after first
        # connection to return control.
        gdb.pause()
        time.sleep(0.2)

        # Set the breakpoint at the dispatcher entry.
        if not gdb.set_breakpoint(DISPATCHER_ENTRY, kind=4):
            raise RuntimeError("set_breakpoint returned False")
        print(f"set Z0 at 0x{DISPATCHER_ENTRY:x}")
        result["stages"]["bp_set"] = True

        # Continue the target and wait for the hit.
        print("continuing until breakpoint hits...")
        stop = gdb.continue_until_stop(timeout=60)
        result["hit"] = stop
        print(f"stop reply: {stop}")
        if stop.get("reason") in ("swbreak", "hwbreak"):
            result["stages"]["bp_hit"] = True

        # Read registers at the hit.
        threads = gdb.inspect_all_threads()
        regs = {}
        if threads:
            gdb.select_thread(threads[0]["tid"])
            # r3..r12 (PPC calling convention first 10 GPRs)
            for rn in range(3, 13):
                regs[f"r{rn}"] = gdb.read_register(rn)
            regs["pc"] = gdb.get_pc()
            regs["lr"] = gdb.get_lr()
        result["regs"] = regs
        if regs:
            result["stages"]["registers_read"] = True

        # If we have r3, dump *(r3 + 0xcc0..0xcdc) — the 8 name-file
        # param struct pointers the iter-106 decompile identified.
        if regs.get("r3"):
            r3 = regs["r3"] & 0xFFFFFFFF
            param_ptrs = {}
            for off in range(0xcc0, 0xce0, 4):
                val = gdb.read_u32(r3 + off)
                param_ptrs[f"+0x{off:03x}"] = hex(val)
            result["name_file_param_ptrs"] = param_ptrs

        # Clear the breakpoint before leaving.
        gdb.clear_breakpoint(DISPATCHER_ENTRY, kind=4)
        gdb.close()

        # Overall pass: all 4 stages true.
        result["pass"] = all(
            result["stages"][k] for k in
            ("gdb_attach", "bp_set", "bp_hit", "registers_read")
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
