# §5.1 `_NCIV` references — PS3 EBOOT (v1.30)

## Status: RESOLVED at iter-213 (2026-04-15) — no single `_NCIV` constant; carousel count is Scaleform-side

The empirical findings of iter-184, iter-197, iter-198, iter-210, and
iter-211 collectively resolve §5.1: the PS3 binary has no single
`_NCIV = 16` constant, the civ count "16" appears at many inline
`cmpwi rN, 0x10` and `li rN, 0x10` sites, but **none of those sites
are on the civ-select carousel render path**. The carousel cell count
is hardcoded SCALEFORM-side in `gfx_chooseciv.gfx`, not in the PPU
EBOOT.

## Empirical resolution (iter-184..211)

1. **Parser is fully dynamic** (iter-197 Ghidra decompile + iter-198
   boot test). `FUN_00a2e640` mallocs `(count*12 + 4)` bytes per
   name file and writes the count as a header word at `(buf - 4)`.
   Safe at any count.

2. **Only 2 PPU `li r5, 0x11` sites** affect parser output: at
   `0xa2ee38` (rulers) and `0xa2ee7c` (civs). Both shipped as
   iter-14 patches bumping to `0x12` (=18). These are the ONLY
   "civ count" PPU constants that matter for the parser path.

3. **Dispatcher uses TOC base `r2 = 0x194a1f8`** (iter-202 correction).
   Civs buffer holder is at .bss `0x1ac93b8`. iter-203 verified
   runtime: `*(0x1ac93b8) = 0x4002a0e0`, count = 18, Korea at
   index 16, all 16 stock civs intact.

4. **14 downstream `li r8, 0x10` consumers** (iter-197) tested
   exhaustively: all 14 together break boot (iter-198), 2 CIVS-only
   are safe but inert (iter-210), consumer A's 7 are safe but
   inert (iter-211). All 14 are NOT on the carousel render path.

5. **6 candidate consumer functions** diagnostically `b .` tested,
   all OFF the carousel path: `FUN_001e49f0` (iter-150),
   `FUN_011675d8` (iter-154), `FUN_001dc0d8` + `FUN_0x111dd70`
   (iter-206), `FUN_001262a0` (iter-209, the CIV_*.dds icon
   registration — civilopedia init).

6. **Scaleform-side modifications** all inert: iter-178 (slotData17
   pool extension), iter-192 (tag[180] LoadOptions hardcode),
   iter-195 (tag[185] numOptions=6 default), iter-200 (tag[184]
   numOptions=17 literal). Four independent angles, all inert.

7. **Hypothesis invalidations**: iter-186 retracted iter-181..183
   cursor-clamp, iter-201 invalidated iter-197's wrong-TOC mapping,
   iter-202 corrected to `r2 = 0x194a1f8`, iter-208 invalidated
   iter-193's `0xf070a0` "ChooseCiv panel loader" hypothesis.

## Unified hypothesis (no further static analysis required)

The civ-select carousel rendering is **entirely Scaleform-side**.
The PPU does NOT call into a "draw-civ-cell" function. Cells exist
as static MovieClip instances in `gfx_chooseciv.gfx` with civ
identification baked in at compile time. PPU only sends cursor input
events, reads the selected index after confirm, and looks up the
chosen civ's data from the parser buffer for in-game init.

## What §5.1 was originally asking for vs what we found

