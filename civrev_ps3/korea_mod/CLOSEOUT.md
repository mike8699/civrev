# Korea Civilization Mod for PS3 — v1.0 closeout

**Status (iter-231, 2026-04-15):** v1.0 has reached its **maximum
reachable state** under the iter-189 strict-reading directive.
PRD §7.7 stop conditions are formally satisfied. The autonomous
loop should not continue spinning on §9 item 2 — every escalation
path (Jython analyzeHeadless, Z-packet GDB instrumentation,
Scaleform tag editing, cross-platform RE) has been exhausted with
documented empirical findings.

## TL;DR

Under the iter-189 strict reading, v1.0 ships:

- **Korea / Sejong in the runtime parser buffers at index 16**
  (verified end-to-end at runtime via GDB memory dump in iter-203).
- **All 16 stock civs unchanged** at indices 0..15 (M9 6/6 PASS
  in iter-216 and iter-224 against the lean install).
- **Common0.FPK untouched** (iter-222 proved it's never opened
  at runtime; iter-223 removed the dead overlays from the
  install pipeline).

But Korea is **invisible in the civ-select carousel**: the cell
count is hardcoded Scaleform-side in `gfx_chooseciv.gfx` and
adding a 17th cell requires modifying the AS2 bytecode, which
is outside this loop's static-patching toolchain. iter-221
proved this is a platform-architecture divergence (iOS uses
OpenGL with native NDSChooseCiv code, PS3 uses Scaleform), not
a hidden PPU function we failed to find.

## §9 Definition of Done — final tally

| # | item | status |
|---|------|--------|
| 1 | `install.sh` works | **MET** (iter-219 + iter-223 + iter-227 verified) |
| 2 | Korea visible at slot 16 in carousel | **OPEN — STRUCTURALLY BLOCKED** (PRD §9.X) |
| 3 | Found capital with Korea | **BLOCKED on item 2** |
| 4 | 50-turn soak as Korea | **BLOCKED on item 2** |
| 5 | Stock regression (6 civs) | **MET** (iter-216 6/6 + iter-224 6/6) |
| 6 | Verification artifacts committed | **MET** (40+ dated dirs under verification/) |

3 items MET, 3 items STRUCTURALLY BLOCKED.

## What v1.0 actually ships

**EBOOT patches** (6 in-place byte changes via `eboot_patches.py`):

| iter | site | what |
|---|---|---|
| iter-4 | `0x017f4038`, `0x017f4040`, `0x01938354`, `0x019398b0` (4 patches) | ADJ_FLAT 17-entry civ-adjective table written into .rodata padding + 2 TOC redirects |
| iter-14 | `0x00a2ee38`, `0x00a2ee7c` (2 patches) | parser-count `li r5, 0x11 → 0x12` for RulerNames / CivNames |

**Pregame.FPK overlays** (2 file replacements via `pack_korea.sh` + `fpk.py repack`):

| file | content |
|---|---|
| `civnames_enu.txt` | 18 rows, `Koreans, MP` at row 17 |
| `rulernames_enu.txt` | 18 rows, `Sejong, M` at row 17 |

**Common0.FPK overlays:** NONE. iter-222 proved Common0.FPK is
never opened at runtime; iter-223 removed the 3 dead overlays
(`leaderheads.xml`, `console_pediainfo_civilizations.xml`,
`console_pediainfo_leaders.xml`) from the build/install
pipeline. They are archived under
`xml_overlays/dead_iter222/` for documentation.

**Total surface area:** 2 file overlays + 6 EBOOT byte patches.
This is the smallest possible v1.0 footprint that still gets
Korea/Sejong into the parser buffers at runtime index 16.

## Why §9 item 2 is structurally blocked

PRD §9.X has the formal record. In summary:

1. The civ-select carousel cells are pre-authored MovieClip
   instances inside `gfx_chooseciv.gfx` (a Scaleform GFx asset).
2. The cell count, layout, and per-cell civ identification are
   hardcoded into the AS2 bytecode — not into the PS3 PPU code.
3. iter-150..218: 9 PPU function candidates `b .` trap-tested
   off the carousel render path. 14 `li r8, 0x10` consumer
   sites bisected (full-set causes RSX hang, safe subset is
   inert).
4. iter-178..200: 4 distinct Scaleform AS2 tag edits attempted
   (slotData17 cell extension, LoadOptions hardcode, two
   numOptions literal swaps) — all boot-safe but inert.
5. iter-201: RPCS3's GDB stub rejects Z2/Z3/Z4 hardware
   watchpoints at the protocol level. Only Z0 software code
   breakpoints work; they need a PC target to install at and
   every tested PC has been off-path.
6. iter-221: cross-platform proof. iOS uses fully-symbolized
   `NDSChooseCiv::ShowCivIcons` / `ShowCivText` rendering
   directly with OpenGL (visible VFP / vmul / blx into GL
   functions). The PS3 build replaced that work with Scaleform
   AS2 at port time. **There is no carousel function in PS3
   PPU because it doesn't exist** — the rendering happens
   Scaleform-side.

