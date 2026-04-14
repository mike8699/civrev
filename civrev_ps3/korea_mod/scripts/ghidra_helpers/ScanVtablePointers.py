# -*- coding: utf-8 -*-
# ScanVtablePointers.py
#
# iter-115: FUN_00c26960 is a method in a class with vtable at
# 0x018fa158 (or some offset of the 0x018fa118 block). Find class
# instances in data memory by scanning for the vtable address as a
# 4-byte word. Uses Ghidra's Memory.findBytes which handles
# memory holes correctly.
#
# Jython 2.7.

import jarray

prog = currentProgram
af = prog.getAddressFactory()
mem = prog.getMemory()

# Candidate vtable addresses: 0x018fa158 is where FUN_00c26960's
# fdesc lives, but the class vtable `this->vtable` probably points
# at the START of the fdesc block — somewhere in 0x018fa118..0x018fa1d8.
CANDIDATES = []
for start in range(0x018fa100, 0x018fa200, 4):
    CANDIDATES.append(start)


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def signed_byte(b):
    """Convert a 0..255 int to Java signed byte range."""
    return b if b < 128 else b - 256


for vt_va in CANDIDATES:
    # Build 4 bytes in big-endian order as Java signed bytes.
    pattern = jarray.array([
        signed_byte((vt_va >> 24) & 0xFF),
        signed_byte((vt_va >> 16) & 0xFF),
        signed_byte((vt_va >> 8) & 0xFF),
        signed_byte(vt_va & 0xFF),
    ], 'b')
    mask = jarray.array([-1, -1, -1, -1], 'b')

    # Walk each loaded memory block and findBytes forward.
    hits = []
    for block in mem.getBlocks():
        if not block.isInitialized():
            continue
        start = block.getStart()
        end = block.getEnd()
        cur = start
        while cur is not None and cur.compareTo(end) < 0:
            try:
                found = mem.findBytes(cur, end, pattern, mask, True, None)
            except Exception:
                break
            if found is None:
                break
            hits.append(found.getUnsignedOffset())
            try:
                cur = found.add(4)
            except Exception:
                break
    if hits:
        print('')
        print('vtable candidate 0x%x: %d hits' % (vt_va, len(hits)))
        for h in hits[:12]:
            print('  0x%08x' % h)
