# -*- coding: utf-8 -*-
# DecompStoreLine.py — decompile FUN_00c72cf8 (the store-line-
# to-entry function) and identify which of its inner calls
# produces the stack frame at 0xc72dc4 and onward.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


for va, name in [
    (0xc72cf8, 'store_line_to_entry'),
    (0xc72dc4, 'c72dc4_cont'),
]:
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is None:
        CreateFunctionCmd(a).applyTo(prog, monitor)
        fn = fm.getFunctionAt(a)
    if fn is None:
        print('%s @ 0x%x: could not create function' % (name, va))
        continue
    print('')
    print('=' * 72)
    print('%s @ 0x%x size=%d' % (name, va, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:120]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')
