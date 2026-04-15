# -*- coding: utf-8 -*-
# DecompDispatcher.py — find what calls parser_worker (FUN_00a2e640)
# and what count argument they pass. The iter-14 patches at 0xa2ee38
# and 0xa2ee7c bumped count from 17 to 18 in TWO sites — but the
# civ18-only test triggers a fault at 0x141fa4c that suggests there's
# ANOTHER fixed-size 17-slot array somewhere downstream of the parsed
# civnames array.
#
# Strategy: decompile the parser_dispatcher region around 0xa2ee30
# and look for any other references to 17 (0x11) that affect array
# sizing.

from ghidra.app.decompiler import DecompInterface
from ghidra.app.cmd.function import CreateFunctionCmd
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

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


# parser_dispatcher per iter-119: starts at 0xa2ec54, with the iter-14
# li r5, 0x11 patches at 0xa2ee38 and 0xa2ee7c.
TARGETS = [
    (0x00a2ec54, 'parser_dispatcher (caller of parser_worker)'),
]

for va, name in TARGETS:
    fn = ensure_fn(va)
    print('')
    print('=' * 72)
    print('%s @ 0x%x' % (name, va))
    if fn is None:
        print('  [could not create]')
        print('=' * 72)
        continue
    print('size=%d body_min=%s body_max=%s' % (
        fn.getBody().getNumAddresses(),
        fn.getBody().getMinAddress(),
        fn.getBody().getMaxAddress(),
    ))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 240, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:200]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')

# Also look at xrefs from parser_worker (FUN_00a2e640) calls — what
# functions does it call that might have hardcoded 17?
print('')
print('=' * 72)
print('All bl call targets inside parser_worker body 0xa2e640..0xa2eb50')
print('=' * 72)
mem = prog.getMemory()
import struct
def get_word(va):
    a = addr(va)
    return mem.getInt(a) & 0xffffffff

for off in range(0xa2e640, 0xa2eb50, 4):
    try:
        w = get_word(off)
    except Exception:
        continue
    op = (w >> 26) & 0x3f
    if op == 18 and (w & 1):  # bl
        li = w & 0x03fffffc
        if li & 0x02000000:
            li -= 0x04000000
        target = (off + li) & 0xffffffff
        # Resolve target name if it's a known function
        ta = addr(target)
        tf = fm.getFunctionContaining(ta)
        tname = tf.getName() if tf else '?'
        print('  0x%08x: bl 0x%08x  %s' % (off, target, tname))
