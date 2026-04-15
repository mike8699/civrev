# -*- coding: utf-8 -*-
# Iter205HolderConsumers.py
#
# Decompile the newly-found civnames holder consumer functions:
#   FUN_001dc0d8  — reads ENTIRE holder struct via unrolled sequence
#                   (iter-204 discovered)
#   FUN_0x111dd70 — contains lwz rN, 0xd50(r2) at 0x111dd90
#                   (iter-204 discovered)
#
# Both are called via r2 = 0x194a1f8 (iter-202 parser dispatcher TOC
# base, which turns out to be THE main-module TOC for ~28.5k functions,
# not a specialized PRX TOC). At that TOC, the offset 0xd50 reaches
# 0x194af48 = &civs_buf_holder = 0x1ac93b8.
#
# This script decompiles both, plus the two helper functions they
# call (bl 0x11230 and bl 0x12080) which are PRX import stubs in the
# low address range.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('%x' % va)


def ensure_function(va):
    """Force-create a function at va if Ghidra hasn't already."""
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is not None:
        return fn
    # Try disassembling first
    DisassembleCommand(a, None, True).applyTo(prog, mon)
    # Create function
    CreateFunctionCmd(a).applyTo(prog, mon)
    return fm.getFunctionAt(a)


def decompile_at(va, lim=250, title=None):
    ensure_function(va)
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        fn = fm.getFunctionContaining(addr(va))
    if fn is None:
        print('  [no function at 0x%x]' % va)
        return
    print('=' * 78)
    print('%s  FUN_%08x (size=%d)' % (
        title or '', fn.getEntryPoint().getUnsignedOffset(),
        fn.getBody().getNumAddresses()))
    print('=' * 78)
    res = decomp.decompileFunction(fn, 180, mon)
    if not res.decompileCompleted():
        print('  [decomp failed: %s]' % res.getErrorMessage())
        return
    code = str(res.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:lim]):
        print('%4d  %s' % (i + 1, line))


def dump_insns(start, end):
    """Dump raw instructions in a range."""
    print('=' * 78)
    print('  raw disas %#x .. %#x' % (start, end))
    print('=' * 78)
    listing = prog.getListing()
    it = listing.getInstructions(addr(start), True)
    while it.hasNext():
        ins = it.next()
        va = ins.getAddress().getUnsignedOffset()
        if va >= end:
            break
        ops = []
        for k in range(ins.getNumOperands()):
            ops.append(ins.getDefaultOperandRepresentation(k))
        print('  %#010x  %-8s %s' % (va, ins.getMnemonicString(),
                                      ', '.join(ops)))


print('')
print('#' * 78)
print('# iter-205: decomp holder-struct consumers')
print('#' * 78)

# 1. FUN_001dc0d8 — the big unrolled consumer found in iter-204
decompile_at(0x1dc0d8, lim=400, title='FUN_001dc0d8 (iter-204 big consumer)')
print('')

# 2. FUN_0x111dd70 — the other outlier consumer
decompile_at(0x111dd70, lim=400, title='FUN_0x111dd70 (iter-204 outlier)')
print('')

# 3. The intra-module-TOC-switching bl targets
decompile_at(0xc71674, lim=200, title='FUN_00c71674 (target of bl 0x11230)')
print('')
decompile_at(0xa97ca8, lim=200, title='FUN_00a97ca8 (target of bl 0x12080)')
print('')

# 3. The helper targets — these are PRX stubs in the low address range.
# Dump their raw bytes to see what they do (stubs are usually tiny).
dump_insns(0x11230, 0x11260)
print('')
dump_insns(0x12080, 0x120b0)
print('')

# 4. Also decompile the parser dispatcher FUN_00a2ec54 WITH the
# corrected TOC base so we can compare the holder accesses.
decompile_at(0x00a2ec54, lim=200, title='FUN_00a2ec54 (dispatcher — re-decomp)')

print('')
print('#' * 78)
print('# end iter-205')
print('#' * 78)
