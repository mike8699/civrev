# -*- coding: utf-8 -*-
# DecompFn2fb78.py
#
# Decompile FUN_0002fb78 — the caller chain above the name-file
# init path that iter-11..26 missed. This function is where the
# iter-105 XREF chase actually lands. Its immediate child is the
# 16-byte TOC stub FUN_00010ef0 which tail-calls FUN_00a21ce8
# (the name-file init dispatcher).
#
# Also decompile FUN_00a21ce8 itself so we can see the static
# dispatch pattern.
#
# Jython 2.7.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()

TARGETS = [
    (0x0002fb78, 'FUN_0002fb78 (caller of TOC stub 0x10ef0)'),
    (0x00a21ce8, 'FUN_00a21ce8 (name-file init dispatcher)'),
]


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


for va, label in TARGETS:
    fn = fm.getFunctionAt(addr(va))
    print('')
    print('=' * 72)
    print('%s' % label)
    if fn is None:
        print('  [no function]')
        continue
    print('size=%d, entry=0x%x' % (fn.getBody().getNumAddresses(), va))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        continue
    code = str(result.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()):
        print('%4d  %s' % (i + 1, line))
