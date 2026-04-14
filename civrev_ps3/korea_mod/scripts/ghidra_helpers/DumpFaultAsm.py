# -*- coding: utf-8 -*-
# DumpFaultAsm.py
#
# iter-114 parallel: iter-21 claimed the faulting instruction at
# 0xc26a98 is `stb r0, 0(r11)`. Validate by dumping the actual
# disassembly around that address. Also dump the 8 instructions
# leading up to it so we can see where r11 gets its value.
#
# Jython 2.7.

prog = currentProgram
af = prog.getAddressFactory()
listing = prog.getListing()
fm = prog.getFunctionManager()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


FAULT_SITE = 0xc26a98
WINDOW_BEFORE = 48
WINDOW_AFTER = 16

print('Disassembly around 0x%x:' % FAULT_SITE)
print('-' * 72)
for off in range(-WINDOW_BEFORE, WINDOW_AFTER + 1, 4):
    a = addr(FAULT_SITE + off)
    insn = listing.getInstructionAt(a)
    marker = '>>' if off == 0 else '  '
    if insn is None:
        print('%s 0x%08x  <no instruction>' % (marker, FAULT_SITE + off))
        continue
    operands = insn.getDefaultOperandRepresentation(0) if insn.getNumOperands() else ''
    if insn.getNumOperands() > 1:
        operands += ', ' + insn.getDefaultOperandRepresentation(1)
    if insn.getNumOperands() > 2:
        operands += ', ' + insn.getDefaultOperandRepresentation(2)
    print('%s 0x%08x  %-8s %s' % (
        marker, FAULT_SITE + off,
        insn.getMnemonicString(), operands))

# Also dump the function containing the fault site.
fn = fm.getFunctionContaining(addr(FAULT_SITE))
print('')
print('=' * 72)
if fn:
    print('Function: %s @ 0x%x (size=%d)' % (
        fn.getName(),
        fn.getEntryPoint().getUnsignedOffset(),
        fn.getBody().getNumAddresses()))
else:
    print('No function at 0x%x' % FAULT_SITE)

# Dump the entire function body assembly.
if fn:
    print('-' * 72)
    print('Full function disassembly:')
    print('-' * 72)
    body_iter = listing.getInstructions(fn.getBody(), True)
    for insn in body_iter:
        a = insn.getAddress().getUnsignedOffset()
        marker = '>>' if a == FAULT_SITE else '  '
        parts = [insn.getMnemonicString()]
        for i in range(insn.getNumOperands()):
            parts.append(insn.getDefaultOperandRepresentation(i))
        print('%s 0x%08x  %s' % (marker, a, ' '.join(parts[:1] + [', '.join(parts[1:])])))
