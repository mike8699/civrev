# -*- coding: utf-8 -*-
# SetTocAndDecomp.py (path-b iter-5) — the civrev_clean decompiles are garbled
# because Ghidra doesn't know r2 (the PPC64 TOC base). We DO: the entry
# descriptor gives toc=0x193a288, and *(0x193a288 - 0x1f34) = 0x195fe28 =
# ADJ_FLAT (addresses.py). Setting r2 as a register-context constant over the
# code lets the decompiler resolve TOC-relative loads AND lets analysis create
# the data xrefs that have been missing. (The parser functions use a different
# TOC 0x194a1f8 and will be mis-resolved — acceptable; we want the main-TOC
# game code.)
#
# Run (drives analysis): analyzeHeadless ghidra_clean/ civrev_clean \
#   -process EBOOT_v130_clean.ELF -scriptPath korea_mod/scripts/ghidra_helpers \
#   -postScript SetTocAndDecomp.py

from java.math import BigInteger
from ghidra.app.plugin.core.analysis import AutoAnalysisManager
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
ctx = prog.getProgramContext()
TOC = 0x193a288


def addr(va):
    return af.getAddress('0x%x' % va)


r2 = ctx.getRegister('r2')
print('r2 register: %s' % r2)
lo, hi = addr(0x10000), addr(0x1680000)
ctx.setValue(r2, lo, hi, BigInteger.valueOf(TOC))
print('set r2=0x%x over 0x10000..0x1680000' % TOC)

mgr = AutoAnalysisManager.getAnalysisManager(prog)
mgr.reAnalyzeAll(None)
mgr.startAnalysis(monitor)
print('functions: %d' % fm.getFunctionCount())

# did TOC refs resolve now?
for va, nm in [(0x195fe28, 'ADJ_FLAT'), (0x1938354, 'ADJ_FLAT_TOC_slot')]:
    print('  %s 0x%x -> %d refs' % (nm, va, len(list(rm.getReferencesTo(addr(va))))))

# re-decompile the ADJ_FLAT consumers; should now be readable with TOC resolved
decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()
for va in [0x13cbf0, 0x97d8f0, 0x17e95c]:
    fn = fm.getFunctionContaining(addr(va))
    if fn is None:
        print('\n--- no fn at 0x%x ---' % va)
        continue
    print('\n' + '=' * 70)
    print('FUNCTION %s @ 0x%x' % (fn.getName(), fn.getEntryPoint().getUnsignedOffset()))
    print('=' * 70)
    try:
        res = decomp.decompileFunction(fn, 90, mon)
        if res.decompileCompleted():
            print('\n'.join(str(res.getDecompiledFunction().getC()).splitlines()[:120]))
        else:
            print('[decomp failed]')
    except Exception as e:
        print('[exc %s]' % e)

print('\n[SetTocAndDecomp] done.')
