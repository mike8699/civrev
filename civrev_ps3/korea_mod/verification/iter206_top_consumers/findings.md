# iter-206: top 10 bl 0x12080 consumers; FUN_001dc0d8 + FUN_0x111dd70 BOTH ruled out

**Date:** 2026-04-15

## Distribution of the 139 bl 0x12080 callers

Python bl-scan for `0x12080` (the intra-module TOC-switching
virtual-dispatch stub) found 139 callers across 50 unique
containing functions. Top 10 by call count:

| rank | fn | calls |
|---|---|---|
| 1 | `0x1db4e8` | 9 |
| 2 | `0x1dde84` | 9 |
| 3 | `0x1de750` | 6 |
| 4 | `0x1ded48` | 6 |
| 5 | `0x1e51ac` | 6 |
| 6 | `0x1e5a68` | 6 |
| 7 | `0x224668` | 6 |
| 8 | `0x1d6758` | 5 |
| 9 | `0x1dc0d8` | 5 (the iter-204 anchor) |
| 10 | `0x1e05c8` | 5 |

**Cluster**: the `0x1d0xxx..0x1e5xxx` region contains 22+
functions using the stub, strongly suggesting a single large
C++ class with many methods, all dispatching to callback
objects via `bl 0x12080`.

## Sample decomps (all have init/serialization shapes)

### `FUN_001db4e8` (top 1)
Unrolled sequence of ~9 `bl 0x12080` calls, each with a
different `r2+0xc7c..0xcc8` TOC offset. Classic "register each
entry of a 9-field struct with a callback object" shape.

### `FUN_001dde84` (top 2)
Same shape — calls `bl 0x12080` 9 times with offsets
`0xefc..0xf3c` and iter indices `0, 1, 3` (discontinuous).

### `FUN_001de750` (top 3)
Simplest example: iter indices `0, 1, 2, 3, 4` — 5 iteration
steps. Uses `r2+0xf7c..0xfa4` offsets.

```c
void FUN_001de750(u32 param_1) {
    puVar4 = *(r2 + 0xf7c);
    uVar2 = func_0x00011230(*puVar4, *(r2 + 0xf80));
    func_0x00012080(param_1, *(r2+0xf84), *(r2+0xf88), uVar2);
    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xf8c));
    uVar2 = *(r2 + 0xf90); uVar1 = *(r2 + 0xf94);
    func_0x00012080(param_1, uVar2, uVar1, 0, uVar3);
    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xf98));
    func_0x00012080(param_1, uVar2, uVar1, 1, uVar3);
    uVar3 = func_0x00011230(*puVar4, *(r2 + 0xf9c));
    func_0x00012080(param_1, uVar2, uVar1, 2, uVar3);
    // iter_idx 3, 4 follow
}
```

This is the same "unrolled registration loop" pattern as
`FUN_001dc0d8`. **All functions in the cluster appear to be
this same shape** — not carousel iterators.

### `FUN_001ded48` (top 4)
A switch/case dispatcher on some enum value (7, 14, 24, 18, 37).
Picks one of 5 different TOC offsets and calls `bl 0x12080`.
Again, not a loop.

## Diagnostic: both `FUN_001dc0d8` and `FUN_0x111dd70` are OFF the boot path

Planted `b .` (= `0x48000000`) infinite-loop traps at the entry
of both functions via temporary patches in `eboot_patches.py`:

```
FUN_001dc0d8 (0x1dc0d8): 0xf821ff61 → 0x48000000
FUN_0x111dd70 (0x111dd70): 0xf821ff71 → 0x48000000
```

**Result**: Romans slot 0 M9 **PASS** with both traps active.
Boot reaches main menu, navigates through scenario menu,
difficulty selection, civ-select (Romans highlighted), game
starts, in-game HUD confirmed by OCR.

**Both functions are NOT called during the normal gameplay
path.** Neither is the carousel render path.

This joins iter-150 (`FUN_001e49f0`) and iter-154
(`FUN_011675d8`) on the "civnames consumer but not on the
carousel path" list. The diagnostic traps are removed;
iter-198 baseline restored.

## What iter-206 definitively rules out

- Every function in the iter-204 / iter-205 static-analysis
  candidate set (the second-holder-struct readers) has now been
  either decompiled or diagnostic-trap tested.
- None of them show carousel-iterator shapes.
- The two tested by `b .` (`FUN_001dc0d8`, `FUN_0x111dd70`) are
  confirmed off the critical path.

## Why this matters

The carousel render path is **not** inside the iter-204/205
candidate set. The class with `*self = 0x1ac93b8` as its first
member is used for some OTHER purpose (probably serialization
or inter-system registration), NOT for the civ-select UI.

The carousel must access civnames via:
- A different class instance (with the civs holder as a later
  field, not field 0)
- A cached pointer stored in some heap object at civ-select
  init time
- Or it doesn't access civnames at all — it might use a
  separate data source entirely (hardcoded table, Scaleform
  static pool, etc.)

## iter-207 plan

A different approach is needed. Options:

1. **Stub-level Z0 trace.** Set a Z0 breakpoint directly at
   `0x12080` (the TOC-switching stub entry) AFTER boot reaches
   civ-select, then poll. Every subsequent `bl 0x12080` call
   hits the Z0. Walk back one frame (via `r3`/`lr`) to see
   which function called it during civ-select specifically.
   This would give a real-time inventory of stub-calling
   activity for the civ-select rendering.

2. **Function-entry Z0 trace.** Set Z0 at ALL 50 unique
   containing functions from iter-206's scan simultaneously.
   Record which hit during civ-select.

3. **Heap scan at civ-select.** Fix the navigator in
   `test_civs_dump.py` to get past main menu reliably (add
   PSN-popup dismissal, per-step timeouts, stdout flushing),
   then scan a wider memory range at civ-select time for
   copies of the civs buffer pointer. iter-203 showed the scan
   of .bss/.data at main menu found zero caches — civ-select
   may create new ones that we can catch.

4. **Disassemble the civ-select panel-loader wrapper** at
   `0xf07078`/`0xf070a0` with the CORRECT TOC base (we used
   the wrong one in iter-193). Walk forward from that function
   to find its downstream calls and see if any touch civnames.

Option 1 (stub-level Z0 trace) is the most targeted — it
specifically catches the carousel call site if one exists. But
it requires the GDB probe to stay stable through civ-select.

Option 4 (revisit panel-loader with correct TOC) is the
cheapest and most likely to reveal the carousel setup sequence.
iter-193 mapped the panel-loader chain but may have been
using the wrong TOC base — with iter-202's correction, the
decomp may read completely differently.

## Files

- `findings.md` — this
- `m9_romans_both_traps_pass.json` — boot test result
- `jython_dump.txt` — 849-line Ghidra output with all top-10
  decompiles
- `Iter206TopConsumers.py` under `scripts/ghidra_helpers/`
