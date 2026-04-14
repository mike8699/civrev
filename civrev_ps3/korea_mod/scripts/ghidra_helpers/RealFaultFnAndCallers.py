# -*- coding: utf-8 -*-
# RealFaultFnAndCallers.py
#
# iter-116: with the correct EBOOT imported, find the function
# containing the actual faulting store at 0xc26a98 (stb r0, 0(r11)),
# decompile it, and enumerate its callers.
#
# Jython 2.7.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


fn = fm.getFunctionContaining(addr(0xc26a98))
if fn is None:
    print('NO FUNCTION at 0xc26a98 — forcing disassembly and function creation')
else:
    entry = fn.getEntryPoint().getUnsignedOffset()
    size = fn.getBody().getNumAddresses()
    print('Enclosing function: %s @ 0x%x (size=%d)' % (
        fn.getName(), entry, size))
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        print('Decompile:')
        for i, line in enumerate(code.splitlines()[:120]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('decomp failed')

    # Callers
    print('')
    print('=' * 72)
    print('Callers of %s:' % fn.getName())
    callers = set()
    for ref in rm.getReferencesTo(fn.getEntryPoint()):
        if ref.getReferenceType().isCall():
            src = ref.getFromAddress()
            cfn = fm.getFunctionContaining(src)
            print('  from %s in %s' % (src, cfn.getName() if cfn else '<none>'))
            if cfn:
                callers.add(cfn.getEntryPoint().getUnsignedOffset())
    for other_ref in rm.getReferencesTo(fn.getEntryPoint()):
        if not other_ref.getReferenceType().isCall():
            print('  [non-call] %s from %s (type=%s)' % (
                other_ref.getReferenceType().getName(),
                other_ref.getFromAddress(),
                other_ref.getReferenceType().getName()))
    print('unique caller fns: %d' % len(callers))
