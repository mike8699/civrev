# -*- coding: utf-8 -*-
# FindNameFileXrefs.py
#
# For the DoD item 1 blocker (18-entry civnames/rulernames crash):
# find every instruction that references the civnames/rulernames
# filename strings, the name-file prefix pointer table, and the
# known parser functions. For each hit, dump the enclosing function
# entry point + a short decompiled snippet so iter-105+ can see
# who actually reads the parser output at runtime.
#
# Jython 2.7 — use % formatting, no f-strings.
#
# Run: analyzeHeadless ghidra/ civrev -process EBOOT.ELF \
#         -scriptPath korea_mod/scripts/ghidra_helpers \
#         -postScript FindNameFileXrefs.py -noanalysis

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()

# Interesting targets — every address known to participate in the
# civnames/rulernames path as of iter-94.
TARGETS = [
    (0x016ee550, 'str_RulerNames_'),
    (0x016ee560, 'str_CivNames_'),
    (0x0194b648, 'name_prefix_ptr_table_base'),
    (0x0194b660, 'name_prefix_RulerNames_ptr'),
    (0x0194b664, 'name_prefix_CivNames_ptr'),
    (0x00a21ce8, 'FUN_name_file_init_dispatcher'),
    (0x00a216d4, 'FUN_name_file_worker_parser'),
    (0x00a2ee38, 'li_r5_0x11_RulerNames'),
    (0x00a2ee7c, 'li_r5_0x11_CivNames'),
]

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def decomp_snippet(fn, greps=None, n_lines=40):
    """Return first n_lines of the decompile, filtered by `greps` if set."""
    try:
        result = decomp.decompileFunction(fn, 60, monitor)
    except Exception as e:
        return '  [decomp exception: %s]' % e
    if not result.decompileCompleted():
        return '  [decomp failed]'
    code = str(result.getDecompiledFunction().getC())
    lines = code.splitlines()
    if greps:
        filtered = [l for l in lines if any(g in l for g in greps)]
        return '\n'.join(filtered[:n_lines])
    return '\n'.join(lines[:n_lines])


for va, label in TARGETS:
    a = addr(va)
    refs = list(rm.getReferencesTo(a))
    print('')
    print('=' * 72)
    print('target 0x%x  %s  -> %d references' % (va, label, len(refs)))
    print('=' * 72)
    if not refs:
        continue
    seen_fns = set()
    for r in refs:
        src = r.getFromAddress()
        rt = r.getReferenceType()
        fn = fm.getFunctionContaining(src)
        fn_name = fn.getName() if fn else '<no-fn>'
        fn_va = fn.getEntryPoint().getUnsignedOffset() if fn else 0
        print('  %-12s from %s in %s @ 0x%x  %s' %
              (rt.getName(), src, fn_name, fn_va,
               listing.getInstructionAt(src).toString()
               if listing.getInstructionAt(src) else ''))
        if fn and fn_va not in seen_fns:
            seen_fns.add(fn_va)
    if seen_fns:
        print('')
        print('  unique caller functions:')
        for fn_va in sorted(seen_fns):
            fn = fm.getFunctionAt(addr(fn_va))
            if fn is None:
                continue
            print('    * %s @ 0x%x (size=%d)' %
                  (fn.getName(), fn_va, fn.getBody().getNumAddresses()))
