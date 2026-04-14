# -*- coding: utf-8 -*-
# Find the function that contains a BL preceded by `li r5, 0x101`
# (city name count) — the name-init function.
prog = currentProgram
fm = prog.getFunctionManager()
listing = prog.getListing()

hits = []
for fn in fm.getFunctions(True):
    body = fn.getBody()
    if body.getNumAddresses() < 40: continue
    # Walk instructions, detect "li r5, 0x101" followed within 4 insns by "bl"
    prev_li_r5_val = None
    prev_li_r5_pos = None
    count = 0
    addr = body.getMinAddress()
    it = listing.getInstructions(body, True)
    insns = list(it)
    for i, insn in enumerate(insns):
        mnem = insn.getMnemonicString()
        if mnem in ("li", "addi"):
            # Check if dest is r5
            try:
                op0 = str(insn.getDefaultOperandRepresentation(0))
                if op0 == "r5":
                    # Get immediate value
                    op1 = str(insn.getDefaultOperandRepresentation(1))
                    if "0x101" in op1 or op1 == "257":
                        prev_li_r5_val = 0x101
                        prev_li_r5_pos = i
            except:
                pass
        if mnem == "bl" and prev_li_r5_val == 0x101 and i - prev_li_r5_pos <= 4:
            count += 1
            hits.append((fn.getEntryPoint(), fn.getName(), str(insn.getAddress()), count))
            prev_li_r5_val = None

print("Functions with 'li r5, 0x101' followed by bl: %d" % len(hits))
# Group by function entry
seen_fns = set()
for h in hits:
    if h[0] not in seen_fns:
        print("  %s %s at %s" % h[:3])
        seen_fns.add(h[0])
