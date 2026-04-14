# -*- coding: utf-8 -*-
# FindVtableInstances.py
#
# iter-112 parallel track: the fault-site method FUN_00c26960 is
# slot 0x20 of a big fdesc-style vtable at 0x018fa118. A class
# instance that uses this vtable will have its first field (this->
# vtable) be a pointer to somewhere in 0x018fa118..0x018fa1d8.
# Find every code reference to this range — those are the
# constructors / assignment sites that set a class instance's
# vtable pointer.
#
# Jython 2.7.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


# The vtable spans 0x018fa118..0x018fa1d8 based on iter-107's dump.
# Walk every 4-byte word in that range and collect all references.
VT_START = 0x018fa118
VT_END = 0x018fa1d8

print('scanning references to vtable words 0x%x..0x%x' % (VT_START, VT_END))
all_refs = []
for va in range(VT_START, VT_END, 4):
    a = addr(va)
    for r in rm.getReferencesTo(a):
        all_refs.append((va, r))

print('total refs: %d' % len(all_refs))

seen_fns = set()
for vt_va, r in all_refs:
    src = r.getFromAddress()
    fn = fm.getFunctionContaining(src)
    if fn is None:
        print('  vt +0x%03x ref at %s (no fn, type=%s)' %
              (vt_va - VT_START, src, r.getReferenceType().getName()))
        continue
    fn_va = fn.getEntryPoint().getUnsignedOffset()
    if fn_va not in seen_fns:
        seen_fns.add(fn_va)
    insn = listing.getInstructionAt(src)
    print('  vt +0x%03x  %-14s from %s in %s @ 0x%x  %s' % (
        vt_va - VT_START,
        r.getReferenceType().getName(),
        src,
        fn.getName(), fn_va,
        insn.toString() if insn else ''))

# Decompile each unique caller — they're likely class constructors
# that assign the vtable pointer to `this->vtable`.
print('')
print('=' * 72)
print('UNIQUE CALLER FUNCTIONS (decompiled snippets)')
print('=' * 72)
for fn_va in sorted(seen_fns):
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        continue
    print('')
    print('-- %s @ 0x%x (size=%d) --' % (
        fn.getName(), fn_va, fn.getBody().getNumAddresses()))
    result = decomp.decompileFunction(fn, 60, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        continue
    code = str(result.getDecompiledFunction().getC())
    for line in code.splitlines()[:50]:
        print('  %s' % line)
