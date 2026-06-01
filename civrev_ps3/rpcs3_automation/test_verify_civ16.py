#!/usr/bin/env python3
"""path-b verify: confirm Korea boots as civ 16 (not China civ 6).

Boots a game selecting slot 16 (Korea), reaches in-game, attaches the rpcs3
gdb stub, and reads the TeamMap[player] array (player->civ index). If any
player has civ 16, the iter-1188 remap removal worked and Korea is a real 17th
civ. Also reads the _lbonus base pointer to confirm the relocation took.

TeamMap base = 0x1b07fa0 (.bss; TOC slot 0x194af24 under module TOC 0x194a1f8).
_lbonus TOC slot = 0x194af5c (should now hold 0x17f4100, the relocated table).
"""
from __future__ import annotations
import json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import launch as L
from config import RPCS3_BIN, RPCS3_BOOT_TIMEOUT
from gdb_client import GDBClient

TEAMMAP_BASE = 0x1b07fa0
LBONUS_TOC_SLOT = 0x194af5c


def _press(b, d=0.5):
    L._send_ps3_button(b); time.sleep(d)


def navigate(rpcs3, slot):
    L._navigate_startup_to_main_menu(rpcs3)
    _press("Down", 0.5); _press("X", 3)
    _press("X", 3); _press("X", 3)
    for _ in range(4): _press("Down", 0.3)
    _press("X", 5)
    for _ in range(20): _press("Left", 0.2)
    for _ in range(slot): _press("Right", 0.3)
    _press("X", 15)
    for _ in range(4): _press("X", 3)
    for _ in range(12):
        time.sleep(5)
        if any(k in L._ocr_screen() for k in ("Turn","Gold","Found City","Settlers","BC")):
            return True
    return False


def main():
    slot = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    game = L._find_game_path()
    t0 = time.time()
    rpcs3 = subprocess.Popen([str(RPCS3_BIN), str(game)],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    res = {"slot": slot, "in_game": False, "teammap": [], "civ16_found": False}
    try:
        time.sleep(2)
        if not L._wait_for_rsx(rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=t0):
            return 3
        res["in_game"] = navigate(rpcs3, slot)
        with GDBClient() as gdb:
            gdb.pause()
            tm = [gdb.read_u32(TEAMMAP_BASE + p*4) for p in range(16)]
            res["teammap"] = tm
            res["civ16_found"] = 16 in tm
            res["lbonus_ptr"] = hex(gdb.read_u32(LBONUS_TOC_SLOT))
            print("TeamMap[0..15] =", tm)
            print("civ 16 present:", res["civ16_found"], " (player index:",
                  tm.index(16) if 16 in tm else None, ")")
            print("_lbonus TOC slot ->", res["lbonus_ptr"], "(want 0x17f4100 = relocated)")
            gdb.resume()
    except Exception as e:
        import traceback; traceback.print_exc(); res["exception"] = str(e)
    finally:
        try: rpcs3.terminate(); rpcs3.wait(timeout=5)
        except Exception:
            try: rpcs3.kill()
            except Exception: pass
    Path("/output/verify_civ16.json").write_text(json.dumps(res, indent=2))
    print("wrote /output/verify_civ16.json")
    return 0 if res.get("civ16_found") else 1


if __name__ == "__main__":
    sys.exit(main())
