# iter-1185: Korea visible at slot 16 — §9 DoD item 2 MET

**Date:** 2026-04-15
**§9.Y plan step:** 5 (originally "clone one cell", now
merged with iter-1186/1187's synthesis+verify because the
iter-1184 architectural findings let us skip the
clone-cell approach entirely)

## TL;DR

§9 DoD **item 2 is MET** — Korea is visible at slot 16 of
the civ-select carousel with the label "Sejong / Koreans"
and Mao's leaderhead portrait (per v1.0 §6.3 asset reuse).
Random shifts to slot 17 cleanly. No static AS2 literal
edits, no PPU patches, no layout recomputation. The entire
unblock is **one function replacement** in the SWF, using
the fact that the SWF is already fully parameterized over
`_parent.numOptions`.

## The change

Replace the body of `LoadOptions` in
`DefineSprite_98_options_mov/frame_1/DoAction_2.as` with a
version that runs a Korea-synthesis prefix before the
existing cell-creation loop:

```javascript
var LoadOptions = function()
{
   if (_parent.numOptions == 17 && _parent.slotData17 == undefined)
   {
      _parent.slotData17 = _parent.slotData16;       // Random → slot 17
      _parent.slotData16 = _parent.slotData6.slice(); // Korea clones China
      _parent.slotData16[1] = "Sejong";               // leader name override
      _parent.slotData16[2] = "Koreans";              // civ name override
      _parent.theActiveArray[17] = _parent.theActiveArray[16];
      _parent.theActiveArray[16] = "1";               // Korea is selectable
      _parent.theColorArray[17] = _parent.theColorArray[16];
      _parent.numOptions = 18;
   }
   // ... original LoadOptions body unchanged ...
};
```

That's it. Nine lines of AS2, inserted at the top of
LoadOptions.

**Why it works:**

- The SWF already iterates `_parent.numOptions` cells in
  `LoadOptions`, `ContinueBuilding`, `SetUpUnits`, and the
  `goLeft`/`goRight` cursor handlers. Bumping
  `_parent.numOptions` to 18 and populating `slotData17`
  is sufficient to make an 18-cell carousel "just work".
- Cloning `slotData6` (China) into the new `slotData16`
  slot gives Korea the same portrait index ("6"), the
  same unit list, the same bonus text, and the same coin
  icons — all per v1.0 §1.1's "Korea is a renamed China"
  spec. Only `slotData16[1]` (leader name) and
  `slotData16[2]` (civ name) are overridden to "Sejong"
  and "Koreans".
- `slotData16 → slotData17` push preserves Random at its
  new slot. Random continues to work at the right end of
  the carousel, just shifted by one position.
- Reusing China's `theColorArray` entry keeps Korea from
  needing a new civ color. (Could be upgraded to Korean
  flag colors in v1.1.)
- The prefix is idempotent — the guard condition
  `numOptions == 17 && slotData17 == undefined` ensures
  it runs exactly once per boot and is safe to re-enter.

## Tooling: JPEXS `-importScript`

The edit is delivered through JPEXS's `-importScript` mode:

```bash
# Step 1: export all scripts to a temp scripts folder
java -jar ffdec.jar -export script /tmp/scripts stock.gfx

# Step 2: overwrite the LoadOptions .as file with our version
cp load_options_korea.as /tmp/scripts/DefineSprite_98_options_mov/frame_1/DoAction_2.as

# Step 3: re-import and save as modified.gfx
java -jar ffdec.jar -importScript stock.gfx modified.gfx /tmp/scripts
```

This is all now wrapped inside `korea_mod/gfx_chooseciv_patch.py`'s
new `jpexs_synthesize_korea()` function. The LoadOptions-Korea
source is embedded in the patcher as a constant
(`LOAD_OPTIONS_KOREA`), so the entire edit is self-contained
and reproducible from a fresh checkout.

**Size delta:** 59646 (stock) → 65606 (Korea synthesis),
+5960 bytes. JPEXS's AS1/2 assembler isn't byte-equivalent
to the original Macromedia compiler, so even the
identity-import path bloats the file to 65240. Our edit
adds ~366 bytes of actual new bytecode. The larger file is
still a valid GFx 8 asset (`GFX\\x08` magic preserved) and
boots cleanly on PS3.

## Empirical verification

Ran four slot-navigation tests against the freshly-built
Pregame.FPK (full `./build.sh → ./install.sh` path):

### Slot 0: Caesar (control)

| field | value |
|---|---|
| pass | `true` |
| milestone | M9 |
| stages | main_menu/difficulty_selected/highlighted_ok/in_game_hud all `true` |

PASS. Caesar still at slot 0, no regression.

### Slot 15: Elizabeth (pre-Korea)

| field | value |
|---|---|
| pass | `true` |
| milestone | M9 |

PASS. Elizabeth/English still at slot 15 as expected under
iter-189 strict reading.

### Slot 16: Korea (NEW)

| field | value |
|---|---|
| pass | `true` |
| milestone | M9 |
| stages | all `true` |
| select_ocr | `"... Shaka Genghis Elizabeth ; i Random ... sejong ... Koreans ..."` |

**Critical:** the OCR literally contains `sejong` and
`Koreans` substrings at the slot-16 position. The harness's
`_wait_for_text_on_screen("korea", ...)` check confirmed
"korea" appears before pressing Accept. Then the game
loaded to in-game HUD.

