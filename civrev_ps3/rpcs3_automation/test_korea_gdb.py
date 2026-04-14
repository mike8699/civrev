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
        # Sample the PC multiple times to distinguish a true hang (same PC
        # across samples) from a slow but progressing boot.
        samples = []
        for i, delay in enumerate([30, 60, 120, 180, 240]):
            while time.time() - launch_time < delay:
                time.sleep(1)
            print(f"[+{delay}s] Attempting GDB attach ...")
            try:
                from gdb_client import GDBClient
                with GDBClient("127.0.0.1", 2345, timeout=10) as gdb:
                    gdb.pause()
                    time.sleep(0.5)
                    threads = gdb.inspect_all_threads()
                    sample = {"t": delay, "threads": threads}
                    samples.append(sample)
                    print(f"  got {len(threads)} threads; pc[0]={threads[0].get('pc','?') if threads else '?'}")
                    gdb.resume()
            except Exception as e:
                print(f"  GDB attach #{i} failed: {e}")
                samples.append({"t": delay, "error": str(e)})
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
