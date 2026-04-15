# gfx_chooseciv.gfx AS2 literal inventory

**Date:** 2026-04-15
**§9.Y plan step:** 2+3+4 (identify real carousel sprite,
dump AS2 bytecode, classify literals)

**Tooling:** JPEXS 22.0.2 `-dumpAS2` and `-export script`
commands. Full decompiled AS2 source staged under
`korea_mod/docs/as2_source/scripts/` for reference (not
intended for git diff; it's a snapshot of the stock file).

---

## The carousel architecture (as it actually is)

This section rewrites the §9.Y plan's assumptions based on
the actual AS2 source (not the iter-212 hypothesis). The
plan asserted iter-212's guess that "tag[177] ChooseCivLeader
char 96" was the carousel sprite. Reality is subtler and
BETTER for the unblock path:

### Two sprites, two roles

| chid | name | role |
|---|---|---|
| 96 | `ChooseCivLeader` | **Per-cell template**. Contains one civ's portrait, leaderhead, lock overlay, and scoot/animate state machine. Instantiated dynamically via `attachMovie("ChooseCivLeader", ...)` |
| 98 | `options_mov` | **Carousel factory**. Placed once at root as `options_mov`. Its frame-0 DoAction defines `LoadOptions()` which iterates `_parent.numOptions` and calls `attachMovie("ChooseCivLeader", "option_"+i, depth)` to spawn the cells |

### How the carousel gets built

Root frame 0 runs (from `scripts/frame_1/`):

1. `DoAction.as` — defines `OnInitComplete` which calls
   `StartBuilding()`
2. `DoAction_4.as` — declares root state:
   - `theSelectedOption = 0`
   - **`numOptions = 6`** (DEFAULT, overridden by PPU)
   - `theOptionArray = []`
   - Defines `StartBuilding()` → calls
     `this.options_mov.LoadOptions()`
   - Defines `ContinueBuilding()` → called after all cells
     finish async loading; iterates `i = 0..numOptions-1`
     and pushes `options_mov["option_"+i]` into
     `theOptionArray`, then calls `SetUpUnits()` which
     reads `this["slotData"+j]` arrays for j=0..numOptions-1
     and sets portraits, colors, text on each cell
   - Defines `SetUpUnits()` — the per-cell populator

3. `DoAction_7.as` — defines cursor handlers:
   - `goLeft()` — decrements `theSelectedOption`, clamps at
     0, scoots cells, updates display
   - `goRight()` — increments `theSelectedOption`,
     **clamps at `numOptions - 1`** (NO hardcoded 16/17),
     scoots, updates display

4. Sprite 98 (`options_mov`)'s frame-0 DoAction_2 defines
   `LoadOptions` as:
   ```javascript
   var LoadOptions = function() {
      if (_root.testingMode == 1) {
         numLoaded = _parent.numOptions - 1;
      } else {
         numLoaded = 0;
      }
      if (_parent.numOptions > 0) {
         i = 0;
         while (i < _parent.numOptions) {
            this.attachMovie("ChooseCivLeader",
                             this["option_" + i],
                             this.getNextHighestDepth(),
                             {_name: ["option_" + i],
                              _x: parseInt(xloc),
                              _y: parseInt(yloc)});
            i++;
         }
      } else {
         trace("PROBLEM LOADING: numOptions = " + numOptions);
      }
   };
   ```

5. PPU side (from EBOOT strings and iter-217 finding):
   - `Flash::GetVariable("theOptionArray[%d].unitStack.goLeft")`
   - `Flash::GetVariable("theOptionArray[%d].unitStack.goRight")`
   - `Flash::GetVariable("theOptionArray[%d].unitStack.ExitPanel")`
   - The PPU uses `theOptionArray` as the Scaleform-side
     carousel data backbone, passing events to the AS2 cells
     via GetVariable path lookups

### The data contract between PPU and SWF

For the carousel to display N cells, these SWF-side globals
must be populated (normally by PPU `SetVariable` calls):

- `_root.numOptions` — integer count (default 6, PPU sets 17)
- `_root.slotData0`, `_root.slotData1`, ... `_root.slotData{numOptions-1}`
  — each an Array of strings/numbers matching
  `SetUpUnits`' expectations (`SetPortrait(arr[0])`,
  `SetColor(theColorArray[j])`, `SetText(0, arr[1] + "\n" +
  arr[2])`, and indices 3..16 for bonus text / unique
  unit / coin icons)
- `_root.theActiveArray` — Array where
  `theActiveArray[j] == "0"` means the civ is locked
  (unselectable)
- `_root.theColorArray` — Array of RGB integers, one per civ

**This is the entire data contract.** There is no separate
"carousel cell count" baked into the SWF — it's all driven
by `numOptions` and the parallel data arrays.

---

## Literal inventory

Every `16` / `17` / `0x10` / `0x11` integer literal that
appears in the AS2 source, classified.

