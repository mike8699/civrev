# -*- coding: utf-8 -*-
# Jython-safe version: no f-strings
prog = currentProgram
fm = prog.getFunctionManager()
af = prog.getAddressFactory()
rm = prog.getReferenceManager()

sites = [0xc26c4c, 0xc43fe4, 0xc4a330, 0xc4a884, 0xc4b18c]

def get_callers(va):
    addr = af.getAddress(hex(va)[2:].rstrip('L'))
    callers = set()
    for ref in rm.getReferencesTo(addr):
        if ref.getReferenceType().isCall():
            fn = fm.getFunctionContaining(ref.getFromAddress())
            if fn:
                callers.add(fn.getEntryPoint().getUnsignedOffset())
    return callers

targets = {0x0002fb78, 0x00a21ce8, 0x00010ef0, 0x00010590, 0x009dca5c}

for site in sites:
    addr = af.getAddress(hex(site)[2:].rstrip('L'))
    fn = fm.getFunctionContaining(addr)
    if fn is None:
        print("%s: no fn" % hex(site))
        continue
    fn_va = fn.getEntryPoint().getUnsignedOffset()
    print("")
    print("%s is in %s @ %s (size=%d)" %
          (hex(site), fn.getName(), fn.getEntryPoint(), fn.getBody().getNumAddresses()))
    current = set([fn_va])
    found = None
    for d in range(5):
        next_level = set()
        for va in current:
            for c in get_callers(va):
                next_level.add(c)
                if c in targets:
                    found = (d+1, c)
        if not next_level:
            break
        print("  d%d: n=%d" % (d+1, len(next_level)))
        if found:
            print("  *** FOUND target %s at depth %d ***" % (hex(found[1]), found[0]))
            break
        current = next_level
