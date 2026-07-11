#!/usr/bin/env python3
"""H7 — crash extractor.

On a crashed run, pull each crash-dump block plus N lines of preceding context
(what the game was doing right before it died — usually the last file resolves or
kernel calls) into one focused file. Recognizes Xenia's "==== CRASH DUMP ===="
banner and generic fatal markers.

Usage:
    extract_crash.py LOG [--context N] [--out FILE]
    extract_crash.py - < LOG
Exit code: 0 if a crash was found, 1 if the log looks clean.
"""
import argparse
import re
import sys

CRASH_BANNER = re.compile(r'====\s*CRASH DUMP\s*====', re.IGNORECASE)
FATAL_MARKERS = re.compile(
    r'(Access Violation|Segmentation fault|SIGSEGV|SIGBUS|unhandled exception|'
    r'assert(ion)? fail|Fatal error|abort\(\)|terminate called|panic:)', re.IGNORECASE)
# End a crash block at a blank-ish transition or the next normal info line.
DUMP_LINE = re.compile(r'^\s*([rvf]\d+|PC:|Thread|Access|Registers|[rvf]\d{1,3}\s*=|\||[+\-])', re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log', help='log file, or - for stdin')
    ap.add_argument('--context', type=int, default=40,
                    help='lines of preceding context to include (default 40)')
    ap.add_argument('--out', help='write here instead of stdout')
    args = ap.parse_args()

    text = sys.stdin.read() if args.log == '-' else open(args.log, encoding='utf-8', errors='replace').read()
    lines = text.splitlines()

    # Find crash start indices (banner preferred; else first fatal marker).
    starts = [i for i, ln in enumerate(lines) if CRASH_BANNER.search(ln)]
    if not starts:
        fatal = [i for i, ln in enumerate(lines) if FATAL_MARKERS.search(ln)]
        starts = fatal[:1]  # a lone fatal line — report the first

    if not starts:
        msg = '# no crash detected\n'
        (open(args.out, 'w').write(msg) if args.out else sys.stdout.write(msg))
        print('[extract_crash] clean log — no crash', file=sys.stderr)
        return 1

    blocks = []
    for s in starts:
        ctx_start = max(0, s - args.context)
        # Extend the dump forward while lines look like register/dump content.
        e = s + 1
        while e < len(lines) and (DUMP_LINE.match(lines[e]) or lines[e].strip() == '' or 'CRASH' in lines[e]):
            e += 1
            if e - s > 400:  # safety cap
                break
        block = []
        block.append(f'# ---- crash @ line {s + 1} (context from line {ctx_start + 1}) ----')
        block.extend(lines[ctx_start:e])
        blocks.append('\n'.join(block))

    body = ('\n\n'.join(blocks)) + '\n'
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(body)
        print(f'[extract_crash] {len(starts)} crash block(s) -> {args.out}', file=sys.stderr)
    else:
        sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
