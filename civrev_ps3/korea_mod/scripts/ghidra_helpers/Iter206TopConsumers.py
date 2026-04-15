# -*- coding: utf-8 -*-
# Iter206TopConsumers.py
#
# iter-205 found 139 callers of bl 0x12080 (the virtual method dispatch
# stub) grouped into 50 functions. Top 10 by call count are all heavy
# consumers of civnames-holding class methods. Decompile them to see
# which is the carousel render path.

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
    a = addr(va)
    fn = fm.getFunctionAt(a)
    if fn is not None:
        return fn
    DisassembleCommand(a, None, True).applyTo(prog, mon)
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


print('')
print('#' * 78)
print('# iter-206: top bl 0x12080 consumer functions')
print('#' * 78)

# Top 10 by call count (iter-206 Python scan):
top_functions = [
    (0x1db4e8, 9),
    (0x1dde84, 9),
    (0x1de750, 6),
    (0x1ded48, 6),
    (0x1e51ac, 6),
    (0x1e5a68, 6),
    (0x224668, 6),
    (0x1d6758, 5),
    (0x1e05c8, 5),
    (0x1e12bc, 5),
]

for va, count in top_functions:
    print('')
    print('# ==== function %#x (%d bl 0x12080 calls) ====' % (va, count))
    decompile_at(va, lim=250,
                 title='top %d/10' % (top_functions.index((va, count)) + 1))

print('')
print('#' * 78)
print('# end iter-206')
print('#' * 78)
