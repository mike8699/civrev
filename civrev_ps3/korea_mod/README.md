# Korea Civilization Mod for PS3 Civilization Revolution (v1.0)

Adds **Korea** (leader: Sejong) as a 17th civilization to
Sid Meier's Civilization Revolution (BLUS-30130) on PS3.

## Current shipping state (iter-1185)

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
- A 17-entry **ADJ_FLAT** civ-adjective pointer table is
  written into `.rodata` padding (iter-4) so the in-game
  "Korean" adjective lookup returns a valid pointer.
- The civnames/rulernames parser dispatcher's hardcoded
  count `li r5, 0x11` (=17) at `0xa2ee38` (rulers) and
  `0xa2ee7c` (civs) is bumped to `0x12` (=18) so the parser
  worker mallocs and parses 18 entries (iter-14).

**All 16 stock civs work normally**: full M9 regression
sweep at iter-216 — Caesar / Catherine / Mao / Lincoln /
Elizabeth / Random — 6/6 PASS. iter-223 Caesar M9 PASS
re-verifies the regression after the Common0_korea.FPK
removal.

- **Korea is visible at slot 16 of the civ-select carousel**
  with the label "Sejong / Koreans" and Mao's leaderhead
  portrait (per v1.0 §6.3 asset reuse). Random shifts to
  slot 17 cleanly. **iter-1185** empirically verified:
  - OCR contains `sejong` and `Koreans` substrings at the
    slot-16 position on the civ-select screen
  - M9 PASS at slots 0 (Caesar), 15 (Elizabeth), 16 (Korea),
    17 (Random)
  - Visual confirmation via
    `verification/iter1185_korea_at_slot_16/korea_slot16_highlighted.png`

The carousel extension is delivered via a **JPEXS-based AS2
edit** to `gfx_chooseciv.gfx`. `gfx_chooseciv_patch.py` runs
`ffdec.jar -export script → overwrite LoadOptions .as →
-importScript` at build time, injecting a Korea-synthesis
prefix into `LoadOptions` that clones `slotData6` (China)
into `slotData16` with "Sejong"/"Koreans" label overrides,
pushes Random from slot 16 to slot 17, and bumps
`_parent.numOptions` from 17 to 18. **Nine lines of AS2**;
no PPU patches needed.

**Why it works so cleanly:** the SWF is already fully
parameterized over `_parent.numOptions`. `goLeft` / `goRight`
clamp at `numOptions - 1` with no hardcoded literals. Cell
layout is algorithmic (`j * (width + buffer)`). The iter-178
through iter-212 attempts to find hardcoded "16" or "17"
carousel counts were searching in the wrong places because
there ARE no such counts — everything flows through the
single `numOptions` global. See PRD §10 iter-1184 entry for
the AS2 literal inventory that proves this.

**iter-222 correction (2026-04-15):** The previously-shipped
`leaderheads.xml` overlay (iter-214) and the two
`console_pediainfo_*.xml` overlays (iter-176-era) are
**STRUCTURALLY INERT**. iter-222 empirically proved that
`Common0.FPK` is never opened by the BLUS-30130 PS3 build at
runtime — M9 Caesar passes with the file renamed away. Those
3 overlays shipped in `Common0_korea.FPK` but couldn't reach
the runtime. **iter-223 removes Common0_korea.FPK from the
build/install pipeline** and archives the dead overlays
under `xml_overlays/dead_iter222/`. The disc Common0.FPK is
now left as the stock file (md5 5032f387...).

**§9 DoD status (iter-1185):**

| # | item | status |
|---|------|--------|
| 1 | install.sh works                | **MET** |
| 2 | Korea visible at slot 16 in carousel | **MET** (iter-1185) |
| 3 | Found capital with Korea        | **MET** (iter-1185 — reached in-game HUD) |
| 4 | 50-turn soak as Korea           | **OPEN** — M7 korea_soak pending (iter-1186) |
| 5 | Stock regression (6 civs)       | **MET** |
| 6 | Verification artifacts committed | **MET** |

**5/6 MET.** The §9.X structural blocker recorded at
iter-212 is obsolete — see PRD §9.X for the SUPERSEDED
banner and §9.Y for the unblock plan.

## Requirements

- Clean BLUS-30130 v1.30 EBOOT as an ELF.
  `civrev_ps3/EBOOT_v130_decrypted.ELF` is the committed base
  — produced by `rpcs3 --decrypt` on the original encrypted
  SCE EBOOT (see iter-137 in PRD §10 for why
  `EBOOT_v130_clean.ELF` is unusable).
- Stock `Common0.FPK` and `Pregame.FPK` from the game disc.
- Extracted source trees at `civrev_ps3/extracted/Common0/`
  and `civrev_ps3/extracted/Pregame/`.
- **JPEXS Free Flash Decompiler** (ffdec 22.0.2+) installed at
  `civrev_ps3/tools/ffdec/ffdec.jar`. Download from
  https://github.com/jindrapetrik/jpexs-decompiler/releases
  (portable zip). Gitignored — re-download on fresh checkout.
  Requires Java runtime (OpenJDK 17+ tested).
- RPCS3 for testing (recent build with working LLVM PPU JIT),
  or a real PS3 with a patched disc/EBOOT.

## Build

```bash
cd civrev_ps3/korea_mod
./build.sh                  # produces _build/Pregame_korea.FPK + EBOOT_korea.ELF
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
3. `pack_korea.sh` repacks **Pregame.FPK** via `fpk.py repack`
   after applying the effective overlays:
   - **Pregame**: `civnames_enu.txt`, `rulernames_enu.txt`
     (two 18-row overlays for parser buffers)
   - **gfx_chooseciv.gfx**: JPEXS `-importScript` applies
     the iter-1185 Korea-synthesis prefix to `LoadOptions`
     (see `gfx_chooseciv_patch.py`). Requires JPEXS installed
     under `civrev_ps3/tools/ffdec/ffdec.jar` (gitignored).

   Common0_korea.FPK production was REMOVED at iter-223
   because iter-222 proved Common0.FPK is never opened at
   runtime. The dead overlays are archived under
   `xml_overlays/dead_iter222/`.
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
- `M9/` — iter-216 6-civ regression sweep + iter-224 6/6
  PASS against the lean iter-223 install
- `iter198_18row_boot_safe/` — iter-198's first-time
  18-row civnames boot
- `iter203_civs_dump/` — runtime memory dump of both parser
  buffers proving Korea/Sejong are at index 16
- `iter212_*` (implicit via PRD §9.X) — structural blocker
  documentation
- `iter222_common0_unused/` — empirical proof that
  `Common0.FPK` is never opened at runtime; 7 of 12 disc
  FPKs are dead carry-over
- `iter224_lean_m9_sweep/` — 6-civ regression refresh
  against the iter-223 lean install
- `iter227_verify_tiers/` — `verify.sh` fast/full tiers
  wired to the docker harness

```bash
./verify.sh --tier=static  # M0 only, <30 seconds
./verify.sh --tier=fast    # M0 + Caesar M9 smoke, ~5 min
./verify.sh --tier=full    # M0 + 6-civ M9 sweep, ~25 min
```

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
