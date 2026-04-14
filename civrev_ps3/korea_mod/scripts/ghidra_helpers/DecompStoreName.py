# -*- coding: utf-8 -*-
# DecompStoreName.py — decompile FUN_009f1d00 (store name into
# entry[+8]) and also FUN_00c27ab4 / FUN_00c27328 / FUN_00c2f0d8
# / FUN_00c2f114 / FUN_00c65188 / FUN_00a3270c that are called
# from FUN_00c72cf8 — to understand the full store pipeline.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


TARGETS = [
    (0x009f1d00, 'store_name'),
    (0x00c27ab4, 'find_char'),
    (0x00c27328, 'string_copy_maybe'),
    (0x00c2f0d8, 'substring_left'),
    (0x00c2f114, 'substring_right'),
    (0x00c65188, 'string_assign_maybe'),
    (0x00a3270c, 'trim_maybe'),
    (0x00c7521c, 'unknown_c7521c'),
]

for va, name in TARGETS:
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is None:
        CreateFunctionCmd(a).applyTo(prog, monitor)
        fn = fm.getFunctionAt(a)
    if fn is None:
        print('%s @ 0x%x: could not create' % (name, va))
        continue
    print('')
    print('=' * 72)
    print('%s @ 0x%x size=%d' % (name, va, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 60, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:40]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')
