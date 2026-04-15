# -*- coding: utf-8 -*-
# Iter207ChooseCivOwners.py
#
# iter-207 found only 4 lwz sites for the ChooseCiv panel function
# descriptor (TOC slot r2-0x2998 = 0x1957810 = 0x191a7f0 with
# r2 = 0x195a1a8). Three of the 4 are ref-count / init / index-dispatch
# bookkeeping. The most promising is FUN_00932a20 at site 0x932bf4,
# which STORES the descriptor into a class field (stw r0, 0(r9)).
#
# Decompile:
#   FUN_00932a20 - the class that holds the ChooseCiv panel descriptor
#   FUN_00f057b0 - the panel-by-index dispatcher
#   FUN_0011b17c - the panel refcount wrapper (for completeness)
#
# All with the correct TOC r2 = 0x195a1a8.

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
print('# iter-207: ChooseCiv panel descriptor owners')
print('#' * 78)

decompile_at(0x932a20, lim=300,
             title='FUN_00932a20 (stores ChooseCiv desc into class field)')
print('')
decompile_at(0xf057b0, lim=200,
             title='FUN_00f057b0 (panel-by-index dispatcher)')
print('')
decompile_at(0x11b17c, lim=200,
             title='FUN_0011b17c (panel refcount wrapper)')
print('')

# Also decompile the call target at 0xc649e4 (acquire) and 0xc6499c (release)
decompile_at(0xc649e4, lim=100,
             title='FUN_00c649e4 (panel acquire/retain)')
print('')
decompile_at(0xc6499c, lim=100,
             title='FUN_00c6499c (panel release)')
print('')

print('#' * 78)
print('# end iter-207')
print('#' * 78)
