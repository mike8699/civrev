# -*- coding: utf-8 -*-
# ChaseC26960Callers.py
#
# iter-107 continuation: the fault-site's enclosing function is
# FUN_00c26960 (444 bytes). Its body is a generic "lookup by
# index in a string-table" dispatch with a proper bounds check
# — so the 17-constant consumer must live in a CALLER, not in
# the function itself. Find every call to FUN_00c26960, decompile
# each caller, and look for a hardcoded 17/16 constant near the
# call.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


# Phase 1: list every direct caller of FUN_00c26960.
target = addr(0x00c26960)
callers = set()
for ref in rm.getReferencesTo(target):
    if ref.getReferenceType().isCall():
        src = ref.getFromAddress()
        fn = fm.getFunctionContaining(src)
        if fn:
            callers.add((fn.getEntryPoint().getUnsignedOffset(), fn.getName()))

print('callers of FUN_00c26960: %d unique' % len(callers))
for va, name in sorted(callers):
    print('  %s @ 0x%x' % (name, va))


# Phase 2: decompile each caller, look for 0x11/0x10/17 constants
# NEAR the c26960 call.
def caller_body(fn_va):
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        return None
    result = decomp.decompileFunction(fn, 60, monitor)
    if not result.decompileCompleted():
        return None
    return str(result.getDecompiledFunction().getC())


print('')
print('=== decompiled bodies ===')
for va, name in sorted(callers):
    body = caller_body(va)
    if body is None:
        continue
    print('')
    print('-' * 72)
    print('%s @ 0x%x' % (name, va))
    print('-' * 72)
    lines = body.splitlines()
    # Flag hotspots: any line containing 0x11 / 0x10 / 17 / 16 / c26960
    for i, line in enumerate(lines):
        is_hot = any(k in line for k in
                     ('c26960', '0x11', '0x10', ' 17 ', ' 17,', ' 17)',
                      ' 16 ', ' 16,', ' 16)', 'FUN_00c26'))
        marker = '*' if is_hot else ' '
        print('%s%4d  %s' % (marker, i + 1, line))


# Phase 3: enumerate anyone who has both a call to c26960 AND
# takes a loop over 17/16 entries. Use decompile text-grep.
print('')
print('=== summary: callers with 17-ish loop bound ===')
for va, name in sorted(callers):
    body = caller_body(va)
    if body is None:
        continue
    hot_lines = [l for l in body.splitlines()
                 if '< 0x11' in l or '< 0x10' in l
                 or '< 17' in l or '< 16' in l
                 or '<= 0x11' in l or '<= 0x10' in l]
    if hot_lines:
        print('  %s @ 0x%x' % (name, va))
        for l in hot_lines[:5]:
            print('      %s' % l.strip()[:100])
