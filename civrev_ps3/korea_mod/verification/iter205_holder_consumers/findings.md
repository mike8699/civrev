# iter-205: decomp of `FUN_001dc0d8` and `FUN_0x111dd70`

**Date:** 2026-04-15
**Tool:** `analyzeHeadless` + `Iter205HolderConsumers.py`.

## `FUN_001dc0d8` is a one-shot name-file registration routine

Decompiled with the corrected TOC base (`r2 = 0x194a1f8`). Full
C:

```c
void FUN_001dc0d8(undefined4 param_1)
{
    undefined4 *puVar4 = *(uint *)(r2 + 0xd38);  // some class instance
    uVar2 = func_0x00011230(*puVar4, *(r2 + 0xd3c));
    func_0x00012080(param_1, *(r2 + 0xd40), *(r2 + 0xd44), uVar2);

    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xd48));
    uVar2 = *(r2 + 0xd50);    // CIVS buffer holder 0x1ac93b8
    uVar1 = *(r2 + 0xd4c);    // rulers holder 0x1ac93ac
    func_0x00012080(param_1, uVar1, uVar2, 0, uVar3);   // iter 0

    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xd54));
    func_0x00012080(param_1, uVar1, uVar2, 1, uVar3);   // iter 1

    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xd58));
    func_0x00012080(param_1, uVar1, uVar2, 2, uVar3);   // iter 2

    ... (iter 3 at r2+0xd60 / 0xd64) ...
}
```

The routine passes `param_1` through as the "caller object",
calls `func_0x00011230` to construct a result per-slot, then
invokes `func_0x00012080` with `(param_1, rulers_holder,
civs_holder, iter_idx, result)` four times with `iter_idx = 0,
1, 2, 3`. That's the classic "loop over 4 name-file items"
shape — but **unrolled, not iterative**. And only 4 items, not 8.

**`func_0x00012080` is NOT a PRX import.** It's an intra-module
TOC-switching stub:

```
0x12080  std   r2, 0x28(r1)        ; save caller's TOC
0x12084  addis r2, r2, 0x1
0x12088  subi  r2, r2, 0x90         ; adjust r2 += 0xff70
0x1208c  b     0xa97ca8             ; tail-jump with NEW TOC
```

The real target is `FUN_00a97ca8`:

```c
undefined4 FUN_00a97ca8(longlong param_1, u32 param_2, u32 param_3) {
    uVar1 = 0;
    if (*(int *)(param_1 + 8) != 0)
        uVar1 = func_0x00a7a2a8(*(int *)(param_1 + 8), param_2, param_3, &stack);
    return uVar1;
}
```

`FUN_00a97ca8` reads `*(param_1 + 8)` as a method/handler pointer
and dispatches through it. So `func_0x00012080(obj, holder1,
holder2, idx, ctx)` is a **virtual method call** on `obj` that
gets invoked once per name-file-holder pair.

**Interpretation:** `FUN_001dc0d8` is a one-shot registration or
init function that feeds each name-file holder into a caller-
provided callback object via indirect dispatch. Not a carousel
iterator.

## `FUN_0x111dd70` is a class destructor / reset

```c
void FUN_0111dd70(undefined4 *param_1) {
    if (!(bool)(in_cr7 >> 1 & 1)) {
        *param_1 = *(r2 + 0xd50);      // set field 0 = civs holder 0x1ac93b8
        if (param_1[1] != 0) {
            // call vtable free on param_1[1]
        }
        param_1[1] = 0;
        param_1[2] = 0;
        ...
        param_1[8] = 0;
        if (param_1[9] != 0) { /* free */ }
        if (param_1[0xb] != 0) { /* free */ }
        param_1[0xb] = 0;
        // call vtable free on param_1 itself
    }
}
```

This is a CLASS DESTRUCTOR (or reset). It:
- Writes `*param_1 = &civs_holder = 0x1ac93b8` — setting the
  object's first word to the civs holder address (this is the
  object's VTABLE slot or first data member).
- Frees heap allocations at `param_1[1]`, `[9]`, `[11]`.
- Zeros `param_1[1..8]`.
- Finally calls `free(param_1)` via a vtable allocator method.

**The object being reset is a "name-file-aware object"** that
holds the civs holder as its first field. Any method of the
class can do `r3 = *self; r4 = *r3;` to dereference the holder
→ civnames buffer.

This is another strong anchor: **whatever class instantiates via
`FUN_0x111dd70`-adjacent code creates objects that can directly
read civnames**. Finding the constructor / instantiation sites
is the next step.

## Caller analysis

Both `FUN_001dc0d8` and `FUN_0x111dd70` have **zero direct `bl`
callers**. Like `FUN_00a2ec54` (the parser dispatcher), they are
invoked indirectly — either via vtable dispatch or via function
descriptor + `mtctr/bctrl`.

The `bl 0x12080` TOC-switching stub (used inside
`FUN_001dc0d8`) has **139 callers** across the binary. Sample
first-6:
- `0x1d1130`
- `0x1d1520`
- `0x1d173c`
- `0x1d1b0c`
- `0x1d1b98`
- `0x1d1bd8`

All in the `0x1d1xxx` region, **very close to `FUN_001dc0d8`
itself at `0x1dc0d8`**. Probably the same module/class. There's
likely a full class with many methods that dispatches via
`bl 0x12080`, and `FUN_001dc0d8` is one of those methods.

## iter-206 plan

1. **Dump all 139 `bl 0x12080` callers, grouped by function.**
   This reveals the full "class" that uses `FUN_00a97ca8` as
   its method dispatcher.
2. **Decompile each function in the `0x1d1xxx` cluster** to see
   what they do. If any of them is a civ-select panel handler
   or carousel iterator, we've found the render path.
3. **Find the constructor site** that creates the class
   `FUN_0x111dd70` destructs — search for allocations whose
   first write is `*self = 0x1ac93b8` or equivalent indirect.
4. **Plant a diagnostic `b .` trap at `FUN_001dc0d8` entry** and
   run korea_play slot 0 to see if it's on the boot path. This
   is cheap and definitive.

Time-boxing static analysis to these four steps. If none
reveals the carousel, pivot back to the dynamic Z0 probe with
fixed navigation.

## Files

- `Iter205HolderConsumers.py` — Jython script
- `jython_dump.txt` — full decompile output (254 lines)
- `findings.md` — this
