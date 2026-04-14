# Korea Civilization Mod for PS3 Civilization Revolution (v0.9)

Adds Korea (leader: Sejong) to Sid Meier's Civilization Revolution
(BLUS-30130) on PS3. Currently ships as a **replacement mod**: Korea
takes slot 15 of the civ-select screen, overwriting England's name
strings. The underlying civ data (portrait, bonuses, unique units)
still comes from England — only the display strings are Korean.

## Current release: v0.9

**What works**
- Civ-select screen renders `Sejong / Koreans` at slot 15 in place
  of `Elizabeth / English`.
- Selecting the slot loads a normal single-player game as Korea.
- 50-turn end-turn soak runs cleanly (tested 4000 BC → 900 BC,
  multiple cities founded, no crashes).
- Founded cities use Korean names (Seoul, Pyongyang, Gyeongju,
  Kaesong, Incheon, Daegu, Cheongju, Jeju, Ulsan, Suwon, Gimpo,
  Chuncheon, Naju, Kunsan, Gangneung, Iksan) instead of the stock
  English set (London, York, Nottingham, ...).
- All 15 other stock civs remain at their original slots and work
  normally (Mao/China regression-tested; Russians implicit via the
  original test_map.py flow).
- Reversible via `.orig` backups written on first install.

**What's not yet implemented**
- Korea as the **17th** civ (the PRD §9 DoD calls for this).
  See `docs/ncv-references.md` for the blocker details — a boot-
  time pair-init loop between civnames/rulernames hits an out-of-
  bounds write at slot 17 and corrupts RSX, requiring live Ghidra
  XREF or GDB work we couldn't do statically.
- Korea-specific civ bonuses, unique unit, or AI personality.
- Korean-language strings (text is English only; Korean
  localization could be added through a similar byte patcher).

## Requirements

- Clean BLUS-30130 v1.30 EBOOT.ELF extracted to
  `civrev_ps3/EBOOT_v130_clean.ELF`.
- Stock `Common0.FPK` and `Pregame.FPK` from the game disc.
- Extracted source trees at `civrev_ps3/extracted/Common0/` and
  `civrev_ps3/extracted/Pregame/` (used by build.sh as the staging
  source for Common0 overlay repacking).
- RPCS3 for testing, or a real PS3 with a patched disc/EBOOT.

## Build

```bash
cd civrev_ps3/korea_mod
./build.sh     # produces _build/EBOOT_korea.ELF + _build/Common0_korea.FPK + _build/Pregame_korea.FPK
./verify.sh --tier=static   # runs M0 (xmllint + FPK content round-trip + eboot dry-run)
```

Build steps:
1. `xml_overlays/*.xml` are validated and staged.
2. `eboot_patches.py` applies 6 patches to EBOOT_v130_clean.ELF:
   two `li r5, 0x11 → 0x12` parser-count bumps (iter-14, for the
   deferred 17-slot extension), a 17-entry ADJ_FLAT relocation,
   and 2 TOC redirects (iter-4). All six patches are harmless
   no-ops on v0.9's shipping path — the civnames/rulernames files
   still have 17 entries so the parser stops at EOF regardless,
   and the new ADJ_FLAT table is loaded by nothing live.
3. `pack_korea.sh`:
   - Repacks `extracted/Common0/` + the XML overlays into
     `Common0_korea.FPK` via `fpk.py`.
   - Runs `fpk_byte_patch.py` against the stock `Pregame.FPK` to
     produce `Pregame_korea.FPK` with 18 byte-level edits:
     `rulernames_enu.txt` slot 15 `Elizabeth` → `Sejong   `,
     `civnames_enu.txt` slot 15 `English` → `Koreans`, and 16
     city-name replacements in `citynames_enu.txt`'s ENGLISH block
     (London → Seoul, York → Naju, ..., Birmingham → Chuncheon).
     Every patch preserves exact byte length by padding Korean
     names with trailing spaces (the name parser trims them before
     display). This preserves Pregame.FPK's internal alignment
     padding byte-for-byte (fpk.py's repack path is unsafe for
     content edits in Pregame — iter-7 proved it).

## Install

```bash
cd civrev_ps3/korea_mod
./install.sh
```

Stages the built artifacts into
`civrev_ps3/modified/PS3_GAME/USRDIR/Resource/Common/` (replacing
Common0.FPK and Pregame.FPK) and
`civrev_ps3/modified/PS3_GAME/USRDIR/EBOOT.BIN`. First install
writes `.orig` backups of each overwritten file next to itself.