### Dead code (testingMode-only fixtures)

These literals are inside code paths guarded by
`_root.testingMode == true`, which the PS3 production build
never enters. The PPU sets `testingMode = false` during
init. All iter-195/200 literal patches targeted code in
this category, which is why they were inert.

| file | line | literal | what it does |
|---|---|---|---|
| `frame_1/DoAction_3.as` | 6 | `while(i <= 17)` | Empty loop, 18 iterations, do-nothing |
| `frame_1/DoAction_3.as` | 18 | `numOptions = 17;` | Test fixture setter inside `thisIsATest` function |
| `frame_1/DoAction_3.as` | 25 | `slotData0 = new Array("14","Caesar"...)` | Test fixture data arrays (slotData0..slotData16) with demo content ("1/2 Price Roads", "1/2 Cost Wonders", etc.) |
| `frame_1/DoAction_3.as` | 41 | `slotData16 = new Array("17","RANDOM"...)` | Test fixture slot 16 = RANDOM |
| `frame_1/DoAction_4.as` | 55 | `while(i < 17)` | Inside `if (_root.testingMode == true)` branch of `ContinueBuilding`. Precomputes `CalculateTargetXLoc(i)` 17 times. Dead in production |

**Verdict:** none of these literals need to be patched.
iter-195 and iter-200 patched literals in DoAction_3 and
tag[184] (which maps to sprite 98's DoAction_2 / tag index
varies) and got inert results because production never
executes those code paths.

### Default values (overridden by PPU)

| file | line | literal | what it does |
|---|---|---|---|
| `frame_1/DoAction_4.as` | 3 | `numOptions = 6;` | Default fallback value if PPU SetVariable fails. Production overrides to 17 |

**Verdict:** don't patch the default. We want the PPU's
runtime value (17 or 18) to flow through unchanged.

### Data-array indices (NOT counts)

These literals index into per-slot data arrays; they
represent the STRUCTURE of slotDataN (each slotData entry
is a ≥17-element array), not the count of civs.

| file | line | literal | what it does |
|---|---|---|---|
| `frame_1/DoAction_4.as` | 110 | `SetCoins(..., myDataArray[16])` | Reads 8 coin icons from slotData array indices 9..16 |

**Verdict:** irrelevant to carousel count. Per-cell data
shape is fixed; we clone existing cell data when synthesizing
new slots.

### Live carousel code (non-test path)

These literals run in production.

