# -*- coding: utf-8 -*-
# Iter199CarouselWriter.py
#
# Goal: find the civ-select carousel render path's *source*. iter-198
# proved the 18-row civnames/rulernames overlay boots clean, and Korea
# now sits at civnames index 16 in the dynamically-allocated parser
# buffer — but the carousel still renders "Random" at slot 16, meaning
# whatever populates the carousel cells is reading from a different
# source.
#
# iter-197's decompile of real_parser_worker (FUN_00a2e640) shows a
# post-parse block at the tail of the function:
#
#     if (cVar6 != '\0') {
#         iStack_bc = *(int *)(unaff_r2 + 0x13fc) + 0x10;
#         iStack_a0 = iStack_bc;
#         for (iVar7 = 0; iVar7 < iVar10; iVar7 = iVar7 + 1) {
#             FUN_009bf5a0(&iStack_a0, iVar7 * 0xc + *param_2 + 8);
#             iVar8 = *param_2;
#             func_0x00c7258c(&uStack_c0, *(...)(*(uint *)(unaff_r2 + 0x1440)), iStack_a0);
#             func_0x009f1c80(iVar7 * 0xc + iVar8, uStack_c0);
#             FUN_009c2f70(&uStack_c0);
#         }
#     }
#
# The three called functions look like:
#   - FUN_009bf5a0  : read something from (buf + entry*12 + 8), store into iStack_a0
#   - func_0x00c7258c : lookup (some_object, iStack_a0) -> uStack_c0
#   - func_0x009f1c80 : write uStack_c0 into (buf + entry*12) ; i.e.
#                       patch the buffer entry's first field with the
#                       looked-up value
#
# So the parser entry layout is { string, ???, key }: 12 bytes where
# offset 0 holds an FStringA, offset 4 is ???, offset 8 holds a "key"
# or path ID that the post-parse block uses to look up something in the
# external object at r2+0x1440, and the result patches offset 0 of the
# entry back.
#
# This whole block is OPTIONAL (cVar6 gate) — it only runs for some
# name files. Which cVar6 and what's r2+0x1440? Both are what we want
# to know.
#
# Separately, we want to find who reads the civs buffer at r2+0x141c
# AFTER the parser completes. iter-197 already scanned every static
# lwz. None of the static consumers are the carousel (iter-150/154/198
# disproved the 16-count downstream).  The carousel must be reading
# via a cached/copied pointer, not via the TOC slot. Candidates:
#   (a) At parser-worker exit, a copy of the buf ptr is written to
#       some class field elsewhere.
#   (b) Some other reader loads the pointer via addis/addi (not a
#       simple lwz r,N(r2)) or computes it from a struct field.
#   (c) Scaleform Invoke: the PPU calls something like
#       panel->SetVariableArray("theOptionArray", buf, count).
#
# This script:
#   1. Decompiles FUN_009bf5a0, FUN_009f1c80, FUN_00c72cf8, FUN_00c7258c
#   2. Decompiles the post-parse block region of FUN_00a2e640 (already
#      done in iter-197 but re-dumped to match against these functions)
#   3. Finds ALL calls to FUN_00a2e640 + the big class method that
#      holds the 0x1440 field initialization (to locate the mystery
#      "Scaleform UI object")
#   4. Dumps the vtable method that func_0x00c7258c dispatches to

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
ref_mgr = prog.getReferenceManager()

decomp = DecompInterface()
decomp.openProgram(prog)
mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('%x' % va)


def decompile_fn(va, lim=250, title=None):
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        # Try containing
        fn = fm.getFunctionContaining(addr(va))
    if fn is None:
        print('  [no function at 0x%x]' % va)
        return
    print('=' * 78)
    print('%s  FUN_%08x  (entry=%s size=%d)' % (
        title or '', fn.getEntryPoint().getUnsignedOffset(),
        fn.getEntryPoint(), fn.getBody().getNumAddresses()))
    print('=' * 78)
    res = decomp.decompileFunction(fn, 180, mon)
    if not res.decompileCompleted():
        print('  [decomp failed: %s]' % res.getErrorMessage())
        return
    code = str(res.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()[:lim]):
        print('%4d  %s' % (i + 1, line))