Unblocking item 2 requires either (a) a wholesale
`gfx_chooseciv.gfx` AS2 rewrite (multi-day Scaleform GFx
engineering effort outside this loop's toolchain), or (b)
runtime instrumentation of the live emulator's Scaleform state
(modifying RPCS3 itself).

## §7.7 stop condition — what was exhausted

Per `prompt.txt`'s "STOP WHEN" clause: "OR a §7.7 stop
condition fires AFTER both Jython and Z-packet paths have been
exhausted (per the EXECUTE block). Write the blocker to the
PRD and exit."

**Jython analyzeHeadless path — exhausted:**

8+ Jython post-scripts in `korea_mod/scripts/ghidra_helpers/`
covering parser dispatcher decompile, parser worker decompile,
ChooseCiv panel-loader candidate enumeration, holder-struct
consumers, top consumer xrefs, civ icon table walk, and 9
candidate carousel-binder functions. All findings logged in
the iter-197..212 PRD entries.

**Z-packet GDB path — exhausted:**

- `gdb_client.py` extended with Z-packet support
- Z0 software code breakpoints work but require knowing the
  target PC; every tested PC has been off the carousel render
  path
- Z2 / Z3 / Z4 (write/read/access watchpoints) are rejected
  by RPCS3's GDB stub at the protocol level (iter-201 verified)
- Memory-read instrumentation (test_civs_dump.py at iter-203)
  did successfully verify Korea/Sejong in the parser buffers,
  but cannot unblock the Scaleform-side rendering question

Both escalation paths are formally documented under §9.X
"Exhausted approaches" subsection. The §7.7 STOP clause is
satisfied.

## Loop iteration count

The autonomous loop ran from iter-1 (2026-04-13) through
iter-231 (2026-04-15). Major phases:

- **iter-1..72:** v0.9 slot-15-replacement build, M9 PASS,
  premature "DONE" claim under the relaxed reading.
- **iter-131..151:** §9.X investigation, Z-packet escalation,
  carousel-binder candidate elimination, original "Final
  Status" closeout.
- **iter-152..188:** documentation refresh, attempted Random-
  cell repurpose (slot 16) under iter-176 directive.
- **iter-189:** **user directive update** tightening to strict
  reading. v0.9 and Random-repurpose both rejected.
- **iter-190..212:** strict-reading reattempts. parser-count
  patches land. 14 `li r8` consumer sites tested. structural
  blocker formally recorded at iter-212.
- **iter-213..221:** loose-end closures and cross-platform
  resolution.
- **iter-222..230:** iter-222 Common0 deadness empirical
  finding → iter-223 install pipeline cleanup → iter-224
  6-civ regression refresh → iter-225 harness fix →
  iter-226 §5.7 step 1 closeout → iter-227 verify.sh
  tier wiring → iter-228..230 polish.
- **iter-231 (this commit):** formal closeout.

230+ iterations. Every concrete v1.0 work item is closed.
Every documented inconsistency between PRD spec and shipping
code has been fixed. Every §5 investigation has at least its
first step closed. The carousel question is permanently
answered (with cross-platform empirical proof). No further
"find the function in PPU" iteration will succeed because
**there is no carousel function in PS3 PPU**.

## What a v1.1 effort would need

If a future v1.1 wants to actually unblock the carousel:

1. **A Scaleform GFx editor.** JPEXS Free Flash Decompiler
   handles SWF reasonably well; the GFx variant needs
   specific GFx-aware tooling. The carousel sprite (likely
   tag[177] ChooseCivLeader, char 96) needs to gain a 17th
   MovieClip child instance with recomputed layout
   coordinates and patched cursor-bound logic.
2. **OR** RPCS3 source modifications to expose Scaleform
   variable writes and ASValue reads to the GDB stub. Then
   live runtime instrumentation can pinpoint where the cell
   count comes from and what to patch.
3. **OR** decompile `civrev_ps3/extracted/Pregame/gfx_chooseciv.gfx`
   directly via a Scaleform AS2 disassembler and edit the
   bytecode in place.

For Korea-specific gameplay differentiation (Hwacha unique
unit, Sejong leader bonuses, Korean civ trait, AI personality):
PRD §5.7 step 4 is the path. Decompile `libTkNativeDll.so`
from CivRev 2's APK, find Korea's civ-record by string-ref to
"Sejong" / "Korean", dump the surrounding struct, and map
field offsets to the PS3 civ-record layout. The CR2 source
data is staged at `civrev2/extracted_apk/` (iter-226).

## How to verify the v1.0 ship state

```bash
cd civrev_ps3/korea_mod
./build.sh                    # ~30 sec
./install.sh                  # ~5 sec
./verify.sh --tier=static     # M0 GREEN, ~30 sec
./verify.sh --tier=fast       # M0 + Caesar M9 smoke, ~5 min
./verify.sh --tier=full       # M0 + 6-civ M9 sweep, ~25 min
```

All three tiers exit 0 against the iter-231 commit on the
`korea-civ-mod` branch. The commit history from iter-218
onwards is reviewable, with each iteration's progress log
entry under PRD §10 documenting what was tried and why.

## Closing note

This mod is a study in REVERSE ENGINEERING ECONOMICS more
than a piece of shipped software. The actual v1.0 user-visible
effect is **none** — Korea exists in the binary but cannot be
selected. What it ships instead is a complete investigation
log proving exactly why a particular goal (a 17-civ visible
carousel on a 16-civ Scaleform-rendered console build) is
structurally unachievable with the available toolchain, and a
clean foundation from which a Scaleform-equipped future
iteration could continue. The §10 Progress Log alone is
~7,500 lines of documented empirical findings, dead-end
disprovals, address constants, and decompile snippets — the
sort of artifact that's worth more than the not-shipped
17th-cell carousel rendering would have been.

The loop chooses to stop here under PRD §7.7.
