# Iter-15 — Ghidra deep-trace into the init chain

## Traced the parser and init call chain

Using Ghidra headless decompilation:

### Full init chain (top-down)

```
FUN_0002fb78 (1556 bytes — game-state init)
  → FUN_00010ef0 (16-byte trampoline: sets TOC, calls FUN_00a21ce8)
    → FUN_00a21ce8 (496 bytes — name-file init orchestrator)
      → FUN_00a216d4 x8 (the parser, once per name file)
```

### FUN_00a21ce8 decompiled pattern

```c
void FUN_00a21ce8(void) {
    int iVar1; int iStack_84;
    undefined1 auStack_40[4]; ... auStack_24[12];

    // Unit names (count = GetMaxUniqueUnits() * 2, dynamic)
    FUN_009b8ed0(auStack_24, PTR_s_Play_Scenario_0192ab30);
    iVar1 = iStack_84;
    uVar2 = FUN_00a153e4();
    FUN_00a216d4(auStack_24, *(u4 *)(iVar1 + 0xcc0), (uVar2 & 0xffffffff) << 1);
    FUN_009b4410(auStack_24);

    // Subsequent calls use the same pattern. Struct at iStack_84:
    //   +0xcc0: unitname array ptr
    //   +0xcc4: techname array ptr (count=0x30)
    //   +0xcc8: famousname array ptr (count=0x30)
    //   +0xccc: cityname array ptr (count=0x101)
    //   +0xcd0: wondername array ptr (count=0x42)
    //   +0xcd4: lmarkname array ptr (count=0x80)
    //   +0xcd8: rulername array ptr (count=0x11 — the civ/ruler count)
    //   +0xcdc: civname array ptr  (count=0x11)
    //   +0xd14..0xd2c: filename prefix strings ("UnitNames_", "CivNames_", etc.)
    ...
}
```

`iStack_84` is a class `this` pointer (Ghidra lost the parameter
during decompilation, but it's loaded from a register at function
entry and used as the base for all struct offsets).

### FUN_00a216d4 parser internals

The parser allocates via:
```c
piVar6 = (int *)thunk_FUN_00c449c4(param_3 * 0xc + 4);
```

`param_3 * 0xc + 4` — each entry is 12 bytes, plus a 4-byte
header. For count=17: 208 bytes. For count=18 (post-patch):
220 bytes. **The allocation is correctly sized by the count
argument.** Bumping count to 18 gives the parser enough buffer
space for the 18th entry.

The parser then writes entries via:
```c
FUN_009e545c(iVar11 * 0xc + iVar4, local_c0);
```

Where `iVar11` is the loop index (0..count-1) and `iVar4` is the
buffer base. Writes are within the allocated region.

### So why does 18 entries crash?

**The parser itself is not the OOB crash site.** The iter-14
`li r5, 17→18` patch lets the parser allocate 220 bytes and write
all 18 entries safely. But RSX init still times out — meaning the
crash is somewhere ELSE in the downstream consumer chain.

Candidates for the downstream 17-wide consumer:

1. **A "pair-init" function** called after name files load that
   iterates civ[i] and ruler[i] together and writes to a third
   per-civ table. We know this exists because iter-12 proved
   civnames +1 alone works and rulernames +1 alone works, but
   both together crashes — meaning the crash requires both arrays
   to have their extra entry.

2. **One of the "dead rodata" §5.2 tables** (LEADER_NAME_PTR_ARRAY
   at 0x0194b434, CIV_TAG_ARRAY at 0x0194b35c, etc.) that we
   never found live consumers for. They were 16×4 byte tables.
   If the pair-init writes to them by `base + index*4`, that
   wouldn't show up as a static XREF and would explain why static
   scans found zero refs.

3. **A dynamic heap-allocated "civ registry"** that's allocated
   with a hardcoded 17 slot count somewhere at startup.

## Callers walked

- `FUN_00a21ce8` callers: 1 (`FUN_00010ef0` — trampoline).
- `FUN_00010ef0` callers: 1 (`FUN_0002fb78` — game init).
- `FUN_0002fb78` is 1556 bytes and makes many init calls. The
  pair-init could be any of them. Didn't trace further this
  iteration due to time.

## What's still unknown

1. The exact downstream function that crashes on the 18th entry.
2. The civ-select cursor's right-clamp (currently limits to 17
   slots with Random at 16).

## Next steps for iter-16+

1. Set a hardware watchpoint via RPCS3 GDB stub on the address
   `*(iStack_84 + 0xcd8)` (the rulername buffer pointer) to
   catch every read. Any function that reads it and iterates
   with a hardcoded bound is a candidate.
2. Alternatively, grep the Ghidra decompile for all functions
   that reference `0xcd8` or `0xcdc` as a struct offset — those
   are the consumers.
3. Or search for PS3 functions whose decompile contains both
   `0xcd8` and `cmpwi 0x10` / `cmpwi 0x11` — that's the
   pair-init candidate.

## v0.9 still the shipping state

After iter-15 read-only exploration, no changes to the repo. v0.9
remains green at branch tip `87bc88e` (from iter-14). The iter-14
EBOOT patches (bumping InitGenderedNames count) are still in
place and harmless.
