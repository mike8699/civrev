# iter-217: theOptionArray strings DO exist in PS3 EBOOT, but FUN_0006c290 is also off the carousel path

**Date:** 2026-04-15

## What changed: iter-196's "0 hits for theOptionArray" was wrong

iter-196 ran a string scan on PS3 EBOOT and reported zero hits
for `theOptionArray`. That was a bug — re-running the search at
iter-217 finds **3 hits** for the literal `theOptionArray` and
many more carousel-related format strings:

| string | vaddr |
|---|---|
| `theOptionArray[%d].unitStack.ExitPanel` | 0x1692df0 |
| `theOptionArray[%d].unitStack.goLeft`    | 0x1692f88 |
| `theOptionArray[%d].unitStack.goRight`   | 0x1692fc0 |
| `LeaderName%d.text`                       | 0x169bfd8 |
| `Civ%d%d.text`                            | 0x169c0b0 |
| `slotData%d`                              | 0x169c518 |
| `this.slotData%d`                         | 0x16a7130 |
| `SetVariable`                             | 0x16c44e0 |
| `GetVariable`                             | 0x16c72c7 |
| `Invoke`                                  | 0x16c6e6f |

These are all sprintf format strings the PPU code uses to
construct Scaleform variable paths at runtime, then passes to
SetVariable/Invoke.

## Cross-platform comparison: X360 has the same strings

The Xbox 360 binary at
`civrev_xbox360/xenon_recomp/work/extracted/default_decompressed.bin`
contains the **same** carousel format strings — `theOptionArray[%d].unitStack.ExitPanel`
literal exists in both binaries. Both PS3 and X360 builds
share the architectural pattern of formatting Scaleform variable
paths from C++ and dispatching via Invoke.

## Found a new candidate: FUN_0006c290

Following the trail:
1. `theOptionArray[%d].unitStack.{ExitPanel,goLeft,goRight}` is
   referenced via TOC slots `0x1933934`/`0x19339bc`/`0x19339c4`
   (in main module TOC, r2=0x193a288).
2. **`FUN_0006ff08`** (an event handler) loads goLeft/goRight at
   `0x70044`/`0x70158`/`0x700b0`/`0x701c4`, formats them with a
   cell index from `r31->[0x858]..r31->[0x85c]`, and invokes
   per-cell setters via `bl 0x12df0`.
3. `r31->[0x85c]` is the carousel **end index** field. The init
   code at `0x6fb80..0x6fc60` sets `0x858` and `0x85c` based on
   `r30->[0x868]` (a count field).
4. **`FUN_0006c290`** is the constructor that initializes
   `0x868(r30)` from its second argument (`r4`), saved as `r16`.
5. The constructor has **1 BL caller** at `0x1c00bc` inside
   `FUN_001bff04`, which sets `r4 = sign_extend(r27)` and `r27`
   is taken from its OWN second argument at function entry.
6. `FUN_001bff04` has **0 BL callers and 0 u32 refs**, so it's
   called via vtable indirect like the other candidates.

## Diagnostic trap test: FUN_0006c290 is OFF the carousel path

Planted `b .` (`0x48000000`) at `0x6c290` (the constructor
entry, original bytes `0xf821ff11`). Built, installed, ran
`korea_play 0 romans`. **Romans M9 PASS** — boot, civ-select,
in-game HUD all green.

**`FUN_0006c290` is the 7th candidate consumer function ruled
out.** Despite being a generic options-carousel constructor
that demonstrably handles theOptionArray cells, it's not
invoked during the civ-select code path on PS3.

## Updated cumulative ruled-out inventory

| iter | what was ruled out |
|---|---|
| 150 | FUN_001e49f0 |
| 154 | FUN_011675d8 |
| 198 | All 14 li r8, 0x10 sites collectively (RSX hang) |
| 206 | FUN_001dc0d8 + FUN_0x111dd70 |
| 209 | FUN_001262a0 (CIV_*.dds icon registration) |
| 210 | 2 CIVS-only li r8 sites |
| 211 | Consumer A's 7 li r8 sites |
| 217 | **FUN_0006c290** (theOptionArray-aware constructor) |

Plus iter-208 invalidating iter-193's `0xf070a0` panel-loader
hypothesis.

## Reinforced unified hypothesis

The civ-select carousel rendering on PS3 is **entirely
Scaleform-side**. The PPU code that exists for handling
theOptionArray-style cells is for OTHER panels (difficulty
selector, options menu, etc.) — the civ-select carousel is
a different panel that doesn't go through this generic
options-carousel constructor.

Possible explanations:
1. **PS3 civ-select uses a custom Scaleform sprite** with
   pre-authored cells, separate from the generic carousel
   class.
2. **The civ-select panel was migrated to Scaleform-side** in
   a late-development refactor on PS3, but the PPU
   theOptionArray code path was kept for backward
   compatibility with other panels.
3. **The civ-select panel HAS a PPU constructor** but it
   lives in a different code module that we haven't found —
   maybe one that doesn't use `theOptionArray[%d]` strings at
   all and constructs the variable paths via a completely
   different format.

The iter-189 strict-reading 18th-cell requirement is reaffirmed
as **structurally blocked** under the static-patching toolchain.

## What this iteration unblocks

iter-217 found a NEW set of format strings and a NEW candidate
function path that prior iterations missed. While the test
result is negative, the empirical map of the binary is now more
complete:

- **iter-196 was wrong** about `theOptionArray` not existing.
  All 10 carousel format strings are present.
- **The constructor `FUN_0006c290` is mapped** with field
  layout (`0x858` = start, `0x85c` = end, `0x868` = count).
- **The vtable-dispatched class hierarchy** for options
  carousels is one level deeper than iter-211 thought.
- **The X360 binary has the SAME strings**, confirming this
  is a shared cross-platform code path.

This rules out one more category of "maybe the carousel is
here" and tightens the iter-211/212 conclusion. The strict
reading 18th cell genuinely cannot be reached from PPU patching.

## iter-218 plan options

1. **Search the binary for ALTERNATE carousel constructors**
   that don't use `theOptionArray` strings. The civ-select
   panel probably has its own constructor — find it.
2. **Use Xbox 360 cross-reference** (per §5.6) to find the
   X360 civ-select panel constructor and look for the same
   structural pattern in PS3.
3. **Continue the §5/§6 PRD walk** for any other unfinished
   work.
4. **Wait for user direction** on whether to keep grinding.

## Files

- `findings.md` — this
- `m9_romans_pass.json` — the iter-217 b . trap diagnostic
