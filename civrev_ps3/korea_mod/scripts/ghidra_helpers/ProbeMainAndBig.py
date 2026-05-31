# -*- coding: utf-8 -*-
# ProbeMainAndBig.py (path-b iter-5) — decompile main (0x147d0) and the big
# ADJ_FLAT consumer FUN_009f95e0 (longer timeout), and dump all DAT_/data
# refs the big consumer makes (to spot a civ-bonus table beyond ADJ_FLAT).
#
# Run: analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript ProbeMainAndBig.py -noanalysis

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


def decompc(va, timeout, n=260):
    fn = fm.getFunctionContaining(addr(va))
    if fn is None:
        return '[no function at 0x%x]' % va
    try:
        r = decomp.decompileFunction(fn, timeout, mon)
        if r.decompileCompleted():
            return '\n'.join(str(r.getDecompiledFunction().getC()).splitlines()[:n])
        return '[decomp failed/timeout]'
    except Exception as e:
        return '[exc %s]' % e


print('=' * 72)
print('main FUN_000147d0')
print('=' * 72)
print(decompc(0x147d0, 120, 120))

print('\n' + '=' * 72)
print('FUN_009f95e0 (big ADJ_FLAT consumer) — data refs first')
print('=' * 72)
fn = fm.getFunctionAt(addr(0x9f95e0))
if fn:
    body = fn.getBody()
    seen = set()
    inst = listing.getInstructions(body, True)
    for ins in inst:
        for ref in ins.getReferencesFrom():
            t = ref.getToAddress().getUnsignedOffset()
            # data region refs (rodata/data, > code)
            if t >= 0x1900000 and t not in seen:
                seen.add(t)
                sym = prog.getSymbolTable().getPrimarySymbol(ref.getToAddress())
                print('  %s -> 0x%x %s' % (ins.getAddress(), t, sym.getName() if sym else ''))
print('\n--- decompile (long timeout) ---')
print(decompc(0x9f95e0, 240, 300))

print('\n[ProbeMainAndBig] done.')
