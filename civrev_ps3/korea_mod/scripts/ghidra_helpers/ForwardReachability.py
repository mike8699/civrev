# -*- coding: utf-8 -*-
# ForwardReachability.py
#
# iter-119: BFS forward through the static call graph from the
# name-file parser worker FUN_00a216d4 AND the scenario init
# FUN_0002fb78 looking for any path that reaches FUN_00c26a00.
# Also try starting from FUN_00a21ce8 and some other anchors.

from ghidra.util.task import ConsoleTaskMonitor

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
rm = prog.getReferenceManager()
listing = prog.getListing()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


def called_from(fn_va):
    """Return set of callee function entry addresses."""
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        return set()
    # Use Ghidra's getCalledFunctions — more reliable than scanning
    # instruction refs which can be filtered by flow override.
    result = set()
    try:
        for callee in fn.getCalledFunctions(ConsoleTaskMonitor()):
            result.add(callee.getEntryPoint().getUnsignedOffset())
    except Exception as e:
        print('  getCalledFunctions error for 0x%x: %s' % (fn_va, e))
    return result


TARGET = 0xc26a00

# Multi-root BFS
roots = [
    (0x00a216d4, 'parser_worker'),
    (0x00a21ce8, 'parser_dispatcher'),
    (0x0002fb78, 'scenario_init'),
    (0x00010ef0, 'TOC_stub_to_dispatcher'),
]

for root_va, root_name in roots:
    print('')
    print('=' * 72)
    print('BFS from %s @ 0x%x -> 0x%x' % (root_name, root_va, TARGET))
    print('=' * 72)
    visited = set([root_va])
    parent = {root_va: None}
    queue = [root_va]
    found_chain = None
    max_depth = 8
    depths = {root_va: 0}
    while queue:
        cur = queue.pop(0)
        d = depths[cur]
        if d >= max_depth:
            continue
        for callee in called_from(cur):
            if callee in visited:
                continue
            visited.add(callee)
            parent[callee] = cur
            depths[callee] = d + 1
            if callee == TARGET:
                found_chain = []
                node = TARGET
                while node is not None:
                    fn = fm.getFunctionAt(addr(node))
                    name = fn.getName() if fn else '0x%x' % node
                    found_chain.append('%s @ 0x%x (depth=%d)' % (
                        name, node, depths[node]))
                    node = parent[node]
                found_chain.reverse()
                break
            queue.append(callee)
        if found_chain:
            break

    if found_chain:
        print('REACHED FUN_00c26a00 in %d hops!' % (len(found_chain) - 1))
        for step in found_chain:
            print('  %s' % step)
    else:
        print('NOT reached within depth %d (visited=%d)' % (max_depth, len(visited)))
