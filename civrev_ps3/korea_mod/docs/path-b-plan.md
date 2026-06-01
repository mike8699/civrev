# Path (b) — Korea as a differentiated civ (v1.2 plan)

Status: planning (first path-b iteration, 2026-05-31). This converts the
PRD §9.AA "path (b)" deferral into a concrete, evidence-based roadmap.

User directive: make Korea **play differently** from China — not a cosmetic
alias. Effort acknowledged as VERY HIGH (10–20 iterations).

## The three layers of "a civ's gameplay"

Reverse-engineering the data so far splits civ behaviour into three layers,
each with a different difficulty:

| Layer | What | Where | Difficulty |
|---|---|---|---|
| **Display** | The bonus *text* shown on civ-select ("begin with knowledge of Writing") | `extracted/Pregame/text.ini` `__VAR` sections — **data-driven** | EASY |
| **Mapping** | Which bonus each civ/leader has (civ→bonus-id, leader→era-bonus-ids) | EBOOT integer tables (unmapped) | MEDIUM (RE) |
| **Effect** | The code that actually grants the bonus at game start / in play | EBOOT code keyed on civ/leader index | HARD (RE) |
| **Gate** | Civ index 16 must be valid everywhere it flows | §9.X OOB blocker (unsolved) | HARD (RE) |

The cosmetic v1.1 ship (Korea-plays-as-China) sidesteps Mapping/Effect/Gate
entirely by remapping slot 16 → civ 6 at OnAccept (iter-1188). Path (b)
removes that remap and makes civ 16 a real, distinct civ.

## Display layer — DATA-DRIVEN (verified 2026-05-31)

`text.ini` holds bonus strings as position-indexed `__VAR` lists:

- **`[CIVBONUSTEXT]`** — 16 entries, **indexed by civ**. Each is that civ's
  single "begin the game with ___" starting bonus. Verified: index 6 =
  "knowledge of Writing" = China, matching the in-game carousel screenshot.
  Full map:
  ```
  0 Rome      a Republic and Code of Laws
  1 Egypt     an Ancient Wonder
  2 Greece    a Courthouse
  3 Spain     knowledge of Navigation
  4 Germany   automatic upgrades for elite units
  5 Russia    a local area map
  6 China     knowledge of Writing
  7 America   a Great Person
  8 Japan     knowledge of Ceremonial Burial
  9 France    an impressive Cathedral
  10 India    access to all resources
  11 Arabia   knowledge of Religion       (text idx 11)
  12 Aztec    a wealth of gold
  13 Africa   overrun combat advantage
  14 Mongolia +50% trade from captured cities
  15 England  knowledge of Monarchy
  ```
- **`[LBTEXT]`** — a flat pool (~60 entries) of *leader* bonus strings. Each
  leader has a set of indices into this pool, shown per era (Ancient/Modern).
  Examples: "Temples produce 3 science", "+2 Cannon attack", "Knowledge of
  Literacy", "Cities not affected by Anarchy".
- **`[CIVNAMEP]`** — civ adjectives (already extended via the ADJ_FLAT EBOOT
  patch + the civnames/rulernames overlays).

To give Korea its own *display* bonuses we add a 17th entry to the relevant
`__VAR` sections (the SWF/PPU index past 15 once civ 16 is valid).

## EBOOT anchors for the Mapping/Effect RE (next iterations)

The `text.ini` section-name keys appear in the EBOOT — these are the xref
anchors that lead to the parser and then the per-civ consumer tables:

Addresses are clean-ELF (`EBOOT_v130_clean.ELF`) offsets, which equal
vaddr for seg0 == the address Ghidra shows (per addresses.py):
- `"CIVBONUSTEXT"` — vaddr `0x16DD35E` (2nd ref `0x16EE4D2`).
- `"LBTEXT"` — vaddr `0x16928A9` (2nd ref `0x169BF94`).
- (`"CIVBONUS"` is just a substring of `CIVBONUSTEXT`; no separate section.)

Method (for a Ghidra Jython post-script under `scripts/ghidra_helpers/`):
1. Resolve each string's vaddr, find xrefs → the `.ini` section-registration
   call → the array the parsed `__VAR` lands in.
2. Find the consumer that indexes that array by the civ/leader enum — that
   consumer's *other* operand is the civ→bonus-id mapping table (or a direct
   `array[civ]` if Display==Mapping).
3. For the **effect**: from the same civ index, find the game-init path that
   grants the actual resource/tech (search near `CcGame`/`StartGame` and the
   tech-grant helper).

This reuses the methodology that mapped the ADJ_FLAT table + 9 call sites
(`addresses.py`), but applied to the bonus tables instead of the name tables.

## The civ-16 OOB gate (the real risk)

