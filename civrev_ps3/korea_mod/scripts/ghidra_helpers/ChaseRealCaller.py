# -*- coding: utf-8 -*-
# ChaseRealCaller.py
#
# iter-116: the real fault function FUN_00c26a00 has exactly ONE
# caller: FUN_00011020 at 0x1102c. Decompile FUN_00011020 and walk
# UP the chain to find the ultimate consumer that passes a
# corrupted FStringA whose buf = 0x2a120.

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


def dump(label, fn_va, max_lines=80):
    print('')
    print('=' * 72)
    print(label)
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        print('  [no fn]')
        return
    print('%s @ 0x%x size=%d' % (
        fn.getName(), fn_va, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        return
    code = str(result.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:max_lines]):
        print('%4d  %s' % (i + 1, line))
    # Also dump callers
    print('')
    print('  callers:')
    seen = set()
    for ref in rm.getReferencesTo(fn.getEntryPoint()):
        if ref.getReferenceType().isCall():
            cfn = fm.getFunctionContaining(ref.getFromAddress())
            if cfn:
                seen.add(cfn.getEntryPoint().getUnsignedOffset())
                print('    from %s in %s' % (
                    ref.getFromAddress(), cfn.getName()))
    return seen


# Chain 1 hop up
callers = dump('HOP 1: FUN_00011020 (caller of fault fn)', 0x11020, max_lines=50)

# Chain 2 hops up for each caller
for cva in sorted(callers or set()):
    dump('HOP 2: caller of FUN_00011020', cva, max_lines=120)
