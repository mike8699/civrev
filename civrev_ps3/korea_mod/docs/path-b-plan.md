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

- `"CIVBONUSTEXT"` — EBOOT file offset `0x16CF0DE` (and a 2nd ref).
- `"LBTEXT"` — EBOOT file offset `0x16811A9` (and a 2nd ref).
- `"CIVBONUS"` — present (2 refs).

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

- Is `CIVBONUSTEXT[civ]` consumed directly (Display==Mapping) or via an
  indirection table? (iter-2 answers.)
- Are the bonus *effects* table-driven or a `switch(civ)`? Table-driven is
  far easier to extend.
- Does the savegame serializer encode civ count? (bump save version if so.)
