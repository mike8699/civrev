# iter-197: parser is dynamic — the "17-wide buffer" doesn't exist; downstream consumers hardcode 16

**Date:** 2026-04-15
**Tool:** `analyzeHeadless` + new Jython script
`scripts/ghidra_helpers/Iter197ParserWriteTarget.py`. Decomp dump
saved to `jython_dump.txt`.

## What the decompile reveals

### `real_parser_dispatcher` (`FUN_00a2ec54`)
Calls `real_parser_worker` (`FUN_00a2e640`) **once per name file** with
hardcoded counts:

| Site (vaddr)  | name file       | count | TOC slot for buf-ptr field |
|---------------|-----------------|-------|----------------------------|
| `0xa2ed64`    | cities          | `0x101` | `r2+0x140c` = `0x193b694` |
| `0xa2eda8`    | wonders         | `0x42`  | `r2+0x1410` = `0x193b698` |
| `0xa2edec(?)` | wonders fem (?) | `0x80`  | `r2+0x1414`               |
| `0xa2ee38`    | **rulers**      | `0x11`  | `r2+0x1418` = `0x193b6a0` |
| `0xa2ee7c`    | **civs**        | `0x11`  | `r2+0x141c` = `0x193b6a4` |

The `0xa2ee38` and `0xa2ee7c` `li r5, 0x11` constants are the
iter-14 patch sites (already bumped to `0x12` in shipping
`eboot_patches.py`).

### `real_parser_worker` (`FUN_00a2e640`)

```
piVar5 = (int *)thunk_FUN_00c4ff00(param_3 * 0xc + 4);  // malloc
*piVar5 = param_3;                                       // count header
piVar9 = piVar5 + 1;
... init each entry via FUN_00a00f54 (param_3 iterations) ...
*param_2 = (int)(piVar5 + 1);                            // store new buf ptr

// parse loop
iVar10 = 0;
while (true) {
    ... read line ...
    if (line not '#' or ';') {
        FUN_00c72cf8(&line_str, iVar10*0xc + *param_2);  // store entry
        iVar10++;
    }
}
```

The buffer is **dynamically sized** as `param_3 * 12 + 4` bytes
(count word + N×12-byte entries). The parse loop writes up to
`iVar10` entries (the actual line count), and there is **no
hardcoded 17 anywhere in the parser**. iter-14 was right that
bumping the dispatcher's `li r5, 0x11` to `0x12` makes the parser
allocate room for 18 entries instead of 17.

**Conclusion:** the "17-wide buffer in the parser" model from
iter-7..72 was wrong. The parser correctly tracks count via
`*param_2` and stores it as a header word.

## The hardcoded `16` downstream

A grep for `li rN, 0x10` within ±8 instructions of every
`lwz r,N(r2)` that loads any of the 7 name-file buffer-pointer
TOC slots (`r2 + 0x1404 / 0x1408 / 0x140c / 0x1410 / 0x1414 /
0x1418 / 0x141c`) finds an extremely consistent pattern:

| name file    | lwz site     | li r8 site   | Δ   |
|--------------|--------------|--------------|-----|
| TECH         | `0x11676cc`  | `0x11676dc`  | +16 |
| FAMOUS       | `0x1167734`  | `0x1167744`  | +16 |
| CITIES       | `0x116779c`  | `0x11677ac`  | +16 |
| WONDERS      | `0x1167804`  | `0x1167814`  | +16 |
| WONDERS_FEM  | `0x116786c`  | `0x116787c`  | +16 |
| **RULERS**   | `0x11678d4`  | `0x11678e4`  | +16 |
| **CIVS**     | `0x1167940`  | `0x1167948`  |  +8 |
| TECH         | `0x1167adc`  | `0x1167af4`  | +24 |
| FAMOUS       | `0x1167b70`  | `0x1167b88`  | +24 |
| CITIES       | `0x1167c18`  | `0x1167c10`  |  -8 |
| WONDERS      | `0x1167ca8`  | `0x1167ca0`  |  -8 |
| WONDERS_FEM  | `0x1167cf0`  | `0x1167d00`  | +16 |
| **RULERS**   | `0x1167d54`  | `0x1167d64`  | +16 |
| **CIVS**     | `0x1167dbc`  | `0x1167dc8`  | +12 |

These are **two consumer functions**, each iterating all 7 name
files and passing `r8 = 16` as the 6th argument to a vtable method
along with the buffer pointer in `r7`. The instruction sequence is
the classic "load buf ptr + count, call method via virtual table":

```
0x01167940  lwz   r7, 0x141c(r2)     ; civs buffer ptr
0x01167944  addi  r4, r1, 0x8c       ; r4 = stack temp
0x01167948  li    r8, 0x10           ; r8 = 16   <-- HARDCODED COUNT
0x0116794c  mr    r3, r9             ; r3 = this
0x01167950  lwz   r11, 0(r9)         ; r11 = vtable
0x01167954  lwz   r9, 0x24(r11)      ; method @ vtable+0x24
... mtctr / bctrl ...
```

This `li r8, 0x10` (=16) is the count of **entries iterated** by
the call, not the buffer size. Because stock civnames has 17
entries (16 real civs + 1 internal "Barbarians" at index 16), the
consumer reads only the 16 real civs and ignores "Barbarians" by
design.

## What this means for the Korea blocker

iter-14 finding 4 said extending civnames+rulernames to 18 entries
(with the parser-count patches active) "still timed out at RSX
init". That **may have been a misdiagnosis** — the test setup at
the time may have had stale or partial files, or RSX timed out for
unrelated reasons.

Reasoning from the decompile:
- Parser allocates the right size for `count = 18`.
- Parser writes the 18 entries correctly.
- The downstream consumers at `0x011679xx` / `0x01167dxx` only
  read 16 entries regardless of file size, so they cannot OOB on
  any extension to 17 or 18 — they simply ignore the new entries.
- The fault site at `0xc26a98` (FStringA `*p++ = 0` clear) needs
  some other corruption path to be triggered.

**Hypothesis for iter-198:** rebuild the mod with civnames+rulernames
extended to 18 entries (insert "Koreans, MP" at index 16 between
"English" and "Barbarians", same for "Sejong, M" in rulernames),
keep the iter-14 parser-count patches active, and re-run the M2
boot test. If iter-14 finding 4 was a misdiagnosis, this should
boot. If it crashes again, the silent-OOB source is somewhere
else and the next move is to set a Z-packet write-watchpoint on
the FStringA buf the fault site reads (PRD §6.2 dynamic path).

## What this rules out

- Parser-side OOB on `param_3 = 18`. Decompile shows the malloc
  is `param_3 * 12 + 4`. Safe.
- The 14 `li r8, 0x10` hardcodes at `0x011676xx-0x01167dxx` are
  NOT a 17-overflow path — they iterate 16 and stop. They cap
  visibility, not capacity.
- The 5-callers analysis from iter-22 (none reach init) is
  consistent with this finding: the fault site is probably
  triggered by some OTHER memory-corruption side effect, NOT by
  a parser/consumer mismatch on count.

## Files

- `Iter197ParserWriteTarget.py` — Jython post-script
- `jython_dump.txt` — full decompile of the 3 functions and call
  site disassembly
- `findings.md` — this file
