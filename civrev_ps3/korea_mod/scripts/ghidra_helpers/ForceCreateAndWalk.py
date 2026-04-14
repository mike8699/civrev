# -*- coding: utf-8 -*-
# ForceCreateAndWalk.py — force Ghidra to disassemble and create
# functions at the REAL parser anchors, then decompile them and
# also BFS forward for a path to FUN_00c26a00.

from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor
from ghidra.program.model.symbol import SourceType

prog = currentProgram
af = prog.getAddressFactory()
fm = prog.getFunctionManager()
listing = prog.getListing()

decomp = DecompInterface()
decomp.openProgram(prog)
monitor = ConsoleTaskMonitor()


def addr(va):
    return af.getAddress(hex(va)[2:].rstrip('L'))


# Disassemble the code flow starting at each anchor so Ghidra can
# follow calls. Use Ghidra's DisassembleCommand.
from ghidra.app.cmd.disassemble import DisassembleCommand
from ghidra.app.cmd.function import CreateFunctionCmd

ANCHORS = [
    (0xa2e640, 'real_parser_worker'),
    (0xa2ec54, 'real_parser_dispatcher'),
]

for va, name in ANCHORS:
    a = addr(va)
    # Disassemble if no instruction yet
    if listing.getInstructionAt(a) is None:
        cmd = DisassembleCommand(a, None, True)
        ok = cmd.applyTo(prog, monitor)
        print('disasm at 0x%x: %s' % (va, ok))
    # Create function via CreateFunctionCmd which auto-detects body
    cfc = CreateFunctionCmd(a)
    ok = cfc.applyTo(prog, monitor)
    print('CreateFunctionCmd at 0x%x: %s' % (va, ok))
    fn = fm.getFunctionAt(a)
    if fn is not None:
        try:
            fn.setName(name, SourceType.USER_DEFINED)
        except Exception as e:
            print('  setName: %s' % e)

# Decompile them
for va, name in ANCHORS:
    fn = fm.getFunctionAt(addr(va))
    if fn is None:
        print('\n[no function at 0x%x after force-create]' % va)
        continue
    print('\n' + '=' * 72)
    print('%s @ 0x%x (size=%d)' % (fn.getName(), va, fn.getBody().getNumAddresses()))
    print('=' * 72)
    result = decomp.decompileFunction(fn, 120, monitor)
    if result.decompileCompleted():
        code = str(result.getDecompiledFunction().getC())
        for i, line in enumerate(code.splitlines()[:80]):
            print('%4d  %s' % (i + 1, line))
    else:
        print('  decomp failed')

# Now BFS from real_parser_dispatcher to FUN_00c26a00.
target = 0xc26a00


def called_from(fn_va):
    fn = fm.getFunctionAt(addr(fn_va))
    if fn is None:
        return set()
    result = set()
    try:
        for callee in fn.getCalledFunctions(monitor):
            result.add(callee.getEntryPoint().getUnsignedOffset())
    except Exception:
        pass
    return result


print('\n' + '=' * 72)
print('BFS from real_parser_dispatcher 0xa2ec54 to 0x%x' % target)
print('=' * 72)
visited = set([0xa2ec54])
parent = {0xa2ec54: None}
depth = {0xa2ec54: 0}
queue = [0xa2ec54]
chain = None
MAX_DEPTH = 10
while queue:
    cur = queue.pop(0)
    if depth[cur] >= MAX_DEPTH:
        continue
    for cal in called_from(cur):
        if cal in visited:
            continue
        visited.add(cal)
        parent[cal] = cur
        depth[cal] = depth[cur] + 1
        if cal == target:
            chain = []
            node = target
            while node is not None:
                fn = fm.getFunctionAt(addr(node))
                chain.append('%s @ 0x%x (d=%d)' % (
                    fn.getName() if fn else '0x%x' % node,
                    node, depth[node]))
                node = parent[node]
            chain.reverse()
            break
        queue.append(cal)
    if chain:
        break

if chain:
    print('REACHED in %d hops!' % (len(chain) - 1))
    for step in chain:
        print('  %s' % step)
else:
    print('NOT reached within %d hops (visited=%d fns)' % (MAX_DEPTH, len(visited)))
