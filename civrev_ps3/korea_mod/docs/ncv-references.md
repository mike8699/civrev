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

## Next concrete steps

1. Grep `civrev_ps3/decompiled_v130/` for references to the confirmed base
   addresses (`0x194b434`, `0x194b35c`, `0x195fe28`, `0x194b3c8`) and the
   individual string pointers (`0x16a38a8` for "Caesar" etc.). Every
   matching function is a loop over the civ set.
2. For each matching function, read its disassembly and catalog the
   immediate-0x10 compares. Many will be actual civ-index loops; a few
   may be unrelated (there are other "16"s in the binary).
3. Separately, enumerate the `LDR_*` internal tag head (which requires
   dumping pointers just below `0x0194b340`).
4. Record all findings in this file, then update the candidate patch
   list in `addresses.py`.

## Why this is strictly harder than the PRD expected

The PRD §5.1 example ("cross-reference iOS `_NCIV` symbol") assumes a
single named global. PS3 CivRev has no such global — the "number of civs"
is inlined at every use site. That means the §5.1 output is not a single
address but a **list of 5–50+ patch sites** that must all be kept in sync.
Getting that list wrong leaks civ 16 → out-of-bounds read → crash in a
random subsystem. Expect this investigation to take multiple iterations.