Making civ 16 a real civ requires every civ-indexed structure on the
game-init + gameplay path to accept index 16. Prior iterations (189–212,
~25 iters) could not solve this for the *carousel* and aliased to China.
NOTE: the known fault anchors (`0xc26a98` / `FUN_00029f18`, addresses.py)
are on the **name-file parse** path, NOT the gameplay path — so the
gameplay OOB is a *separate, unexplored* failure surface. Establishing
exactly which gameplay tables are 16-bounded (and whether they sit in
`.rodata` with no append room, like the string tables) is the gating
investigation. If a structure can be relocated+extended (as ADJ_FLAT was),
it's tractable; if civ count is baked into many `cmpwi rN,0x10` sites across
the sim, the cost balloons.

## Proposed Korea/Sejong design (reuse existing pools — no new mechanics)

Sejong the Great: scholar-king, invented Hangul, promoted science and
astronomy; the **Hwacha** (rocket-arrow artillery) is Korea's iconic unit.
Map these onto *existing* CivRev1 bonus strings so no new mechanics/assets
are needed — only a different *selection*:

- **Civ starting bonus** (`CIVBONUSTEXT[16]`): "knowledge of Writing" is
  China's; give Korea a science-flavored but distinct one, e.g. a new 17th
  string "knowledge of Literacy" (Hangul/literacy theme) — or reuse "a Great
  Person" (Sejong as a great scholar). TBD pending the effect mapping.
- **Sejong leader bonuses** (`LBTEXT` indices, by era):
  - Ancient: "Temples produce 3 science" (Sejong's science/astronomy).
  - Modern: "+2 Cannon attack" — the **Hwacha** captured as an artillery
    bonus, zero new-unit work.
  - (defensive option available: "Cities not affected by Anarchy" / loyalty).
- **Special Unit**: defer a true Hwacha unit (new model/stats = large);
  the "+2 Cannon attack" leader bonus stands in for v1.2.

This keeps v1.2 within "reassign from the existing pool", which is the only
tractable scope until/unless the effect layer proves freely extensible.

## Roadmap (path-b iterations)

1. **(this iter)** Plan + display-layer findings + EBOOT anchors. ← done
2. RE the Mapping layer: civ→CIVBONUSTEXT consumer + leader→LBTEXT indices
   (Ghidra, anchored on the string xrefs above). Record tables in addresses.py.
3. RE the Effect layer: where the per-civ starting bonus + leader bonuses are
   applied at game start. Identify the civ-16 OOB surface.
4. Feasibility verdict on the civ-16 gate. If tractable: extend the bonus
   tables to 17 (relocate like ADJ_FLAT), add Korea's selection.
5. Remove the iter-1188 OnAccept slot-16→6 AS2 remap so slot 16 flows as
   civ 16; add the `[CIVBONUSTEXT]`/`[LBTEXT]` 17th display entries.
6. Verify in-game (M9 + a new oracle): Korea starts with its own bonus, shows
   its own bonus text, and does NOT match China's start.

## Open questions

- Are the bonus *effects* table-driven or a `switch(civ)`? Table-driven is
  far easier to extend.
- Does the savegame serializer encode civ count? (bump save version if so.)

## RE log — iter-2 (2026-05-31)

Goal was to pin the civ→bonus consumer. Result: ruled out the naive
approaches and uncovered two structural facts that redirect the RE.

1. **The display is a template engine with `@TOKEN` substitution.** The
   EBOOT strings `CIVBONUSTEXT` / `LBTEXT` are not section-name comparands
   or pointer-table entries — they are embedded in larger template strings
   as `@CIVBONUSTEXT`, `@LBTEXT`, alongside `@ERA`, `@BLDGNAME`, etc. (e.g.
   "...inherited @CIVBONUSTEXT..."). The renderer resolves `@TOKEN` at
   runtime by looking up the `[TOKEN]` `text.ini __VAR` list, **indexed by
   the current civ/leader/era context**. So civ-indexing happens *generically
   inside the template engine* — there is no per-civ bonus pointer table to
   find, which is why neither a Ghidra xref, a clean-ELF `lis/addi` scan, nor
   a 4-byte pointer scan reaches a "consumer". **Implication:** the display
   layer is fully data-driven — extend the `__VAR` lists to a 17th entry and
   make Korea's civ context resolve to index 16. (A validated pointer scan
   confirms ADJ_FLAT `0x195fe28` *is* referenced from `0x1938354`/`0x19398b0`,
   so the tooling is sound; the bonus tokens simply have no such table.)

