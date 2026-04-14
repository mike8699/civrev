# -*- coding: utf-8 -*-
# Decompile specific candidate functions and look for name-file patterns
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
fm = prog.getFunctionManager()
af = prog.getAddressFactory()
decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()

candidates = [0x00a21ce8, 0x00ad2218, 0x00d018e8, 0x00f35b38, 0x00f36508, 0x00f368e8]
for va in candidates:
    addr = af.getAddress(hex(va)[2:].rstrip('L'))
    fn = fm.getFunctionAt(addr)
    if fn is None:
        print("no fn at %x" % va)
        continue
    print("\n==== %s (%s) ====" % (fn.getName(), addr))
    result = decomp.decompileFunction(fn, 60, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        # Print only lines that contain name-file-related strings or key patterns
        for line in code.splitlines():
            if any(k in line for k in ("CivNames", "RulerNames", "CityNames", "FamousNames",
                                        "UnitNames", "TechNames", "Wondernames", "Landmark",
                                        "GenderedNames", "17", "0x11", "0x30", "0x52", "0x101")):
                print("  %s" % line.strip()[:120])
    else:
        print("  decomp failed")
