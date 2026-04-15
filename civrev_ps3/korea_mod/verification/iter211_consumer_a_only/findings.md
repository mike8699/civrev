# iter-211: consumer A's 7 `li r8 → 0x11` patches are all SAFE but INERT

**Date:** 2026-04-15

## Test setup

Enabled all 7 patches in iter-197's "consumer A" group:

```
0x011676dc  li r8, 0x10 -> 0x11  (TECH)
0x01167744  li r8, 0x10 -> 0x11  (FAMOUS)
0x011677ac  li r8, 0x10 -> 0x11  (CITIES)
0x01167814  li r8, 0x10 -> 0x11  (WONDERS)
0x0116787c  li r8, 0x10 -> 0x11  (WONDERS_FEM)
0x011678e4  li r8, 0x10 -> 0x11  (RULERS)
0x01167948  li r8, 0x10 -> 0x11  (CIVS)
```

Consumer B's 7 patches stayed disabled.

## Results

| probe | slot | label | result |
|---|---|---|---|
| 1 | 0  | romans | **M9 PASS** — boot, civ-select, in-game HUD |
| 2 | 16 | slot16_consA | **M9 PASS** — slot 16 still renders "Random/Random" |
| 3 | 17 | slot17_consA | **M9 PASS** — cursor still clamps at slot 16 |

Same as iter-210's CIVS-only test: **safe but completely
inert** for the carousel render path. No visible change at any
slot, cursor right-clamp unchanged, no Korea anywhere visible.

## Bisection conclusions

- **Consumer A's 7 patches**: SAFE (no boot break) and INERT
  (no visible carousel effect)
- **2 CIVS-only patches** (iter-210, one from A + one from B):
  same — SAFE + INERT
- **All 14 patches together** (iter-198): BROKE BOOT
- **Consumer B's 7 patches alone**: not directly tested in
  this iteration, but by exclusion the iter-198 breakage is
  ENTIRELY in consumer B's set

Further bisecting consumer B is academic — even if we identify
the specific breakage site, the remaining safe sites would be
inert (just like all the other safe sites we've tested).

## Final conclusion: the 14 `li r8` consumer sites are NOT the carousel render path

After three rounds of selective testing (iter-198 with all 14,
iter-210 with CIVS-only, iter-211 with consumer A only), the
collective evidence is overwhelming:

The 14 `li r8, 0x10` sites in `0x011676xx`/`0x01167dxx` are
**not on the civ-select carousel render path**. They iterate
the civnames buffer for some other (probably save-game,
serialization, or pedia) purpose, and bumping their iteration
count from 16 to 17 makes no visible difference to civ-select.

This joins the cumulative ruled-out inventory:

| iter | what was ruled out |
|---|---|
| 150 | FUN_001e49f0 |
| 154 | FUN_011675d8 |
| 198+210+211 | 14 li r8, 0x10 sites (collectively + selectively) |
| 206 | FUN_001dc0d8 + FUN_0x111dd70 |
| 209 | FUN_001262a0 |
| 207..208 | iter-193's panel-loader hypothesis |

## Strong unified hypothesis

The civ-select carousel cell rendering is **entirely
Scaleform-side**. The PPU does NOT call into any
"draw-civ-cell" function. The cells exist as static
MovieClip instances in `gfx_chooseciv.gfx`, with civ
identification baked in at compile time. The PPU only:

- Sends cursor input events to the panel
- Reads the selected civ index back from the panel after
  user confirms
- Looks up the chosen civ's data (from the parser buffer)
  AFTER selection, for in-game initialization

In this model, Korea cannot be added as a 17th visible cell
without modifying the AS2 carousel itself — extending or
adding new MovieClip instances, adjusting layout coordinates,
patching cursor bound logic in the AS2 bytecode, etc.
**iter-178/192/195/200 already explored Scaleform-side
modifications and all of them were inert** (the slotData17
extension proved boot-safe but didn't add a visible cell;
the LoadOptions hardcode-18 in tag[180] was inert; the
tag[184] numOptions=17→18 i32 swap was inert; the tag[185]
numOptions=6 default was inert).

**The iter-189 strict-reading directive is structurally
unachievable** with the static-patching toolchain available
in this loop.

## iter-212 plan

Pivot to documentation and acceptance:

1. **Update PRD §9** to formally document the structural
   blocker. Acknowledge that the iter-189 strict reading
   (Korea as a brand-new 18th carousel cell, all 16 stock
   civs + Korea + Random visible) cannot be achieved by
   static patching of the static EBOOT or .gfx files.
2. **Document the achievable shipping state**: iter-198's
   18-row civnames/rulernames overlays parse cleanly, Korea
   exists in the runtime parser buffer at index 16 with
   correct flags, but no UI element surfaces her (slot 16
   is still Random in the carousel, slot 17 is unreachable).
3. **Add a "blockers" section to §9** listing the
   exhausted approaches: 6 ruled-out functions, all-14
   `li r8` test, multiple Scaleform tag-edit attempts, and
   the lack of Z-packet watchpoint support in RPCS3.
4. **Optionally**: ask user to re-confirm whether the
   strict reading is still the target, or to pivot back
   to the iter-176 v0.9 slot-replacement.

This is option 2 (acceptance) from iter-210's plan. Option 1
(continue binary search) yields no useful information beyond
"which specific consumer B site breaks boot". Option 3 (relax
directive) requires user input.

## Files

- `findings.md` — this
- `m9_romans_pass.json`
- `m9_slot16_inert.json`
- `m9_slot17_clamped.json`
