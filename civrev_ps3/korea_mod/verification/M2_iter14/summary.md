# Iter-14 — Ghidra headless located the parser; partial unblock

## Major RE win

Ran Ghidra 11.3.1 in headless mode against
`civrev_ps3/ghidra/civrev.rep` with custom Jython post-scripts.
First iteration where Ghidra's analysis database + decompiler
were available.

### Finding 1 — name-file parser located

`FUN_00a21ce8` is the name-file init function. It calls
`FUN_00a216d4` (the PS3 equivalent of iOS's
`InitGenderedNames(FStringA, void**, int)`) with counts matching
iOS's pattern: 0x30 (techs), 0x30 (famous), 0x101 (cities), 0x42
(wonders), 0x80 (landmarks), 0x11 (rulers), 0x11 (civs).

### Finding 2 — exact v130_clean instruction addresses

Sequence-matched the distinctive count literals (0x101, 0x42,
0x80, 0x11, 0x11) in EBOOT_v130_clean.ELF — a single function at
`0xa2ed6c..0xa2ee80` matches. RulerNames_ init count is at
`0xa2ee38` and CivNames_ init count is at `0xa2ee7c`, both as
`li r5, 0x11` (`0x38a00011`).

### Finding 3 — two-byte patch landed cleanly

Added to `eboot_patches.py`:
- `0xa2ee38`: `0x38a00011` → `0x38a00012`
- `0xa2ee7c`: `0x38a00011` → `0x38a00012`

Dry-run passes. Installed; v0.9 state still boots with these
active (no-op when files still have 17 entries).

### Finding 4 — bumping count alone is INSUFFICIENT

Extended `civnames_enu.txt` / `rulernames_enu.txt` to 18 entries
via `fpk.py` repack, rebuilt with the `li r5, 18` patches,
installed, and boot-tested. **Still timed out at RSX init.**

Confirms iter-12 hypothesis: the crash is from a **downstream
consumer** of the parsed list that has its own 17-wide buffer,
not from `InitGenderedNames`'s r5 count argument. Bumping r5 just
tells the parser to iterate one more time; it doesn't resize the
downstream per-civ table.

The downstream table is likely one of the "dead rodata" arrays
from §5.2 (LEADER_NAME_PTR_ARRAY, CIV_TAG_ARRAY, LDR_TAG_ARRAY,
ADJ_PAIR_ARRAY). Those were 16×4-byte arrays that looked
unreferenced via static XREFs, but might be populated by the
parser's write path (computed addressing base+index*4, not
inline-immediate).

### Finding 5 — v0.9 still boots with the new patches in place

Reverted `pack_korea.sh` to use `fpk_byte_patch.py` (the v0.9
Elizabeth→Sejong patcher) while keeping the new `eboot_patches.py`
patches active. Boot test confirms M6 still passes — the
`li r5, 18` change is a no-op when the name files have only 17
entries.

## Next iteration should

1. Open `FUN_00a216d4` (the parser) in Ghidra and trace what it
   writes to via `PTR_rulername` / `PTR_civname`. The write target
   is the downstream 17-wide buffer.
2. Find the buffer's allocation site (static struct construction)
   and bump its size.
3. Find the civ-select cursor's 17-slot right-clamp.
4. All three patches together should unblock Korea at slot 16.

## Ghidra scripts used

- `/tmp/FindLi17Sites.py` — locate `li r5, 0x11` instructions
  inside FUN_00a21ce8 that precede BL to FUN_00a216d4.
- `/tmp/FindCityInit.py` — filter for functions with a BL
  preceded by `li r5, 0x101` (narrowed to 6 candidates).
- `/tmp/DecompFn.py` — decompile candidates and grep for name-
  file patterns.

These scripts are preserved in the iteration's build environment
but not committed (generated on the fly).
