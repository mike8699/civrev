# -*- coding: utf-8 -*-
# GameObjMethods.py (path-b iter-7) — decompile the game session object's class
# methods to find the player-array member offset. The object (runtime heap,
# from .bss 0x1ac1678) has vtable 0x18a2738; its method descriptors use TOC
# 0x194a1f8 (parser-module TOC), so we set r2=0x194a1f8 per-method for clean
# decompiles. Look for a member iterated to ~8/16 (the player array).
#
# Run: analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript GameObjMethods.py -noanalysis

from java.math import BigInteger
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
mem = prog.getMemory()
ctx = prog.getProgramContext()
listing = prog.getListing()

VTABLE = 0x0188ac38
MODULE_TOC = 0x194a1f8


mon = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


def u32(va):
    return mem.getInt(addr(va)) & 0xffffffff


# read vtable -> method entry points (descriptors {entry, toc})
methods = []
for i in range(24):
    desc = u32(VTABLE + i * 4)
    if not (0x1800000 <= desc < 0x1c00000):
        break
    entry = u32(desc)
    if 0x10000 <= entry < 0x1680000:
        methods.append(entry)
print('vtable 0x%x -> %d methods: %s' % (VTABLE, len(methods),
                                         ['0x%x' % m for m in methods]))

# disassemble + create a function at each method entry (the 0x9axxxx region
# wasn't reached by the seeded analysis), then set r2 = module TOC on its body.
r2 = ctx.getRegister('r2')
for entry in methods:
    a = addr(entry)
    DisassembleCommand(a, None, True).applyTo(prog, mon)
    if fm.getFunctionContaining(a) is None:
        try:
            createFunction(a, None)
        except Exception as e:
            print('  createFunction(0x%x) failed: %s' % (entry, e))
    fn = fm.getFunctionContaining(a)
    if fn:
        body = fn.getBody()
        ctx.setValue(r2, body.getMinAddress(), body.getMaxAddress(),
                     BigInteger.valueOf(MODULE_TOC))

decomp = DecompInterface()
decomp.openProgram(prog)

# decompile the first several methods; flag member-offset loops
for idx, entry in enumerate(methods[:8]):
    fn = fm.getFunctionContaining(addr(entry))
    if fn is None:
        print('\n[vtbl+%d] 0x%x no function' % (idx, entry))
        continue
    print('\n' + '=' * 70)
    print('[vtbl+%d] method @ 0x%x  %s  size=%d' % (
        idx, entry, fn.getName(), fn.getBody().getNumAddresses()))
    print('=' * 70)
    try:
        r = decomp.decompileFunction(fn, 60, mon)
        if r.decompileCompleted():
            code = str(r.getDecompiledFunction().getC())
            for line in code.splitlines()[:55]:
                low = line.lower()
                mark = ''
                if '0x10' in line and ('<' in line or 'cmp' in low or 'while' in low or 'for' in low):
                    mark = '   <== count?'
                if '+ 0x' in line and ('* 4' in line or '<< 2' in line or '* 8' in line):
                    mark = '   <== array idx?'
                print(line + mark)
        else:
            print('[decomp failed]')
    except Exception as e:
        print('[exc %s]' % e)

print('\n[GameObjMethods] done.')
