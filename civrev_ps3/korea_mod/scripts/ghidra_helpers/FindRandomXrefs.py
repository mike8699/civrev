# -*- coding: utf-8 -*-
# FindRandomXrefs.py — locate the carousel cell-grid builder by
# walking xrefs to the "Random" string at vaddr 0x168ef7d (the
# civ-select fallback "Random" cell label).
#
# Strategy:
#   1. Find the "Random" string in the binary.
#   2. List every xref to it (computed addresses, lis/addi pairs,
#      TOC entries — Ghidra's reference manager handles all of them).
#   3. For each xref, identify the enclosing function and decompile it.
#   4. The right function is the cell-grid builder — it iterates 0..15
#      to render civ cells and falls back to "Random" for cell 16.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
ref_mgr = prog.getReferenceManager()
mem = prog.getMemory()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


# Possible "Random" string addresses from the iter-141 binary scan:
#   vaddr 0x168ef7d   "Random\0\0\0\0\0PS3 Profi"
#   vaddr 0x169d290   "Random\0\0@ORDINAL @RU"
TARGETS = [0x168ef7d, 0x169d290]

print('=' * 72)
print('XREFS TO "Random" STRINGS')
print('=' * 72)

found_callers = set()
for va in TARGETS:
    a = addr(va)
    print('')
    print('--- xrefs to vaddr 0x%x ---' % va)
    refs_iter = ref_mgr.getReferencesTo(a)
    n_refs = 0
    while refs_iter.hasNext():
        ref = refs_iter.next()
        from_addr = ref.getFromAddress()
        ref_type = ref.getReferenceType().getName()
        fn = fm.getFunctionContaining(from_addr)
        fn_name = fn.getName() if fn else '?'
        fn_entry = fn.getEntryPoint().getOffset() if fn else 0
        print('  %s in %s (entry 0x%x) [%s]' % (
            from_addr, fn_name, fn_entry, ref_type))
        if fn:
            found_callers.add(fn_entry)
        n_refs += 1
    if n_refs == 0:
        print('  (no refs found by Ghidra reference manager — likely'
              ' lis/addi pair not yet analyzed)')

# Decompile each unique caller
print('')
print('=' * 72)
print('DECOMPILED CALLERS (%d unique)' % len(found_callers))
print('=' * 72)
for entry in sorted(found_callers):
    fn = fm.getFunctionAt(addr(entry))
    if fn is None:
        DisassembleCommand(addr(entry), None, True).applyTo(prog, monitor)
        CreateFunctionCmd(addr(entry)).applyTo(prog, monitor)
        fn = fm.getFunctionAt(addr(entry))
    print('')
    print('--- 0x%x %s (size %d) ---' % (entry, fn.getName(), fn.getBody().getNumAddresses()))
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:80]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')

# Even if Ghidra has zero refs to the "Random" string, the lis+addi
# pair that computes its address is still in the binary. Scan for
# `lis rN, 0x168` followed by `addi rN, rN, 0xef7d` (the high+low
# 16-bit halves of 0x168ef7d) within ~16 bytes.
print('')
print('=' * 72)
print('STATIC SCAN FOR lis/addi PAIRS COMPUTING 0x168ef7d')
print('=' * 72)

import struct
raw_size = mem.getSize()
def get_word(va):
    try:
        return mem.getInt(addr(va)) & 0xffffffff
    except Exception:
        return None

# 0x168ef7d split: high = 0x168f, low = -0x83 (0xff7d sign-extended)
# (since 0x168ef7d = (0x168f << 16) - 0x83)
# Or with addi (signed 16-bit imm): high = 0x168f, low = -0x83
# Encoded: addis rN, 0, 0x168f  then  addi rN, rN, -0x83
HIGH = 0x168f  # because 0x168f0000 - 0x83 = 0x168eff7d... wait
# 0x168ef7d = 0x168f0000 - 0x83 = 0x168f0000 - 0x83 = 0x168efF7D
# Actually 0x168f0000 - 0x83 = 0x168effFD. Not matching.
# Let me compute properly: 0x168ef7d
#   high16 ext low16 = (0x168ef7d >> 16) + (1 if (0x168ef7d & 0x8000) else 0)
#   low16 = 0x168ef7d & 0xffff = 0xef7d, signed = -0x1083
#   high16 needs to compensate: 0x168ef7d - (-0x1083) = 0x168ef7d + 0x1083 = 0x16900000
#   so addis 0x1690, addi -0x1083
HIGH = 0x1690
LOW = -0x1083

print('Looking for: addis rN, 0, %#x ; addi rN, rN, %d' % (HIGH, LOW))

text_start = 0x10000
text_end = 0x1853648 + 0x10000  # rough
hits = 0
for off in range(text_start, text_end - 8, 4):
    w0 = get_word(off)
    if w0 is None: continue
    op = (w0 >> 26) & 0x3f
    if op != 15:  # addis
        continue
    rt = (w0 >> 21) & 0x1f
    ra = (w0 >> 16) & 0x1f
    if ra != 0:
        continue
    si = w0 & 0xffff
    if si != HIGH:
        continue
    # Check next 1-3 instructions for addi rN, rN, LOW
    for d in (4, 8, 12):
        w1 = get_word(off + d)
        if w1 is None: continue
        op1 = (w1 >> 26) & 0x3f
        if op1 != 14:  # addi
            continue
        rt1 = (w1 >> 21) & 0x1f
        ra1 = (w1 >> 16) & 0x1f
        if ra1 != rt or rt1 != rt:
            continue
        si1 = w1 & 0xffff
        if si1 & 0x8000:
            si1 -= 0x10000
        if si1 != LOW:
            continue
        fn = fm.getFunctionContaining(addr(off))
        fn_name = fn.getName() if fn else '?'
        fn_entry = fn.getEntryPoint().getOffset() if fn else 0
        print('  0x%08x: addis r%d, 0, %#x; +%d addi -> %s (entry 0x%x)' % (
            off, rt, HIGH, d, fn_name, fn_entry))
        hits += 1
        if fn:
            found_callers.add(fn_entry)
        break

print('Found %d lis/addi pairs computing 0x168ef7d' % hits)
