# -*- coding: utf-8 -*-
# SeedDisasmAnalyze.py (path-b iter-4) — properly seed disassembly of the
# fresh civrev_clean project. The default import only found ~510 functions
# because the ELF entry is a PPC64 descriptor in .data; the real entry is
# 0x147d0 (descriptor target, toc=0x193a288 == addresses.py TOC_BASE).
#
# Seed from the real entry + known addresses.py code addresses and FOLLOW
# FLOW (DisassembleCommand followFlow=True) so we disassemble along real code
# paths — NOT a brute-force range, which disassembles data-as-code and sends
# Ghidra into an infinite function-repair loop (iter-3). Then auto-analyze.
#
# Run (drives analysis; no -noanalysis):
# analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript SeedDisasmAnalyze.py

from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.plugin.core.analysis import AutoAnalysisManager

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()

SEEDS = [
    0x000147d0,  # REAL entry (descriptor target)
    # parser path (addresses.py)
    0x00a216d4, 0x00a21ce8, 0x00a2ec54, 0x00a2e640,
    # ADJ_FLAT consumer functions (containing the civ-text builders)
    0x0013cbf0, 0x0017e95c, 0x0097d878, 0x0097e060, 0x009f6c88,
    0x009f95e0, 0x00ff07e8,
    # fault region
    0x00c26a00,
]


def addr(va):
    return af.getAddress('0x%x' % va)


print('functions before: %d' % fm.getFunctionCount())

for va in SEEDS:
    a = addr(va)
    # follow flow from this seed (restrictedSet=None, followFlow=True)
    DisassembleCommand(a, None, True).applyTo(prog, monitor)
    if fm.getFunctionContaining(a) is None:
        try:
            createFunction(a, None)
        except Exception as e:
            print('  createFunction(0x%x) failed: %s' % (va, e))

print('functions after seed-disasm: %d' % fm.getFunctionCount())

# Let auto-analysis follow the newly disassembled calls + resolve data refs.
mgr = AutoAnalysisManager.getAnalysisManager(prog)
mgr.startAnalysis(monitor)
print('functions after analysis: %d' % fm.getFunctionCount())

for va, nm in [(0x195fe28, 'ADJ_FLAT'), (0x1938354, 'ADJ_FLAT_TOC_ptr')]:
    print('  %s 0x%x -> %d refs' % (nm, va, len(list(rm.getReferencesTo(addr(va))))))

print('[SeedDisasmAnalyze] done (headless saves the program).')
