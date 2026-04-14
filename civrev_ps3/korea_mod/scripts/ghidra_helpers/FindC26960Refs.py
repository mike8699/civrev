# -*- coding: utf-8 -*-
# FindC26960Refs.py
#
# iter-107: FUN_00c26960 has zero direct bl callers. It must be
# invoked through a function pointer or vtable. Find every
# reference (code + data) to FUN_00c26960's entry address, then
# walk outward to find the actual caller chain.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
mem = prog.getMemory()
listing = prog.getListing()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


target = addr(0x00c26960)

# All references to the entry address
all_refs = list(rm.getReferencesTo(target))
print('FUN_00c26960 has %d refs' % len(all_refs))
for r in all_refs:
    src = r.getFromAddress()
    fn = fm.getFunctionContaining(src)
    print('  %-14s from %s in %s' % (
        r.getReferenceType().getName(),
        src,
        fn.getName() if fn else '<no-fn>'))

# The rodata for this binary is the single big text/rodata segment.
# A full memory scan hits holes. Instead, look at the known data
# reference at 0x018fa158 found above and dump its neighborhood.
print('')
print('Vtable/fdesc around known data ref 0x018fa158:')
hits = [0x018fa158]
print('  %d hits' % len(hits))
for h in hits:
    # What's around it? A vtable / fdesc will have the neighbors be
    # other function pointers.
    print('  0x%08x:' % h)
    for off in range(-64, 128, 4):
        try:
            v = mem.getInt(addr(h + off)) & 0xFFFFFFFF
        except Exception:
            continue
        fn = fm.getFunctionAt(addr(v)) if 0x10000 <= v <= 0x1500000 else None
        marker = '<' if off == 0 else ' '
        print('   %s +0x%03x  %08x  %s' % (
            marker, off, v, fn.getName() if fn else ''))

# Also: what's the parent class of FUN_00c26960? Check the function
# body start for a `mr r3, r3` convention (or the prologue pattern).
# Look for nearby functions in 0xc26xxx to guess the class scope.
print('')
print('Nearby functions in 0xc26xxx (class scope guess):')
for off in range(-0x400, 0x800, 0x10):
    a = addr(0x00c26960 + off)
    fn = fm.getFunctionContaining(a)
    if fn and fn.getEntryPoint().getUnsignedOffset() not in \
            [0x00c26960]:
        print('  %s @ 0x%x (size=%d)' % (
            fn.getName(),
            fn.getEntryPoint().getUnsignedOffset(),
            fn.getBody().getNumAddresses()))