2. **CRITICAL: the existing Ghidra project (`ghidra/civrev.rep`) is a
   DIFFERENT binary from the clean ELF that `addresses.py` / `eboot_patches.py`
   target.** In Ghidra the `CIVBONUSTEXT` string is at vaddr `0x16ccf96`; in
   `EBOOT_v130_clean.ELF` it is at file-off/vaddr `0x16dd35e` (clean ELF seg0
   is file_off==vaddr per readelf, and `eboot_patches.py` verifiably matches
   `addresses.py` offsets). The rodata bias is ~`0x3c8` vs the *decrypted*
   ELF and ~`0x103c8` vs the *clean* ELF, and code at `addresses.py` callsites
   does not match either. **Do NOT trust the existing Ghidra project for
   addresses that feed the patcher.** All of `addresses.py` is clean-ELF
   space; the Ghidra project must be reconciled (re-import the current
   `EBOOT_v130_clean.ELF` into a fresh project) before decompiler-based RE.

**Next RE step (iter-3): the EFFECT layer, not the display.** The display is
solved-in-principle (data). To make Korea *play* differently we need the code
that GRANTS the per-civ starting bonus at game start (China → free Writing
tech). Two viable routes now that string-xref is ruled out:
  (a) Re-import `EBOOT_v130_clean.ELF` into a fresh Ghidra project (correct
      addresses + decompiler), then find the game-init bonus-grant from the
      tech-grant helper / `StartGame` path, keyed on civ.
  (b) GDB runtime watchpoint (rpcs3_automation `gdb_client.py`): break at
      game start, watch the player's tech/bonus write, backtrace to the
      civ-keyed grant site. Anchors to translate: clean-ELF space.

New helper scripts committed: `FindCivBonusConsumer.py` (string xref +
pointer scan — came up empty, documents the @token indirection) and
`DecompAdjFlatConsumers.py` (decompiled the ADJ_FLAT callsite functions;
they are buffer/parser routines, not the bonus assembly — and exposed the
Ghidra-vs-clean address-space mismatch).

## RE log — iter-3 (2026-05-31)

Goal: locate the EFFECT layer (the code that grants a civ its starting
bonus). Confirmed it is NOT data-driven (leaderhead `chi_mao.xml` etc. are
pure 3D-asset manifests — model/anim/texture paths, no gameplay), so it is
EBOOT code. Then hit the **anchor problem** and a **Ghidra tooling problem**.

**The anchor problem (key finding).** The gameplay/effect code is enum-driven
C++ with almost no string anchors. The strings that *look* like anchors all
live in one big Scaleform/UI/entity string pool around `0x169xxxx` and lead to
the UI/binding layer, NOT gameplay:
- `theSelectedOption` (`0x169cacd`) is part of an SWF variable path
  (`this.theSelectedOption`) — Flash binding.
- `OnAccept` (`0x1694708`), `OnCancel`, `OnPressY/X` — fscommand names.
- `CcCivFlagEntity` (`0x1692728`), `CcGameCamera` (`0x1693630`) — C++ entity
  class-name strings (RTTI/registration), not the civ-bonus logic.
- `CIVBONUSTEXT`/`LBTEXT` — `@`-tokens in templates (iter-2).
None of these have a `lis/addi` load, a 4-byte pointer, or a Ghidra ref
(validated scanner; the same scan DOES find ADJ_FLAT's pointer at
`0x1938354`). So string-xref RE cannot reach the effect grant. The only solid
*gameplay* anchor remains **ADJ_FLAT `0x195fe28`** and its 9 call sites
(`addresses.py`) — real civ-text builders that index by civ; the bonus table
is most likely accessed nearby.

**The Ghidra tooling problem.** Built a fresh, correctly-addressed project
`ghidra_clean/civrev_clean` by importing `EBOOT_v130_clean.ELF` (gitignored).
BUT Ghidra's default analysis under-covers it: only ~510 functions, and even
ADJ_FLAT has no refs — because the ELF entry (`0x18b5b20`) is a PPC64 function
*descriptor* in the data segment, so flow-seeded disassembly never reached
`.text`. A brute-force `DisassembleCommand` over `0x10000..0x1680000`
(`ForceDisasmAnalyze.py`) is the WRONG fix: it disassembles data-as-code in
the non-code parts of that range, which creates overlapping garbage functions
(`0158a198`/`0158a8f0`) and sends Ghidra into an **infinite "function body
repair" loop** — it ran the full 40-min timeout (EXIT=124), saved nothing, and
left the project at ~510 functions. Do NOT brute-force-disassemble a range
that contains data. iter-4 must SEED from known code entries and let
auto-analysis follow flow (or disassemble only the true `.text` sub-range,
not all of seg0 which includes rodata).

## RE log — iter-4 (2026-05-31)

Built a working clean-ELF project and exhausted the ADJ_FLAT lead.

