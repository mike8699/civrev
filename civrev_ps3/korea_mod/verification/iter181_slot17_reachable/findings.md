# iter-181: BREAKTHROUGH — slot 17 reachable via goRight clamp extension

**Date:** 2026-04-14

## The finding

A single 4-byte change to `gfx_chooseciv.gfx` — patching the i32 literal
`1` to `0` in the `goRight` function's clamp subtraction — **extends the
right-arrow cursor beyond slot 16 into a new slot 17**. The carousel
responds. This is the first time the cursor has moved past the 17-cell
limit in any iteration.

## The patch

tag[188] at file offset `0x6fd6` contains the `goRight` function. In its
body, at bc offset `0x28a` (file offset `0x7461`), the opcode:

```
96 05 00 07 01 00 00 00   # ActionPush: i32(1)
```

...was patched to:

```
96 05 00 07 00 00 00 00   # ActionPush: i32(0)
```

This `PUSH 1` is consumed by the `Sub` opcode at bc@0x292, which
computes `numOptions - 1` as the clamp comparison target. Changing it
to `PUSH 0` makes the comparison `numOptions - 0`, so `theSelectedOption
== numOptions` triggers the clamp instead of `theSelectedOption ==
numOptions - 1`. Result: cursor max = `numOptions`, not `numOptions - 1`.

## M9 test result

- `korea_play 17 clamp_test` M9 **PASS** (`in_game_hud: true`, game
  loaded after pressing Right 17 times from slot 0).
- OCR shows `Genghis Khan / Elizabeth English / Random Random`
  visible at the left of the carousel, and the central cell is
  `"undefined / undefined"` with all fields (era bonuses, special
  units, description) reading `undefined`.
- The yellow right-arrow is still visible in the screenshot — the
  carousel thinks there's still "more" to scroll to.

Screenshot at `korea_play_06_slot_highlighted.png`.

## Why the central cell is "undefined"

After the clamp extension, the cursor reaches `theSelectedOption = 17`.
But `theActiveArray[17]` was never populated (only slots 0..16 exist),
so the carousel renders the cell with undefined values for every text
field. The "?" silhouette portrait is used as the fallback image,
likely because the 3D portrait at slot 17 doesn't exist either.

This is **expected behavior** for this minimal patch and confirms that:
  1. The clamp was the blocker.
  2. The carousel *will* render a new cell if the cursor can reach it.
  3. The data-array side (slotData17, theActiveArray extension,
     per-cell values) is an independent work item.

## Path forward for a fully populated slot 17

With this clamp unblock in hand, the next steps are:

1. **Add slotData17 to the Scaleform constant pool and create a
   setVariable block for it.** iter-178 already proved this is safe
   (boot preserved, game still loads). This populates the cell's
   primary data reference.

2. **Extend `theActiveArray`** — either by dynamically appending a
   17th element in an init script, or by finding and bumping the
   hardcoded length N in theActiveArray's constructor in tag[184]
   (around bc@0x2d where the `new Array()` call happens).

3. **Feed real Korea data into slot 17's slot data.** Options:
     - Copy slot 6's (China's) data as a clone, then override a few
       fields with Korea-specific strings.
     - Or populate via PPU SetVariable calls once the EBOOT-side
       init loop is found and extended.

4. **Optionally**: add a new 3D leader-head model placement for
   slot 17 via a DefinePlaceObject tag. Low priority — slot 16
   (Random) uses the generic "?" silhouette for the same reason.

None of these are committed in iter-181. The clamp-extension patch is
documented here as a proven-working technique for future iterations.

## Side findings during iter-181 investigation

- **`slotData%d\0` format string** exists in the EBOOT at
  file offset `0x168c518` (vaddr `0x169c518`) and a second copy at
  `0x1697135`. One TOC slot (r2-0x3d04) points at it. Three lwz
  sites load it: `0xdfd0c`, `0xdffb8`, `0xeb4a14`. Disassembled the
  loop at `0xdfd78..0xdffec` that uses it (sprintf format + Scaleform
  SetVariable), but the loop bound is `r21 = 1` set at `0xdf690` —
  not a 17-iteration bulk initializer.

- **No `li rN, 17` instruction is found within 120 bytes of any of the
  43 lwz sites that load the numOptions string pointer.** The value
  17 is not being loaded as a literal immediate; it likely comes from
  a parsed civ count stored in memory.

- **`numOptions` has 10 TOC slots** (iter-180 finding). These are
  scattered across 43 lwz call sites in the text segment.

- **iter-181 made no committed changes to `eboot_patches.py` or any
  shipped artifact.** The clamp test was reverted by
  `korea_mod/install.sh` after the M9 PASS. The committed
  `Pregame_korea.FPK` remains the iter-176 v0.9 byte-patch version.
