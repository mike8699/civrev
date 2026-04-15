# Korea Civilization Mod for PS3 Civilization Revolution (v1.0)

Adds Korea (leader: Sejong) data to Sid Meier's Civilization
Revolution (BLUS-30130) on PS3.

## Current shipping state (iter-218)

This mod operates under the **iter-189 strict-reading directive**
(see PRD §9): Korea must be a brand-new 17th civilization with
ALL 16 stock civs (including Elizabeth/England) AND Random AND
Korea all selectable. NO civ may be replaced, renamed, or
repurposed.

Under this directive, the v1.0 shipping state is:

**What ships and works:**

- **Korean** civ name and **Sejong** ruler name added to the
  game's runtime parser buffers as the 17th entry (index 16)
  via 18-row `civnames_enu.txt` / `rulernames_enu.txt`
  overlays. Verified end-to-end at runtime via GDB memory
  reads (iter-203):
  - civs buffer at heap, count = 18, index 16 → "Koreans"
  - rulers buffer at heap, count = 18, index 16 → "Sejong"
  - All 16 stock civs unchanged at indices 0..15
  - Internal "Barbarians/Grey Wolf" placeholder shifts to
    index 17
- A 17th `<LeaderHead Nationality="16" Text="Sejong">` entry
  is registered with the game's leaderhead loader via a
  `leaderheads.xml` overlay (iter-214). The entry reuses the
  existing `GLchi_Mao.xml` / `GLchi_Mao_` Mao leaderhead
  assets — no new binary assets ship.
- Pediainfo overlays for `CIV_KOREA` and `LEADER_SEJONG`
  (iter-176-era files) reuse `PEDIA_CHINA_*.dds` and
  `PEDIA_MAO_*.dds` assets per spec.
- A 17-entry **ADJ_FLAT** civ-adjective pointer table is
  written into `.rodata` padding (iter-4) so the in-game
  "Korean" adjective lookup returns a valid pointer.
- The civnames/rulernames parser dispatcher's hardcoded
  count `li r5, 0x11` (=17) at `0xa2ee38` (rulers) and
  `0xa2ee7c` (civs) is bumped to `0x12` (=18) so the parser
  worker mallocs and parses 18 entries (iter-14).

**All 16 stock civs work normally**: full M9 regression
sweep at iter-216 — Caesar / Catherine / Mao / Lincoln /
Elizabeth / Random — 6/6 PASS.

**What does NOT ship and is structurally blocked:**

- **Korea is NOT visible in the civ-select carousel**. The
  carousel cell rendering is **entirely Scaleform-side**
  (cells are static MovieClip instances in `gfx_chooseciv.gfx`
  with civ identification baked in at compile time). 33+
  iterations across iter-178..218 explored every static
  patching angle:
  - 9 PPU candidate functions diagnostically `b .` tested OFF
    the carousel render path
  - 14 `li r8, 0x10` consumer sites tested in collective +
    selective subsets — all safe but inert
  - 4 Scaleform-side tag edits (slotData17, LoadOptions
    hardcode, two numOptions literal swaps) — all inert
- Bumping the carousel cell count to 17 would require
  modifying the AS2 carousel itself (adding a 17th MovieClip
  child instance, recomputing layout coordinates, patching
  cursor-bound logic, etc.) — a Scaleform engineering effort
  outside this loop's static-patching toolchain.

**§9 DoD status:**

| # | item | status |
|---|------|--------|
| 1 | install.sh works                | **MET** (iter-219 verified) |
| 2 | Korea visible at slot 16 in carousel | **OPEN — STRUCTURALLY BLOCKED** (iter-212 §9.X) |
| 3 | Found capital with Korea        | **BLOCKED on item 2** |
| 4 | 50-turn soak as Korea           | **BLOCKED on item 2** |
| 5 | Stock regression (6 civs)       | **MET** (iter-216 6/6 PASS) |
| 6 | Verification artifacts committed | **MET** |

The PRD §9.X subsection (added at iter-212) formally records
the structural blocker on item 2 and lists every exhausted
approach.

## Requirements

- Clean BLUS-30130 v1.30 EBOOT as an ELF.
  `civrev_ps3/EBOOT_v130_decrypted.ELF` is the committed base
  — produced by `rpcs3 --decrypt` on the original encrypted
  SCE EBOOT (see iter-137 in PRD §10 for why
  `EBOOT_v130_clean.ELF` is unusable).
- Stock `Common0.FPK` and `Pregame.FPK` from the game disc.
- Extracted source trees at `civrev_ps3/extracted/Common0/`
  and `civrev_ps3/extracted/Pregame/`.
- RPCS3 for testing (recent build with working LLVM PPU JIT),
  or a real PS3 with a patched disc/EBOOT.

## Build

```bash
cd civrev_ps3/korea_mod
./build.sh                  # produces _build/{Common0,Pregame}_korea.FPK + EBOOT_korea.ELF
./verify.sh --tier=static   # runs M0 (xmllint + FPK round-trip + eboot dry-run)
```

Build steps:

1. `xml_overlays/*.xml` are validated (xmllint).
2. `eboot_patches.py` applies **6 in-place byte patches** to
   `EBOOT_v130_decrypted.ELF`:
   - **iter-4** (×4): writes a 17-entry ADJ_FLAT civ-adjective
     pointer table into `.rodata` padding (with a "Korean"
     entry at index 16) and redirects two TOC entries so
     in-game adjective lookups return valid pointers.
   - **iter-14** (×2): `li r5, 0x11 → 0x12` parser-count
     bumps at `0xa2ee38` (rulers) and `0xa2ee7c` (civs).
