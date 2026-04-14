# -*- coding: utf-8 -*-
# Hop4Decomp.py
#
# Decompile FUN_00a7dd98 and FUN_00ae3160 — the actual high-level
# callers discovered at hop 4 of the fault chain.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


TARGETS = [
    (0x00a7dd98, 'FUN_00a7dd98'),
    (0x00ae3160, 'FUN_00ae3160'),
]

for va, label in TARGETS:
    fn = fm.getFunctionAt(addr(va))
    print('')
    print('=' * 72)
    print(label)
    if fn is None:
        print('  [no function]')
        continue
    print('size=%d' % fn.getBody().getNumAddresses())
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        continue
    code = str(result.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:200]):
        print('%4d  %s' % (i + 1, line))

    # Callers
    seen = set()
    for ref in rm.getReferencesTo(fn.getEntryPoint()):
        if ref.getReferenceType().isCall():
            cfn = fm.getFunctionContaining(ref.getFromAddress())
            if cfn:
                seen.add((cfn.getEntryPoint().getUnsignedOffset(),
                          cfn.getName()))
    print('')
    print('  callers (%d unique):' % len(seen))
    for fv, nm in sorted(seen):
        print('    %s @ 0x%x' % (nm, fv))
