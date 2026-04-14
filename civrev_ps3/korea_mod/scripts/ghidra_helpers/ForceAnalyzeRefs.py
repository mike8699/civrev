# -*- coding: utf-8 -*-
# ForceAnalyzeRefs.py — Ghidra flagged two "<none>" callsites at
# 0x00a6d958 (-> FUN_00ae1bc0) and 0x00011cdc (-> FUN_00a7e080).
# Disassemble 32 instructions around each address to see what
# kind of code is there.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

from ghidra.program.model.symbol import SourceType


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


for site, label in [(0x00a6d958, 'call to FUN_00ae1bc0'),
                    (0x00011cdc, 'call to FUN_00a7e080')]:
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (label, site))
    print('=' * 72)
    fn = fm.getFunctionContaining(addr(site))
    if fn is not None:
        print('  enclosing fn: %s @ 0x%x' % (
            fn.getName(), fn.getEntryPoint().getUnsignedOffset()))
    else:
        print('  NO enclosing fn in Ghidra DB')
    # Walk backward up to 0x200 bytes looking for a function prologue
    prologue_start = None
    for back in range(0, 0x400, 4):
        va = site - back
        insn = listing.getInstructionAt(addr(va))
        if insn is None:
            continue
        mnem = insn.getMnemonicString().lower()
        if mnem == 'stdu':
            # likely prologue
            prologue_start = va
            break
    if prologue_start:
        print('  likely function entry: 0x%x' % prologue_start)
    # Dump 16 insns before and 8 after the call
    print('  disassembly around call site:')
    for off in range(-60, 20, 4):
        va = site + off
        insn = listing.getInstructionAt(addr(va))
        marker = '>>' if off == 0 else '  '
        if insn is None:
            print('%s 0x%08x  <no insn>' % (marker, va))
            continue
        operands = []
        for i in range(insn.getNumOperands()):
            operands.append(insn.getDefaultOperandRepresentation(i))
        print('%s 0x%08x  %-8s %s' % (
            marker, va, insn.getMnemonicString(), ', '.join(operands)))
