# -*- coding: utf-8 -*-
# DecompWorkerAndDispatcher.py
#
# iter-106: we found FUN_00a21ce8 decompiles to 8 calls to
# FUN_00a216d4, each passing (auStack_NN, string_from_global_struct,
# count). Dump the FULL dispatcher + the worker + the stringtable
# ctor/dtor so we can see the parser's actual target buffer.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()

TARGETS = [
    (0x00a21ce8, 'FUN_00a21ce8 (name-file init dispatcher — FULL)'),
    (0x00a216d4, 'FUN_00a216d4 (name-file worker parser)'),
    (0x009b8ed0, 'FUN_009b8ed0 (StringTable-ctor candidate)'),
    (0x009b4410, 'FUN_009b4410 (StringTable-dtor candidate)'),
]


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


for va, label in TARGETS:
    fn = fm.getFunctionAt(addr(va))
    print('')
    print('=' * 72)
    print('%s' % label)
    if fn is None:
        print('  [no function at 0x%x]' % va)
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
