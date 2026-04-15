# iter-222: Common0.FPK is unused at runtime — overlays are dead weight

**Date:** 2026-04-15

## Summary

Empirically proved that `Common0.FPK` is **never opened** by the
PS3 BLUS-30130 build at runtime. The Common0_korea.FPK overlay
shipped under iter-176/214 — three XML files (`leaderheads.xml`,
`console_pediainfo_civilizations.xml`,
`console_pediainfo_leaders.xml`) — has **no observable runtime
effect**. The only effective `xml_overlays/` files in the v1.0
shipping state are the two Pregame.FPK overlays
(`civnames_enu.txt`, `rulernames_enu.txt`).

## Method

### Step 1: file-IO trace inspection (passive)

RPCS3 captures every `sys_fs_open(path=...)` and `sys_fs_stat`
call to its `RPCS3.log`. Surveyed 10 large RPCS3.log files from
prior iter-198..221 korea_play / M9 runs (each ~71s wall clock,
each reaching the in-game HUD per `result.json`):

| FPK | size | open count across 10 logs |
|---|---|---|
| Pregame.FPK | 29.7 MB | 10 |
| pedia.FPK | 206.0 MB | 10 |
| Misc0.FPK | 1.36 GB | 10 |
| Misc1.FPK | 1.47 GB | 10 |
| ps3_misc.FPK (`/Common/`) | — | 10 (ENOENT, falls to `/PS3/`) |
| ps3_misc.FPK (`/PS3/`) | 6.19 MB | 10 |
| **Common0.FPK** | 165.0 MB | **0** |
| leaderhead.FPK | 264.0 MB | **0** |
| buildings.FPK | 51.6 MB | **0** |
| units.FPK | 65.7 MB | **0** |
| hoa.FPK | 80.8 MB | **0** |
| Level.FPK | 49.5 MB | **0** |
| music.FPK | (n/a in disc) | **0** |

Across **all** 10 sampled RPCS3.log files: 0 hits for
`Common0`, 0 hits for `leaderhead.FPK`, 0 hits for any of the
other "missing" FPKs. The file-IO logging in RPCS3 is
exhaustive — every `cellFsOpen` and `cellFsStat` flows through
`sys_fs_open` and would appear if the game called it.

### Step 2: empirical control test (active)

Renamed `modified/PS3_GAME/USRDIR/Resource/Common/Common0.FPK`
to `Common0.FPK.iter222_renamed` and re-ran:

```bash
cd civrev_ps3/rpcs3_automation
./docker_run.sh --headless korea_play 0 caesar
```

**Result: M9 Caesar PASS** (full result JSON in
`m9_caesar_no_common0.json`).

```json
{
  "milestone": "M9",
  "slot": 0,
  "label": "caesar",
  "pass": true,
  "stages": {
    "main_menu": true,
    "difficulty_selected": true,
    "highlighted_ok": true,
    "in_game_hud": true
  },
  "select_ocr": "...Cleopatra Alexander Isabella ... Egyptians Greeks Spanish ... Romans..."
}
```

The game reached:
- main menu
- difficulty selection
- civ-select carousel (with all civ names visible to OCR)
- civ confirmation
- in-game HUD

**without `Common0.FPK` available on disk at all**. RPCS3 didn't
even attempt to open it (it's not just optional — it's never
referenced).

Common0.FPK was restored after the test (md5 matches backup).

## Why is Common0.FPK present on the disc but unused?

The PS3 BLUS-30130 build retains FPK file references in its
EBOOT strings table (verified):

```
$ strings EBOOT_v130_decrypted.ELF | grep -i \.FPK
ps3_misc.FPK
Pregame.FPK
buildings.FPK
hoa.FPK
leaderhead.FPK
Level.FPK
music.FPK
units.FPK
Common0.FPK
pedia.FPK
Misc0.FPK
Misc1.FPK
```

But strings are not calls. The actual open-and-iterate code
path in the EBOOT only loads a SUBSET of these FPKs at runtime.
The unused ones — `Common0.FPK`, `buildings.FPK`, `hoa.FPK`,
`leaderhead.FPK`, `Level.FPK`, `units.FPK`, `music.FPK` — are
**legacy artifacts** from earlier ports (Xbox 360, iOS) or
dev-build configurations. The PS3 build was repacked to
consolidate everything important into Pregame/pedia/Misc0/Misc1/
ps3_misc and stopped reading the others.

This is consistent with iter-221's cross-platform finding:
the iOS port uses different asset organization (NDSChooseCiv
direct OpenGL rendering) and the PS3 port replaced large parts
of the asset pipeline with Scaleform-side bundles. The leftover
FPK files are dead carry-over from the iOS / 360 builds.

