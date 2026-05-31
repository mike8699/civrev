# -*- coding: utf-8 -*-
# ProbeEffectLayer.py (path-b iter-5) — with r2/TOC set, xrefs + decompiles
# work. List ADJ_FLAT's consumers (the civ-data functions) and decompile each
# to classify (text builder vs game/civ-setup that might grant the bonus).
# Also re-test refs for the bonus/civ-select strings now that TOC is resolved.
#
# Run: analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript ProbeEffectLayer.py -noanalysis

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()

decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


def decompc(fn, n=90):
    try:
        r = decomp.decompileFunction(fn, 90, mon)
        if r.decompileCompleted():
            return '\n'.join(str(r.getDecompiledFunction().getC()).splitlines()[:n])
    except Exception as e:
        return '[exc %s]' % e
    return '[decomp failed]'


# 1) which strings now resolve refs?
print('=== ref re-test (TOC resolved) ===')
for va, nm in [(0x16dd35e, 'CIVBONUSTEXT'), (0x16928a9, 'LBTEXT'),
               (0x169cacd, 'theSelectedOption'), (0x195fe28, 'ADJ_FLAT'),
               (0x1ac93b8, 'civs_buffer_holder')]:
    print('  %-20s 0x%x -> %d refs' % (nm, va, len(list(rm.getReferencesTo(addr(va))))))

# 2) ADJ_FLAT consumers — unique functions referencing the table or its TOC slot
print('\n=== ADJ_FLAT consumer functions ===')
consumers = []
for tgt in (0x195fe28, 0x1938354):
    for r in rm.getReferencesTo(addr(tgt)):
        fn = fm.getFunctionContaining(r.getFromAddress())
        if fn:
            va = fn.getEntryPoint().getUnsignedOffset()
            if va not in consumers:
                consumers.append(va)
for va in consumers:
    fn = fm.getFunctionAt(addr(va))
    print('  FUN_%08x size=%d' % (va, fn.getBody().getNumAddresses() if fn else 0))

# 3) decompile each consumer (classify)
for va in consumers:
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        continue
    print('\n' + '=' * 72)
    print('FUNCTION FUN_%08x  size=%d' % (va, fn.getBody().getNumAddresses()))
    print('=' * 72)
    print(decompc(fn, 80))

print('\n[ProbeEffectLayer] done.')
