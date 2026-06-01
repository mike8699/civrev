# -*- coding: utf-8 -*-
# DecompAtAddr.py (path-b iter-11) — decompile the function containing a target
# address in civrev_clean, seeding disassembly + setting the main TOC so the
# body is readable. Target(s) passed via the TARGETS list below.
#
# Run: analyzeHeadless ghidra_clean/ civrev_clean -process EBOOT_v130_clean.ELF \
#   -scriptPath korea_mod/scripts/ghidra_helpers -postScript DecompAtAddr.py

from java.math import BigInteger
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
ctx = prog.getProgramContext()
listing = prog.getListing()
mon = ConsoleTaskMonitor()
TOC = 0x193a288

# qBeginTurn era-threshold site found by the cmpwi 4/0xd/0x17 scan.
TARGETS = [0xa22810, 0x9d1bac]


def addr(va):
    return af.getAddress('0x%x' % va)


def ensure_fn(va):
    # seed-disassemble a window before the target so the function body exists
    for seed in (va - 0x600, va - 0x400, va - 0x200, va):
        DisassembleCommand(addr(seed), None, True).applyTo(prog, mon)
    fn = fm.getFunctionContaining(addr(va))
    if fn is None:
        # scan back for a likely entry; just create at a 0x100-aligned-ish start
        a = addr(va - 0x400)
        try:
            createFunction(a, None)
        except Exception:
            pass
        fn = fm.getFunctionContaining(addr(va))
    return fn


decomp = DecompInterface()
decomp.openProgram(prog)

for va in TARGETS:
    fn = ensure_fn(va)
    if fn is None:
        print('no function containing 0x%x' % va)
        continue
    body = fn.getBody()
    ctx.setValue(ctx.getRegister('r2'), body.getMinAddress(), body.getMaxAddress(),
                 BigInteger.valueOf(TOC))
    entry = fn.getEntryPoint().getUnsignedOffset()
    print('=' * 72)
    print('FUNCTION containing 0x%x: %s @ 0x%x  size=%d' %
          (va, fn.getName(), entry, body.getNumAddresses()))
    print('=' * 72)
    # list called functions (HasLBonus/AddTech/SetEra candidates)
    called = []
    for ins in listing.getInstructions(body, True):
        m = ins.getMnemonicString()
        if m in ('bl', 'b'):
            for r in ins.getReferencesFrom():
                t = r.getToAddress().getUnsignedOffset()
                if 0x10000 <= t < 0x1680000 and t not in called:
                    called.append(t)
    print('calls: %s' % ['0x%x' % c for c in called[:40]])
    try:
        res = decomp.decompileFunction(fn, 120, mon)
        if res.decompileCompleted():
            print(str(res.getDecompiledFunction().getC()))
        else:
            print('[decomp failed]')
    except Exception as e:
        print('[exc %s]' % e)

print('[DecompAtAddr] done.')
