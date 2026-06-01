#!/usr/bin/env python3
"""path-b iter-9: 3-way noise-subtracted diff to isolate civ-specific state.

A plain China-vs-Rome diff is dominated by noise: two different New-Game maps
differ in map / RNG / GPU-render state (iter-8 found the cleanest "localized"
signal was a render-pass counter). To cut the noise, dump China TWICE (A and B,
both civ 6, different maps) plus Rome (civ 0). Then for each .bss global, a byte
offset that DIFFERS China_A-vs-Rome but is STABLE China_A-vs-China_B is
civ-specific (changes with civ, not with the random map) — i.e. the civ index /
starting-tech bitfield / starting-bonus output we're hunting.

Usage: diff3_player_dumps.py <chinaA.json> <rome.json> <chinaB.json>
"""
from __future__ import annotations
import json
import sys


def load(p):
    return {h["bss"]: bytes.fromhex(h["dump"]) for h in json.load(open(p))["bss_hits"]}


def asc(bs):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in bs)


def main():
    A = load(sys.argv[1])   # china A (civ 6)
    R = load(sys.argv[2])   # rome   (civ 0)
    Bb = load(sys.argv[3])  # china B (civ 6, noise baseline)
    common = set(A) & set(R) & set(Bb)
    print(f"globals: chinaA={len(A)} rome={len(R)} chinaB={len(Bb)} common={len(common)}")

    results = []
    for bss in common:
        a, r, b = A[bss], R[bss], Bb[bss]
        n = min(len(a), len(r), len(b))
        civ = set(i for i in range(n) if a[i] != r[i])      # differs by civ
        noise = set(i for i in range(n) if a[i] != b[i])    # differs by map/run
        specific = sorted(civ - noise)                       # civ-only
        if specific:
            results.append((bss, specific, a, r, b))
    # rank: globals with the fewest civ-specific bytes = the cleanest civ fields
    results.sort(key=lambda x: len(x[1]))
    print(f"\n=== {len(results)} globals have civ-specific (noise-subtracted) bytes ===")
    for bss, spec, a, r, b in results[:40]:
        # group contiguous offsets, show china-vs-rome values
        head = spec[0]
        lo = max(0, head - 6)
        cv = a[lo:head + 10]
        rv = r[lo:head + 10]
        tag = ""
        # civ-index signal: a byte 6 (china) vs 0 (rome)
        if any(a[o] == 6 and r[o] == 0 for o in spec):
            tag = "  <== civ-index 6->0!"
        # tech-bitfield signal: same-position bits differ
        print(f"  {bss}: {len(spec)} civ-bytes at {[hex(o) for o in spec[:8]]}{tag}")
        print(f"      china +{lo:#x}: {cv.hex()}  '{asc(cv)}'")
        print(f"      rome  +{lo:#x}: {rv.hex()}  '{asc(rv)}'")
    print("\nThe civ-index (6->0) / few-byte globals are the player/civ struct.")
    print("Read the full object there to find the starting-tech bitfield, then")
    print("set a Z0 breakpoint on / static-trace the writer of that offset.")


if __name__ == "__main__":
    main()
