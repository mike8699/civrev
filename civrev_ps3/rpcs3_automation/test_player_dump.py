#!/usr/bin/env python3
"""path-b iter-6: runtime .bss scan to find the game/player-state globals.

The civ-bonus EFFECT (granting a starting tech) has no static string/data
anchor (iter-1..5). Pivot to runtime: at in-game, the game object + player
array are heap-allocated and pointed at by .bss globals (like the known
civs-buffer holder 0x1ac93b8). This boots a game as a chosen civ, attaches
the rpcs3 gdb stub, scans a .bss window for heap pointers (0x4xxxxxxx), and
dumps each with a peek at what it points to — the lay of the land for finding
player[i].techs. Run twice (China vs Rome) and diff the dumps offline to find
the per-civ tech state.

Usage: test_player_dump.py [slot] [label]   (default slot 6 = China)
Writes /output/player_dump_<label>.json.
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

# .bss window to scan for game-state heap pointers. seg1 (RW) is
# 0x1870000..0x1bd5f38. iter-7: the narrow 0x1ab0000..0x1ae0000 window held
# only charset/widget/entity objects, not the game session / player array, so
# scan the full .bss range. (~2.3MB; slower but one-time per run.)
BSS_SCAN_LO = 0x01990000
BSS_SCAN_HI = 0x01bd0000
CIVS_BUF_HOLDER = 0x01ac93b8
HEAP_LO, HEAP_HI = 0x40000000, 0x50000000


def _press(b, d=0.5):
    L._send_ps3_button(b)
    time.sleep(d)


def navigate_in_game(rpcs3, slot):
    """Reuse the test_korea_play flow to reach the in-game HUD."""
    L._navigate_startup_to_main_menu(rpcs3)
    _press("Down", 0.5); _press("X", 3)           # Single Player
    _press("X", 3)                                 # New Game
    _press("X", 3)                                 # map/earth
    for _ in range(4):
        _press("Down", 0.3)
    _press("X", 5)                                 # Deity
    for _ in range(20):
        _press("Left", 0.2)                        # normalize to Romans
    for _ in range(slot):
        _press("Right", 0.3)                       # to target civ
    _press("X", 15)                                # confirm
    for _ in range(4):
        _press("X", 3)                             # intro cutscene
    # wait for HUD
    for _ in range(12):
        time.sleep(5)
        t = L._ocr_screen()
        if any(k in t for k in ("Turn", "Gold", "Found City", "Settlers", "BC")):
            return True
    return False


def _mask(buf):
    """Zero 4-byte words that look like heap/EBOOT pointers so China-vs-Rome
    diffs isolate real data (civ index, tech bitfield, stats) not addresses."""
    out = bytearray(buf)
    for i in range(0, len(out) - 3, 4):
        v = int.from_bytes(out[i:i + 4], "big")
        if HEAP_LO <= v < HEAP_HI or 0x10000 <= v < 0x1c00000:
            out[i:i + 4] = b"\x00\x00\x00\x00"
    return bytes(out)


def scan_bss(gdb):
    """Scan the .bss range for heap-pointer globals; for each UNIQUE global,
    deep-dump 0x400 bytes of the pointed object with pointers masked, so the
    full set is diff-able China-vs-Rome to localize per-civ state."""
    seen = {}
    addr = BSS_SCAN_LO
    while addr < BSS_SCAN_HI:
        chunk = gdb.read_memory(addr, 0x400)
        if chunk:
            for i in range(0, len(chunk) - 3, 4):
                v = int.from_bytes(chunk[i:i + 4], "big")
                if HEAP_LO <= v < HEAP_HI:
                    bss = addr + i
                    if bss not in seen:
                        obj = gdb.read_memory(v, 0x400) or b""
                        seen[bss] = {"bss": hex(bss), "ptr": hex(v),
                                     "dump": _mask(obj).hex()}
        addr += 0x400
    return list(seen.values())


def main():
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    label = sys.argv[2] if len(sys.argv) > 2 else "china"
    game_path = L._find_game_path()
    launch_time = time.time()
    print(f"Launching RPCS3 ({game_path}) for slot {slot} ({label})")
    rpcs3 = subprocess.Popen([str(RPCS3_BIN), str(game_path)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = {"slot": slot, "label": label, "in_game": False, "bss_hits": []}
    try:
        time.sleep(2)
        if not L._wait_for_rsx(rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time):
            print("RSX did not come up"); return 3
        in_game = navigate_in_game(rpcs3, slot)
        result["in_game"] = in_game
        print(f"in_game={in_game}; attaching gdb")
        with GDBClient() as gdb:
            gdb.pause()
            civs_ptr = gdb.read_u32(CIVS_BUF_HOLDER)
            result["civs_buf_ptr"] = hex(civs_ptr)
            print(f"civs buffer ptr = {civs_ptr:#x} (orientation)")
            hits = scan_bss(gdb)
            result["bss_hits"] = hits
            print(f"deep-dumped {len(hits)} unique game-state .bss globals in "
                  f"{BSS_SCAN_LO:#x}..{BSS_SCAN_HI:#x}")
            gdb.resume()
    except Exception as e:
        import traceback; traceback.print_exc()
        result["exception"] = str(e)
    finally:
        try:
            rpcs3.terminate(); rpcs3.wait(timeout=5)
        except Exception:
            try: rpcs3.kill()
            except Exception: pass
    out = Path(f"/output/player_dump_{label}.json")
    out.write_text(json.dumps(result, indent=2))
    print(f"wrote {out}; in_game={result['in_game']} hits={len(result['bss_hits'])}")
    return 0 if result["in_game"] else 1


if __name__ == "__main__":
    sys.exit(main())