| file | line | literal | what it does |
|---|---|---|---|
| `frame_1/DoAction_2.as` | 21 | `case 16:` | Key.getCode() Shift key handler (`this.theMainPanel.ShowPortrait(false)`). NOT a civ count — it's keycode 16 = Shift |
| `DefineSprite_96_ChooseCivLeader/frame_1/DoAction.as` | 158 | `case "16":` | `GetImageName` switch: maps `"16"` → `"barbarian"` (Random's LDR texture key) |
| `DefineSprite_96_ChooseCivLeader/frame_1/DoAction.as` | 163 | `case "17":` | `GetImageName` switch: `"17"` → `"default"` (fallback) |

**Verdict:** `case "16"`/`case "17"` in GetImageName is the
only live code that maps civ identifiers to LDR texture keys.
Under the iter-189 strict reading where Korea is at slot 16
and Random shifts to slot 17, this switch needs one edit:

```javascript
// NEW: add Korea case
case "16":
case "korean":
case "sejong":
   _loc1_ = "china";  // reuse Mao's leaderhead per §6.3
   break;
// SHIFT: barbarian was case "16", move to case "17"
case "17":
case "barbarian":
   _loc1_ = "barbarian";
   break;
// SHIFT: default was case "17", move to case "18"
case "-1":
case "18":
default:
   _loc1_ = "default";
```

Or (simpler) — since we're reusing China's portrait anyway,
we can make Korea at slot 16 pass `"6"` (China's index
string) to `SetPortrait()`, hitting the existing `case "6":`
→ `_loc1_ = "china"` branch with no edit to GetImageName. The
civ's displayed leader/name/text comes from slotData16[1]
and slotData16[2] which we set separately.

---

## Strategic implication: the unblock path is simpler than §9.Y thought

§9.Y's 6-change list assumed a lot of hardcoded AS2 literals
to patch. The reality is the SWF is **fully parameterized**
over `numOptions` — only the GetImageName lookup in sprite
96 has any hardcoded civ identification, and even that can
be sidestepped by passing China's index string.

**Minimum-edit unblock path** (revised from §9.Y):

1. **Inject an AS2 prefix into `options_mov`'s frame-0
   DoAction_2 (or wrap `LoadOptions`)** that runs
   immediately before the cell-creation loop. This prefix
   checks if `_parent.numOptions == 17` and if so:
   - Bumps `_parent.numOptions` to 18
   - Clones `_parent.slotData16` into `_parent.slotData17`
     (so Random shifts right)
   - Overwrites `_parent.slotData16` with a Korea-themed
     array: `["6", "Sejong", "Koreans", ...rest cloned
     from slotData6]` (China's slotData) so Korea reuses
     China's portrait, unit list, bonus text, and coin
     icons per v1.0 §1.1
   - Copies `theActiveArray[16]` to `theActiveArray[17]`
     and sets `theActiveArray[16] = "1"` (Korea selectable)
   - Copies `theColorArray[16]` to `theColorArray[17]` and
     sets `theColorArray[16]` to a Korean flag color
     (or reuses China's)

2. **PPU fscommand handler patch:** when the user confirms
   their civ selection, the SWF fires
   `fscommand("OnAccept", theSelectedOption)`. The PPU's
   OnAccept handler currently does `if (slot == 16)
   doRandom() else startGameWithCiv(slot)`. Under our new
   layout, slot 16 = Korea and slot 17 = Random, so the
   PPU needs `if (slot == 17) doRandom() else
   startGameWithCiv(slot)`. This is a one-byte immediate
   patch (bump a `16` literal to `17`) that can be found by
   static search in the EBOOT. **No static_ppu search is
   needed because we already have the fscommand infra:
   search for `OnAccept` string xref in EBOOT, find the
   handler, patch the immediate.**

3. **NOT NEEDED from §9.Y's original plan:**
   - Recomputing layout coordinates — `SetUpUnits` uses
     `_loc2_._x = j * (_loc2_._width + theBuffer)` which is
     parameterized over `j`, so 18 cells Just Work
   - Patching cursor right-clamp — `goRight` reads
     `numOptions - 1`, no hardcoded 16
   - Patching `theOptionArray` init — it's a local runtime
     array, populated per-run
   - Patching `numOptions` literals — dead test code

This reduces §9.Y's work from ~9 iterations to ~2-3.

---

## Still to verify in iter-1185 / iter-1186

1. **Assumption:** PPU sets `numOptions = 17` via
   `Flash::SetVariable("numOptions", 17)` during panel
   init. Verify via RPCS3 log trace or GDB watchpoint on
   the SetVariable call site.

2. **Assumption:** PPU sets `slotData0..slotData16` via
   16 individual `Flash::SetVariable("slotDataN", [...])`
   calls. Same verification.

3. **Assumption:** Adding `slotData17` via AS2 synthesis
   after PPU finishes SetVariables but before LoadOptions
   runs will be picked up by the existing iteration loops
   in ContinueBuilding and SetUpUnits. (Should be true
   since those loops are purely data-driven.)

4. **Assumption:** The JPEXS AS2 edit path (modify
   DoAction_2.as source, re-import via `-importScript`, or
   hand-edit the XML's actionBytes hex) produces a GFx file
   that still round-trips cleanly. iter-1183 verified the
   IDENTITY round-trip works; an actual-edit round-trip is
   the next empirical unknown.

---

## Key file references

All paths relative to repo root.

| file | purpose |
|---|---|
| `civrev_ps3/extracted/Pregame/gfx_chooseciv.gfx` | Stock source (59646 bytes, GFX\\x08 magic) |
| `civrev_ps3/korea_mod/docs/as2_source/scripts/` | JPEXS-exported AS2 source (staged for this iteration; may be removed later if too heavy) |
| `civrev_ps3/korea_mod/docs/as2_source/scripts/frame_1/DoAction_4.as` | Root state, StartBuilding, ContinueBuilding, SetUpUnits |
| `civrev_ps3/korea_mod/docs/as2_source/scripts/frame_1/DoAction_7.as` | goLeft, goRight (numOptions-parameterized clamps) |
| `civrev_ps3/korea_mod/docs/as2_source/scripts/DefineSprite_98_options_mov/frame_1/DoAction_2.as` | LoadOptions (carousel factory) |
| `civrev_ps3/korea_mod/docs/as2_source/scripts/DefineSprite_96_ChooseCivLeader/frame_1/DoAction.as` | Per-cell SetPortrait, SetPortraitImage, GetImageName |

---

## Deliverable status

| §9.Y step 2 (identify carousel sprite) | **DONE** — chid 96 ChooseCivLeader (template), chid 98 options_mov (factory) |
| §9.Y step 3 (dump AS2) | **DONE** — JPEXS `-export script` produced full AS2 source |
| §9.Y step 4 (classify literals) | **DONE** — 6 literals in dead code, 1 default value, 2 live GetImageName cases, 1 keycode (unrelated), 1 data-array index (unrelated) |
| addresses.py update | Deferred to iter-1185 — the AS2 edit sites are file-relative, not EBOOT-relative, so `addresses.py` isn't the right home. The sites live in this doc and in `gfx_chooseciv_patch.py`'s edit plan. |

iter-1185 can proceed directly to the AS2 synthesis edit
in `DefineSprite_98_options_mov/frame_1/DoAction_2.as`
without further literal hunting.
