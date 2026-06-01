#!/usr/bin/env python3
"""path-b iter-8: diff two player_dump JSONs (China vs Rome) to localize the
per-civ game state. Each dump has, per unique .bss heap-pointer global, a
0x400-byte pointer-masked dump of the pointed object. A global whose masked
content DIFFERS between civs holds civ-specific data (civ index, tech bitfield,
starting bonus, stats) — i.e. the effect output we've been hunting.

Usage: diff_player_dumps.py <china.json> <rome.json>
"""
from __future__ import annotations
import json
import sys


def load(path):
    d = json.load(open(path))
    return {h["bss"]: bytes.fromhex(h["dump"]) for h in d["bss_hits"]}, d


def main():
    a_path = sys.argv[1] if len(sys.argv) > 1 else "rpcs3_automation/output/player_dump_china.json"
    b_path = sys.argv[2] if len(sys.argv) > 2 else "rpcs3_automation/output/player_dump_rome.json"
    A, da = load(a_path)
    B, db = load(b_path)
    print(f"china in_game={da['in_game']} globals={len(A)}; "
          f"rome in_game={db['in_game']} globals={len(B)}")
    common = sorted(set(A) & set(B), key=lambda x: int(x, 16))
    print(f"common .bss globals: {len(common)}  "
          f"(china-only {len(set(A)-set(B))}, rome-only {len(set(B)-set(A))})")
    print()
    differing = []
    for bss in common:
        a, b = A[bss], B[bss]
        n = min(len(a), len(b))
        diffs = [i for i in range(n) if a[i] != b[i]]
        if diffs:
            differing.append((bss, diffs, a, b))
    # rank: fewer diffs = more localized (a civ-index byte or small bitfield)
    differing.sort(key=lambda x: len(x[1]))
    print(f"=== {len(differing)} globals differ between China and Rome ===")
    for bss, diffs, a, b in differing:
        # show first few diff offsets with the byte values
        sample = []
        for off in diffs[:12]:
            sample.append(f"+{off:#x}:{a[off]:02x}->{b[off]:02x}")
        # flag: a single-byte change to a small value looks like a civ index
        cividx = [off for off in diffs
                  if a[off] <= 16 and b[off] <= 16 and a[off] != b[off]]
        tag = ""
        if len(diffs) <= 8:
            tag += "  <== LOCALIZED"
        if cividx:
            tag += f"  <== civ-index? offs={[hex(o) for o in cividx[:6]]}"
        print(f"  {bss}: {len(diffs)} diff bytes  {' '.join(sample)}{tag}")
    print()
    print("Next: globals tagged LOCALIZED / civ-index are the player/civ state.")
    print("Read the full object in both dumps at those offsets to find the")
    print("starting-tech bitfield (China=Writing set); then find the writer.")


if __name__ == "__main__":
    main()
