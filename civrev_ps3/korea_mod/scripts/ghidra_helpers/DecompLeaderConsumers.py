# -*- coding: utf-8 -*-
# DecompLeaderConsumers.py — decompile the two functions iter-145
# identified as accessing all 16 LEADER_N entries from the table at
# vaddr 0x0193a158. One of these is likely the civ-select carousel
# cell-grid builder.

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
    (0x0019fe90, 'leader_consumer_A'),
    (0x00a087bc, 'leader_consumer_B'),
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
