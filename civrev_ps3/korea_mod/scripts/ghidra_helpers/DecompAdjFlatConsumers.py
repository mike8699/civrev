# -*- coding: utf-8 -*-
# DecompAdjFlatConsumers.py  (path-b iter-2, 2026-05-31)
#
# The text.ini section-name strings (CIVBONUSTEXT/LBTEXT) have no Ghidra
# references (lis/addi loads the analysis never turned into refs). Pivot:
# decompile the 9 VERIFIED ADJ_FLAT (civ-adjective table) call sites from
# addresses.py. The civ-select sentence "The <Chinese> begin the game with
# <knowledge of Writing>" assembles the civ adjective AND the per-civ bonus
# together, so the adjective consumer is the most likely place the bonus
# array is indexed by civ. Code addresses are seg0 (file-offset==vaddr) so
# they are valid in the Ghidra program even though rodata addresses are not.
#
# Jython 2.7. Run: analyzeHeadless ghidra/ civrev -process EBOOT.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers \
#   -postScript DecompAdjFlatConsumers.py -noanalysis

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

ADJ_FLAT_CALLSITES = [
    0x0013cbf8, 0x0017e9b0, 0x0097d948, 0x0097dad0, 0x0097db28,
    0x0097e0ac, 0x009f81d4, 0x009f9600, 0x00ff09e4,
]

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


def decomp_c(fn, maxlines=220):
    try:
        res = decomp.decompileFunction(fn, 120, monitor)
        if not res.decompileCompleted():
            return '  [decomp failed]'
        return str(res.getDecompiledFunction().getC())
    except Exception as e:
        return '  [decomp exc: %s]' % e


seen = []
for va in ADJ_FLAT_CALLSITES:
    a = addr(va)
    ins = listing.getInstructionAt(a)
    fn = fm.getFunctionContaining(a)
    print('\n' + '=' * 74)
    print('CALLSITE 0x%x  ins=%s  fn=%s @ 0x%x' % (
        va, ins.toString() if ins else '<none>',
        fn.getName() if fn else '<none>',
        fn.getEntryPoint().getUnsignedOffset() if fn else 0))
    print('=' * 74)
    if fn is None:
        continue
    fva = fn.getEntryPoint().getUnsignedOffset()
    if fva in seen:
        print('  (already decompiled above)')
        continue
    seen.append(fva)
    code = decomp_c(fn)
    # Print the full body but flag lines that look like array-index-by-civ or
    # bonus assembly so they're easy to spot.
    for line in code.splitlines():
        mark = ''
        low = line.lower()
        if ('[' in line and (']' in line)) and ('* 4' in line or '<< 2' in line or 'param' in low):
            mark = '   <== idx?'
        if 'bonus' in low or 'begin' in low or 'civbonus' in low:
            mark = '   <== BONUS?'
        print(line + mark)

print('\n[DecompAdjFlatConsumers] done.')
