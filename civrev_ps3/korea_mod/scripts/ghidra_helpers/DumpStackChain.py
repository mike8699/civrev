# -*- coding: utf-8 -*-
# DumpStackChain.py — walk the stack trace from iter-123's
# rpcs3.log and dump the instruction at each frame PC plus
# decompile each function in the chain.

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


# Stack frames from iter-123 rpcs3.log:
FRAMES = [
    (0x00c26a00, 'fault site'),
    (0x00c26a64, 'FUN_00c26a00 + 0x64 (inner call)'),
    (0x00036354, 'FUN_00036314 + 0x40'),
    (0x009f1c98, '9f1c98 first layer'),
    (0x009f1d18, '9f1d18 second layer'),
    (0x00c72dc4, 'c72dc4 container method'),
    (0x00a2ea68, 'parser worker 0xa2e640 + 0x428'),
]

for va, label in FRAMES:
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (label, va))
    a = addr(va)
    insn = listing.getInstructionAt(a)
    if insn is None:
        dc = DisassembleCommand(a, None, True)
        dc.applyTo(prog, monitor)
        insn = listing.getInstructionAt(a)
    if insn is not None:
        parts = [insn.getMnemonicString()]
        for i in range(insn.getNumOperands()):
            parts.append(insn.getDefaultOperandRepresentation(i))
        print('instruction: %s %s' % (parts[0], ', '.join(parts[1:])))
    fn = fm.getFunctionContaining(a)
    if fn is None:
        # Try to create a function at this address
        cfc = CreateFunctionCmd(a)
        cfc.applyTo(prog, monitor)
        fn = fm.getFunctionContaining(a)
    if fn is not None:
        print('enclosing fn: %s @ 0x%x (size=%d)' % (
            fn.getName(), fn.getEntryPoint().getUnsignedOffset(),
            fn.getBody().getNumAddresses()))
        result = decomp.decompileFunction(fn, 90, monitor)
        if result.decompileCompleted():
            code = str(result.getDecompiledFunction().getC())
            for i, line in enumerate(code.splitlines()[:40]):
                print('%3d  %s' % (i + 1, line))
        else:
            print('  [decomp failed]')
    else:
        print('  [no enclosing function]')
