# -*- coding: utf-8 -*-
# DecompRandomCallers.py — decompile the functions that load the
# "Random" string via TOC offsets r2+0xa20 / r2-0x3540. iter-141
# binary scan found 8 such loads clustered around 0xa14XXX, plus
# scattered hits at 0xf46f4, 0x1d4810, 0x86097c, 0xecc81c. The
# cluster is most likely the civ-select cell-grid builder.

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


# Each (load_va, comment) tuple. The function CONTAINING each load
# is what we want.
SITES = [
    (0x000f46f4, 'r2-0x3540 (Random)'),
    (0x001d4810, 'r2+0xa20  (Random)'),
    (0x0086097c, 'r2-0x3540 (Random)'),
    (0x00a14448, 'r2+0xa20  (Random) — cluster'),
    (0x00a14b38, 'r2+0xa20  (Random) — cluster'),
    (0x00a14c34, 'r2+0xa20  (Random) — cluster'),
    (0x00a1fa84, 'r2+0xa20  (Random)'),
    (0x00ecc81c, 'r2-0x3540 (Random)'),
]
# Pre-computed function entries from prologue walk (iter-141 helper):
ENTRIES = [
    0x000f3aac,
    0x001d46fc,
    0x008607fc,
    0x00a130dc,
    0x00a14720,  # contains TWO loads (0xa14b38 and 0xa14c34) — likely carousel
    0x00a1da18,
    0x00ecbd68,
]

found = set(ENTRIES)
for va, note in SITES:
    print('site 0x%x %s' % (va, note))

print('')
print('=' * 72)
print('Decompiling %d unique functions' % len(found))
print('=' * 72)

for entry in sorted(found):
    fn = fm.getFunctionAt(addr(entry))
    if fn is None:
        DisassembleCommand(addr(entry), None, True).applyTo(prog, monitor)
        CreateFunctionCmd(addr(entry)).applyTo(prog, monitor)
        fn = fm.getFunctionAt(addr(entry))
    if fn is None:
        print('FUN_%08x: could not create' % entry)
        continue
    print('')
    print('=' * 72)
    print('FUN_%08x %s (size %d)' % (entry, fn.getName(), fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 180, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:200]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  [decomp failed]')