The PRD §5.1 task ("find every site that depends on 0x10 as a civ
count and patch them to 0x11") is the wrong shape for what PS3 CivRev
actually needs:

- **Parser-side count**: already done by iter-14 patches.
- **Consumer-side count**: only 14 sites use `li r8, 0x10` paired
  with civnames pointers; all 14 are off the carousel (iter-210/211).
- **Carousel-side count**: lives in Scaleform AS2 bytecode, not PPU.

**§5.1 is therefore CLOSED as "no further PPU enumeration is useful"
for v1.0.** Any future iteration aiming at the carousel must either
edit the Scaleform AS2 directly (4+ angles tried, all inert) or use
runtime instrumentation to find the cell factory in the live emulator
(blocked because RPCS3's GDB stub doesn't support Z2/Z3/Z4
watchpoints, iter-201).

## ----- HISTORICAL iter-1 content from §5.1 below -----

The PS3 binary does not expose a single `_NCIV = 16` constant. Every place
that needs "number of civs" encodes `16` directly as an immediate — either
as `cmpwi rN, 0x10` (loop-bound compare) or `li rN, 0x10` (pre-loop init)
or as a multiply by 0x40 (the byte size of the 16-pointer × 4-byte arrays
discovered in §5.2).

## What needs to happen

For every parallel pointer array documented in `civ-record-layout.md`, list
every machine-code site that:

1. Loads the array base (LIS/ADDI pair yielding one of the known base
   addresses).
2. Compares a register holding an index against 0x10 (`cmpwi rN, 0x10`).
3. Initializes a loop counter with 0x10 (`li rN, 0x10` followed by `bl`/
   `cmp`-against-0x10 flow).
4. Computes `array_end = base + 0x40` (the raw byte-length of a 16-entry
   4-byte array).

Each hit becomes a candidate patch site. For a 17-entry table, (1)/(2)/(3)
need to become 0x11, and (4) needs to become `+ 0x44`.

## Confirmed array bases (from §5.2)

| Purpose                    | Base        | Notes                                      |
|----------------------------|-------------|--------------------------------------------|
| Leader display names       | `0x0194b434`| 16 × 4                                     |
| Civ internal tags          | `0x0194b35c`| 16 × 4                                     |
| Civ adjectives (flat)      | `0x0195fe28`| 16 × 4                                     |
| Civ adjective+plural pairs | `0x0194b3c8`| irregular stride, walk by pointer scanning |
| Leader internal tags       | ? (near `0x0194b318`–`0x0194b358`) | head not yet scanned |

## Known candidate call-site regions (not yet dumped)

- `FUN_0002dfb4` (config loader from `docs/debug-mode.md`) — reads XML
  bools and iterates something; may or may not walk the civ enum.
- Any function whose decompile in `civrev_ps3/decompiled_v130/` references
  the adjective/plural strings ("Roman", "Chinese", etc.) is a candidate
  consumer of the flat adjective table.
- The function loading `leaderheads.xml` is a candidate consumer of both
  the leader-display-name array and the civ-internal-tag array.

## iOS cross-reference (CORRECTED understanding)

The iOS binary exposes `_NCIV` as `PTR__NCIV_001fc1e0`, referenced
**286 times** across the symboled Ghidra export. On first read I
assumed `_NCIV` was a compile-time constant set to 16 and that the
mod reduced to a single init-site byte patch. **That is wrong.**

Looking at iOS assignment sites:

```c
// civrev_ios/ghidra_decompiled/CustomMap.c:1048
*(int *)PTR__NCIV_001fc1e0 = iPositionCount + 1;

// civrev_ios/ghidra_decompiled/_global.c:17875  (and 19941, 31787, 33853)
*(undefined4 *)PTR__NCIV_001fc1e0 = 6;
```

`_NCIV` is the **current game's civ count**, not a compile-time max.
It's written dynamically based on the number of players in the
current scenario (commonly 6). The 286 reads are the loops that walk
"every civ that's in the current game", not "every possible civ".

**Consequence for the mod:** patching `_NCIV` from 16 to 17 is the
wrong lever entirely. A fresh Korea start would set `_NCIV` to
whatever the player-count dictates, probably 6 or 7 — and if slot 6
is Korea (nationality=16), the loops will correctly iterate over
slots 0..6 without any `_NCIV` tweak required.

**What we actually need to patch is the per-civ lookup arrays**: the
parallel 16-entry pointer tables in rodata (see `civ-record-layout.md`)
that are indexed by `Nationality` field, not by the loop counter. If
slot 6's `Nationality == 16` and the leader-name table only has 16
entries, `leader_names[16]` reads out of bounds regardless of what
`_NCIV` is set to.

The real §6.2 work is:
1. Identify how the 5 confirmed parallel arrays in rodata are
   consumed at runtime. If they're the live lookup tables, extend
   them to 17 entries. If they're just init-copy sources feeding a
   heap-allocated runtime array, extend the runtime array instead.
2. Find any hardcoded `< 16` bound in code that iterates "all
   possible civs" (as distinct from "all civs in this game"). These
   are the true upper-limit checks that need to become `< 17`. The
   iOS build probably has them too — re-grep iOS for raw `0x10`
   constants in a civ context.

This correction invalidates iter-2's "89 `li 0x10 → stw` candidates"
hunt and the two false positives at `0x359300` / `0x95e258` — the
former is a cross-function boundary false match, and the latter has
an intermediate `li r0, 1` that clobbers the `li r0, 16`. Neither is
the `_NCIV` initializer, and even if one were, it wouldn't be the
right thing to patch.

## Important caveat: iOS is NDS lineage, NOT PS3 lineage

`civrev_ios/CLAUDE.md` is explicit: the iOS build was ported from the
**Nintendo DS** branch of Civilization Revolution, not the PS3/Xbox 360
branch. The `NDS*` class prefix throughout the iOS binary is the
tell. PS3 and iOS share only the low-level Firaxis engine (F-classes),
not the game-logic layer. Class hierarchies, struct layouts, function
signatures, and globals differ substantially between the two branches.

The iOS build also has **16 civs, not 17** — CivRev 2 (Android Unity)
added Korea, but iOS predates that. iOS has 17 **leaders** (the 17th is
"Grey Wolf" for barbarians), which is unrelated to our Korea work.

Concretely, PRD §5.6's "Rosetta Stone" assumption — that the iOS
symboled binary tells us where PS3 globals live — is weaker than
advertised for civ-specific code. It still works for engine-level
globals (PRNG, string pools, IO buffers) but not for civ tables.

## iter-13 addendum — iOS InitGenderedNames pattern

Against the iter-6 caveat that iOS is NDS-lineage (not PS3), the
iOS decompile still reveals a likely-shared engine function:
`InitGenderedNames(FStringA const&, FGenderVariable*&, int)` at
iOS VA `0x7af14`.

Usage pattern (from `civrev_ios/ghidra_decompiled/_all_functions.c`
around line 77439+):

```c
FStringA::Copy(&buf, 11, "RulerNames_", 0);
InitGenderedNames(&buf, PTR__rulername_001fc5c4, 0x11);   // 17 rulers

FStringA::Copy(&buf, 9, "CivNames_", 0);
InitGenderedNames(&buf, PTR__civname_001fc5b8, 0x11);     // 17 civs

FStringA::Copy(&buf, 10, "CityNames_", 0);
InitGenderedNames(&buf, PTR__cityname_001fc5b4, 0x101);   // 257 cities
```

**The count is passed as a literal argument (`0x11` for civs and
rulers).** Internally, `InitGenderedNames` allocates an array of
that size and parses the text file into it. Passing 17 (hardcoded
at every call site) is why the civnames/rulernames buffer is
exactly 17 wide — and why adding an 18th entry to the source text
files OOB-writes adjacent memory.

**Implication for the 17-slot extension:** to land Korea as a
proper 17th civ on PS3, you must find the PS3 equivalent of these
`InitGenderedNames(RulerNames_, ..., 0x11)` and
`InitGenderedNames(CivNames_, ..., 0x11)` call sites and change
the `0x11` literal to `0x12` (18). That's ONE byte patch per call
site (the immediate in `li r5, 17` → `li r5, 18`).

**Static-search impediment:** the PS3 binary has 283 sites of
`li rX, 17` — too many to brute-force. The distinguishing context
is that the right sites are immediately preceded (within ~15
instructions) by an FStringA::Copy call that loads "RulerNames_"
or "CivNames_". But those strings aren't reachable via LIS/ADDI
or TOC-relative addis+addi in PS3 code (verified: the name-prefix
pointer table at `0x194b648..0x194b668` has zero 32-bit or 64-bit
references anywhere in the binary).

The strings MUST be accessed somehow at runtime — the game boots
and loads civnames_enu.txt successfully on stock data — so there's
either:
- A C++ class-method that inlines string literals as part of a
  template instantiation we haven't decoded
- A vtable-indirect call path (the name-prefix table is the
  vtable, accessed via `this->vtable->string_ptrs[i]`)
- A TOC-of-TOCs indirection (table pointer in TOC → table → strings)

None of these are static-searchable without Ghidra UI XREFs. The
blocker is fundamental: in the Ralph-loop harness we have Bash +
Python but no Ghidra UI session. The iter-13 cross-ref narrows
the target but does not make it directly reachable.

## Corrected iter-3 plan (after the iOS caveat)

1. **Use the Xbox 360 binary as the real Rosetta Stone.** Per §5.6,
   PS3 and Xbox 360 CivRev share the actual game-logic codebase (both
   compiled from the same Firaxis PPC console branch, unlike iOS).
   The 360 ISO is at `civrev_xbox360/Sid Meier's Civilization
   Revolution (USA)...iso` and `civrev_xbox360/xenon_recomp/` can
   translate the XEX directly to C/C++ — often more readable for
   data-table consumers than Ghidra's heuristic decomp.
2. **Locate the leaderheads.xml loader function in the 360 binary**
   by string-ref to `"leaderheads.xml"` or `"Nationality"`, then
   find the structurally identical function in the PS3 Ghidra DB
   (same class hierarchy, same logic, different compiler output).
   That function is the single best entry point for understanding
   how the 0x0194bxxx parallel arrays are actually used.
3. **Fall back to live RPCS3 GDB** if xenon-recomp output is
   unreadable. The docker harness already exists at
   `rpcs3_automation/docker_run.sh` and the host has the PS3 game
   disc staged at `civrev_ps3/modified/`. Attach at main-menu and
   scan BSS for `int 16` values in the cluster whose TOC entries
   are read by 20+ functions.

## Iter-1 unaltered dead-end (kept for historical context)

The iOS globals sit in a cluster:
`PTR__BARB_001fc0b0`, `PTR__War_001fc2b8`, `PTR__Treaty_001fc2a0`,
`PTR__Turn_001fc2a4`, `PTR__Govt_001fc24c`, `PTR__Diplomacy_001fc22c`,
`PTR__NRes_001fc268`, `PTR__NCIV_001fc1e0`, `PTR__who_001fc328`,
`PTR__work_001fc330`. They're all within `0x001fc0b0..0x001fc330`.
**This is the iOS "game globals pointer table" — `_NCIV` lives in it.**

The PS3 equivalent is a same-shaped region somewhere in the data
segment. The existing `docs/debug-mode.md` already identified
`PTR_DAT_01929e14` as a "debug config" pointer in the same style, so
at least one global pointer lives at `0x01929e14`. The civ-system
globals table is probably adjacent — a structured scan of
`0x0192xxxx..0x0193xxxx` for a block of pointer-typed globals would
localize it.

## Iteration 1 dead-end (documented for iter-2)

Both static approaches tried this iteration failed to surface a single
call-site that references any of the four 0x194bxxx parallel arrays:

1. **Bulk decompile grep.** `civrev_ps3/decompiled_v130/` has ~36k per-
   function files, but Ghidra's bulk export stripped all DAT_<addr>
   cross-refs — grepping for the known base addresses, the
   `DAT_0194b*` prefix, or literal leader strings like "Caesar" returns
   zero hits. Any §5.1 work that relies on this text dump is blocked
   until a fresh headless Ghidra pass is run with cross-refs preserved.
2. **Instruction-level LIS/ADDI scan.** Walking the text segment
   (0x10000..0x1400000) and decoding every `addis rN,0,high` + paired
   `addi/ld/lwz` instruction produces ZERO hits whose effective address
   lands inside any of the five confirmed parallel arrays. The LIS
   high-half distribution in the code region is dominated by
   float constants (0x3f80 = 1.0) and small integers — no addis sites
   with high half `0x0194`, `0x0195`, or `0x0196` at all. This is
   consistent with the PS3 ELFv1 ABI using TOC-relative addressing
   (`ld rN, offset(r2)` where r2 = shared TOC base at `0x0193a288`) for
   global data, rather than LIS/ADDI absolute immediates.
3. **TOC entry scan.** Searching the whole file for 32-bit BE or 64-bit
   BE values equal to each table base address finds:
   - `LDR_TAG` 0x194b318 — 0 refs
   - `CIV_TAG` 0x194b35c — 0 refs
   - `ADJ_PAIR` 0x194b3c8 — 0 refs
   - `LEADER_NAMES` 0x194b434 — 0 refs
   - `ADJ_FLAT` 0x195fe28 — 2 32-bit matches, both inside unrelated
     string-pointer tables (not real references).

This means **the four 0x194bxxx tables are either not referenced at
runtime at all, or they're referenced via a form of addressing that
static analysis alone can't recover.** The most likely explanations are:

- The live civ data is a **heap-allocated copy** populated by a one-shot
  initializer that walks these static tables by base (loaded once at
  init-time via a code path we haven't found), then stores a pointer
  to the heap table in a global. All subsequent civ lookups hit the
  heap copy, not the rodata tables.
- Or the static tables are partially dead/redundant rodata left over
  from C++ static-init code that the compiler hoisted but never
  actually uses at runtime.

A third table class was found at `0x0193908x..0x193920x` (in the
**writable data segment**) containing leader display names and
`<leaderhead>.xml` filenames: "Caesar"→"rom_caesar.xml",
"Mao"→"chi_mao.xml", "Shaka Zulu"→"mal_shaka.xml", plus barbarian heads
and advisor assets. This looks like the live, post-load
`leaderheads.xml` parse result, not the initial rodata image. Entries
are NOT in civ-enum order and mix civilizations with non-civ leader
head types, so it's not directly civ-indexed — probably a `std::map`
or `std::vector` of all leaderhead entries keyed by filename prefix.

## Next concrete steps (iter-2)

1. **Live GDB inspection.** Boot `EBOOT_v130_clean.ELF` under RPCS3
   with the GDB stub enabled, set a breakpoint immediately after the
   leaderheads.xml loader (function TBD — find via string ref to
   `"leaderheads.xml"` in Ghidra), and dump the live civ-indexed data
   tables from guest memory. The resulting addresses will tell us where
   the real runtime civ data lives.
2. **Re-run Ghidra with full analysis.** The bulk `.c` export at
   `decompiled_v130/` is a stripped form that lost DAT cross-refs; open
   the `civrev.gpr` project directly and query for XREFs to addresses
   0x194b318 / 0x194b35c / 0x194b3c8 / 0x194b434 / 0x195fe28 in the UI.
   If even Ghidra's full XREF database shows no references, the
   "mostly dead rodata" hypothesis is confirmed and we can focus
   exclusively on the live runtime heap tables.
3. **Inventory the `0x1939xxx` leaderhead-parse region.** Walk the
   entire data-segment range `0x1938000..0x193a288` (up to the TOC
   base) and catalog every pointer-to-string block. The live
   leaderheads.xml parse result lives somewhere in there; once located,
   adding a 17th entry becomes "add one `<LeaderHead Nationality="16"
   .../>` row to the overlaid leaderheads.xml and let the existing
   loader populate the new slot" — IF the loader's allocation honors
   the input file's entry count rather than a hardcoded `new
   LeaderHead[16]`.
4. Identify the ELFv1 TOC base at `0x0193a288` (confirmed via the
   entry-point function descriptor table at `0x018b5b20`, where every
   8-byte (entry_ptr, toc_ptr) descriptor shares `toc_ptr == 0x0193a288`)
   and use it to decode `ld rN, offset(r2)` TOC-relative global loads
   — which is how the PS3 binary actually accesses its globals.

## Why this is strictly harder than the PRD expected

The PRD §5.1 example ("cross-reference iOS `_NCIV` symbol") assumes a
single named global. PS3 CivRev has no such global — the "number of civs"
is inlined at every use site. That means the §5.1 output is not a single
address but a **list of 5–50+ patch sites** that must all be kept in sync.
Getting that list wrong leaks civ 16 → out-of-bounds read → crash in a
random subsystem. Expect this investigation to take multiple iterations.