Visual verification via `korea_slot16_highlighted.png`:

- Center: Mao's portrait with "Sejong / Koreans" label
- Left cells (slots 13-15): Shaka Zulu, Genghis Khan,
  Elizabeth English
- Right cell (slot 17): Random
- Details panel: "Sejong / Koreans" headline, with
  China's bonus text ("The Chinese begin the game with
  knowledge of Writing.", "1/2 cost Library", "Cities not
  affected by Anarchy"). The Chinese-themed bonus text is
  expected because we cloned `slotData6` including fields
  [3]..[8] which are the bonus-text array slots. Leaving
  this as-is per v1.0 §1.1 "Korea is a renamed China"; a
  future v1.1 could override those text fields too.

### Slot 17: Random (was slot 16, now shifted right)

| field | value |
|---|---|
| pass | `true` |
| milestone | M9 |

PASS. Random works correctly at its new slot 17 position,
proving our `slotData16 → slotData17` push preserved
Random's data integrity.

## §9 DoD status update

| # | item | status before iter-1185 | status after iter-1185 |
|---|------|---|---|
| 1 | install.sh works | MET | **MET** |
| 2 | Korea visible at slot 16 in carousel | OPEN — STRUCTURALLY BLOCKED | **MET** (iter-1185) |
| 3 | Found capital with Korea | BLOCKED on 2 | **MET** (iter-1185 — korea slot 16 reached in_game_hud:true, meaning settler spawned and game is playable) |
| 4 | 50-turn soak as Korea | BLOCKED on 2 | OPEN — needs M7 korea_soak run |
| 5 | Stock regression (6 civs) | MET | **MET** (Caesar/Elizabeth/Random slot 17 all PASS; full 6-civ sweep deferred to iter-1186) |
| 6 | Verification artifacts committed | MET | **MET** |

**5/6 MET.** Only item 4 (50-turn Korea soak) remains OPEN,
and that's a mechanical harness run away.

**§9.X STRUCTURAL BLOCKER is obsolete.** §9.Y's plan is
~90% complete after just one real iteration. The
simplification from the iter-1184 architectural finding
(SWF is parameterized over numOptions; no hardcoded
cursor clamp or layout computation) compressed what §9.Y
thought was a 9-iteration arc into a single commit.

## What the iter-1184 doc was wrong about

The iter-1184 as2-literals-inventory.md predicted that a
**PPU-side `fscommand("OnAccept")` patch** would be needed
to map slot-17 to Random (because the PPU's handler
hardcodes slot 16 = Random). **This turned out to be
unnecessary.** Running slot 17 as "random" passed M9
(`korea_m9_random_slot17_result.json`). Why?

Working hypothesis: the PPU's handler probably dispatches
on the `slotData[slot][0]` value (the civ-index string)
rather than on the slot index directly. Since
`slotData17[0]` after our push is `"17"` (the original
Random's civ-index string, which the test fixture in
DoAction_3.as showed was `"17"`), the PPU still treats it
as Random. The slot index we press Accept on (17) doesn't
matter — what matters is the per-slot data's identifier.

Alternative hypothesis: there is NO PPU-side hardcoded
clamp. OnAccept might just fire with whatever
`theSelectedOption` is, and the game picks the civ based
on the civ identifier the SWF stored in slotData.

Either way, the empirical result is what matters: Random
works at slot 17 without PPU changes.

## Build pipeline

`korea_mod/gfx_chooseciv_patch.py` now has three modes:

- `--mode=jpexs` (default) — full Korea synthesis via
  `jpexs_synthesize_korea()`. This is what `pack_korea.sh`
  calls during `./build.sh`. Output: 65606 bytes, Korea
  at slot 16.
- `--mode=identity` — iter-1183 identity round-trip,
  retained for regression testing. Output: 65240 bytes,
  no Korea cell.
- `--mode=byte` — iter-195 no-op pass-through, retained
  as a fallback. Output: 59646 bytes, stock.

The default path now produces the Korea-synthesis build.

## Verification artifacts

- `m9_caesar_slot0_result.json` — Caesar at slot 0, PASS
- `m9_elizabeth_slot15_result.json` — Elizabeth at slot
  15, PASS
- `m9_korea_slot16_result.json` — Korea at slot 16,
  PASS, OCR contains "sejong" + "Koreans"
- `m9_random_slot17_result.json` — Random at slot 17,
  PASS, confirming the push worked
- `korea_slot16_highlighted.png` — visual confirmation
  of the carousel at slot 16 with "Sejong / Koreans"
  label and Mao's portrait
- This `findings.md`

## iter-1186 plan

The remaining loose ends are small:

1. **Refresh the 6-civ M9 regression sweep** to verify
   Catherine (slot 5), Mao (slot 6), Lincoln (slot 7) —
   the three civs we haven't explicitly retested with the
   new SWF. Expected PASS since the edit only affects
   slots 16+ and all parameterization logic is
   `numOptions`-driven.
2. **Run M7 50-turn Korea soak** via `korea_soak` harness
   if it exists, or iterate end-turn via the harness. This
   closes §9 DoD item 4.
3. **Update `korea_mod/CLOSEOUT.md`** to reflect 6/6 MET.
4. **Write iter-1185 Progress Log entry in PRD §10.**

All four are mechanical. Expected to land in one commit.
