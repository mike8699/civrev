# iter-200: tag[184] `_root.numOptions = 17` literal is INERT (confirming iter-179)

**Date:** 2026-04-15
**Goal:** iter-199's Option D — stack the REAL `numOptions=17`
Scaleform literal (in tag[184], NOT tag[185]) flipped to 18 on top
of iter-198's 18-row civnames/rulernames overlay. See if the
combined "parser-buffer-Korea + Scaleform-numOptions-18" produces
a visible 17th/18th carousel cell.

## The correction of iter-195

iter-195 flipped tag[185]'s `_root.numOptions = 6` default from 6
to 18 at file offset `0x59eb` and found it INERT. I described
that finding as "tag[185]'s default is dead code".

iter-200's tag[184] parse revealed that the REAL `numOptions = 17`
setter is in tag[184] (the `slotData0..slotData16 + numOptions`
constant pool DoAction), not tag[185]. Pool count 96, entry 11 is
`"numOptions"`, entry 93 is `"slotData16"`. At bc@0x4af inside
tag[184]'s action stream (file offset 0x52f2) is:

```
0x52f2  Push[(c1, idx=11 "numOptions"), (i32, value=17)]
0x52fc  ActionSetVariable (0x1d)
```

The i32 literal 17 lives at file offset `0x52f8..0x52fb` as
`11 00 00 00`. This is the source the PPU iter-180 search was
looking for all along — but it's a **Scaleform-local initializer**,
not a PPU SetVariable call. iter-180's hypothesis that the PPU
overrides this via Flash::Invoke was wrong in direction: the
setter is IN the gfx file all along, just in tag[184] not tag[185].

## iter-200 probe

1. `gfx_chooseciv_patch.py` flipped `11 00 00 00 → 12 00 00 00`
   at file offset `0x52f8`.
2. Rebuilt Pregame via the fpk.py repack path.
3. Installed, booted via the harness.
4. Ran `korea_play 17 slot17_probe` to check cursor reachability.
5. Ran `korea_play 16 slot16_probe` to check slot 16 content.

## Result

| probe | slot | label | result | cursor ended | OCR snippet |
|-------|------|-------|--------|---------------|-------------|
| 1     | 17   | slot17_probe | PASS | Random (=16) | "Shaka Genghis Elizabeth ... Random Random" |
| 2     | 16   | slot16_probe | PASS | 15/16 | "Aontezuma Shaka Genghis ... Random" |

Both probes "pass" only because M9's oracle is "in-game HUD
appears after X is pressed" — any civ at the cursor position
starts a game successfully. Neither probe reached slot 17. The
visual carousel is unchanged — slot 16 is still Random, slot 17
doesn't exist, and Korea at civnames index 16 in the parser
buffer remains invisible.

**The tag[184] `numOptions = 17` literal is INERT for the cursor
clamp.** Confirms iter-179's isolated finding and the iter-186
retraction of iter-181..183. The right-arrow handler's upper
bound is read from somewhere else.

## Net state for §9 DoD item 2

Still blocked. Korea exists in the parser buffer. The Scaleform
side has been fully probed: tag[184] numOptions literal is inert,
tag[185] numOptions default is inert, tag[180]'s LoadOptions loop
bound is inert (iter-192). Every known static cell-count location
has been tested and none affect the carousel visible count.

## What this leaves

The carousel cell count/bound must live in **one of**:
- A hardcoded `16` / `0x10` constant in the PPU code that
  intercepts the right-arrow key-event BEFORE it reaches the
  Scaleform panel, and rejects input past slot 16. iter-187's
  "double-clamp" attempt was on this path and also failed.
- A value computed at runtime from one of the `li r8, 0x10`
  consumer functions' OTHER outputs (iter-198 disproved the
  direct `li r8` bump, but those functions write to other class
  fields we haven't traced).
- A Scaleform internal that we're not hitting via our static
  patches — for example, a DefineSprite child-clip count on the
  carousel sprite, or a MovieClipLoader queue that only receives
  16 items regardless of numOptions.

**iter-201 pivot: Option C (dynamic).** Extend `gdb_client.py`
with Z2 write-watchpoint support and plant a watchpoint on the
civnames buffer header at `*(r2 + 0x141c) - 4` immediately after
boot. During civ-select panel init, observe every read of the
buffer — the reader is the render path, and its surrounding code
will contain the actual cursor bound. PRD §6.2 declares this
first-class in-scope.

## Files

- `findings.md` (this)
- `m9_slot17_probe_result.json`
- `m9_slot16_probe_result.json`
