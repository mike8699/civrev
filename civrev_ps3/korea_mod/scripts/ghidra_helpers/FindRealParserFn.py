# -*- coding: utf-8 -*-
# FindRealParserFn.py
#
# iter-119: the iter-14 byte-patch sites 0xa2ee38 and 0xa2ee7c
# (both `li r5, 0x11`) are valid in EBOOT_v130_clean.ELF, but
# the function anchors iter-106..118 used for dispatcher /
# worker / scenario_init were from the wrong Ghidra project.
# Those addresses are MID-function in the correct binary.
#
# Find the REAL functions containing 0xa2ee38 / 0xa2ee7c and
# decompile them. The real "name-file parser call site" is
# inside whichever function contains those li instructions.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


for site_va, label in [
    (0xa2ee38, 'iter14_ruler_li_r5_11'),
    (0xa2ee7c, 'iter14_civ_li_r5_11'),
]:
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (label, site_va))
    print('=' * 72)
    fn = fm.getFunctionContaining(addr(site_va))
    if fn is None:
        print('  NOT in any function in this project')
        continue
    entry = fn.getEntryPoint().getUnsignedOffset()
    size = fn.getBody().getNumAddresses()
    print('Containing function: %s @ 0x%x (size=%d)' % (
        fn.getName(), entry, size))
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:100]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  decomp failed')
