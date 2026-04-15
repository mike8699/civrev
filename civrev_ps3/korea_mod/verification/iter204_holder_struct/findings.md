# iter-204: second .data name-file holder table + new consumer functions

**Date:** 2026-04-15
**Findings:**

## Two .data tables point at the .bss name-file holders

iter-202 identified the sparse 8-slot array at `0x194b5f8..0x194b614`
(the dispatcher's TOC offsets `r2+0x1400..0x141c` with r2 =
0x194a1f8). iter-204 discovered a **second** table at
`0x194af2c..0x194af9c` (reachable via the SAME r2 = 0x194a1f8 at
offsets `0xd34..0xda4`). This second table is a LARGER class
instance: 29+ pointer fields, interleaving the 8 .bss buffer
holders with other pointers into rodata and .data.

### Holder struct layout (partial, r2+0xd34..r2+0xda4):

| r2 offset | vaddr | value | meaning |
|---|---|---|---|
| 0xd34 | 0x194af2c | 0x1ac93a0 | UnitNames holder |
| 0xd38 | 0x194af30 | 0x1ac93a4 | ? |
| 0xd3c | 0x194af34 | 0x1ac93a8 | ? |
| 0xd40 | 0x194af38 | 0x1ac356c | (other ptr) |
| 0xd44 | 0x194af3c | 0x1ac93b0 | ? |
| 0xd48 | 0x194af40 | 0x1ac332c | (other ptr) |
| 0xd4c | 0x194af44 | 0x1ac93ac | ? |
| **0xd50** | **0x194af48** | **0x1ac93b8** | **CIVS holder** |
| 0xd54 | 0x194af4c | 0xa22408 | (code ptr) |
| 0xd58 | 0x194af50 | 0x1ac939c | (name slot 0 holder) |
| 0xd5c | 0x194af54 | 0x1969718 | (other ptr) |
| ... | ... | ... | ... |

The civs buffer holder `0x1ac93b8` is at `r2+0xd50` in this
second table.

## Consumer lwz sites for the holder struct

Scan of every lwz rN, 0xd34..0xda4 (r2):

| r2 offset | # lwz sites | sample sites |
|---|---|---|
| 0xd34 (unit?)  | 2 | 0xa22310, 0x111c890 |
| 0xd38          | 4 | 0x1dc0e4, 0xa22328, 0xa29dac, 0xa29ff0 |
| 0xd3c          | 2 | 0x1dc0f0, 0xa22340 |
| 0xd40          | 70 | 0x1dc110, 0xa22358, ... |
| 0xd44          | 2 | 0x1dc10c, 0xa22370 |
| 0xd48          | 2 | 0x1dc124, 0xa22388 |
| 0xd4c (rulers?) | 3 | 0x1dc138, 0xa223a0, 0xa2abf0 |
| **0xd50 (civs)** | **5** | **0x1dc134, 0xa223b8, 0xa2a8c4, 0xa2a9c8, 0x111dd90** |
| 0xd54          | 3 | 0x1dc158, 0xa223ec, 0x111ea00 |
| 0xd58          | 4 | 0x1dc184, 0xa226a0, 0xa22734, 0x111e9f8 |

The `0x1dc0xx` sites are clustered in ONE function:
`FUN_001dc0d8` (entry at `0x1dc0d8`, body ~0x190 bytes, ends at
`0x1dc264 blr`). It reads the ENTIRE holder struct via an
unrolled sequence and calls `bl 0x11230` / `bl 0x12080` with
each name-file holder as an argument.

### FUN_001dc0d8 shape (partial disas)

```
stdu r1, -0xa0(r1)
lwz r28, 0xd38(r2)             ; name slot holder
...
lwz r4, 0xd40(r2); bl 0x12080  ; call with slot
...
lwz r29, 0xd50(r2)             ; r29 = CIVS holder
lwz r31, 0xd4c(r2)             ; r31 = rulers holder(?)
mr r5, r29; mr r4, r31; li r6, 0; bl 0x12080  ; call with civs, r6=0
...
mr r5, r29; mr r4, r31; li r6, 1; bl 0x12080  ; call with civs, r6=1
...
mr r5, r29; mr r4, r31; li r6, 2; bl 0x12080  ; call with civs, r6=2
...
li r6, 3; bl 0x12080  ; more iterations with r6=3 etc.
blr
```

The pattern is `bl 0x12080(r3=r30, r4=rulers_holder, r5=civs_holder,
r6=iter_idx, ...)` called with incrementing r6. `0x12080` is in the
PRX import stub range (below 0x20000) — so this is an EXTERNAL
PRX function call taking the civs+rulers holder addresses.

**This is NOT the typical "iterate civs for carousel" shape.**
It looks like an init or serialization routine that passes name
holders to an external service (sysPrxForUser, cellSysutil,
cellSaveData, or similar).

## Second outlier reader: FUN_0x111dd70

Another lwz site for `r2+0xd50` (the civs holder) exists at
`0x111dd90`, inside function `FUN_0x111dd70` (closest stdu). This
function is far from the main parser region and needs
independent decompilation.

## What's ruled out by iter-204

- Direct `lis rN, 0x01ad; addi rN, rN, -0x6c48` constructions of
  `0x1ac93b8`: 0 hits in the entire binary. No code builds that
  address via immediate pair. All access goes through TOC.
- TOC access from `r2 = 0x193a288` or `r2 = 0x195a1a8`: neither
  can reach `0x1ac93b8` or `0x194af48` via signed-16. Only
  `r2 = 0x194a1f8` can. So only functions in that TOC group
  directly access the civnames holder.

## iter-205 plan

1. **Diagnostic trap on FUN_001dc0d8**. Plant `b .` at its entry
   via a temporary eboot patch, rebuild, run korea_play slot 0
   Romans. If the test hangs/crashes at boot, FUN_001dc0d8 IS on
   the boot path. If it PASSES, FUN_001dc0d8 runs after boot or
   not at all on that path.
2. Same for FUN_0x111dd70.
3. If either is on the carousel path, set Z0 via `test_civs_z0_probe.py`
   at their entry and capture which thread+PC reaches them.
4. Decompile both in Ghidra to see what they do with the holder
   addresses.
5. If neither is on the carousel path, fall back to the navigator-
   fix approach for `test_civs_dump.py` and run the 2-phase scan
   for real.

## Files

- `findings.md` — this
