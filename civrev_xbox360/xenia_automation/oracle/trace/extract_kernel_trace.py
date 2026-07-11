#!/usr/bin/env python3
"""H7 — kernel-trace extractor.

Pull the kernel-facing signals from a Xenia (or ReXGlue) log that matter for the
port's correctness and for finding missing shims:

  * RUNTIME GAPS  - "undefined extern call to <addr> <name>" lines: kernel/XAM
                    imports the game actually invoked but the runtime doesn't
                    implement. These are the highest-value milestone-M3/M8 signal
                    (each is a concrete shim to write). Reported with hit counts.
  * IMPORT SUMMARY- per-library implemented/unimplemented percentages from the
                    module load banner (Xenia), so you know the total surface.
  * THREADS       - thread creation / crash-thread markers, for comparing the
                    threading sequence across implementations.

Usage:
    extract_kernel_trace.py LOG [--out FILE]
    extract_kernel_trace.py - < LOG
"""
import argparse
import re
import sys
from collections import Counter, OrderedDict

UNDEF_CALL = re.compile(r'undefined extern call to\s+([0-9A-Fa-f]+)\s+(\S+)')
IMPL_SUMMARY = re.compile(r'Implemented:\s+(\d+)%\s+\((\d+)\s+implemented,\s+(\d+)\s+unimplemented\)')
IMPORT_LIB = re.compile(r'^\s*([a-zA-Z0-9_]+\.(?:xex|exe))\s+-\s+(\d+)\s+imports')
THREAD_MARK = re.compile(r'Thread ID \(Host:\s*(0x[0-9A-Fa-f]+)\s*/\s*Guest:\s*(0x[0-9A-Fa-f]+)\)')
# ReXGlue-style (defensive; not yet observed): "unimplemented kernel import: Name"
REXGLUE_UNIMPL = re.compile(r'unimplemented (?:kernel |xam )?import[:\s]+(\S+)', re.IGNORECASE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log', help='log file, or - for stdin')
    ap.add_argument('--out', help='write here instead of stdout')
    args = ap.parse_args()

    text = sys.stdin.read() if args.log == '-' else open(args.log, encoding='utf-8', errors='replace').read()
    lines = text.splitlines()

    undef = Counter()          # name -> hit count
    undef_addr = {}            # name -> address (last seen)
    impl_summaries = []        # (pct, impl, unimpl) in file order
    import_libs = OrderedDict()
    threads = []

    for line in lines:
        m = UNDEF_CALL.search(line)
        if m:
            addr, name = m.group(1), m.group(2)
            undef[name] += 1
            undef_addr[name] = addr
        m = REXGLUE_UNIMPL.search(line)
        if m:
            undef[m.group(1)] += 1
        m = IMPL_SUMMARY.search(line)
        if m:
            impl_summaries.append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        m = IMPORT_LIB.search(line)
        if m:
            import_libs[m.group(1)] = int(m.group(2))
        m = THREAD_MARK.search(line)
        if m:
            threads.append((m.group(1), m.group(2)))

    out = []
    out.append('# kernel trace')
    out.append('')
    out.append('## runtime gaps (undefined/unimplemented imports actually invoked)')
    if undef:
        for name, count in sorted(undef.items(), key=lambda kv: (-kv[1], kv[0])):
            addr = undef_addr.get(name, '?')
            out.append(f'{count:5d}x  {name}  @{addr}')
    else:
        out.append('(none — every invoked import was implemented)')
    out.append('')
    out.append('## import libraries (from module banner)')
    if import_libs:
        for lib, n in import_libs.items():
            out.append(f'{lib}: {n} imports')
    else:
        out.append('(no import banner found)')
    out.append('')
    out.append('## implemented summaries (pct, implemented, unimplemented)')
    if impl_summaries:
        for pct, impl, unimpl in impl_summaries:
            out.append(f'{pct}%  {impl} implemented / {unimpl} unimplemented')
    else:
        out.append('(none)')
    out.append('')
    out.append('## thread markers')
    if threads:
        # collapse consecutive dupes (crash dumps repeat the same thread)
        prev = None
        for host, guest in threads:
            if (host, guest) != prev:
                out.append(f'host={host} guest={guest}')
                prev = (host, guest)
    else:
        out.append('(none)')

    body = '\n'.join(out) + '\n'
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(body)
        print(f'[extract_kernel_trace] {len(undef)} distinct gaps, '
              f'{len(import_libs)} libs -> {args.out}', file=sys.stderr)
    else:
        sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
