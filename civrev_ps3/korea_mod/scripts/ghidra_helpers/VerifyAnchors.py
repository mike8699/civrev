# -*- coding: utf-8 -*-
# VerifyAnchors.py — check that critical function anchors exist
# in the new v130 Ghidra project.

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()

for name, va in [
    ('parser_worker', 0xa216d4),
    ('parser_dispatcher', 0xa21ce8),
    ('scenario_init', 0x2fb78),
    ('TOC_stub_dispatcher', 0x10ef0),
    ('fault_fn', 0xc26a00),
    ('caller_0ae1bc0', 0xae1bc0),
    ('li_r5_11_ruler', 0xa2ee38),
    ('li_r5_11_civ', 0xa2ee7c),
]:
    fn_at = fm.getFunctionAt(af.getAddress(hex(va)[2:].rstrip('L')))
    fn_cont = fm.getFunctionContaining(af.getAddress(hex(va)[2:].rstrip('L')))
    print('%-24s @ 0x%07x  At=%s  Containing=%s' % (
        name, va,
        (fn_at.getName() + ' size=' + str(fn_at.getBody().getNumAddresses())) if fn_at else 'None',
        (fn_cont.getName() + ' size=' + str(fn_cont.getBody().getNumAddresses())) if fn_cont else 'None'))
