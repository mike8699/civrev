#!/usr/bin/env python3
"""iter-203: dump all 18 civnames entries via GDB and verify Korea at index 16.

iter-202 established the correct civs buffer holder at .bss
address 0x1ac93b8. At runtime *(0x1ac93b8) is the heap-allocated
buffer pointer. The buffer layout is:
    count at (bufptr - 4)
    18 entries of 12 bytes each: { u32 gender, u32 plurality, u32 fstring_ptr }

Each fstring_ptr points to an FStringA — a C++ string object
whose data layout the game uses is roughly:
    struct FStringA {
        char* buf;      // offset 0, points to character bytes
        u32   len;      // offset 4
        ... (more fields)
    }
Reading the first word tells us where the character bytes live,
reading 32 bytes from there gives us the string content.

This probe:
  1. Attaches to the running RPCS3 at main menu.
  2. Reads the civs buffer header + count.
  3. Walks all 18 entries, reading gender, plurality, fstring_ptr.
  4. For each fstring_ptr, reads 32 bytes starting at *fstring_ptr
     to get the character data.
  5. Prints a table: index, gender, plurality, fstring_ptr, chars.
  6. Flags the index where the name starts with "Koreans" — that's
     the Korea slot position confirmation.
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


CIVS_BUF_HOLDER = 0x01ac93b8
RULERS_BUF_HOLDER = 0x01ac93b4


def read_fstring_chars(gdb: GDBClient, fstring_ptr: int) -> str:
    """Read FStringA character data. iter-203: the layout isn't
    `char* buf` at offset 0 — probing shows offset 0 reads as zero.
    Try several candidate layouts:
      (a) first word = char* buf (standard C++ FString)
      (b) offset 4 = char* buf
      (c) offset 0 itself is the char data (small-string optimization)
      (d) offset 8 / 12 = char*
    """
    if not fstring_ptr:
        return ""
    # Dump 48 bytes at the FStringA and try to make sense of it.
    raw = gdb.read_memory(fstring_ptr, 48)
    if not raw:
        return "(unreadable)"
    # Try each candidate offset
    for cand_off in (0, 4, 8, 12, 16, 20):
        if cand_off + 4 > len(raw):
            continue
        cand_ptr = int.from_bytes(raw[cand_off:cand_off + 4], "big")
        if 0x40000000 <= cand_ptr < 0x50000000:
            # Looks like a heap ptr — try dereferencing
            chars = gdb.read_memory(cand_ptr, 40)
            end = chars.find(b"\x00")
            if end < 0:
                end = len(chars)
            if 0 < end < 40:
                try:
                    s = chars[:end].decode("latin1", "replace")
                    if all(32 <= ord(c) < 127 or c in "\r\n\t" for c in s):
                        return f"[{cand_off:+d}] {s}"
                except Exception:
                    pass
    # Fallback: maybe the FStringA data is inline at offset 0
    end = raw.find(b"\x00")
    if end < 0 or end > 40:
        return f"(raw: {raw[:24].hex()})"
    try:
        return f"[inline] {raw[:end].decode('latin1','replace')}"
    except Exception:
        return f"(raw: {raw[:24].hex()})"


def dump_name_buffer(gdb: GDBClient, holder_va: int, label: str,
                     expected_count: int = 18) -> dict:
    """Dump a parsed name-file buffer. Returns a dict for JSON serialization."""
    print(f"\n=== {label} ({holder_va:#x}) ===")
    buf_ptr = gdb.read_u32(holder_va)
    result = {
        "label": label,
        "holder_va": hex(holder_va),
        "buf_ptr": hex(buf_ptr),
        "count": None,
        "entries": [],
    }
    if not buf_ptr:
        print("  buf_ptr is NULL — parser hasn't run yet")
        return result
    # Count is at (buf_ptr - 4)
    count = gdb.read_u32(buf_ptr - 4)
    result["count"] = count
    print(f"  buf_ptr = {buf_ptr:#x}  count = {count}")
    if count < 1 or count > 100:
        print(f"  count out of sane range, bailing")
        return result
    # Read all entries
    for i in range(min(count, expected_count + 4)):
        entry_addr = buf_ptr + i * 12
        gender = gdb.read_u32(entry_addr + 0)
        plurality = gdb.read_u32(entry_addr + 4)
        fstring_ptr = gdb.read_u32(entry_addr + 8)
        chars = read_fstring_chars(gdb, fstring_ptr)
        entry = {
            "idx": i,
            "gender": gender,
            "plurality": plurality,
            "fstring_ptr": hex(fstring_ptr),
            "chars": chars,
        }
        result["entries"].append(entry)
        # Print table row
        gender_char = {0: "M", 1: "F", 2: "N"}.get(gender, "?")
        plural_char = {0: "S", 1: "P"}.get(plurality, "?")
        print(f"  [{i:2d}] {gender_char}{plural_char}  "
              f"fs={fstring_ptr:#010x}  {chars!r}")
    return result


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
        "iteration": "iter-203",
        "civs_holder": hex(CIVS_BUF_HOLDER),
        "rulers_holder": hex(RULERS_BUF_HOLDER),
        "civs_buffer": None,
        "rulers_buffer": None,
        "korea_idx": None,
        "sejong_idx": None,
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

        print("Attaching GDB, pausing...")
        korea_fs_ptr = None
        sejong_fs_ptr = None
        with GDBClient("127.0.0.1", 2345, timeout=15) as gdb:
            gdb.pause()
            time.sleep(0.3)

            civs = dump_name_buffer(gdb, CIVS_BUF_HOLDER, "civs")
            rulers = dump_name_buffer(gdb, RULERS_BUF_HOLDER, "rulers")
            result["civs_buffer"] = civs
            result["rulers_buffer"] = rulers

            # Flag Korea/Sejong
            for e in civs.get("entries", []):
                if "Korea" in e.get("chars", "") or "korea" in e.get("chars", ""):
                    result["korea_idx"] = e["idx"]
                    korea_fs_ptr = int(e["fstring_ptr"], 16)
                    print(f"\n  *** KOREA confirmed at civs index {e['idx']} "
                          f"FStringA @ {e['fstring_ptr']} ***")
            for e in rulers.get("entries", []):
                if "Sejong" in e.get("chars", "") or "sejong" in e.get("chars", ""):
                    result["sejong_idx"] = e["idx"]
                    sejong_fs_ptr = int(e["fstring_ptr"], 16)
                    print(f"  *** SEJONG confirmed at rulers index {e['idx']} ***")

            gdb.resume()

        if korea_fs_ptr is None:
            print("No Korea ptr — skipping memory scans")
            return 0

        import struct as _s

        def scan_once(label: str, state_tag: str):
            """Reconnect GDB, pause, scan .data + .bss for a fixed set
            of pointers, resume, detach. Returns hits dict."""
            print(f"\n=== scan_once: {label} (state={state_tag}) ===")
            needles = {
                f"korea_fs ({korea_fs_ptr:#x})": _s.pack(">I", korea_fs_ptr),
                f"civs_buf ({int(civs['buf_ptr'], 16):#x})":
                    _s.pack(">I", int(civs["buf_ptr"], 16)),
            }
            if sejong_fs_ptr is not None:
                needles[f"sejong_fs ({sejong_fs_ptr:#x})"] = _s.pack(">I", sejong_fs_ptr)
            needles[f"rulers_buf ({int(rulers['buf_ptr'], 16):#x})"] = \
                _s.pack(">I", int(rulers["buf_ptr"], 16))

            # Fix duplicate-hit bug: scan each region SEQUENTIALLY with
            # non-overlapping chunks.
            regions = [
                ("data", 0x1870000, 0x11be78),
                ("bss",  0x198be78, 0x34a0c0),
            ]
            CHUNK = 0x8000
            phase_hits = {name: [] for name in needles}
            with GDBClient("127.0.0.1", 2345, timeout=10) as g:
                g.pause()
                time.sleep(0.3)
                for rname, base, size in regions:
                    t0 = time.time()
                    for off in range(0, size, CHUNK):
                        take = min(CHUNK, size - off)
                        raw = g.read_memory(base + off, take)
                        if not raw:
                            continue
                        for needle_name, needle in needles.items():
                            start = 0
                            while True:
                                i = raw.find(needle, start)
                                if i == -1:
                                    break
                                if (i & 3) == 0:
                                    va = base + off + i
                                    phase_hits[needle_name].append(
                                        {"region": rname, "va": hex(va)})
                                start = i + 1
                    print(f"    {rname} scan done in {time.time() - t0:.1f}s")
                g.resume()
            # Dedupe
            for k, lst in phase_hits.items():
                seen = set()
                uniq = []
                for h in lst:
                    key = (h["region"], h["va"])
                    if key in seen:
                        continue
                    seen.add(key)
                    uniq.append(h)
                phase_hits[k] = uniq
                print(f"  {k}: {len(uniq)} unique hits")
                for h in uniq[:20]:
                    print(f"    {h['region']:6s}  {h['va']}")
            return phase_hits

        # Phase A: scan at main menu (pre-navigation)
        result["scan_main_menu"] = scan_once("main menu", "MAIN_MENU")

        # Phase B: navigate to civ-select then scan
        print("\nNavigating to civ-select...")
        import launch as L2
        def _p(b, d=0.5):
            L2._send_ps3_button(b)
            time.sleep(d)
        _p("Down", 0.5)
        _p("X", 3)
        _p("Down", 0.5); _p("Down", 0.5); _p("Down", 0.5)
        _p("X", 3)
        for _ in range(15):
            t = L2._ocr_screen()
            if "earth" in t.lower() or "scenario" in t.lower():
                break
            time.sleep(2)
        for _ in range(30):
            t = L2._ocr_screen()
            if "earth" in t.lower():
                break
            _p("Down", 0.4)
        _p("X", 3)
        for _ in range(4):
            _p("Down", 0.3)
        _p("X", 8)  # Difficulty → civ-select
        time.sleep(3)
        result["scan_civ_select"] = scan_once("civ-select", "CIV_SELECT")

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
    out = Path("/output/iter203_civs_dump_result.json")
    out.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nwrote {out}")
    return 0 if result.get("korea_idx") is not None else 1


if __name__ == "__main__":
    sys.exit(main())
