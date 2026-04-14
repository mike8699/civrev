# -*- coding: utf-8 -*-
# DecompParserConsumers.py — decompile candidate carousel functions
# that read the parser_worker output buffers (TOC r2+0x1418 for
# rulernames, r2+0x141c for civnames). Excluding parser_dispatcher
# itself (0xa2ec54) and 0x00a2e1c4 which is in the parser writer
# area — leaves 0x001e49f0 and 0x011675d8 as the carousel candidates.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.app.cmd.disassemble import DisassembleCommand
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


def ensure_fn(va):
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is None:
        DisassembleCommand(a, None, True).applyTo(prog, monitor)
        CreateFunctionCmd(a).applyTo(prog, monitor)
        fn = fm.getFunctionAt(a)
    return fn


TARGETS = [
    (0x001e489c, 'vtable_method_0_001e489c'),  # vtable[+0]
    (0x001e493c, 'vtable_method_1_001e493c'),  # vtable[+8]
    (0x001e4a9c, 'vtable_method_3_001e4a9c'),  # vtable[+18] (after 49f0)
    (0x001e4b5c, 'vtable_method_4_001e4b5c'),
    (0x001e4c20, 'vtable_method_5_001e4c20'),
]

for va, name in TARGETS:
    fn = ensure_fn(va)
    print('')
    print('=' * 72)
    print('%s @ 0x%x (size %d)' % (
        name, va, fn.getBody().getNumAddresses() if fn else -1))
    print('=' * 72)
    if fn is None:
        print('  [could not create]')
        continue
    result = decomp.decompileFunction(fn, 240, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:200]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')
