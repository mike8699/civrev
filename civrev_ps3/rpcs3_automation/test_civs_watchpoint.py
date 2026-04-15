#!/usr/bin/env python3
"""iter-201: catch the civ-select carousel render path via a GDB
read/access watchpoint on the civnames buffer.

Static search is exhausted — iter-196..200 proved that every known
static consumer of the civs name-file buffer pointer TOC slot
(r2+0x141c = 0x193b6a4) is NOT the carousel. The carousel must read
from the buffer via a cached pointer that's stored in a class field
somewhere, OR via indirect dispatch Ghidra can't resolve.

This probe:
  1. Launches RPCS3 with the iter-198 build (18-row civnames +
     Korea at index 16 in the dynamically-allocated parser buffer).
  2. Waits for main menu, which confirms the parser has completed
     and `*(0x193b6a4)` holds the runtime buffer base.
  3. Attaches the GDB stub, pauses, reads the buffer pointer from
     the TOC slot.
  4. Tries to install an access watchpoint (Z4) on the first few
     bytes of the buffer itself — specifically at
     `(buf_ptr + 16*12)` which is where Korea's entry lives.
     Falls back to Z3 then Z2 if Z4 is unsupported.
  5. Resumes, drives navigation through Main → Single Player →
     Play Scenario → Earth → Difficulty → civ-select.
  6. Polls all threads for PCs inside the civ-select code path
     until a watchpoint fires (or the poll budget exhausts).
  7. On fire: dumps PC, LR, r2, a few GPRs from the offending
     thread — the PC is the carousel-side reader of Korea's entry.
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


# r2 base = 0x193a288, r2+0x141c = civnames buffer pointer slot
CIVS_BUF_PTR_SLOT = 0x193b6a4
# Entry layout is 12 bytes per civ: { FStringA name, int gender, int plurality }.
# Korea at index 16 sits at buf_ptr + 16*12 = buf_ptr + 192
KOREA_ENTRY_BYTE_OFFSET = 16 * 12
# The entry's FStringA pointer is at offset 0 of the entry
KOREA_FSTRING_PTR_OFFSET = KOREA_ENTRY_BYTE_OFFSET + 0


def _press(button, delay=0.5):
    L._send_ps3_button(button)
    time.sleep(delay)


def _shot(label):
    from PIL import Image
    frame = L._capture_display()
    if frame is None:
        return
    out = Path(f"/output/iter201_{label}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        Image.fromarray(frame).save(str(out))
    except Exception as e:
        print(f"  shot save fail: {e}")


def _try_set_watch(gdb: GDBClient, addr: int, length: int = 4):
    """Try Z4 (access), then Z3 (read), then Z2 (write). Return (kind, ok)."""
    for kind_name, setter in (
        ("access", gdb.set_access_watchpoint),
        ("read", gdb.set_read_watchpoint),
        ("write", gdb.set_write_watchpoint),
    ):
        try:
            if setter(addr, length):
                return kind_name, True
        except Exception as e:
            print(f"  watchpoint {kind_name} at {addr:#x}: exception {e}")
    return None, False


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
        "iteration": "iter-201",
        "civs_buf_ptr_slot": hex(CIVS_BUF_PTR_SLOT),
        "runtime_buf_ptr": None,
        "korea_entry_addr": None,
        "watchpoint_kind": None,
        "watchpoint_set": False,
        "stops": [],
        "buffer_snapshot": None,
        "error": None,
    }

    try:
        time.sleep(2)
        if not L._is_rpcs3_alive(rpcs3):
            print("RPCS3 failed to start")
            return 2
        print("Waiting for RSX...")
        if not L._wait_for_rsx(rpcs3, timeout=RPCS3_BOOT_TIMEOUT, launch_time=launch_time):
            print("RSX did not come up")
            return 3

        L._navigate_startup_to_main_menu(rpcs3)
        _shot("00_main_menu")

        # -- phase 1: read the runtime buffer pointer --
        print("Attaching GDB, reading civs buffer pointer from TOC slot...")
        with GDBClient("127.0.0.1", 2345, timeout=10) as gdb:
            gdb.pause()
            time.sleep(0.3)
            print("  qSupported:", gdb.query_supported()[:200])
            buf_ptr = gdb.read_u32(CIVS_BUF_PTR_SLOT)
            print(f"  *{CIVS_BUF_PTR_SLOT:#x} = {buf_ptr:#x}")
            result["runtime_buf_ptr"] = hex(buf_ptr)
            if buf_ptr == 0:
                print("  buf ptr is NULL — parser may not have run yet")
                result["error"] = "NULL buf_ptr at main menu"
                gdb.resume()
                return 4

            # Dump the buffer header (4 bytes before the ptr) + first 4 entries
            count_bytes = gdb.read_memory(buf_ptr - 4, 4)
            header_count = int.from_bytes(count_bytes, "big") if len(count_bytes) == 4 else None
            print(f"  buffer count header @ {buf_ptr-4:#x} = {header_count}")
            result["buffer_count"] = header_count

            # Korea's entry
            korea_addr = buf_ptr + KOREA_FSTRING_PTR_OFFSET
            korea_ptr = gdb.read_u32(korea_addr)
            print(f"  Korea entry FStringA ptr @ {korea_addr:#x} = {korea_ptr:#x}")
            result["korea_entry_addr"] = hex(korea_addr)
            result["korea_fstring_ptr"] = hex(korea_ptr)

            # Read the first 8 bytes at korea_ptr (FStringA contents)
            if korea_ptr:
                korea_bytes = gdb.read_memory(korea_ptr, 16)
                print(f"  Korea FStringA first bytes: {korea_bytes!r}")
                result["korea_fstring_bytes"] = korea_bytes.hex()

            # Dump first 48 bytes of the buffer to verify structure
            snap = gdb.read_memory(buf_ptr, 48)
            result["buffer_snapshot"] = snap.hex()
            print(f"  first 48 bytes of buffer: {snap.hex()}")

            # -- phase 2: set access watchpoint on Korea's entry --
            kind, ok = _try_set_watch(gdb, korea_addr, 4)
            result["watchpoint_kind"] = kind
            result["watchpoint_set"] = ok
            print(f"  watchpoint at {korea_addr:#x} ({kind}): {'OK' if ok else 'FAILED'}")
            gdb.resume()

        # -- phase 3: navigate to civ-select --
        print("Navigating to civ-select...")
        _press("Down", 0.5)
        _press("X", 3)  # Single Player
        _shot("01_single_player")
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("Down", 0.5)
        _press("X", 3)  # Play Scenario
        _shot("02_scenario_menu")
        # Wait for scenario list
        for _ in range(15):
            t = L._ocr_screen()
            if "earth" in t.lower() or "scenario" in t.lower():
                break
            time.sleep(2)
        # Scroll to Earth
        for _ in range(30):
            t = L._ocr_screen()
            if "earth" in t.lower():
                break
            _press("Down", 0.4)
        _press("X", 3)  # Earth
        _shot("03_after_earth")
        # Difficulty
        for _ in range(4):
            _press("Down", 0.3)
        _press("X", 2)
        _shot("04_after_difficulty_civ_select_should_load")

        # -- phase 4: poll all threads for watchpoint hits --
        print("Polling for watchpoint hits + thread PCs...")
        for poll in range(20):
            try:
                with GDBClient("127.0.0.1", 2345, timeout=5) as gdb:
                    gdb.pause()
                    time.sleep(0.1)
                    threads = gdb.inspect_all_threads()
                    sample = {"poll": poll, "threads": []}
                    for t in threads:
                        tid = t.get("tid", "?")
                        pc = t.get("pc", 0)
                        lr = t.get("lr", 0)
                        entry = {"tid": tid, "pc": hex(pc), "lr": hex(lr)}
                        sample["threads"].append(entry)
                    result["stops"].append(sample)
                    # Show any interesting (non-zero, non-common) PCs
                    for e in sample["threads"]:
                        p = int(e["pc"], 16)
                        if 0x10000 <= p <= 0x1200000:
                            print(f"  poll {poll} tid={e['tid']} PC={e['pc']} LR={e['lr']}")
                    gdb.resume()
            except Exception as e:
                print(f"  poll {poll}: GDB error {e}")
            _press("Right", 0.2)
            time.sleep(0.2)

        # Also probe after confirming a slot
        _press("X", 10)
        _shot("05_after_confirm")

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
    out = Path("/output/iter201_civs_watchpoint_result.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"wrote {out}")
    return 0 if result.get("watchpoint_set") else 1


if __name__ == "__main__":
    sys.exit(main())