def find_callers(target_va):
    t = addr(target_va)
    callers = []
    for ref in ref_mgr.getReferencesTo(t):
        if ref.getReferenceType().isCall():
            callers.append(ref.getFromAddress().getUnsignedOffset())
    return callers


print('')
print('#' * 78)
print('# iter-199: carousel writer hunt')
print('#' * 78)

# 1. The three post-parse helper functions
decompile_fn(0x009bf5a0, lim=80, title='FUN_009bf5a0 (post-parse arg0 builder)')
print('')
decompile_fn(0x009f1c80, lim=80, title='FUN_009f1c80 (post-parse arg1 writer)')
print('')
decompile_fn(0x00c72cf8, lim=80, title='FUN_00c72cf8 (parse-loop line storer)')
print('')
decompile_fn(0x00c7258c, lim=80, title='FUN_00c7258c (lookup at r2+0x1440)')
print('')

# 2. Callers of each
print('=' * 78)
print('callers of FUN_009bf5a0:')
for c in find_callers(0x009bf5a0)[:30]:
    print('  0x%08x' % c)
print('')
print('callers of FUN_009f1c80:')
for c in find_callers(0x009f1c80)[:30]:
    print('  0x%08x' % c)
print('')

# 3. What is r2+0x1440? Dump that TOC slot and find lwz sites that
#    load it. r2 = 0x193a288, so r2+0x1440 = 0x193b6c8.
import struct
slot_va = 0x193a288 + 0x1440
print('TOC slot r2+0x1440 = 0x%x' % slot_va)
mem = prog.getMemory()
slot_bytes = mem.getInt(addr(slot_va))
print('  -> 0x%x' % (slot_bytes & 0xffffffff))
# Dereference: that's probably a class instance pointer.
target_ptr = slot_bytes & 0xffffffff
print('  *r2+0x1440 = 0x%x (probably a class instance pointer)' % target_ptr)

# 4. Find all callers/writers to r2+0x1440 (lwz/stw sites)
print('')
print('all references to addr 0x%x (r2+0x1440 slot):' % slot_va)
for ref in ref_mgr.getReferencesTo(addr(slot_va)):
    from_va = ref.getFromAddress().getUnsignedOffset()
    rt = ref.getReferenceType().getName()
    print('  0x%08x  %s' % (from_va, rt))

# 5. Also dump r2+0x13fc = 0x193b684 (the other mystery TOC slot)
slot13fc = 0x193a288 + 0x13fc
print('')
print('TOC slot r2+0x13fc = 0x%x:' % slot13fc)
print('  references:')
for ref in ref_mgr.getReferencesTo(addr(slot13fc)):
    from_va = ref.getFromAddress().getUnsignedOffset()
    rt = ref.getReferenceType().getName()
    print('  0x%08x  %s' % (from_va, rt))

# 6. Decompile FUN_00a2e640 itself (the parser worker) to compare with
#    iter-197 — already did this. Skip here for brevity.

# 7. The parser dispatcher's caller — who calls FUN_00a2ec54?
print('')
print('=' * 78)
print('callers of FUN_00a2ec54 (real_parser_dispatcher):')
for c in find_callers(0x00a2ec54)[:10]:
    print('  0x%08x' % c)
# Decompile the first caller
callers_dispatcher = find_callers(0x00a2ec54)
if callers_dispatcher:
    first_caller_va = callers_dispatcher[0]
    first_caller_fn = fm.getFunctionContaining(addr(first_caller_va))
    if first_caller_fn is not None:
        fn_va = first_caller_fn.getEntryPoint().getUnsignedOffset()
        print('')
        decompile_fn(fn_va, lim=180,
                     title='first caller of real_parser_dispatcher')

print('')
print('#' * 78)
print('# end iter-199 dump')
print('#' * 78)