- **Resolved the real entry.** The ELF entry `0x18b5b20` is a PPC64 function
  descriptor; `*0x18b5b20 = {entry=0x147d0, toc=0x193a288}`. The toc
  `0x193a288` == `addresses.py` `KOREA_MOD_TOC_BASE` — final confirmation that
  the clean ELF == `addresses.py` space.
- **Seeded disassembly works** (`SeedDisasmAnalyze.py`, 6G heap via Ghidra
  `support/launch.properties MAXMEM=6G`). Seeding from the real entry + the
  `addresses.py` functions and FOLLOWING FLOW raised coverage 510 → **1357
  functions** and the project saved. This is the reusable clean-ELF project
  for future RE (`ghidra_clean/civrev_clean`, gitignored). In it the ADJ_FLAT
  call sites now match `addresses.py` exactly (`lwz r9,-0x1f34(r2)`), proving
  the binary/addresses are right.
- **ADJ_FLAT consumers are TEXT BUILDERS, not the effect.** `FUN_0013cbf0`
  does `ADJ_FLAT[civ]` (`*(TOC[-0x1f34] + (civ<<2))`) + several fixed
  template-string TOC slots — it formats "The [adjective] ..." text. The
  other consumers similarly build/compare civ text. None index a *second*
  civ table that looks like a bonus/effect table. So the adjective anchor
  does NOT reach the bonus grant.
