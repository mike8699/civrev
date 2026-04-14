# -*- coding: utf-8 -*-
# DumpFun00c26a00.py — full instruction dump of FUN_00c26a00
# in the correct v130 binary. We need to see every bl and every
# conditional branch to plan a minimal null-guard patch that
# silently skips the operation when *param_1 == 0.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


fn = fm.getFunctionAt(addr(0xc26a00))
print('FUN_00c26a00 @ 0xc26a00 (size=%d)' % fn.getBody().getNumAddresses())
print('')
for insn in listing.getInstructions(fn.getBody(), True):
    va = insn.getAddress().getUnsignedOffset()
    bytes4 = ''
    for b in insn.getBytes():
        bytes4 += '%02x' % (b & 0xFF)
    parts = [insn.getMnemonicString()]
    for i in range(insn.getNumOperands()):
        parts.append(insn.getDefaultOperandRepresentation(i))
    print('  0x%08x  %s  %-8s %s' % (
        va, bytes4, parts[0], ', '.join(parts[1:])))