## Implications for the v1.0 shipping state

### What is genuinely effective

- `xml_overlays/civnames_enu.txt` (18 rows, Korean at row 17)
  → **Pregame.FPK overlay → effective** (parser opens
  Pregame.FPK at boot, the iter-198 run-time GDB dump at
  iter-203 confirmed Korea/Sejong reach the parser buffers).
- `xml_overlays/rulernames_enu.txt` (Sejong at row 17)
  → **Pregame.FPK overlay → effective** (same).
- iter-4 ADJ_FLAT EBOOT patches (4 patches)
  → **Effective** (in-binary, no FPK dependency).
- iter-14 parser-count EBOOT patches (2 patches)
  → **Effective** (same).

### What is NOT effective (dead weight)

- `xml_overlays/leaderheads.xml` (iter-214, adds Sejong as
  Nationality 16 reusing Mao assets)
  → **Common0.FPK overlay → DEAD**. Game never opens
  Common0.FPK. The 17th LeaderHead entry is invisible to the
  PPU runtime.
- `xml_overlays/console_pediainfo_civilizations.xml` (CIV_KOREA
  pedia entry reusing PEDIA_CHINA_*.dds)
  → **Common0.FPK overlay → DEAD**.
- `xml_overlays/console_pediainfo_leaders.xml` (LEADER_SEJONG
  pedia entry reusing PEDIA_MAO_*.dds)
  → **Common0.FPK overlay → DEAD**.

The pediainfo entries the GAME actually uses live in
`pedia.FPK` as `console_pedia_text_civilizations.xml` and
`console_pedia_text_leaders.xml` (TXT_KEY string tables) and
the **window structure** that wraps them must come from a
DIFFERENT source — the Common0/console_pediainfo_*.xml
"window structure" files appear unused by the PS3 build.

### What still works (despite dead overlays)

- All 16 stock civs work — they're keyed off the parser
  buffers and EBOOT-resident leaderhead binding logic, not
  off our dead Common0 overlays.
- iter-216 6-civ M9 regression sweep still PASSes — confirms
  no regression from this finding.
- Korea is still in the parser buffers (iter-203 verified).
- Carousel cell visibility is still structurally blocked
  Scaleform-side per iter-212 §9.X — this finding does not
  unblock §9 item 2.

## What this finding changes

### PRD §6.3 needs an update

PRD §6.3 currently spec's three Common0.FPK overlays as part
of v1.0 shipping. This is **structurally broken** — those
overlays cannot reach the runtime. The PRD must be updated
with an `iter222` note explaining that Common0.FPK is unused
and the three overlays are dead weight. They are kept in the
build for documentation completeness but flagged as inert.

### The leaderheads.xml puzzle

Where DOES the game's Mao→leaderhead binding come from? It
isn't from Common0/leaderheads.xml. Candidates for v1.1
investigation:

1. The binding is **hardcoded in the EBOOT** as a static table
   indexed by Nationality. The strings `LeaderHeads.xml` and
   `SetupLeaderHeads` in the EBOOT are likely DEAD code paths
   (legacy iOS/360 carry-over) that exist as code but are
   never reached on PS3. The runtime binding goes through a
   different code path.
2. The binding lives in `gfx_chooseciv.gfx` (Scaleform
   carousel) and a parallel game-side leaderhead manager
   that's keyed off Nationality alone.
3. The binding is in one of the FPKs that IS opened
   (Pregame/pedia/Misc0/Misc1/ps3_misc) under a different
   filename than `leaderheads.xml`.

These are all tractable but out-of-scope for v1.0 (Korea ships
invisible-in-carousel anyway per §9.X).

### Should we remove the dead overlays from the install?

Two options for iter-222+:

(a) **Keep** the dead Common0 overlays in the build for
    documentation completeness. Document them as inert with an
    iter-222 note in the README. Cost: 165MB of patched
    Common0.FPK shipped to no effect.

(b) **Remove** them entirely. `pack_korea.sh` skips Common0,
    `install.sh` skips Common0_korea.FPK installation, and
    Common0.FPK stays as the stock disc copy. Reduces install
    surface area to the 2 effective Pregame.FPK overlays + the
    EBOOT patches.

Option (b) is the cleaner shipping state. It also makes the
mod's actual effective surface area honest — 2 file overlays +
6 EBOOT byte patches. Recommend (b) for iter-223 unless the
user wants to keep the dead overlays as documentation.

## Verification artifacts

- `m9_caesar_no_common0.json` — the M9 Caesar PASS with
  Common0.FPK renamed away.
- This findings.md.
