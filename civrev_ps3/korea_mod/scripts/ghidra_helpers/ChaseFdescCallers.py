# -*- coding: utf-8 -*-
# ChaseFdescCallers.py
#
# iter-106 follow-up: FUN_00a21ce8 and FUN_00a216d4 have function-
# descriptor table entries at 0x18dfc78 / 0x18dfc80. Those fdescs are
# the indirect-call vehicle that iter-11/22/26 missed when chasing
# the caller chain via direct `bl` refs alone. This script:
#
#   1. Decompiles FUN_00010ef0 (the sole direct caller).
#   2. Finds every reference to the fdesc words at 0x18dfc78 and
#      0x18dfc80 — those are the true upstream callers.
#   3. Walks the caller graph one hop up and dumps the enclosing
#      function entries.
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


def print_fn_decomp(fn, max_lines=60):
    try:
        result = decomp.decompileFunction(fn, 60, monitor)
    except Exception as e:
        print('  [decomp exception: %s]' % e)
        return
    if not result.decompileCompleted():
        print('  [decomp failed]')
        return
    code = str(result.getDecompiledFunction().getC())
    for line in code.splitlines()[:max_lines]:
        print('  %s' % line)


# === Step 1: decompile the sole static caller ===
print('=' * 72)
print('STEP 1: FUN_00010ef0 (the only direct bl caller of FUN_00a21ce8)')
print('=' * 72)
fn = fm.getFunctionAt(addr(0x00010ef0))
if fn is None:
    print('  [no function at 0x10ef0]')
else:
    print_fn_decomp(fn, max_lines=40)
    # Who calls THIS stub?
    print('')
    print('  callers of FUN_00010ef0:')
    for ref in rm.getReferencesTo(addr(0x00010ef0)):
        if ref.getReferenceType().isCall():
            src = ref.getFromAddress()
            parent = fm.getFunctionContaining(src)
            print('    %s from %s in %s' % (
                ref.getReferenceType().getName(),
                src,
                parent.getName() if parent else '<no-fn>'))


# === Step 2: fdesc table references ===
print('')
print('=' * 72)
print('STEP 2: references to fdesc entries 0x18dfc78 / 0x18dfc80')
print('=' * 72)
for fdesc_va, label in [
    (0x018dfc78, 'fdesc_worker_FUN_00a216d4'),
    (0x018dfc80, 'fdesc_dispatcher_FUN_00a21ce8'),
]:
    fdesc = addr(fdesc_va)
    refs = list(rm.getReferencesTo(fdesc))
    print('')
    print('  %s  @ 0x%x  -> %d refs' % (label, fdesc_va, len(refs)))
    seen_fns = set()
    for r in refs:
        src = r.getFromAddress()
        parent = fm.getFunctionContaining(src)
        insn = listing.getInstructionAt(src)
        print('    %-14s from %s in %s  %s' % (
            r.getReferenceType().getName(),
            src,
            parent.getName() if parent else '<no-fn>',
            insn.toString() if insn else ''))
        if parent:
            seen_fns.add(parent.getEntryPoint().getUnsignedOffset())
    if seen_fns:
        print('  unique enclosing functions:')
        for fn_va in sorted(seen_fns):
            f = fm.getFunctionAt(addr(fn_va))
            if f:
                print('    * %s @ 0x%x (size=%d)' %
                      (f.getName(), fn_va, f.getBody().getNumAddresses()))


# === Step 3: scan a wider nearby fdesc region in case the two entries
# are just part of a function-pointer table (fdesc_base) ===
print('')
print('=' * 72)
print('STEP 3: walk 0x18dfc00..0x18dfd00 looking for fn-ptr-shaped entries')
print('=' * 72)
mem = prog.getMemory()
base = 0x18dfc00
for off in range(0x100 / 4):
    a = addr(base + off * 4)
    try:
        val = mem.getInt(a) & 0xFFFFFFFF
    except Exception:
        continue
    # PPC32 text segment heuristic
    if 0x10000 <= val <= 0x1500000:
        fn = fm.getFunctionAt(addr(val))
        name = fn.getName() if fn else '?'
        print('  0x%08x -> 0x%08x %s' % (base + off * 4, val, name))
