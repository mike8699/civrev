#!/usr/bin/env python3
"""Boot RPCS3 with the broken 18-entry Pregame, wait for crash/hang,
then attach GDB and dump all thread PCs to find the crash site.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import launch as L
from config import RPCS3_BIN


def main():
    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 with {game_path}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    result = {"stages": {}, "threads": []}

    try:
        # Dense sampling every 2 seconds from 20s to 80s. Catches the
        # exact second when a hanging boot's PPU thread dies.
        from gdb_client import GDBClient
        samples = []
        for delay in range(20, 82, 2):
            while time.time() - launch_time < delay:
                time.sleep(0.5)
            try:
                with GDBClient("127.0.0.1", 2345, timeout=8) as gdb:
                    gdb.pause()
                    time.sleep(0.3)
                    threads = gdb.inspect_all_threads()
                    row = {"t": delay, "n_threads": len(threads)}
                    if threads:
                        t0 = threads[0]
                        row["pc0"] = hex(t0.get("pc", 0))
                        row["lr0"] = hex(t0.get("lr", 0))
                    samples.append(row)
                    print(f"[+{delay}s] n_thr={row['n_threads']} pc={row.get('pc0','?')} lr={row.get('lr0','?')}")
                    gdb.resume()
            except Exception as e:
                samples.append({"t": delay, "error": str(e)[:80]})
                # Failed attach = RPCS3 likely dead; stop sampling
                if "timed out" in str(e).lower() or "refused" in str(e).lower():
                    print(f"[+{delay}s] GDB failed ({e}); stopping sampling")
                    break
        result["samples"] = samples
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
    out = Path("/output/korea_gdb_dump.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
