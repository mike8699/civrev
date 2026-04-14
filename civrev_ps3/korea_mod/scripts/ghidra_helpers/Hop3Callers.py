# -*- coding: utf-8 -*-
# Hop3Callers.py
#
# iter-117: chain walk continues from iter-116. FUN_009bf5a0 calls
# FUN_000297d0 which calls FUN_00011020 which calls FUN_00c26a00.
# FUN_009c4650 calls FUN_00036314 which calls FUN_00011020 which
# calls FUN_00c26a00. Decompile both HOP-3 callers.
#
# Also dump FUN_00c25f8c and FUN_009c05c0 referenced from
# FUN_00c26a00's else-branch — they're the allocator/copier used
# when the assign goes through the "needs new buffer" path.

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
    (0x009bf5a0, 'FUN_009bf5a0 (HOP-3 caller via FUN_000297d0)'),
    (0x009c4650, 'FUN_009c4650 (HOP-3 caller via FUN_00036314)'),
    (0x00c25f8c, 'FUN_00c25f8c (used in realloc path)'),
    (0x009c05c0, 'FUN_009c05c0 (used in realloc path)'),
    (0x009c1390, 'FUN_009c1390 (used in empty path)'),
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
    for i, line in enumerate(code.splitlines()[:80]):
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
