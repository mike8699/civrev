# -*- coding: utf-8 -*-
# Find the exact instruction addresses of "li r5, 0x11" inside FUN_00a21ce8
# that precede calls to FUN_00a216d4 (the name-file init function)
prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

fn_addr = af.getAddress("00a21ce8")
fn = fm.getFunctionAt(fn_addr)
body = fn.getBody()
call_target = af.getAddress("00a216d4")

# Find all instructions in the function
insns = list(listing.getInstructions(body, True))
print("Function %s has %d instructions" % (fn.getName(), len(insns)))

# For each bl to 0x00a216d4, look BACKWARD up to 10 insns for `li r5, N`
for i, insn in enumerate(insns):
    if insn.getMnemonicString() != "bl": continue
    refs = [r for r in insn.getReferencesFrom() if r.getReferenceType().isCall()]
    targets = [r.getToAddress() for r in refs]
    if call_target not in targets: continue
    # Look back for `li r5, N` and `lwz r4, d(r?)`
    print("\n=== BL to FUN_00a216d4 at %s ===" % insn.getAddress())
    for k in range(max(0, i-12), i):
        prev = insns[k]
        line = "  %s  %s %s" % (prev.getAddress(),
                                 prev.getMnemonicString(),
                                 prev.getDefaultOperandRepresentation(0) if prev.getNumOperands() else "")
        if prev.getNumOperands() > 1:
            line += ", " + str(prev.getDefaultOperandRepresentation(1))
        if prev.getNumOperands() > 2:
            line += ", " + str(prev.getDefaultOperandRepresentation(2))
        print(line[:120])
