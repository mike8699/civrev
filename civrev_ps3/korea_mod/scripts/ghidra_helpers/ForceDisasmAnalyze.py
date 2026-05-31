# -*- coding: utf-8 -*-
# ForceDisasmAnalyze.py (path-b iter-3) — the fresh civrev_clean import only
# found 538 functions because the ELF entry is a PPC64 function descriptor in
# the data segment, so flow-seeded disassembly never covered .text. Force-
# disassemble the executable code range and re-run auto-analysis.
#
# Run (NOT -noanalysis; we drive analysis ourselves):
# analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript ForceDisasmAnalyze.py

from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.program.model.address import AddressSet
from ghidra.app.plugin.core.analysis import AutoAnalysisManager

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()


def addr(va):
    return af.getAddress('0x%x' % va)


print('functions before: %d' % fm.getFunctionCount())

# seg0 is 0x10000..0x1863648 (R E). Code occupies the lower part; rodata
# strings begin ~0x168xxxx. Disassemble the code region generously.
lo, hi = addr(0x10000), addr(0x1680000)
aset = AddressSet(lo, hi)
print('disassembling 0x10000..0x1680000 ...')
cmd = DisassembleCommand(aset, None, True)
ok = cmd.applyTo(prog, monitor)
print('  disassemble applied: %s' % ok)

mgr = AutoAnalysisManager.getAnalysisManager(prog)
mgr.reAnalyzeAll(aset)
mgr.startAnalysis(monitor)
print('functions after analysis: %d' % fm.getFunctionCount())

# control check: does ADJ_FLAT table now have refs (from its TOC pointer)?
from ghidra.program.model.symbol import RefType
rm = prog.getReferenceManager()
for va, nm in [(0x195fe28, 'ADJ_FLAT'), (0x16dd35e, 'CIVBONUSTEXT'),
               (0x169cacd, 'theSelectedOption')]:
    refs = list(rm.getReferencesTo(addr(va)))
    print('  %s 0x%x -> %d refs' % (nm, va, len(refs)))

print('[ForceDisasmAnalyze] done (program will be saved by headless).')
