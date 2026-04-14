# -*- coding: utf-8 -*-
# AllC26a00Refs.py — find EVERY reference to FUN_00c26a00 and
# FUN_00ae33b0 (call + data), plus refs to their fdesc addresses.
# Some invocations might go via fdesc indirection Ghidra tracks
# as DATA refs only.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
mem = prog.getMemory()

import jarray


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def signed_byte(b):
    return b if b < 128 else b - 256


TARGETS = [
    ('FUN_00c26a00', 0xc26a00),
    ('FUN_00011020', 0x11020),
    ('FUN_000297d0', 0x297d0),
    ('FUN_00036314', 0x36314),
    ('FUN_00ae3160', 0xae3160),
    ('FUN_00ae33b0', 0xae33b0),
    ('FUN_00ae1bc0', 0xae1bc0),
    ('FUN_00a7e080', 0xa7e080),
]


def find_pattern_bytes(target_va):
    pattern = jarray.array([
        signed_byte((target_va >> 24) & 0xFF),
        signed_byte((target_va >> 16) & 0xFF),
        signed_byte((target_va >> 8) & 0xFF),
        signed_byte(target_va & 0xFF),
    ], 'b')
    mask = jarray.array([-1, -1, -1, -1], 'b')
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
    return hits


for name, va in TARGETS:
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (name, va))
    print('=' * 72)

    # Ghidra's known refs (any type)
    refs = list(rm.getReferencesTo(addr(va)))
    print('known refs from Ghidra: %d' % len(refs))
    for r in refs[:20]:
        src = r.getFromAddress()
        fn = fm.getFunctionContaining(src)
        print('  %-14s from %s in %s' % (
            r.getReferenceType().getName(),
            src,
            fn.getName() if fn else '<none>'))

    # Raw byte pattern scan: the address as a 4-byte word in memory
    hits = find_pattern_bytes(va)
    print('raw 4-byte word matches: %d' % len(hits))
    for h in hits[:20]:
        fn = fm.getFunctionContaining(addr(h))
        print('  0x%08x  %s' % (
            h, ('in ' + fn.getName()) if fn else '(data)'))
