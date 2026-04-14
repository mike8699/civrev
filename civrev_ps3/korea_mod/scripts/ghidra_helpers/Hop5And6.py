# -*- coding: utf-8 -*-
# Hop5And6.py — walk up from FUN_00ae33b0 and FUN_00a7e080 to
# find where the 17-constant loop lives.

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


def dump_and_callers(label, va):
    fn = fm.getFunctionAt(addr(va))
    print('')
    print('=' * 72)
    print(label)
    if fn is None:
        print('  [no fn]')
        return set()
    print('size=%d' % fn.getBody().getNumAddresses())
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:150]):
            print('%4d  %s' % (i + 1, line))
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
    return seen


# Chain 1: FUN_00ae3160 (the std::vector iteration) <- FUN_00ae33b0
hop5a = dump_and_callers('HOP 5A: FUN_00ae33b0 (caller of 0xae3160 vector loop)',
                         0xae33b0)

# Chain 2 sibling: FUN_00a7dd98 <- FUN_00a7e080
hop5b = dump_and_callers('HOP 5B: FUN_00a7e080 (caller of 0xa7dd98)',
                         0xa7e080)

# Chase the lead: whoever calls the ae33b0 chain one more hop.
for fn_va, fn_name in sorted(hop5a):
    dump_and_callers('HOP 6 from %s' % fn_name, fn_va)
