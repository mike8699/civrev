# iter-199: post-parse block is NOT the carousel render path; TOC-ref blind spot in Ghidra

**Date:** 2026-04-15
**Goal:** Trace the civ-select carousel render path from iter-197's
post-parse block in `FUN_00a2e640`, via `FUN_009bf5a0` /
`FUN_009f1c80` / `FUN_00c72cf8` / `FUN_00c7258c`.

## What the Jython decompile actually shows

### FUN_00c72cf8 — per-line parser

Takes `(line_str, entry_ptr)`. Searches for `','` in the line, splits:
- left half → stored at `entry[0]` via `FUN_009f1d00` (FString store)
- right half → parsed for letters 'M'/'F'/'N' → `entry[0]` = 0/1/2
  (gender), and 'S'/'P' → `entry[1]` = 0/1 (singular/plural)

So each 12-byte entry layout is: `{ FStringA name, int gender, int plurality }`.
This matches the civnames format ("Romans, MP" etc.). The parser
writes this on every line, dynamically sized. **This is the per-
line parser, not a carousel writer.**

### FUN_009bf5a0 — trivial wrapper

16-byte function:
```
FUN_009bf5a0(): FUN_000297d0(); return;
```

Just a call-through to another function. Called from 16+ sites
across the binary (not carousel-specific). Not useful.

### FUN_009f1c80 — doesn't exist in Ghidra DB

Ghidra did not auto-analyze this function. When I ask
`getFunctionAt(0x9f1c80)` it returns None. Callers search finds
3 sites: `0xa2eb50` (inside the parser worker's post-parse loop),
`0xa00f28` (inside `FUN_00a00f54` which is the per-entry INIT),
and `0x9f1d14` (an adjacent helper). **All three are inside the
parser-side code path**, not on the carousel render side.

`FUN_009f1c80` appears to be the "write FString to entry's `[0]`
field" setter used by both the parser's init loop and its
post-parse loop.

### FUN_00c7258c — also not in Ghidra DB

No function at that address either. I skipped the deeper chase.

### TOC slots `r2+0x1440` and `r2+0x13fc`

`r2+0x1440 = 0x193b6c8` holds pointer `0x198bf08` (a class
instance used inside the parser worker — probably the .txt
tokenizer/reader state). Ghidra's `ref_mgr.getReferencesTo()`
returns **zero references** for both this slot and `r2+0x13fc`,
because Ghidra's reference manager doesn't track `lwz rN,
offset(r2)` loads as explicit references — it only tracks
direct addressing. Known Ghidra blind spot.

## Why the caller-graph queries are empty

Calling `find_callers(0x00a2ec54)` (the real_parser_dispatcher)
also returns zero results. Ghidra's reference DB doesn't know
that anything calls it, because the dispatcher is presumably
itself reached via a TOC-based `lwz` → `mtctr` → `bctrl`
indirect call, OR via a vtable dispatch that Ghidra's static
reference pass can't resolve.

This means Ghidra is **not going to give us the carousel render
path via simple reference queries**. The civ-select panel's C++
class is instantiated dynamically, its methods are dispatched
via vtables, and the vtable slots are populated at runtime by
C++ constructors — none of which show up as cross-references.

## What's ruled out this iteration

- **`FUN_00c72cf8` is the line parser** — writes to the parser
  buffer entry. Not the carousel.
- **`FUN_009bf5a0` is a trivial 16-byte utility** used in 16+
  places. Not unique to the carousel.
- **`FUN_009f1c80` is the FString setter** for the entry's
  `[0]` field. Used by the parser, not by the carousel.
- **Ghidra's reference manager cannot find the carousel render
  path** via TOC slot references or caller queries — the
  dispatch is indirect / vtable-based.

## What this changes for iter-200+

**Option A (static, harder):** manually disassemble the
parser-worker return path and follow what happens to the buffer
pointer (`*param_2 = piVar5 + 1`) AFTER the worker returns. The
global slot at `r2+0x141c` receives the new pointer. Look for
ANY code that writes the pointer into a class field somewhere
(`stw rN, OFF(rO)` where `rN` previously held `lwz r,0x141c(r2)`
or a cached copy thereof). That's the handoff to the next layer.

**Option B (static, more scope):** search for `addis`/`addi`
constructions of the numOptions string vaddr (`0x01692b68`) that
bypass the TOC loads entirely. The PPU might be building the
string pointer inline for a rare SetVariable call.

**Option C (dynamic, most direct):** extend `gdb_client.py` with
Z2 watchpoint support and plant a write-watchpoint on the parser
buffer's FStringA header at `(*param_2) - 4` immediately after
the parser returns. Whichever code writes or reads near that
address during civ-select panel init is the render path.
PRD §6.2 declares this first-class in-scope.

**Option D (empirical, cheapest):** try the iter-178 slotData17
gfx extension on top of iter-198's 18-row overlay. If the
combination produces a visible 17th cell (even as a broken-render
"Korean" with missing assets), that confirms the carousel source
is the Scaleform slotDataN constants and the parser buffer
isn't even consulted. If it's still stock, that rules out
Scaleform slotDataN and points firmly at Option C.

iter-200 should start with Option D (cheapest, unambiguous
either-way test). If slot 16 or a new slot 17 gets Korea-like
data, we've won on two fronts (slotDataN works + iter-198
parser path is redundant for display). If nothing changes, we
commit to Option C for the actual render path chase.

## Files

- `Iter199CarouselWriter.py` — Jython post-script
- `jython_dump.txt` — truncated Ghidra output (183 lines)
- `findings.md` — this
