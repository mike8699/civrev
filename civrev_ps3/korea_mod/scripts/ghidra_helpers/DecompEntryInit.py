# -*- coding: utf-8 -*-
# DecompEntryInit.py — look at func_0x00a00f54 (the per-entry
# initializer the parser calls inside its init loop) and the
# surrounding parser_worker init bytes to understand what it
# actually does with the 12-byte entry.

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


TARGETS = [
    (0x00a00f54, 'entry_init'),
    (0x009c31e0, 'file_open_maybe'),
    (0x00c25ebc, 'resize_buffer'),
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
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:80]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')

# Also disassemble the parser_worker init loop to see what
# actually calls func_00a00f54 and what args it passes.
print('')
print('=' * 72)
print('parser_worker init-loop bytes (0xa2e6a0..0xa2e700)')
print('=' * 72)
for va in range(0xa2e6a0, 0xa2e700, 4):
    a = addr(va)
    insn = listing.getInstructionAt(a)
    if insn is None:
        print('  0x%08x  <none>' % va)
        continue
    parts = [insn.getMnemonicString()]
    for i in range(insn.getNumOperands()):
        parts.append(insn.getDefaultOperandRepresentation(i))
    print('  0x%08x  %-8s %s' % (va, parts[0], ', '.join(parts[1:])))
