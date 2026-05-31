# -*- coding: utf-8 -*-
# CleanProbeAnchors.py (path-b iter-3) — run against the FRESH civrev_clean
# project (correct clean-ELF addressing). Verify analysis quality and test
# whether Ghidra resolved refs to civ-select / game anchors.
#
# Run: analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript CleanProbeAnchors.py -noanalysis

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

print('function count: %d' % fm.getFunctionCount())
print('min=%s max=%s' % (prog.getMinAddress(), prog.getMaxAddress()))

ANCHORS = [
    (0x169cacd, 'theSelectedOption'),
    (0x1694708, 'OnAccept'),
    (0x1693e50, 'OnPressY'),
    (0x1692728, 'CcCiv'),
    (0x1693630, 'CcGame'),
    (0x16dd35e, 'CIVBONUSTEXT'),
    (0x16928a9, 'LBTEXT'),
    (0x195fe28, 'ADJ_FLAT_table'),   # known-good control (should have refs)
]

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


for va, name in ANCHORS:
    a = addr(va)
    refs = list(rm.getReferencesTo(a))
    print('\n0x%x %-20s -> %d refs' % (va, name, len(refs)))
    fns = set()
    for r in refs[:12]:
        src = r.getFromAddress()
        fn = fm.getFunctionContaining(src)
        ins = listing.getInstructionAt(src)
        print('   %-10s %s  fn=%s  %s' % (
            r.getReferenceType().getName(), src,
            fn.getName() if fn else '<none>',
            ins.toString() if ins else '<data>'))
        if fn:
            fns.add(fn.getEntryPoint().getUnsignedOffset())
    for fva in sorted(fns):
        print('     -> fn @ 0x%x' % fva)

print('\n[CleanProbeAnchors] done.')
