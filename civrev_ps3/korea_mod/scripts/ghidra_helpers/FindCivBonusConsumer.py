# -*- coding: utf-8 -*-
# FindCivBonusConsumer.py  (path-b iter-2, 2026-05-31)
#
# Locate the EBOOT consumer of the text.ini [CIVBONUSTEXT] / [LBTEXT]
# bonus pools. These section-name strings are the xref anchors:
#   CIVBONUSTEXT @ 0x16dd35e (2nd 0x16ee4d2)
#   LBTEXT       @ 0x16928a9 (2nd 0x169bf94)
#
# For each: (1) code/data references to the string, (2) rodata pointer-table
# entries holding &string (the parser's section registry), (3) decompile of
# every referencing function so we can see how the parsed array is indexed
# by the civ/leader enum.
#
# Jython 2.7 — % formatting, no f-strings.
# Run: analyzeHeadless ghidra/ civrev -process EBOOT.ELF \
#        -scriptPath korea_mod/scripts/ghidra_helpers \
#        -postScript FindCivBonusConsumer.py -noanalysis

import jarray
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()
mem = prog.getMemory()

# True in-program vaddrs (PS3 ELF loader != raw file offset), found by
# ASCII-searching the Ghidra program memory 2026-05-31.
TARGETS = [
    (0x016ccf96, 'CIVBONUSTEXT'),
    (0x016dec7a, 'CIVBONUSTEXT_2'),
    (0x01684569, 'LBTEXT'),
    (0x0168dc9c, 'LBTEXT_2'),
]

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress('0x%x' % va)


def be4(v):
    out = []
    for sh in (24, 16, 8, 0):
        b = (v >> sh) & 0xff
        out.append(b if b < 128 else b - 256)
    return jarray.array(out, 'b')


def decomp_c(fn, maxlines=160):
    try:
        res = decomp.decompileFunction(fn, 90, monitor)
        if not res.decompileCompleted():
            return '  [decomp failed]'
        return '\n'.join(str(res.getDecompiledFunction().getC()).splitlines()[:maxlines])
    except Exception as e:
        return '  [decomp exc: %s]' % e


fns_to_decomp = []  # list of (entry_va, why)


def remember(fn, why):
    if fn is None:
        return
    va = fn.getEntryPoint().getUnsignedOffset()
    if va not in [v for v, _ in fns_to_decomp]:
        fns_to_decomp.append((va, why))


# --- 1 & 2: references + pointer-table scan -------------------------------
for va, label in TARGETS:
    a = addr(va)
    print('\n' + '=' * 74)
    print('STRING 0x%x  %s' % (va, label))
    print('=' * 74)

    refs = list(rm.getReferencesTo(a))
    print('  getReferencesTo -> %d' % len(refs))
    for r in refs:
        src = r.getFromAddress()
        rt = r.getReferenceType().getName()
        fn = fm.getFunctionContaining(src)
        ins = listing.getInstructionAt(src)
        print('    %-12s from %s  fn=%s  %s' %
              (rt, src, fn.getName() if fn else '<none>',
               ins.toString() if ins else '<data>'))
        remember(fn, 'ref to %s' % label)

    # pointer-table scan: who stores &string as a 4-byte BE word?
    pat = be4(va)
    found = 0
    start = mem.getMinAddress()
    while True:
        hit = mem.findBytes(start, pat, None, True, monitor)
        if hit is None:
            break
        # skip the string's own bytes region
        ptr_owner = fm.getFunctionContaining(hit)
        print('    PTR &%s stored at %s  (in fn=%s)' %
              (label, hit, ptr_owner.getName() if ptr_owner else '<data/table>'))
        # dump the 0x18 bytes around it as candidate {name_ptr, type, dest} struct
        base = hit.subtract(8)
        row = []
        for i in range(8):
            try:
                w = mem.getInt(base.add(i * 4)) & 0xffffffff
            except Exception:
                w = -1
            row.append('0x%08x' % w)
        print('       window @ %s: %s' % (base, ' '.join(row)))
        remember(ptr_owner, 'ptr-table to %s' % label)
        found += 1
        start = hit.add(1)
        if found > 12:
            print('    (>12 pointer hits, stopping)')
            break
    if found == 0:
        print('    (no 4-byte BE pointer to the string found in memory)')


# --- 3: decompile every collected function --------------------------------
print('\n\n' + '#' * 74)
print('# DECOMPILES (%d functions)' % len(fns_to_decomp))
print('#' * 74)
for va, why in fns_to_decomp:
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        continue
    print('\n' + '-' * 74)
    print('FUNCTION %s @ 0x%x   (%s)   size=%d' %
          (fn.getName(), va, why, fn.getBody().getNumAddresses()))
    print('-' * 74)
    print(decomp_c(fn))

print('\n[FindCivBonusConsumer] done.')
