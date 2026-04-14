# §5.1 `_NCIV` references — PS3 EBOOT (v1.30)

## Status: INCOMPLETE — candidates identified, call sites not yet enumerated

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
