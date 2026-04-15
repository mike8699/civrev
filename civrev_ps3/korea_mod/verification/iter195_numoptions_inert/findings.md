# iter-195: tag[185] `_root.numOptions` default is INERT for civ-select

**Date:** 2026-04-15
**Hypothesis under test (from iter-194):** tag[185] in
`gfx_chooseciv.gfx` is the civ-select carousel factory, and its
`_root.numOptions = 6` setter at bc@0x3b7 is the bound that the
collection loop at bc@0x153 reads when populating the carousel.
If true, flipping that default from 6 to 18 should either grow
the carousel to 18 cells or break it visibly.

## What changed

A new helper `civrev_ps3/korea_mod/gfx_chooseciv_patch.py` was
introduced and wired into `pack_korea.sh`. Pregame is now built
through the **fpk.py repack** path (proven byte-identical-safe in
iter-177) instead of the iter-190 byte-patcher path:

```
extracted/Pregame/  -->  _build/Pregame_korea/
    -> gfx_chooseciv_patch.py (in-place edit)
    -> fpk.py repack
    -> Pregame_korea.FPK
```

For this iteration the helper applied **one** 4-byte same-size
swap: at file offset `0x59eb` of `gfx_chooseciv.gfx`, the i32
literal in the `_root.numOptions = 6` Push (tag[185], bc@0x3b7)
was changed from `06 00 00 00` to `12 00 00 00`. Verified the
repack produced exactly one byte-diff at offset `0x59eb` (`06`
-> `12`). Pregame_korea.FPK SHA-256:
`eb3d6d6057447d1abb672572f990d7df747d609cc1802b70a8be76650b618abe`.

## Test results

| Probe | Slot | Label | Expected if hypothesis true | Result |
|---|---|---|---|---|
| 1 (M6) | 15 | elizabeth | regression PASS | **PASS** (`highlighted_ok=true`, `in_game_hud=true`) |
| 2 (M9) | 17 | slot17_probe2 | new 18th cell visible OR cursor reaches slot 17 | **CURSOR CLAMPED AT 16** |

`m6_elizabeth_result.json` and `m9_slot17_probe2_result.json` are
in this directory. The slot-17 06_slot_highlighted screenshot
(`slot17_06_clamp_at_random.png`) shows the cursor locked on the
**Random** cell after 17 right-presses — exactly where it would
clamp without any patch. No 18th cell is visible. No visual
change anywhere on the civ-select screen.

(Probe 2 was a re-run; the first run was eaten by an unrelated
PSN Sign-In modal popup that the test harness happened to land
on. The retry was clean.)

## Conclusion

The `_root.numOptions = 6` default in tag[185] of
`gfx_chooseciv.gfx` is **not** the authoritative bound for the
civ-select carousel. Flipping it to 18 has zero observable effect:

- Boot still succeeds (so the file isn't broken)
- Stock civs still work (Elizabeth M6 still PASSes)
- No 18th cell appears
- Cursor still right-clamps at slot 16 (Random)

The PPU must be overriding `numOptions` to 17 at civ-select panel
init time — almost certainly via a `Flash::Invoke SetVariable`
call against the `ChooseCiv` panel — *before* tag[185]'s
collection loop at bc@0x153 ever runs. The static AS2 default is
dead by the time the loop sees the variable.

## What this rules out

- iter-194's hypothesis "tag[185] is the carousel factory" is
  **disproved**. Or more precisely: even if tag[185] *does* run
  the collection loop, its statically-defined bound is dead code
  for the civ-select use of the panel, and patching it goes
  nowhere.
- The right-clamp at slot 16 is **not** in the AS2 either — the
  cursor still stops at 16 even with `numOptions = 18` set
  statically. Whatever bounds the cursor is reading the runtime
  `numOptions`, which the PPU controls.

## Next iteration

Locate the PPU `Flash::Invoke "SetVariable"` (or equivalent) call
that writes `numOptions` for the "ChooseCiv" panel. Two viable
paths:

1. **Static**: search the EBOOT for the string `"numOptions"`,
   find every site that takes its address, and trace which ones
   feed into a Flash invoke wrapper (the panel-loader at
   `0xf070a0` mapped in iter-193 is the natural starting point —
   walk forward from there looking for SetVariable shape: `argc`
   set to 2, `numOptions` arg, target panel "ChooseCiv").
2. **Dynamic**: use the GDB Z-packet support in `gdb_client.py`
   to set a write-watchpoint on the Scaleform variable storage
   for `numOptions` once we identify the live address (likely
   inside the GFx ASValue table for the panel), then trigger the
   civ-select panel and capture the writer.

A complementary sanity check worth running cheap: write a
distinctive marker into the existing `slotData16` block and see
if the Random cell title actually picks it up at runtime — that
would confirm the slotData arrays are being consulted at all
during civ-select rendering, vs. being purely the legacy/dead
data from a Pregame template that the runtime ignores.

The infrastructure scaffolding (gfx repack pipeline, gfx patcher
hook in pack_korea.sh) is in place and proven boot-safe for
future iterations to use without the iter-178 byte-injection
acrobatics.
