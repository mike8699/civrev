# -*- coding: utf-8 -*-
# CompareBytes.py — dump raw bytes at 0xc26a80..0xc26ab0 as
# Ghidra sees them. If Ghidra shows different bytes than the
# local EBOOT_v130_clean.ELF, Ghidra's project is tracking a
# different binary and iter-114/115 conclusions were invalid.

prog = currentProgram
af = prog.getAddressFactory()
mem = prog.getMemory()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


print('ghidra bytes at 0xc26a80..0xc26b00:')
for va in range(0xc26a80, 0xc26b00, 4):
    a = addr(va)
    try:
        b = [mem.getByte(a.add(i)) & 0xFF for i in range(4)]
    except Exception as e:
        print('  0x%x: %s' % (va, e))
        continue
    word = (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]
    print('  0x%08x: %02x %02x %02x %02x  (word=0x%08x)' %
          (va, b[0], b[1], b[2], b[3], word))
