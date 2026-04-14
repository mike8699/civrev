# -*- coding: utf-8 -*-
# DumpWorkerCallSite.py — disassemble around parser_worker +
# 0x428 (0xa2ea68) to see the EXACT bl instruction that starts
# the fault chain. Also disassemble FUN_009f1c98 / FUN_009f1d18
# bodies to understand what globals they return.

prog = currentProgram
af = prog.getAddressFactory()
listing = prog.getListing()
fm = prog.getFunctionManager()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def dump_range(label, start, end):
    print('')
    print('=' * 72)
    print('%s: 0x%x..0x%x' % (label, start, end))
    print('=' * 72)
    for va in range(start, end, 4):
        a = addr(va)
        insn = listing.getInstructionAt(a)
        if insn is None:
            print('  0x%08x  <no instruction>' % va)
            continue
        parts = [insn.getMnemonicString()]
        for i in range(insn.getNumOperands()):
            parts.append(insn.getDefaultOperandRepresentation(i))
        mark = '>>' if va == 0xa2ea68 else '  '
        print('%s 0x%08x  %-8s %s' % (
            mark, va, parts[0], ', '.join(parts[1:])))


dump_range('parser_worker near call site', 0xa2ea40, 0xa2ea90)
dump_range('FUN_009f1c98 body', 0x9f1c98, 0x9f1cb0)
dump_range('FUN_009f1d18 body', 0x9f1d18, 0x9f1d38)
dump_range('FUN_00c72dc4 around 348-byte body',
           0xc72dc4, 0xc72dc4 + 60)
