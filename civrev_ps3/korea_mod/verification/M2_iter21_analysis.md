# Iter-21 disasm finding

v130_clean's function at 0xc26a00..0xc26ac4 is a small string utility (200 bytes). Only ONE non-stack store instruction:

```
0xc26a7c  lwz r11, 0(r30)       ; r11 = *(param_1 + 0)
0xc26a80  addi r9, r11, -16
0xc26a88  lwz r0, 12(r9)         ; r0 = *(r11 - 4)  (length header)
0xc26a8c  add r11, r11, r0       ; r11 = buffer_end
0xc26a90  li r0, 0
0xc26a98  stb r0, 0(r11)         ; *** write 0 to byte at buffer_end ***
```

Semantics: clear the null-terminator byte at the end of a string buffer
(classic FStringA::Clear() or length reset). Param_1 points at an
FStringA object whose internal struct is { char* buf; size_t len; } with
the `len` field stored at offset -4 before the buffer data.

When fed a corrupted FStringA (invalid `buf` pointer), `buffer_end =
*buf + *(buf-4)` can be anywhere — including code memory at 0x2a12c.

The RPCS3 fault log line:
  F 0:00:11.620486 {PPU[0x1000000] ... [0x00c26a00]}
    VM: Access violation writing location 0x2a12c (read-only memory)

is consistent with this instruction being the fault site. The LR context
0xc26a00 points at the function's START (RPCS3 sometimes reports LR = 
current function entry when recording a PPU fault).

## What's corrupted

The caller of this function passed an FStringA whose internal `buf`
pointer is garbage. That FStringA is somewhere in the civ/ruler name
init chain. Extending civnames+rulernames to 18 entries corrupts the
FStringA before this function gets called with it.

## Where to look next

The 5 callers of the function at 0xc26a00 (from iter-19):
- 0xc26c4c
- 0xc43fe4
- 0xc4a330
- 0xc4a884
- 0xc4b18c

One of these is passing the corrupt FStringA. The immediate predecessor
to each bl site sets up r3 (the FStringA pointer). Tracing r3 back to
its source would find the corruption origin — most likely a function
that constructs an FStringA from the parsed name data and assumes a
17-entry bound on some indexing.

## Blocker remaining

Identifying WHICH caller, and WHICH downstream allocation is 17-wide,
still requires further RE. But the crash is now pinpointed to a specific
instruction pattern in a specific small function.