- **Coverage/quality still limited.** 1357 functions is far short of full
  coverage (static flow misses C++ vtable/function-pointer targets), and
  decompiles are garbled (no TOC/`r2` propagation → `unaff_r2`), so reading
  the bonus logic by eye is unreliable. ADJ_FLAT still has 0 data-xrefs
  (pointer analyzer didn't classify the TOC entry).

**Conclusion after 4 iterations:** the EFFECT layer (per-civ starting-bonus
grant) is a genuinely deep hunt — enum-driven, no string anchor, the adjective
anchor leads only to text, and Ghidra static coverage/quality is poor for this
binary. The remaining realistic routes are both substantial:
  (a) **Runtime** — find the player/game struct by observation (the known
      civs-buffer holder `0x1ac93b8` is names only; the gameplay struct is
      unmapped), then read tech state / breakpoint the grant.
  (b) **Deeper static** — improve TOC propagation + coverage in
      `civrev_clean`, then navigate the call graph from `main` (0x147d0) to
      the StartGame/new-game init and read the per-civ setup.
Plus the civ-16 OOB gate still looms after the table is found. This warrants a
scope decision (see PRD progress log iter-4): keep investing in deep RE, or
descope to display-only differentiation (data-driven, tractable), or stop at
the shipped cosmetic v1.1.

## RE log — iter-5 (2026-05-31) — TOC breakthrough; effect still anchor-less

User chose to keep grinding. Major tooling win, but the effect anchor problem
persists.

- **TOC breakthrough (the key asset).** The civrev_clean decompiles were
  garbled because Ghidra didn't know `r2` (PPC64 TOC base). Setting
  `r2=0x193a288` as a register-context constant over the code
  (`SetTocAndDecomp.py`) and re-analyzing gives: **ADJ_FLAT (0x195fe28) → 14
  refs (was 0)**, readable decompiles (TOC loads show as `DAT_0193xxxx`), 1483
  functions. This is THE reusable clean-ELF RE environment for all future
  path-b work (saved in the gitignored `ghidra_clean/civrev_clean`; rebuild
  with `SeedDisasmAnalyze.py` then `SetTocAndDecomp.py`).
- **ADJ_FLAT fully exhausted for the effect.** Its 14 refs are 4 functions
  (`FUN_0013cbf0`, `FUN_0017e95c`, `FUN_0097d8f0`, `FUN_009f95e0`). With
  readable decompiles, all 4 are civ-TEXT/message builders (`ADJ_FLAT[civ]` +
  format/notify); the big one (`FUN_009f95e0`) is game-logic that flag-ORs a
  player/2D matrix and uses the adjective only for a message. None grant a
  bonus. The bonus/UI strings (`CIVBONUSTEXT`, `theSelectedOption`) still have
  0 refs (indirect). `main` (0x147d0) is a thin wrapper → `FUN_00014900` (real
  main); the grant is deep in the call graph with no string/data anchor.

**iter-6 plan — RUNTIME `.bss`-diff (the route that sidesteps the static
anchor problem):** the game runs in the docker harness with an RPCS3 gdb stub
(port 2345); `gdb_client.py` does `read_memory`, and iter-202/203 already
attach mid-game (the civs-buffer holder `0x1ac93b8` is a known `.bss` global
populated at init). Concrete steps:
  1. Attach gdb at the MAIN MENU; snapshot the `.bss` pointer region (scan a
     few KB around the known holders, e.g. `0x1ac8000..0x1aca000`, widen as
     needed) — game not started, so game-state globals are null/stale.
  2. Start a game as China; attach IN-GAME; snapshot the same region.
  3. DIFF: `.bss` words that flipped null→heap (or changed) are the game/
     player-state globals. Follow them to the player array → `player[i].civ`
     and the tech bitfield (China has Writing set).
  4. Repeat starting as Rome; the tech bitfield differs → that IS the effect
     output. Then find the writer: set a Z0 code breakpoint on the function
     that writes the tech field (find via the static decompiler now that we
     can read it), or static-analyze around the found player-struct offset.
  5. The civ-keyed grant site + the per-civ bonus table fall out from there →
     extend to 17 for Korea, then tackle the OOB gate.

New scripts: `SetTocAndDecomp.py` (the TOC fix — run after SeedDisasmAnalyze),
`ProbeEffectLayer.py`, `ProbeMainAndBig.py`.

## RE log — iter-6 (2026-05-31) — RUNTIME route works; game-object found

Pivoted to runtime and it WORKS — the breakthrough the static hunt couldn't
reach.

- **`test_player_dump.py`** (new harness mode `player_dump`) boots a game to
  the in-game HUD as a chosen civ, attaches the rpcs3 gdb stub, and scans a
  `.bss` window for heap pointers. China run: `in_game=True`, civs buffer at
  runtime `0x4002a0e0`, **14 unique game-state `.bss` globals** found (heap
  ptrs `0x4xxxxxxx`), peeks showing live data (city "Karakorum", entity
  objects with float stats).
- **Found the game session object.** `.bss 0x1ac1678 → heap 0x40003000`, whose
  first word is **vtable `0x18a2738`** — confirmed a real C++ vtable (entries
  are PPC64 function descriptors → methods at `0x9a6018`/`0x9a7228`/`0x9a7350`,
  compiled in the `0x194a1f8`-TOC module, same as the parser). Two more C++
  objects share vtable `0x0188ac38` (`.bss 0x1ad8114`, `0x1add514`). The
  `0x40003000` object has member pointers into both EBOOT and heap — it is the
  gateway to players → civs → techs.

**iter-7 (clear, tooling all in place):**
1. STATIC: decompile the game-object class methods (vtable `0x18a2738`,
   set `r2=0x194a1f8` for these — they use the parser module's TOC) to find
   the member offset of the player array / player count.
2. RUNTIME: extend `test_player_dump.py` to follow `0x1ac1678 → 0x40003000`,
   walk to the player array, find the human (China) player, and read its tech
   bitfield/array. Identify the tech-state offset.
3. DIFF: run `player_dump 0 rome` and compare the China vs Rome player tech
   state — the bytes that differ ARE the starting-bonus effect output (China:
   Writing). Then set a Z0 breakpoint on / static-trace the writer to find the
   civ-keyed grant + the per-civ bonus table. Extend to 17 for Korea; then the
   OOB gate.

Runtime anchors recorded in addresses.py.

## RE log — iter-7 (2026-05-31) — in-window objects ruled out; widen the scan

Used the now-working static decompiler to identify the runtime objects found
in iter-6, and they are NOT the game session:
- `0x1ac1678 → vtable 0x18a2738` is a **charset/locale object** — its methods
  index 256-entry u16 tables by a byte (members at 0xc/0x10 = case-conversion
  / encoding tables). That's why text/city-names were near it.
- `0x1ad8114` / `0x1add514 → vtable 0x0188ac38` are small **widget/data-display
  objects** (members 0x10/0x14 u32, 0x18 float, 0x1c, 0x35). Not the players.
- The other in-window globals point to entity/city objects ("Karakorum",
  "Barbarian"+floats), not the player array.

**Root issue:** the iter-6 `.bss` scan window (`0x1ab0000..0x1ae0000`, 192 KB)
was too narrow — `.bss` spans ~2.4 MB (`0x198be78..0x1bd5f38`). The game
session / player array global is almost certainly outside it. `test_player_dump.py`
scan widened to `0x1990000..0x1bd0000`. New helper `GameObjMethods.py`
disassembles + decompiles a class's vtable methods (with a per-method TOC) to
identify an object — reuse it to classify the wider scan's candidates.

**iter-8:** re-run `player_dump` with the wide scan; among the game-state
globals, find the one whose object holds an **array of ~8-16 similar sub-objects**
(the player array) or a civ-index byte field (0-16). Classify candidates with
`GameObjMethods.py`. Then read the human (China) player's tech bitfield, diff
vs Rome. (If the wide blind scan is still ambiguous, pivot to finding a
`GetGame()`/`GetActivePlayer()` accessor statically now that xrefs work, or
search the heap for the civ-index/tech signature directly.)

**Honest status:** this is among the hardest RE — a stripped, enum-driven,
indirection-heavy console C++ binary whose gameplay code has no string/data
anchors. Tooling is now strong (working clean-ELF decompiler+xrefs + runtime
probe), and leads are being ruled out methodically, but pinning the
effect-grant may take several more iterations of runtime exploration.

## RE log — iter-8 (2026-05-31) — wide runtime diff works but is noise-dominated

- Rewrote `test_player_dump.py` to deep-dump (0x400 B, pointer-masked) EVERY
  heap-pointer global in the full `.bss` range. China + Rome each found ~3160
  globals. (Note: two concurrent emulator boots FAIL — GPU/RSX starvation; run
  them SEQUENTIALLY. The full-`.bss` gdb scan is slow, ~16 min/run.)
- `diff_player_dumps.py` (China vs Rome): 1518 globals differ. But the cleanest
  "localized" 1-byte signal (`7→6` in a 5-object cluster) turned out to be a
  **GPU render-pass counter** — the object held "Render Click / Render Frame /
  ShadowCubeMap / TexTransform" strings. **The diff is dominated by map / RNG /
  render noise** (two different New-Game maps differ in everything); the human
  civ index isn't even cleanly a `6→0` byte in any low-diff global.

## iter-9 plan — 3-way noise subtraction

Dump China TWICE (A, B — both civ 6, different maps) + Rome (civ 0).
`diff3_player_dumps.py`: per `.bss` global, a byte that DIFFERS China_A-vs-Rome
but is STABLE China_A-vs-China_B is **civ-specific** (changes with civ, not the
random map). That cancels the map/render noise and should surface the civ-index
/ starting-tech bitfield. Then read the full struct there and trace/breakpoint
the writer (Z0; the static decompiler now works to identify it). China-B run is
launched; run `diff3_player_dumps.py chinaA rome chinaB` when it lands.

## RE log — iter-9 (2026-05-31) — 3-way subtraction localizes the player/civ state

**The 3-way noise subtraction works** — biggest effect-layer progress yet. With
China-A, China-B (both civ 6) and Rome (civ 0), bytes that differ
China-vs-Rome but are stable across the two China runs are civ-deterministic.
This cancels the map/render noise and cleanly surfaced civ-specific data:
- **Civ team colors**: China `06 96 44` vs Rome `05 aa a3` (RGB) — confirms
  we're in real player/civ state (propagates to ~15 globals).
- **Leader-name strings** that differ by civ.
- **The human civ index `06` (China) → `00` (Rome)** in a cluster of objects.

**Candidate player/civ objects (vtable `0x0188ac38`):** five `.bss` globals
spaced EXACTLY `0x5400` apart — `0x1ad8114, 0x1add514, 0x1ae2914, 0x1ae7d14,
0x1aed114` — each holds the human civ index (6→0) + ~80 civ-specific bytes
(color, name, civ). (Two of these were the iter-7 "widgets"; they are actually
large per-player/per-civ objects, civ data deep at offset ~0x4d3..0x853.) The
`0x1ad8114` object's civ region is a list of 24-byte `{type, payload}` entries
reordered by civ — likely a civ-info/UI cache rather than the raw tech array.

**iter-10:** within the player/civ objects, find the **starting-tech bitfield**
(a region where individual BITS differ — China=Writing set; Rome=its starting
techs — not a reordered list). Then static-trace or Z0-breakpoint the WRITER of
that offset (the decompiler works now). That writer, keyed on civ, IS the
effect-grant. The civ index field itself is also a patch target (it's read to
look up bonuses). Tooling (3-way runtime diff + clean-ELF decompiler) is now
sufficient; this is mechanical from here, though still several iterations to
the grant + the OOB gate.

**iter-4 plan (two routes; try runtime first — it's likely faster):**
1. **Runtime diff (preferred).** The game runs in the docker harness. Start a
   game as China (slot 6) and as Rome (slot 0); read player memory via the
   rpcs3 gdb stub (`gdb_client.py read_memory`) and diff to locate the tech/
   bonus storage (China has Writing, Rome has Republic+Code of Laws). That
   anchors the EFFECT in the live process with no static-analysis guesswork;
   then find the writer (Z0 code breakpoint — Z2 watchpoints are rejected by
   the RPCS3 stub per iter-201) or static analysis around the found address.
2. **Better static analysis.** Rebuild `civrev_clean` with a larger heap
   (set Ghidra `support/launch.properties` `MAXMEM=8G`, or `-Xmx`) and seed
   disassembly from KNOWN code addresses (the `addresses.py` functions /
   ADJ_FLAT call sites) so auto-analysis follows flow, instead of a brute
   range disassemble. Then decompile the ADJ_FLAT consumers (`0x13cbf8` etc.)
   in the correct clean-ELF space — they should reveal the civ-indexed bonus
   table accessed alongside the adjective lookup.

New helper scripts: `CleanProbeAnchors.py` (anchor refs + function-count
sanity), `ForceDisasmAnalyze.py` (force-disassemble — too slow as written;
iter-4 should seed instead). `ghidra_clean/` is gitignored.

## RE log — iter-10 (2026-05-31) — localized objects are UI caches, not the struct

- Decompiled the vtable `0x0188ac38` class (the iter-9 "player/civ" objects)
  fully: its big methods (`0xa6e784`/`0xa6e4b4`) format a value at `+0x10` for
  display, with a float at `+0x18` and render/state flag bits at `+0x4` — a
  **UI display-widget class**, NOT the authoritative player struct. The civ
  data inside (index, color, name, 24-byte list) is a CACHED/displayed copy of
  the human player's civ, not the game-logic state the grant writes.
- Hunted the authoritative starting-tech BITFIELD directly (small region with
  individual bit flips, noise-subtracted): **41,630 candidates — far too
  noisy.** The recurring `88 08 02`/`86 08 02` patterns are UI-list/coordinate
  data, not techs.

**The hard wall (after 10 iterations):** civ data propagates to a great many
UI/cache/display objects, and EVERY object the runtime diff localizes is one of
those — never the single authoritative game-logic player/game struct the
effect-grant writes. Reaching it needs either (a) the real game/player
singleton found STATICALLY — but the gameplay code is enum-driven with NO
string/data anchor (exhaustively confirmed iters 2-5), or (b) per-object class
identification across thousands of `.bss`-referenced heap objects to separate
UI from logic — intractable by hand. And even if the grant were found, the
**civ-16 OOB gate** (unsolved by ~25 prior iterations) still blocks a real
17th civ.

## FEASIBILITY CONCLUSION (path b) — SUPERSEDED by the iter-11 BREAKTHROUGH below

**SUPERSEDED 2026-06-01.** The conclusion below ("not reachable") was WRONG —
it was reached by hammering the stripped PS3 binary alone. Pivoting to the
already-decompiled **sibling ports** cracked it: see "## BREAKTHROUGH" at the
end of this file. The effect layer is now fully understood in readable form.
Keeping the original text for the record:

Full path b — a true differentiated 17th civ — is **not reachable with the
available tooling in a reasonable number of further iterations.** Ten
iterations built excellent infrastructure (working clean-ELF decompiler+xrefs,
runtime probe, the 3-way noise-subtraction method) and ruled out every avenue:
static gameplay anchors don't exist; the runtime route localizes only UI caches
of the civ data, not the authoritative struct; the OOB gate looms beyond.
A realistic path b would need a *full* game decompilation/symbolication effort
(recovered types across the whole binary, or original source/symbols) — well
beyond this loop's scope.

**Recommended outcome:** ship the cosmetic v1.1 (Korea selectable + Sejong
portrait, done + verified) and, if visible differentiation is wanted, the
DISPLAY-ONLY path (data-driven `text.ini` `__VAR` 17th entries — tractable),
leaving this fully-documented deep-RE trail (tooling + findings + the exact
walls) for any future attempt with heavier tooling. All artifacts committed.

## BREAKTHROUGH (iter-11, 2026-06-01) — effect layer fully understood via sibling ports

A 4-way parallel cross-port scout (Xbox360 recomp / iOS / CR2 C# / PS3 RTTI)
broke the wall. Two findings reverse the "not reachable" conclusion:

**1. The authoritative state is PARALLEL GLOBAL ARRAYS, not a heap struct.**
That is exactly why 10 iterations of runtime object scanning only ever hit UI
caches: the PS3-RTTI scout proved the entire `Cc*` namespace (CcCivFlagEntity,
CcGameCamera, CcCityEntity, … 98 classes) is the engine PRESENTATION/entity
layer (Gamebryo/PhysX, has RTTI); the GAME-LOGIC classes are compiled
`-fno-rtti` and store civ/tech/player state in `.data`/`.bss` arrays indexed by
player or civ — the same shape as the ADJ_FLAT name arrays found in iter-1.

**2. The iOS iPad build (`civrev_ios/`) is a SYMBOLICATED Rosetta Stone.**
Decompiled at `civrev_ios/ghidra_decompiled/_all_functions.c` (+`_global.c`,
`NDSEraBonusesScreen.c`) with real function names. Same Firaxis CcCiv engine as
PS3. It handed over the entire effect layer:

### The effect-layer model (from decompiled iOS C, symbol names)
- `TeamMap[player]` = civ index 0..0x10 (`PTR__TeamMap_001fc0ec`).
- `Techs[tech]` = bitmask of which players own the tech (`|= 1<<player`),
  0x30=48 slots, 0x2f=47 future-tech sentinel (`PTR__Techs_001fc29c`).
- `_lbonus[ civ*0x10 + era*4 ]` = per-civ, per-era (4 eras) leader-bonus IDs;
  `int[NUM_CIV][4]`, stride 0x10 (`PTR__lbonus_001fc554`). Read by
  `HasLBonus(bonusID, player, era)` (vaddr 0x72574).
- `ucStartTechs[ civ*0x2f + tech ]` = byte table of per-civ starting techs
  (`PTR_ucStartTechs_001fc488`).
- Other per-player arrays: Era, NTech, Researched/Researching, TFirst, TSource
  (stride 0xc0=48*4), NRes (0x28), Gold, Govt, etc.

### Grant sites (where the bonus is APPLIED)
- `AddTech(player, tech, src, type, flags)` (vaddr 0x338b0) — primitive;
  **flags value 6 = "free/granted"** (vs 0=researched, 5=traded).
- `InitCustomGame` (0x3130c) — per-player loop reads `ucStartTechs` (0x2f/civ)
  and calls `AddTech(player, tech, -1, 6, 1)` for each set byte. (scenario/custom)
- `InitCGame` (0x2e49c) — random-game init; zeroes the arrays; the civ's
  starting tech is delivered as the **era-0 `_lbonus` entry that is a free-tech
  bonus-ID**, applied in `qBeginTurn`. Free-tech bonus IDs: 9,10,0x2b,0x30,
  0x39,0x3a,0x3b,0x3c (→ AddTech of Mathematics/Literacy/Monarchy/Communism/
  Feudalism/Construction/Pottery/Currency).
- `qBeginTurn` (0x3c9a0) — each turn, `HasLBonus(id,player,0)` gates
  `AddTech(...,6,1)` + unique-unit/extra effects.
- `getRealUnitType` (`_global.c:4062`) — `switch(TeamMap[player])` civ→unique
  unit (Hwacha would be a `case 0x10`).

### PS3 value-match signatures (to locate the same code in the stripped EBOOT)
Use the working `ghidra_clean` decompiler + these fingerprints:
- **HasLBonus**: tiny (~200B), clamps era to [0,3], then `civ*0x10 + era*4`
  indexing + linear scan comparing table ints to the bonus-ID arg. Its base
  pointer reveals the PS3 `_lbonus` table → dump 17*4 ints for the per-civ
  bonuses + which are free-tech.
- **qBeginTurn**: nested `if(NTech>4){SetEra(p,1); if(NTech>0xd){SetEra(p,2);
  if(NTech>0x17)SetEra(p,3)}}`.
- **AddTech**: `Techs[tech] |= 1<<player`; flag const 6.
- Tech enum: Writing=8, Currency=0xf, Monarchy=0x13 (TechNames_enu.txt).
- String anchors likely in PS3 .rodata: `@LBTEXT`, `@TECHNAME`, `@ERA`,
  `gamecore/CcCiv.cpp`, "What shall we research next?", "Era Bonuses\n".
- Distinctive strides to confirm a struct match: 0x5800 (unit block), 0x110
  (city), 0xc0 (TSource), 0x28 (NRes), 0x98 (unit-type record), 0x10 (_lbonus).

### The plan to differentiate Korea (civ 0x10)
1. PS3-locate `_lbonus` + `HasLBonus` (era-clamp+civ*0x10 sig), `ucStartTechs`
   + `InitCustomGame`, `AddTech`, `qBeginTurn`. Record in addresses.py.
2. Read the 16 civs' `_lbonus`/`ucStartTechs` rows; design Korea's row (e.g.
   era-0 free-tech = Writing or a science tech; reuse existing LBTEXT bonus IDs,
   incl. a "+Cannon"/Hwacha-flavored one). No new mechanics needed.
3. **The OOB gate, now precisely scoped:** the per-civ tables are sized for
   16/17 (`_lbonus` 0x10-stride ×16, `DAT_001fa760[16]` AI table, 16-case
   switches, `< 0x10` bounds). Extend each to 17 (relocate like ADJ_FLAT in
   iter-1) + bump the `< 0x10` bounds to `< 0x11`. Atomic — miss one and civ 16
   reads OOB.
4. Remove the iter-1188 AS2 slot-16→6 remap so slot 16 flows as civ 16.
5. Verify: M9 boot + a new oracle (read `Techs`/`_lbonus` for the Korea player,
   confirm it differs from China's start).

The runtime 3-way diff + the symbolicated iOS reference together are now
sufficient. This is real, scoped engineering — not an open-ended search.