3. `pack_korea.sh` repacks `Common0.FPK` and `Pregame.FPK`
   via `fpk.py repack` after applying overlays:
   - **Common0**: `leaderheads.xml`,
     `console_pediainfo_civilizations.xml`,
     `console_pediainfo_leaders.xml`
   - **Pregame**: `civnames_enu.txt`, `rulernames_enu.txt`
4. `install_eboot.sh` installs the patched EBOOT to BOTH
   `modified/PS3_GAME/USRDIR/EBOOT.BIN` (tracked in git) AND
   `~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN`
   (the path RPCS3 actually boots from — dual-install is
   required per the iter-133 finding).

## Install

```bash
./install.sh
```

The script wraps `build.sh` (only if needed), copies
`_build/*_korea.FPK` to `modified/PS3_GAME/USRDIR/Resource/Common/`,
and runs `scripts/install_eboot.sh` for the dual-path EBOOT
install. First-time install creates `.orig` backups of every
file it overwrites.

Then boot the game in RPCS3 via
`civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play 0 romans`
or run `civrev_ps3/korea_mod/run_m9_regressions.sh` for the
6-civ regression sweep.

## Verification

All verification artifacts live under `verification/` in
dated per-iteration subdirectories. Key results:

- `M0/` — static M0 GREEN: xmllint + FPK round-trip + eboot
  dry-run + committed-artifact health (10,216 files checked,
  0 mismatches as of iter-216)
- `M9/` — iter-216 6-civ regression sweep, 6/6 PASS
- `iter198_18row_boot_safe/` — iter-198's first-time
  18-row civnames boot
- `iter203_civs_dump/` — runtime memory dump of both parser
  buffers proving Korea/Sejong are at index 16
- `iter212_*` (implicit via PRD §9.X) — structural blocker
  documentation

Run `./verify.sh --tier=static` for a green M0 signoff.

## Architecture notes

This mod is the result of 200+ iterations of reverse engineering
across the PRD's §10 Progress Log. Key technical findings:

- **iter-4** (and again iter-176): The PS3 EBOOT stores civ data
  as PARALLEL POINTER ARRAYS (16 × 4 bytes each), not as a
  single struct table. Of 5 such arrays, only ADJ_FLAT at
  `0x0195fe28` is actually consulted at runtime; the other 4
  are dead rodata. Extending Korea requires writing a new
  17-entry table elsewhere and redirecting the 2 TOC entries
  that reference the old base.
- **iter-14**: The civnames/rulernames parser at `0xa216d4` is
  invoked via a dispatcher that passes `count = 0x11 = 17`. The
  parser allocates `(count * 12 + 4)` bytes per call. Bumping
  the count constant lets it read 18 entries from an extended
  overlay file.
- **iter-133**: RPCS3 boots from the HDD path
  (`~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN`),
  not the disc path. Every patch must be installed to both.
- **iter-137**: The old `EBOOT_v130_clean.ELF` was extracted
  by a buggy SELF unpacker that stripped `PT_SCE_RELA` and the
  runtime fixups. The new `EBOOT_v130_decrypted.ELF` (via
  `rpcs3 --decrypt`) is the real base ELF.
- **iter-189** (user directive update): tightened the v1.0
  DoD to require Korea as a brand-new 17th civ at a brand-new
  18th carousel cell with no replacements.
- **iter-197**: Ghidra decompile of the parser dispatcher
  established that the parser is fully dynamic (mallocs based
  on count argument, no fixed 17-wide buffer). The "downstream
  17-wide buffer" model from iter-7..72 was wrong.
- **iter-198**: First successful boot with 18-row civnames,
  proving the iter-14 patches + 18-row overlay work end-to-end.
- **iter-201**: RPCS3's GDB stub rejects Z2/Z3/Z4 watchpoints
  at the protocol level. Only Z0 software code breakpoints
  work for runtime debugging. Watchpoint-driven RE is
  structurally unavailable.
- **iter-202**: The parser dispatcher uses a DIFFERENT TOC
  base (`r2 = 0x194a1f8`) than the main module
  (`r2 = 0x193a288`). Earlier iterations using the wrong r2
  resolved TOC slots to garbage rodata.
- **iter-203**: First end-to-end runtime verification that the
  18-row overlay reaches the parser buffers correctly. Korea
  at civs index 16 = "Koreans", Sejong at rulers index 16 =
  "Sejong".
- **iter-211/212**: Definitive ruling that the carousel cell
  count is hardcoded SCALEFORM-side, not in PPU code. The 14
  PPU `li r8, 0x10` consumers are off the carousel path. The
  carousel cells are pre-authored MovieClip instances in
  `gfx_chooseciv.gfx`.

## Mod's actual cosmetic effect

Because the carousel rendering is structurally blocked, this
v1.0 ships **invisible** Korea — the data is in the parser
buffers and registered with the leaderhead loader, but no UI
element ever shows her. A user installing the mod will see no
visible difference from the stock game on the civ-select
screen.

The mod is best understood as **the maximum reachable shipping
state under iter-189 strict reading**, plus a complete
investigation log under PRD §10 documenting what was tried and
why each angle failed. A future v1.1 (or a different toolchain
that allows Scaleform AS2 editing) could build on this
foundation to actually surface Korea in the carousel.