To uninstall, restore the `.orig` files:
```bash
for f in civrev_ps3/modified/PS3_GAME/USRDIR/Resource/Common/*.orig civrev_ps3/modified/PS3_GAME/USRDIR/*.orig; do
  mv "$f" "${f%.orig}"
done
```

## Test in RPCS3 (docker harness)

```bash
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play     # M6: select Korea, reach in-game HUD
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_soak     # M7: 50-turn end-turn soak
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea          # M2: sweep civ-select for Sejong/Koreans
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play 0 caesar     # M9: regress Caesar (slot 0)
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play 5 catherine  # M9: regress Catherine (slot 5)
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play 6 mao        # M9: regress Mao (slot 6)
civrev_ps3/rpcs3_automation/docker_run.sh --headless korea_play 7 lincoln    # M9: regress Lincoln (slot 7)
```

All result JSONs land under
`civrev_ps3/rpcs3_automation/output/korea_*_result.json`; durable
verification artifacts are committed to
`civrev_ps3/korea_mod/verification/`.

## Verification state (v0.9)

| Milestone | Status | Evidence |
|---|---|---|
| M0 static | green | `verify.sh --tier=static`; xmllint + FPK round-trip (~9632 file content checks) + eboot dry-run + M0e committed-artifact pass-flag scan (13 result.json files) |
| M1 boot | green | `verification/M1/ingame_spawn_screenshot.png` |
| M2 civ-select | green | `verification/M2_iter8/slot15_sejong_koreans_final.png` |
| M3 post-select | green | implicit through M6/M7 |
| M4 `_NCIV==17` | N/A | v0.9 doesn't bump the civ count |
| M5 civ-table[16] | N/A | v0.9 reuses slot 15 |
| M6 in-game start | green | `verification/M6/in_game_settlers.png` |
| M7 50-turn soak | green | `verification/M7/turn50_900bc.png` |
| M9 stock regression | green | All four PRD-required samples under `verification/M9/`: Caesar slot 0, Catherine slot 5, Mao slot 6, Lincoln slot 7 — each with `<name>_result.json` + civ-select + in-game screenshots |

§9 DoD: 4 of 5 items met (1 is the 17-slot blocker).

## Repository layout

```
korea_mod/
  README.md                  # (this file)
  build.sh                   # validate → patch → pack
  install.sh                 # stage into civrev_ps3/modified/...
  verify.sh                  # run verification tiers
  pack_korea.sh              # Common0 repack + Pregame byte-patch
  eboot_patches.py           # EBOOT binary patcher (dry-run + apply)
  scripts/ghidra_helpers/    # Jython post-scripts for headless Ghidra
  fpk_byte_patch.py          # in-place Pregame.FPK byte-level patcher
  addresses.py               # confirmed EBOOT addresses (from §5 RE)
  xml_overlays/
    console_pediainfo_civilizations.xml     # CIV_KOREA civilopedia entry (dead in v0.9 replacement mode)
    console_pediainfo_leaders.xml           # LEADER_SEJONG civilopedia entry (dead in v0.9)
  docs/
    civ-record-layout.md     # §5.2 RE notes
    ncv-references.md        # §5.1 / 17-slot blocker analysis
  verification/              # committed JSON result files + screenshots
  _build/                    # gitignored build outputs
```

## Known blocker for §9 DoD compliance

The true 17-slot extension (Korea as a proper 17th civ, not a
replacement for England) is gated on a boot-time pair-init loop
between `civnames_enu.txt` and `rulernames_enu.txt` that writes to
a downstream per-civ table at the new slot 17 and OOBs it. Five
iterations (iter-7, iter-10, iter-11, iter-12) of static analysis
failed to locate the parser / pair-init function without access to
Ghidra UI XREFs or RPCS3 GDB stub debugging.

Next steps for a human or better-equipped agent:
1. Open `civrev_ps3/ghidra/civrev.gpr` in the Ghidra UI.
2. XREF the strings at `0x16ee550` (`RulerNames_`) and `0x16ee560`
   (`CivNames_`) to find the name-file parser.
3. Trace into the parser's consumer to find the pair-init loop.
4. Identify the 17-wide downstream table and bump its count.
5. Extend civnames/rulernames and civ-select cursor bound.

Detailed notes in `docs/ncv-references.md` and
`verification/M2_iter12/summary.md`.
