# -*- coding: utf-8 -*-
# DecompParserWorkerFull.py — full decompile of real_parser_worker
# at 0xa2e640 and identify bl FUN_009bf5a0 call sites.

from ghidra.app.decompiler import DecompInterface
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


fn = fm.getFunctionAt(addr(0xa2e640))
if fn is None:
    print('real_parser_worker not found — run ForceCreateAndWalk first')
else:
    print('real_parser_worker @ 0xa2e640 (size=%d)' %
          fn.getBody().getNumAddresses())
    result = decomp.decompileFunction(fn, 180, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()):
            print('%4d  %s' % (i + 1, line))

    # Find every `bl 0x9bf5a0` instruction in the function body.
    print('')
    print('=' * 72)
    print('bl FUN_009bf5a0 call sites in real_parser_worker:')
    target = 0x9bf5a0
    for insn in listing.getInstructions(fn.getBody(), True):
        for ref in insn.getReferencesFrom():
            if ref.getReferenceType().isCall():
                if ref.getToAddress().getUnsignedOffset() == target:
                    print('  0x%08x  %s' % (
                        insn.getAddress().getUnsignedOffset(),
                        insn.toString()))
