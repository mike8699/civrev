# -*- coding: utf-8 -*-
# IdentifyRealFaultFn.py
#
# iter-115 breakthrough: the RPCS3 log at iter-20 captured
# PC=0xc26a00 (the faulting PPU thread's actual instruction) and
# last-executed 0xc26a24: `7c 7e 1b 78` = mr r30, r3.
#
# Raw bytes at 0xc26a00 are `2f 04 00 00 7c 08 02 a6 f8 21 ff 71`
# = cmpwi cr6, r4, 0 / mfspr LR / stdu r1,-... — a function
# PROLOGUE, not mid-function instructions. So 0xc26a00 IS a
# function entry and iter-21..114 all chased the wrong function
# FUN_00c26960 at 0xc26960.
#
# Find the Ghidra function whose entry is at 0xc26a00 (or closest),
# decompile it, and inspect the register-state dump from the log
# (r3..r11 at fault, r5="Sejong", r11=0x2a120) for what actually
# happens.

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


# 1. What function contains 0xc26a00 in Ghidra's current database?
fn1 = fm.getFunctionContaining(addr(0xc26a00))
print('getFunctionContaining(0xc26a00) =>', fn1.getName() if fn1 else 'None',
      '@ 0x%x' % (fn1.getEntryPoint().getUnsignedOffset() if fn1 else 0))

# 2. Is there an explicit function AT 0xc26a00?
fn2 = fm.getFunctionAt(addr(0xc26a00))
print('getFunctionAt(0xc26a00) =>', fn2.getName() if fn2 else 'None')

# 3. Disassemble 0xc26a00 through 0xc26b20 using Ghidra's listing.
print('')
print('Disassembly 0xc26a00..0xc26b20 (what Ghidra thinks is there):')
for va in range(0xc26a00, 0xc26b24, 4):
    a = addr(va)
    insn = listing.getInstructionAt(a)
    if insn is None:
        print('  0x%08x  <no instruction>' % va)
        continue
    parts = [insn.getMnemonicString()]
    for i in range(insn.getNumOperands()):
        parts.append(insn.getDefaultOperandRepresentation(i))
    line = '%-8s %s' % (parts[0], ', '.join(parts[1:]))
    marker = '>>' if va == 0xc26a00 else '  '
    print('%s 0x%08x  %s' % (marker, va, line))

# 4. If Ghidra doesn't recognize 0xc26a00 as a function entry,
# create one and decompile.
if fn2 is None:
    print('')
    print('NO function at 0xc26a00 — creating one and decompiling.')
    from ghidra.program.model.symbol import SourceType
    try:
        fm.createFunction(None, addr(0xc26a00), None, SourceType.USER_DEFINED)
    except Exception as e:
        print('  createFunction failed: %s' % e)
    fn2 = fm.getFunctionAt(addr(0xc26a00))
    if fn2:
        print('  created %s' % fn2.getName())

if fn2:
    print('')
    print('Decompile of function at 0xc26a00:')
    result = decomp.decompileFunction(fn2, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:200]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  decomp failed')
