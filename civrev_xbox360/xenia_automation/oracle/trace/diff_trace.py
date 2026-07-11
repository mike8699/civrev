#!/usr/bin/env python3
"""H7 — file-trace comparator (the port-vs-oracle correctness check).

Compares two normalized file traces (from extract_file_trace.py) with the
semantics the PRD calls for: SET equality plus LANDMARK ORDERING, tolerant of
thread interleaving. Threads may reorder neighboring accesses, so we do NOT
require identical sequences — we require:

  1. Set parity: the two runs touch the same set of files (within --tolerance),
     reporting anything the port MISSED (in reference, not port) or added.
  2. Landmark order: significant files (xex, config, archives, shaders, caches,
     movies) that appear in BOTH runs must appear in the same relative order.
     Reversals ("inversions") are reported — those indicate a real boot-flow
     divergence, not benign interleaving.

Usage:
    diff_trace.py REFERENCE PORT [--tolerance 0.10] [--json OUT]
      REFERENCE = oracle (Xenia) trace;  PORT = ReXGlue trace.
Exit: 0 = match within tolerance and no landmark inversions; 2 = diverged.
"""
import argparse
import json
import re
import sys

# Landmark = a boot-significant file (not an intermediate directory walk).
LANDMARK_RE = re.compile(r'\.(xex|ini|fpk|fxobj|psc|bik|xzp|dds|swf|gfx|bin|mp3)$', re.IGNORECASE)


def load(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return [ln.strip() for ln in f if ln.strip()]


def first_index(seq):
    """path -> first occurrence index."""
    idx = {}
    for i, p in enumerate(seq):
        if p not in idx:
            idx[p] = i
    return idx


def landmark_inversions(ref, port):
    """Shared landmarks whose relative order flips between ref and port."""
    ref_i = first_index(ref)
    port_i = first_index(port)
    shared = [p for p in ref_i if p in port_i and LANDMARK_RE.search(p)]
    # order shared landmarks by their reference index
    shared.sort(key=lambda p: ref_i[p])
    inversions = []
    for a in range(len(shared)):
        for b in range(a + 1, len(shared)):
            pa, pb = shared[a], shared[b]
            # pa precedes pb in reference by construction; flag if not in port
            if port_i[pa] > port_i[pb]:
                inversions.append((pa, pb))
    return shared, inversions


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('reference', help='oracle (Xenia) normalized trace')
    ap.add_argument('port', help='port (ReXGlue) normalized trace')
    ap.add_argument('--tolerance', type=float, default=0.10,
                    help='max fraction of reference files the port may miss (default 0.10)')
    ap.add_argument('--json', help='write a machine-readable result here')
    args = ap.parse_args()

    ref = load(args.reference)
    port = load(args.port)
    ref_set, port_set = set(ref), set(port)

    missed = sorted(ref_set - port_set)   # in oracle, absent from port  (bad)
    added = sorted(port_set - ref_set)     # in port, absent from oracle  (usually benign)

    miss_frac = (len(missed) / len(ref_set)) if ref_set else 0.0
    shared, inversions = landmark_inversions(ref, port)

    set_ok = miss_frac <= args.tolerance
    order_ok = len(inversions) == 0
    passed = set_ok and order_ok

    print(f'reference files: {len(ref_set)}   port files: {len(port_set)}')
    print(f'shared landmarks: {len(shared)}')
    print(f'missed by port:  {len(missed)}  ({miss_frac:.1%} of reference; tolerance {args.tolerance:.0%})')
    print(f'added by port:   {len(added)}')
    print(f'landmark order inversions: {len(inversions)}')
    if missed:
        print('\n-- MISSED (in oracle, not in port) --')
        for p in missed[:40]:
            print(f'   {p}')
        if len(missed) > 40:
            print(f'   … +{len(missed) - 40} more')
    if inversions:
        print('\n-- ORDER INVERSIONS (oracle: A before B; port: B before A) --')
        for a, b in inversions[:20]:
            print(f'   {a}   <->   {b}')
    print(f'\nRESULT: {"PASS" if passed else "FAIL"} '
          f'(set {"ok" if set_ok else "DIVERGED"}, order {"ok" if order_ok else "DIVERGED"})')

    if args.json:
        with open(args.json, 'w') as f:
            json.dump({
                'reference_count': len(ref_set), 'port_count': len(port_set),
                'missed': missed, 'added': added,
                'missed_fraction': miss_frac, 'tolerance': args.tolerance,
                'shared_landmarks': len(shared),
                'inversions': inversions,
                'set_ok': set_ok, 'order_ok': order_ok, 'passed': passed,
            }, f, indent=2)

    return 0 if passed else 2


if __name__ == '__main__':
    sys.exit(main())
