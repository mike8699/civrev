# -*- coding: utf-8 -*-
# DecompResizeAndAlloc.py — answer the iter-134 question:
# can FUN_00c25ebc (the SetLength resize/allocator) handle a NULL
# initial buf, or does it require an already-allocated FStringA?
#
# Also pulls FUN_00c26a00 (the fault site) and the parser_worker
# (0xa2e640) decompilation so we can see, in one log, the full
# allocation contract for the 18th-entry FStringA.

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
    (0x00c25ebc, 'FUN_00c25ebc / resize_or_alloc'),
    (0x00c25f8c, 'FUN_00c25f8c / FStringA::SetLength'),
    (0x00c26a00, 'FUN_00c26a00 / fault site (lazy-init?)'),
    (0x00a00f54, 'FUN_00a00f54 / entry_init'),
    (0x00a2e640, 'FUN_00a2e640 / parser_worker'),
]

for va, name in TARGETS:
    fn = ensure_fn(va)
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (name, va))
    if fn is None:
        print('  [could not create function]')
        print('=' * 72)
        continue
    print('size=%d body_min=%s body_max=%s' % (
        fn.getBody().getNumAddresses(),
        fn.getBody().getMinAddress(),
        fn.getBody().getMaxAddress(),
    ))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 180, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:120]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed: %s]' % result.getErrorMessage())
