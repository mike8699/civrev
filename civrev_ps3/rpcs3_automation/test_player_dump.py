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
# 0x1870000..0x1bd5f38; the known name-file holders cluster at 0x1ac93xx.
# Scan a generous window around there for heap pointers.
BSS_SCAN_LO = 0x01ab0000
BSS_SCAN_HI = 0x01ae0000
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


def scan_bss(gdb):
    """Return list of (bss_addr, heap_ptr, peek_hex) for heap pointers in .bss."""
    hits = []
    addr = BSS_SCAN_LO
    while addr < BSS_SCAN_HI:
        chunk = gdb.read_memory(addr, 0x400)
        if chunk:
            for i in range(0, len(chunk) - 3, 4):
                v = int.from_bytes(chunk[i:i + 4], "big")
                if HEAP_LO <= v < HEAP_HI:
                    peek = gdb.read_memory(v, 32) or b""
                    hits.append({
                        "bss": hex(addr + i),
                        "ptr": hex(v),
                        "peek": peek.hex(),
                    })
        addr += 0x400
    return hits


GAME_OBJ_HOLDER = 0x01ac1678  # .bss -> game session object (vtable 0x18a2738)


def _mask_ptrs(buf):
    """Zero out 4-byte words that look like heap/EBOOT pointers so a China-vs-
    Rome diff isolates real data (tech bitfields, civ index, stats) and ignores
    per-run allocation addresses."""
    out = bytearray(buf)
    for i in range(0, len(out) - 3, 4):
        v = int.from_bytes(out[i:i + 4], "big")
        if HEAP_LO <= v < HEAP_HI or 0x10000 <= v < 0x1c00000:
            out[i:i + 4] = b"\x00\x00\x00\x00"
    return bytes(out)


def deep_dump_game_obj(gdb):
    """Read the game session object + follow its heap-pointer members one level.
    Returns {obj_ptr, self (masked hex), members:[{off, ptr, data masked hex}]}.
    Pointers are masked so the dump is diff-able across runs."""
    obj = gdb.read_u32(GAME_OBJ_HOLDER)
    res = {"holder": hex(GAME_OBJ_HOLDER), "obj_ptr": hex(obj),
           "self": "", "members": []}
    if not (HEAP_LO <= obj < HEAP_HI):
        return res
    raw = gdb.read_memory(obj, 0x1000) or b""
    res["self"] = _mask_ptrs(raw).hex()
    # follow each heap-pointer member one level
    seen = set()
    for i in range(0, len(raw) - 3, 4):
        v = int.from_bytes(raw[i:i + 4], "big")
        if HEAP_LO <= v < HEAP_HI and v not in seen:
            seen.add(v)
            sub = gdb.read_memory(v, 0x400) or b""
            res["members"].append({"off": hex(i), "ptr": hex(v),
                                   "data": _mask_ptrs(sub).hex()})
            if len(res["members"]) > 64:
                break
    return res


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
            print(f"found {len(hits)} heap pointers in .bss window "
                  f"{BSS_SCAN_LO:#x}..{BSS_SCAN_HI:#x}")
            result["game_obj"] = deep_dump_game_obj(gdb)
            print(f"deep-dumped game obj {result['game_obj']['obj_ptr']} "
                  f"with {len(result['game_obj']['members'])} heap members")
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
