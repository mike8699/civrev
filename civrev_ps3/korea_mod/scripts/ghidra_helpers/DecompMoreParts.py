# -*- coding: utf-8 -*-
# DecompMoreParts.py — chase the rest of the parser/storage chain:
#   FUN_00a00f04 — the second half of entry_init
#   FUN_00c25b1c — the inner allocator called by FUN_00c25ebc
#   FUN_00c72cf8 — the per-line store function called by parser_worker
# Also dump the TOC region around r2-0x52c (where entry_init reads
# the static empty FStringA) to see what static object lives there.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()
mem = prog.getMemory()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def ensure_fn(va):
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is None:
        DisassembleCommand(a, None, True).applyTo(prog, monitor)
        CreateFunctionCmd(a).applyTo(prog, monitor)
        fn = fm.getFunctionAt(a)
    return fn


TARGETS = [
    (0x00a00f04, 'FUN_00a00f04 / entry_init second half'),
    (0x00c25b1c, 'FUN_00c25b1c / inner allocator'),
    (0x00c72cf8, 'FUN_00c72cf8 / per-line entry store'),
    (0x00c27328, 'FUN_00c27328 / store_copy_maybe (line read)'),
]

for va, name in TARGETS:
    fn = ensure_fn(va)
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (name, va))
    if fn is None:
        print('  [could not create function]')
        print('=' * 72)
        continue
    print('size=%d' % fn.getBody().getNumAddresses())
    print('=' * 72)
    result = decomp.decompileFunction(fn, 180, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:120]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')

# Also try to find the TOC base. The disassembler doesn't track r2
# as a constant, but typically the TOC for a PS3 ELFv1 binary is at
# the start of the .data segment. Let's just dump common TOC offsets
# around -0x52c and other small offsets to see what's there.
print('')
print('=' * 72)
print('TOC contents (likely TOC base = 0x193a288 per RPCS3 dump)')
print('=' * 72)
toc_base = 0x193a288
for off in range(-0x540, -0x500, 8):
    a = addr(toc_base + off)
    try:
        v = mem.getLong(a) & 0xffffffffffffffff
        print('  r2%+#x (=%#x): %#018x' % (off, toc_base + off, v))
    except Exception as e:
        print('  r2%+#x: <unreadable> %s' % (off, e))
