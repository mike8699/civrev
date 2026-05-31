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
