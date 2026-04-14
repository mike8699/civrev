# -*- coding: utf-8 -*-
# FindFaultSiteConsumer.py
#
# iter-107: find the function containing the 0xc26a98 faulting
# instruction and decompile it. iter-21/25 pinpointed the fault
# address but never identified the enclosing function. This is
# where the 17-constant consumer of the parsed civnames/rulernames
# is most likely hiding.
#
# Also decompile FUN_00029f18 (the std::vector::insert variant
# that contains the fault-target 0x2a12c) to confirm it's not
# itself the bug.
#
# Jython 2.7.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def find_fn_containing(va):
    a = addr(va)
    return fm.getFunctionContaining(a)


def dump_fn(fn, label, max_lines=200):
    print('')
    print('=' * 72)
    print('%s' % label)
    if fn is None:
        print('  [no function]')
        return
    entry = fn.getEntryPoint().getUnsignedOffset()
    print('entry=0x%x size=%d' % (entry, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if not result.decompileCompleted():
        print('  [decomp failed]')
        return
    code = str(result.getDecompiledFunction().getC())
    for i, line in enumerate(code.splitlines()):
        print('%4d  %s' % (i + 1, line))
        if i + 1 >= max_lines:
            print('  ... [truncated at %d lines]' % max_lines)
            break


# 1. Fault-site enclosing function
fault_fn = find_fn_containing(0xc26a98)
dump_fn(fault_fn, 'FUNCTION CONTAINING FAULT SITE 0xc26a98', max_lines=250)

# 2. FUN_00029f18 — the std::vector::insert variant whose
# instruction at 0x2a12c is the fault target
vec_fn = fm.getFunctionAt(addr(0x00029f18))
dump_fn(vec_fn, 'FUN_00029f18 (vector::insert variant)', max_lines=150)

# 3. The init function we found — full body
init_fn = fm.getFunctionAt(addr(0x0002fb78))
dump_fn(init_fn, 'FUN_0002fb78 AFTER name-file init — find 17 consumer',
        max_lines=400)
