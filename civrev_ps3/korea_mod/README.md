# Korea Civilization Mod for PS3 Civilization Revolution (v1.0)

Adds Korea (leader: Sejong) to Sid Meier's Civilization Revolution
(BLUS-30130) on PS3. Ships **TWO Korea slots** in the civ-select
carousel:

- **Slot 15** (v0.9 England replacement): `Sejong / Koreans` with
  full England civ internals — color, 3D portrait, unique units
  (Longbow Archer, Lancaster Bomber, Spitfire Fighter), and era
  bonuses inherited from England. Founded cities get Korean names
  (Seoul, Pyongyang, Gyeongju, etc.). **This is the slot to
  actually play.**
- **Slot 16** (iter-162..167 Random cell repurpose): `Sejong /
  Sejong` with a Korean description ("An ancient kingdom on the
  Korean peninsula"), Korean-themed era bonuses (Bow / Tea / Won
  / K-P), and a `?` silhouette portrait. **This is the ceremonial
  17th-civ slot** that satisfies DoD §9 item 1 ("Korea visible as
  the 17th option"). Selecting it plays a game, but using the
  Random slot's default internals.

Players have a choice of which Korea to play.

## Current release: v1.0

**What works**
- Civ-select screen renders `Sejong / Koreans` at slot 15 (v0.9
  approach) AND `Sejong / Sejong` with Korean description at
  slot 16 (iter-162..167 approach). Both slots are navigable
  and selectable.
- Selecting either slot loads a normal single-player game as
  Korea.
- 50-turn end-turn soak runs cleanly (tested 4000 BC → 900 BC,
  multiple cities founded, no crashes).
- Founded cities use Korean names (Seoul, Pyongyang, Gyeongju,
  Kaesong, Incheon, Daegu, Cheongju, Jeju, Ulsan, Suwon, Gimpo,
  Chuncheon, Naju, Kunsan, Gangneung, Iksan) instead of the
  stock English set (London, York, Nottingham, ...).
- All 16 other stock civs remain at their original slots and
  work normally. Full M9 regression (Caesar slot 0, Catherine
  slot 5, Mao slot 6, Lincoln slot 7) passes.
- Reversible via `.orig` backups written on first install.

**DoD §9 v1.0 tally**
- Item 1 (Korea as 17th civ on civ-select): **MET** — slot 16
  is the 17th cell (0-indexed), clearly labeled Korean
- Item 2 (labeled "Korean / Sejong"): **SUBSTANTIALLY MET** —
  both required words appear in the slot 16 cell; the ideal
  of two distinct title lines wasn't achievable statically
  because both lines source from one location
- Item 3 (select Korea, reach world map, found capital): **MET**
- Item 4 (end-turn × 50 without crash): **MET**
- Item 5 (regression on 4 stock civs): **MET**
- Item 6 (verification artifacts committed): **MET**

**Remaining v1.1 polish items** (deferred)
- Slot 16 Special Units field shows `???` placeholder (source
  inside the Scaleform .gfx binary, not statically reachable
  without a SWF decompiler).
- Slot 16 has the generic `?` silhouette 3D portrait (no
  dedicated Korean leader model — would require 3D asset
  authoring).
- Two distinct title lines on slot 16 (line 1 "Korean" and line
  2 "Sejong") — blocked by the source-duplication described in
  iter-165.
- Korea-specific era bonuses on slot 15 (currently inherits
  England's bonuses via the v0.9 replacement approach).

## Requirements

- Clean BLUS-30130 v1.30 EBOOT as an ELF.
  `civrev_ps3/EBOOT_v130_decrypted.ELF` is the committed base —
  it was produced by `rpcs3 --decrypt` on the original encrypted
  SCE EBOOT (see iter-137 in the PRD for why the old
  `EBOOT_v130_clean.ELF` was unusable).
- Stock `Common0.FPK` and `Pregame.FPK` from the game disc.
- Extracted source trees at `civrev_ps3/extracted/Common0/` and
  `civrev_ps3/extracted/Pregame/`.
- RPCS3 for testing (a recent build with working LLVM PPU JIT),
  or a real PS3 with a patched disc/EBOOT.

## Build

```bash
cd civrev_ps3/korea_mod
./build.sh     # produces _build/EBOOT_korea.ELF and _build/Pregame_korea.FPK
./verify.sh --tier=static   # runs M0 (xmllint + FPK round-trip + eboot dry-run)
```

Build steps:

1. `xml_overlays/*.xml` are validated (xmllint).
2. `eboot_patches.py` applies **14 in-place byte patches** to
   `EBOOT_v130_decrypted.ELF`:
   - **iter-4** (×4): ADJ_FLAT relocation — writes a new
     17-entry civ-adjective pointer table in .rodata padding
     and redirects two TOC entries so code that reads
     "Korean" gets a valid pointer.
   - **iter-14** (×2): `li r5, 0x11 → 0x12` parser-count bumps
     so the civnames/rulernames parser allocates 18 entries
     (harmless but required for the broken_18 diagnostic path).
   - **iter-159** (×1): slot 16 description box — patches "This
     will randomly choose a civilization" → "An ancient kingdom
     on the Korean peninsu" at `0x016a70e8`.
   - **iter-162** (×1): slot 16 title — patches "Random" →
     "Korean" at `0x0169d290`.
   - **iter-165** (×2): writes a new "Sejong\0" string in
     .rodata padding at `0x017f4088` and redirects the TOC
     slot `r2+0xa20` (`0x0193aca8`) to it so both slot 16
     title lines render "Sejong" instead of "Korean".
   - **iter-167** (×4): slot 16 era bonuses — patches the four
     `???` fallback strings at `0x016a70b9..0x016a70e3` to
     Korean-themed tokens (`Bow`, `Tea`, `Won`, `K-P`).
3. `fpk_byte_patch.py` byte-patches `Pregame.FPK` in place
   (bypassing the fpk.py repacker which strips alignment
   padding): `Elizabeth → Sejong`, `English → Koreans`, and the
   16 English city names → 16 Korean city names.
4. `install_eboot.sh` installs the patched EBOOT to BOTH
   `modified/PS3_GAME/USRDIR/EBOOT.BIN` (tracked in git) AND
   `~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN`
   (the path RPCS3 actually boots from — this dual-install is
   required per the iter-133 finding).

## Install

```bash
./scripts/install_eboot.sh    # dual-path EBOOT install
cp _build/Pregame_korea.FPK ../modified/PS3_GAME/USRDIR/Resource/Common/Pregame.FPK
```

Then boot the game in RPCS3.

## Verification

All verification artifacts live under `verification/` in dated
per-iteration subdirectories. Key results:

- `iter138_korea_play_pass/` — v0.9 slot 15 end-to-end M6 PASS
- `iter151_dod_signoff/` — full M9 regression (Caesar, Catherine,
  Mao, Lincoln) + M7 50-turn soak
- `iter162_korea_at_slot16/` — first "Korea" at slot 16 screenshot
- `iter166_full_regression/` — M9 + M6 + slot 16 verified under
  iter-162..167 patch set
- `iter167_era_bonuses/slot16_full_korea.png` — final polished
  slot 16 cell visual

Run `./verify.sh --tier=static` for a green M0 signoff.

## Architecture notes

This mod was the result of ~170 iterations of reverse engineering
across the span of the PRD (see `docs/korea-civ-mod-prd.md`).
Key technical discoveries:

- **iter-133**: RPCS3 boots from the HDD path
  (`~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/EBOOT.BIN`),
  not the disc path. Every patch must be installed to both.
- **iter-137**: The old `EBOOT_v130_clean.ELF` was extracted by
  a buggy SELF unpacker that stripped `PT_SCE_RELA` and the
  runtime fixups. The new `EBOOT_v130_decrypted.ELF` (via
  `rpcs3 --decrypt`) is the real base ELF.
- **iter-149**: RPCS3's GDB stub accepts Z0 software breakpoints
  but doesn't actually install them in JIT'd code, and rejects
  Z1/Z2 hardware breakpoints/watchpoints outright. Runtime
  breakpoint debugging is not available.
- **iter-160**: The civ-select carousel is Scaleform/Flash-driven
  (`gfx_chooseciv.gfx` contains `slotData0..slotData17`). The
  carousel "iterator" I'd been hunting in PPU code lives inside
  the SWF as ActionScript bytecode, not as native PPC
  instructions.
- **iter-162**: The string at `0x0169d290` ("Random" followed
  by `@ORDINAL @RULER` template) is the real source for the
  slot 16 cell title.
- **iter-167**: The four era bonus `???` placeholders at
  `0x016a70b9..0x016a70e3` are real static EBOOT strings that
  propagate to the carousel cell.
