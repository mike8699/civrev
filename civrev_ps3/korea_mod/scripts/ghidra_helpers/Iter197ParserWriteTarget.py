# -*- coding: utf-8 -*-
# Iter197ParserWriteTarget.py
#
# Goal: identify the 17-wide downstream buffer that is OOB-written when
# the civnames parser is asked to read 18 entries. iter-14 found that
# bumping the parser limit (li r5, 0x11 -> 0x12 at 0xa2ee38/0xa2ee7c) is
# necessary but insufficient — there's a separate buffer pre-allocated
# to 17 wide that gets overflowed on the 18th row write. iter-22
# established that the late-fault site at 0xc26a98 is in a downstream
# consumer not directly on the init path, meaning the corruption happens
# during init and surfaces 11.6 s later.
#
# This script:
#   1. Decompiles FUN_00a21ce8 (dispatcher), FUN_00a216d4 (parser worker)
#   2. Disassembles the BL FUN_00a216d4 sites in the dispatcher to dump
#      the `addi rN, ...` that builds the per-call output buffer pointer
#   3. For each "this/output" register passed at the civnames bl site,
#      walks back ~12 instructions to find what it points at
#
# Output goes to stdout — capture via analyzeHeadless redirect.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('%x' % va)


def decompile_fn(va, lim=200):
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        print('  [no function at 0x%x]' % va)
        return
    print('=' * 76)
    print('FUN_%08x  (size=%d)' % (va, fn.getBody().getNumAddresses()))
    print('=' * 76)
    res = decomp.decompileFunction(fn, 180, mon)
    if not res.decompileCompleted():
        print('  [decomp failed: %s]' % res.getErrorMessage())
        return
    code = str(res.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:lim]):
        print('%4d  %s' % (i + 1, line))


def find_bl_sites(fn_va, target_va):
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        return []
    sites = []
    for insn in listing.getInstructions(fn.getBody(), True):
        for ref in insn.getReferencesFrom():
            if ref.getReferenceType().isCall():
                if ref.getToAddress().getUnsignedOffset() == target_va:
                    sites.append(insn.getAddress().getUnsignedOffset())
    return sites


def disas_window(va_center, before=12, after=4):
    print('  -- disas window around 0x%x (-%d/+%d insns) --' % (
        va_center, before, after))
    insn = listing.getInstructionAt(addr(va_center))
    if insn is None:
        print('  [no instruction at 0x%x]' % va_center)
        return
    # Walk backward
    chain = []
    cur = insn
    for _ in range(before):
        prev = cur.getPrevious()
        if prev is None:
            break
        chain.insert(0, prev)
        cur = prev
    chain.append(insn)
    cur = insn
    for _ in range(after):
        nxt = cur.getNext()
        if nxt is None:
            break
        chain.append(nxt)
        cur = nxt
    for ins in chain:
        va = ins.getAddress().getUnsignedOffset()
        marker = '   '
        if va == va_center:
            marker = '>>>'
        ops = []
        for i in range(ins.getNumOperands()):
            ops.append(ins.getDefaultOperandRepresentation(i))
        print('  %s 0x%08x  %-7s %s' % (
            marker, va, ins.getMnemonicString(), ', '.join(ops)))


print('')
print('#' * 78)
print('# iter-197: parser write-target hunt')
print('#' * 78)

# Step 1: decompile the dispatcher and worker.
decompile_fn(0xa21ce8, lim=300)  # InitGenderedNamesDispatcher
print('')
decompile_fn(0xa216d4, lim=300)  # parser worker
print('')

# Step 2: find all bl FUN_00a216d4 inside the dispatcher.
bl_sites = find_bl_sites(0xa21ce8, 0xa216d4)
print('')
print('=' * 76)
print('bl FUN_00a216d4 sites inside dispatcher 0xa21ce8:')
for s in bl_sites:
    print('  0x%08x' % s)

# Step 3: For each bl site, dump the surrounding setup window.
print('')
print('=' * 76)
for s in bl_sites:
    disas_window(s, before=14, after=2)
    print('')

# Step 4: decompile the "real parser worker" 0xa2e640 (named in
# DecompParserWorkerFull.py) — iter-13 thought this was the real worker.
print('')
decompile_fn(0xa2e640, lim=300)

# Step 5: dump anything 0xa2ed6c..0xa2ee80 — the function with li r5,
# 0x11 sequence iter-14 found. This is the function that actually has
# the civnames/rulernames count constants.
print('')
# Find function containing 0xa2ee38
fn_li = fm.getFunctionContaining(addr(0xa2ee38))
if fn_li is not None:
    fn_va = fn_li.getEntryPoint().getUnsignedOffset()
    print('Function containing 0xa2ee38: 0x%x' % fn_va)
    decompile_fn(fn_va, lim=400)
else:
    print('No function contains 0xa2ee38')

print('')
print('#' * 78)
print('# end iter-197 dump')
print('#' * 78)
