# -*- coding: utf-8 -*-
# DumpC25f8cAsm.py — full instruction dump of FUN_00c25f8c
# (FStringA::SetLength) to plan a null-guard patch.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


fn = fm.getFunctionAt(addr(0xc25f8c))
print('FUN_00c25f8c @ 0xc25f8c (size=%d)' % fn.getBody().getNumAddresses())
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
