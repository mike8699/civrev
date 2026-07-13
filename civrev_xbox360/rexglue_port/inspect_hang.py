#!/usr/bin/env python3
"""gdb script: break in sub_8268E100 (the turn-wait step), read the PPC context,
and dump the values the wait loop depends on — especially the timer
[[r13+256]+88] and the elapsed threshold. Run twice (a few seconds apart, via
two breakpoint hits) to see whether the timer ADVANCES (stuck => infinite loop).

Guest memory is BIG-ENDIAN; r13 is a guest virtual address -> host = 0x100000000+addr.
PPCContext offsets (Register=8B, order r3,r0,r1,r2,r4,r5,...): r13=0x68, r29=0xE8, r31=0xF8, r3=0x00.
Usage (inside container):  gdb -p <pid> -batch -x inspect_hang.py
"""
import gdb

VMEM = 0x100000000  # virtual membase

def rd_be32(guest_addr):
    """Read a big-endian uint32 from guest virtual memory."""
    host = VMEM + (guest_addr & 0xFFFFFFFF)
    raw = gdb.selected_inferior().read_memory(host, 4)
    return int.from_bytes(bytes(raw), 'big')

def rd_ctx_u32(ctx, off):
    """Low 32 bits of a PPC register (stored little-endian in the host union)."""
    raw = gdb.selected_inferior().read_memory(ctx + off, 4)
    return int.from_bytes(bytes(raw), 'little')

def snapshot(tag):
    ctx = int(gdb.parse_and_eval("$rdi"))
    r13 = rd_ctx_u32(ctx, 0x68)
    r29 = rd_ctx_u32(ctx, 0xE8)
    r31 = rd_ctx_u32(ctx, 0xF8)   # the arg struct (r1+80 from caller)
    sp  = rd_be32(r13 + 256)      # [r13+256] -> struct pointer
    timer88  = rd_be32(sp + 88)   # r30 in the loop (the wait clock)
    field332 = rd_be32(sp + 332)  # sub_82809E98 return
    flag_10941 = gdb.selected_inferior().read_memory(VMEM + r29 + 10941, 1)[0]
    if isinstance(flag_10941, (bytes, bytearray)): flag_10941 = flag_10941[0]
    f10888 = rd_be32(r29 + 10888)
    arg8  = rd_be32(r31 + 8)
    arg12 = rd_be32(r31 + 12)
    print(f"[{tag}] ctx={ctx:#x} r13={r13:#010x} [r13+256]={sp:#010x} r29={r29:#010x} r31={r31:#010x}")
    print(f"[{tag}]   TIMER [struct+88]={timer88}  [struct+332]={field332}")
    print(f"[{tag}]   arg.8={arg8} arg.12(last_timer)={arg12} elapsed={(timer88-arg12)&0xFFFFFFFF} (exit when >=5000)")
    print(f"[{tag}]   flag[r29+10941]={flag_10941:#04x} (bit1 set => exit)  [r29+10888]={f10888}")
    return timer88

gdb.execute("set pagination off")
gdb.execute("break sub_8268E100")
gdb.execute("continue")
t0 = snapshot("hit1")
# advance a few loop iterations of real wall-time, then sample again
gdb.execute("delete breakpoints")
gdb.execute("break sub_8268E100")
import time
# let it run ~4s of guest wall time across many iterations
for _ in range(200):
    gdb.execute("continue")
t1 = snapshot("hit200")
print(f"[RESULT] timer advanced by {(t1 - t0) & 0xFFFFFFFF} over 200 loop iterations "
      f"({'STUCK -> infinite loop' if t1 == t0 else 'advancing'})")
gdb.execute("detach")
gdb.execute("quit")
