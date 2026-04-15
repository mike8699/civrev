# iter-210: 2 CIVS-only `li r8 → 0x11` patches are SAFE but INERT

**Date:** 2026-04-15

## Test setup

Enabled ONLY 2 of the 14 `li r8, 0x10 → 0x11` consumer
patches from iter-197/198:

```
0x01167948 (consumer A CIVS): li r8, 0x10 -> 0x11
0x01167dc8 (consumer B CIVS): li r8, 0x10 -> 0x11
```

The other 12 patches (TECH, FAMOUS, CITIES, WONDERS,
WONDERS_FEM, RULERS in both consumers) stayed disabled.

iter-198 had tested ALL 14 simultaneously and the boot HUNG at
RSX init. Subsetting was needed to see if the CIVS-only pair
is safe in isolation.

## Boot test results

| probe | slot | label | result |
|---|---|---|---|
| 1 | 0  | romans | **M9 PASS** — boot, navigation, civ-select, in-game HUD |
| 2 | 16 | slot16_probe | **M9 PASS** — slot 16 still renders "Random/Random" |
| 3 | 17 | slot17_probe | **M9 PASS** — cursor still clamps at slot 16 |

**Conclusion**:
- The 2 CIVS-only patches are **safe** (don't crash boot)
- They are **inert** for the carousel render (no visible
  change at slot 16, cursor still clamped at 16)

The breakage in iter-198 was caused by some combination of the
OTHER 12 patches (TECH, FAMOUS, CITIES, WONDERS, WONDERS_FEM,
RULERS in both consumers).

## What this confirms

The 2 CIVS sites at `0x01167948` and `0x01167dc8` are NOT on
the civ-select carousel render path. Bumping the count from 16
to 17 at these sites doesn't make the carousel draw a 17th
cell, doesn't change the cursor right-clamp, and doesn't
expose Korea anywhere visible.

These sites are some other consumer — most likely save-game,
game-state serialization, or pedia code that iterates the
civnames buffer for non-UI purposes. Bumping their count makes
them iterate one more entry per call, but that entry's data
(Korea or Barbarians) is consumed and discarded by code that
the player never sees.

## Joining the long list of "ruled out" candidates

This is the 6th major "civnames consumer ruled out as not the
carousel" finding:

| iter | what was ruled out |
|---|---|
| 150 | FUN_001e49f0 (suspected per-cell carousel binder) |
| 154 | FUN_011675d8 (second 16-count consumer) |
| 198 | All 14 li r8, 0x10 sites bumped together (BREAKS boot) |
| 206 | FUN_001dc0d8, FUN_0x111dd70 (b . tested, off path) |
| 209 | FUN_001262a0 (CIV_*.dds icon registration; civilopedia) |
| 210 | 2 CIVS-only li r8 patches (safe but inert) |

Plus iter-208's invalidation of iter-193's
`0xf070a0`/`FUN_00f057b0` "ChooseCiv panel loader" hypothesis.

## Implications for §9 DoD item 2

The strict-reading directive (Korea as a brand-new 17th civ
visible at a brand-new 18th carousel cell) **continues to be
unreachable via the static-patching approaches available in
this loop**. We have:

- Korea in the parser buffer at index 16 (verified iter-203)
- Korea's FString correctly read as "Koreans" at runtime
- All 16 stock civs unchanged
- Random still at slot 16 of the carousel
- Cursor right-clamp still at slot 16

But no PPU code path that we've been able to find exposes
Korea to the rendering layer.

## Hypothesis for why nothing surfaces Korea

The Scaleform `gfx_chooseciv.gfx` carousel may have its cells
**hardcoded as static MovieClip instances** with compile-time
civ assignment. There may be NO PPU→Scaleform data flow for
the cells — the cells are purely AS2 / Scaleform-side, with
the PPU only sending cursor events and "current selection"
indices.

In that model:
- Adding a 19th `slotData17` constant is inert (iter-178/200
  already proved this — no visible change)
- The civnames parser buffer is consumed by other systems
  (in-game UI, pedia, save game) but not by the carousel
- The CIV_*.dds icon table feeds the civilopedia, not the
  carousel
- The cursor right-clamp is in some piece of Scaleform AS2
  bytecode we haven't found, OR is hardcoded in PPU as a
  separate constant disconnected from civnames

If true, the iter-189 strict-reading is **structurally
unachievable** without rewriting the AS2 carousel to add a
new cell — which is a much bigger surgery than this loop's
toolchain supports.

## iter-211 plan options

1. **Continue the binary search:** enable consumer A (7
   patches) only. If boot passes, the breakage is in B. If
   hangs, in A. Then halve again. ~3-4 test cycles to find
   the specific breakage site.
2. **Retract the strict-reading** and pivot to a relaxed DoD:
   ship Korea as a slot-replacement for a stock civ (the
   iter-176 v0.9 approach), accepting the iter-189 directive
   was overambitious for this toolchain.
3. **Accept the iter-198 partial state** and document the
   blocker as "carousel render path lives in Scaleform AS2,
   not PPU code; static patching cannot extend it; runtime
   instrumentation (Z-packets) blocked because the stub
   doesn't support them".

iter-211 should make a definitive call: continue with binary
search (option 1) for one more iteration, OR pivot to
acceptance/documentation (option 3). The user directive
favors option 3 if option 1 doesn't yield a breakthrough.

## Files

- `findings.md` — this
- `m9_romans_pass.json`
- `m9_slot16_unchanged.json`
- `m9_slot17_clamped.json`
