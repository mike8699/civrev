#!/usr/bin/env python3
"""H7 — file-trace extractor.

Normalize a Xenia log OR a ReXGlue port log into a comparable ordered list of
guest file/path accesses. The file trace is the cheapest cross-implementation
correctness signal: if the port opens the same files in the same landmark order
as Xenia during boot, the early game logic is behaving.

Both emulator families log path resolution differently, so we normalize to a
bare, lower-cased, backslash-delimited guest path with device/symlink prefixes
stripped (e.g. Xenia `DiscImageDevice::ResolvePath(\\Resource\\Common)` and
ReXGlue `game:\\Resource\\Common` both become `resource\\common`).

Usage:
    extract_file_trace.py LOG [--format {auto,xenia,rexglue}] [--out FILE]
                              [--unique] [--keep-dirwalk]
    extract_file_trace.py - < LOG        # read stdin

Output: one normalized path per line (order preserved; consecutive duplicates
collapsed unless --keep-dirwalk). With --unique, first-seen order of the set.
"""
import argparse
import re
import sys

# --- line patterns ------------------------------------------------------------
# Xenia: "F> F8000008 DiscImageDevice::ResolvePath(\Resource\Common)"
#        also NullDevice::ResolvePath()  (no path — skipped)
XENIA_RESOLVE = re.compile(r'(?:[A-Za-z]+Device)?::?ResolvePath\((\\[^)]*)\)')
# Xenia file opens that carry a path, if present at higher log levels:
XENIA_OPEN = re.compile(r'(?:NtCreateFile|NtOpenFile|CreateFile)[^\\]*(\\[^\s")]+)')

# ReXGlue: VFS lines are not yet observed from a real run. Match the documented
# shapes defensively: "VirtualFileSystem::ResolvePath(game:\...)",
# "ResolvePath(d:\...)", "OpenFile(game:\...)", or any bare game:/d: token.
REXGLUE_RESOLVE = re.compile(
    r'(?:ResolvePath|OpenFile|OpenFileEx|NtCreateFile)\(\s*([a-zA-Z]:\\[^)\s]*|\\[^)\s]*)')
REXGLUE_TOKEN = re.compile(r'\b((?:game|d|update|cache):\\[^\s")]+)')

# Device / symlink prefixes to strip so the two implementations line up.
PREFIX_RE = re.compile(
    r'^(?:'
    r'\\device\\harddisk0\\partition1|'
    r'\\device\\harddisk0\\partitionupdate|'
    r'\\device\\cdrom0|'
    r'game:|d:|update:|cache:'
    r')', re.IGNORECASE)


def normalize(path: str) -> str:
    """Lower-case, unify separators, strip device/symlink prefix, trim slashes."""
    p = path.strip().replace('/', '\\').lower()
    p = PREFIX_RE.sub('', p)
    p = p.lstrip('\\')
    return p


def detect_format(text: str) -> str:
    if 'device::resolvepath' in text.lower() or 'discimagedevice' in text.lower():
        return 'xenia'
    if re.search(r'(game|d|update):\\', text, re.IGNORECASE):
        return 'rexglue'
    return 'xenia'  # default; the historical oracle log is Xenia


def extract(lines, fmt: str):
    resolve = XENIA_RESOLVE if fmt == 'xenia' else REXGLUE_RESOLVE
    opener = XENIA_OPEN if fmt == 'xenia' else None
    token = None if fmt == 'xenia' else REXGLUE_TOKEN
    out = []
    for line in lines:
        m = resolve.search(line)
        hit = None
        if m:
            hit = m.group(1)
        elif opener and opener.search(line):
            hit = opener.search(line).group(1)
        elif token and token.search(line):
            hit = token.search(line).group(1)
        if hit is None:
            continue
        norm = normalize(hit)
        if norm:
            out.append(norm)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('log', help='log file, or - for stdin')
    ap.add_argument('--format', choices=['auto', 'xenia', 'rexglue'], default='auto')
    ap.add_argument('--out', help='write here instead of stdout')
    ap.add_argument('--unique', action='store_true',
                    help='emit each path once, in first-seen order (the set)')
    ap.add_argument('--keep-dirwalk', action='store_true',
                    help='do not collapse consecutive duplicate paths')
    args = ap.parse_args()

    text = sys.stdin.read() if args.log == '-' else open(args.log, encoding='utf-8', errors='replace').read()
    fmt = detect_format(text) if args.format == 'auto' else args.format

    paths = extract(text.splitlines(), fmt)

    if args.unique:
        seen, result = set(), []
        for p in paths:
            if p not in seen:
                seen.add(p); result.append(p)
        paths = result
    elif not args.keep_dirwalk:
        collapsed, prev = [], None
        for p in paths:
            if p != prev:
                collapsed.append(p); prev = p
        paths = collapsed

    body = '\n'.join(paths) + ('\n' if paths else '')
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write(body)
        print(f'[extract_file_trace] format={fmt} wrote {len(paths)} paths -> {args.out}',
              file=sys.stderr)
    else:
        sys.stdout.write(body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
