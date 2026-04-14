# -*- coding: utf-8 -*-
# DecompCodeHits.py
#
# iter-115: ScanVtablePointers found 2 code-segment hits for the
# fdesc address 0x018fa160 (= FUN_00c26b1c's fdesc, one slot past
# FUN_00c26960 in the fdesc table): 0xa00d1d and 0xc24b11. Decompile
# the functions containing those addresses — they're callers of
# the class that owns FUN_00c26960.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


HIT_SITES = [0xa00d1c, 0xc24b10]

for hit in HIT_SITES:
    fn = fm.getFunctionContaining(addr(hit))
    print('')
    print('=' * 72)
    print('code ref at 0x%x' % hit)
    if fn is None:
        print('  [no function]')
        continue
    entry = fn.getEntryPoint().getUnsignedOffset()
    print('Containing function: %s @ 0x%x (size=%d)' % (
        fn.getName(), entry, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        continue
    code = str(result.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:200]):
        print('%4d  %s' % (i + 1, line))
