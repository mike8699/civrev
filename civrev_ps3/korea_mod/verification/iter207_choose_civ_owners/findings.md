# iter-207: ChooseCiv panel descriptor has only 4 loaders; `FUN_00932a20` is the state dispatcher

**Date:** 2026-04-15

## TOC base correction

iter-193's panel-loader mapping at `0xf07078`/`0xf070a0` used
`r2 = 0x193a288`. That was wrong. A function-descriptor scan
for the panel-loader family reveals they all use
**`r2 = 0x195a1a8`**:

| function | descriptor @ | TOC base |
|---|---|---|
| `0xf070a0` (ChooseCiv entry) | `0x191a7f0` | `0x195a1a8` |
| `0xf05aa8` (panel loader core) | `0x191a6d0` | `0x195a1a8` |
| `0xf07010` | `0x191a7d8` | `0x195a1a8` |
| `0xf07040` | `0x191a7e0` | `0x195a1a8` |
| `0xf07070` | `0x191a7e8` | `0x195a1a8` |

Three distinct TOC bases are now confirmed in the binary:
- `0x194a1f8` — the parser dispatcher + 28,525 functions (main)
- `0x193a288` — the "main menu / other systems" TOC (~17,882 fns)
- `0x195a1a8` — panel-loader / UI TOC (~17,320 fns)

With r2 = 0x195a1a8, the panel function descriptors live at
`r2 - 0x29c0..r2 - 0x2980` (= `0x19577e8..0x1957820`). The
ChooseCiv descriptor at `0x1957810` sits at `r2 - 0x2998`.

## 4 unique loaders of the ChooseCiv descriptor

Python scan for `lwz rN, -0x2998(r2)`:

| site | containing fn | disas context |
|---|---|---|
| `0x11b324` | `0x11b17c` | `lwz r3, -0x2998(r2); bl 0xc649e4` — acquire/retain |
| `0x11b360` | `0x11b17c` | `lwz r3, -0x2998(r2); bl 0xc6499c` — release |
| `0x932bf4` | `0x932a20` | `stw r0, 0(r9)` — STORES desc into a class field |
| `0xf058c8` | `0xf057b0` | `li r7, 3; b 0xf057b0` — panel-by-index case (idx 3) |

`FUN_0011b17c` is just a refcount wrapper (`bl 0xc649e4` = retain,
`bl 0xc6499c` = release). 533 and 546 callers respectively — all
generic retain/release calls. Not useful.

`FUN_00f057b0` is a panel register/init function: takes a panel
descriptor pointer, calls `func_0x00f060d8(param_1, ...)` to load
the panel, and stores the result into `*(param_1 + 0x48)`. Caller
holds a class instance (`param_1`) where the panel handle goes.
**0 direct BL callers** — invoked via function descriptor /
tail-branch only. The `0xf058c8` site is the ChooseCiv case
inside a sequence of panel-by-index tail-branches into `0xf057b0`:

```
0xf058b8  lwz r8, -0x299c(r2)    ; r8 = panel desc for idx 4
0xf058bc  li r7, 4
0xf058c0  b 0xf057b0              ; tail-call to loader
0xf058c4  nop
0xf058c8  lwz r8, -0x2998(r2)    ; r8 = ChooseCiv desc
0xf058cc  li r7, 3                ; idx = 3
0xf058d0  b 0xf057b0              ; tail-call to loader
0xf058d4  nop
0xf058d8  lwz r8, -0x2994(r2)    ; r8 = panel desc for idx 2
0xf058dc  li r7, 2
```

This is a **panel-index → loader** tail-call dispatcher.
ChooseCiv is panel index 3 here.

**`FUN_00932a20` is the most interesting** — it's a
**jumptable-based panel-state dispatcher**:

```c
undefined8 FUN_00932a20(longlong param_1, uint param_2, u32 *param_3) {
    if (5 < *(param_1 + 0x18)) {
        *param_2 = *(r2 - 0x2990);   // default descriptor
        *param_3 = param_1;
        return 0;
    }
    // jumptable at (r2 - 0x29a8) indexed by *(param_1 + 0x18)
    return (*(code*)((longlong)*(int*)(*(uint*)(param_1 + 0x18) * 4 +
                                        *(uint*)(r2 - 0x29a8)) +
                     *(uint*)(r2 - 0x29a8)))();
}
```

Ghidra warns "Could not recover jumptable at 0x00932a90". The
jumptable base is at `r2 - 0x29a8` = `0x1957800` (which is inside
the panel-descriptor registry!). The dispatcher indexes into the
registry by `*(param_1 + 0x18)` — probably a "menu state" enum.

**The store at `0x932bf4` (`lwz r0, -0x2998(r2); stw r0, 0(r9)`)
is inside the jumptable body — probably one of the case arms,
specifically the case that returns the ChooseCiv descriptor.**

## Callers of `FUN_00932a20`

Only **2 callers**: `0x9099ac` and `0x932ddc`.

Very narrow signal. Both are candidates to be in the menu-state
machine that decides which panel to show.

## Key conclusion

The civ-select setup path is:
1. Some menu-state manager calls `FUN_00932a20(state, ...)` with
   the current menu enum.
2. `FUN_00932a20` uses the jumptable at `r2 - 0x29a8` to fetch
   the descriptor for the requested state.
3. For state enum `5` (or whichever hits the `-0x2998` case), it
   returns the **ChooseCiv** descriptor `0x191a7f0`.
4. The returned descriptor is fed to `FUN_00f057b0` (or similar)
   which actually loads the panel and stashes it in a class
   field.
5. Subsequent rendering calls a method on that class to populate
   the panel's variables (numOptions, slotDataN, etc.) — the
   **actual carousel setup**.

**None of this has been directly tested** — the critical step 5
is still unidentified. But we now know the call chain that leads
to the ChooseCiv panel being loaded. Following the class whose
field +0x48 holds the panel handle is the next step.

## iter-208 plan

1. Decompile the 2 callers of `FUN_00932a20` (`0x9099ac`,
   `0x932ddc`) to see what the menu-state machine looks like and
   when it calls into ChooseCiv.
2. Decompile `func_0x00f060d8` (the real panel-loader inside
   `FUN_00f057b0`) and its call chain, with r2 = 0x195a1a8, to
   find what CLASS the panel handle gets stored into
   (`*(param_1 + 0x48) = panel_handle`).
3. Once the "panel owner class" is identified, find its methods
   that invoke Scaleform SetVariable — those are the ones that
   write numOptions + slotDataN + other AS2 vars at render time.
4. Plant a diagnostic `b .` trap at `FUN_00932a20` entry to
   verify it runs at civ-select transition. If korea_play slot 0
   PASSes, the state dispatcher isn't on the path (another dead
   end). If the harness hangs past main menu but before civ-select,
   we've confirmed this is the civ-select entry point.

## Files

- `findings.md` — this
- `jython_dump.txt` — 246-line Ghidra decomp output
- `Iter207ChooseCivOwners.py` under `scripts/ghidra_helpers/`
