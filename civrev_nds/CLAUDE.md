# Civilization Revolution NDS - ROM Investigation

### Read First
Don't modify or delete the original ROM file when working on this.

## Detailed Documentation

See `docs/` for in-depth analysis:
- [docs/README.md](docs/README.md) — Overview and document index
- [docs/rom-structure.md](docs/rom-structure.md) — NDS ROM layout, filesystem, asset formats
- [docs/binary-analysis.md](docs/binary-analysis.md) — ARM9 executable analysis, Firaxis engine classes
- [docs/game-constants.md](docs/game-constants.md) — Civilizations, units, techs, wonders, differences from iOS/PS3

## Overview

- **Game**: Sid Meier's Civilization Revolution (NDS)
- **Developer**: Firaxis Games / 2K Games
- **Platform**: Nintendo DS (ARM9 + ARM7)
- **Engine**: Native C++ (Firaxis custom engine)
- **ROM**: `civrev.nds` (64 MB, game code "YS6P54")
- **ARM9 binary**: 1.6 MB (decompressed from ROM)
- **Data files**: 2,796 files (45 MB) in NDS filesystem
- **Version**: 103780 (from Version.Txt)
- **Extracted dir**: `../NDS_UNPACK/` (extracted via `extract_nds.py`)

## Architecture: Origin of the iOS/Android Lineage

The PS3/Xbox 360 version (June 2008) was the first CivRev release. The NDS version (November 2008) was a separate handheld port built on the same Firaxis engine. Both share `F*` engine classes, identical PRNG, and the same game rules, but have different rendering pipelines and binary structure.

The NDS version is significant because the **iOS iPad port was built directly from this NDS codebase** — all `NDS*`-prefixed class names in the iOS binary (`NDSWorldScreen`, `NDSCombat`, `NDSTechTree`, etc.) originate here, not from the PS3 version.

### Codebase Lineage
```
Shared Firaxis engine (F* classes, PRNG, game rules)
  ├─> CivRev PS3/Xbox 360 (June 2008) — console version, 26 MB binary
  └─> CivRev NDS (Nov 2008) — handheld port, 1.6 MB ARM9
        └─> CivRev iOS/iPad (~2009-2013) — direct port of NDS code, NDS* prefix retained
              └─> CivRev 2 Android (2014) — Unity wrapper around iOS codebase
```

### Key Difference from iOS
| | NDS | iOS |
|---|---|---|
| ARM9 binary | 1.6 MB | 3.4 MB (CivIPAD Mach-O) |
| Architecture | ARMv4T (ARM9, 32-bit) | ARMv7 (32-bit) |
| Overlays | 17 code overlays (hot-swapped) | Single binary |
| Graphics | NDS hardware sprites (NBFC/NBFP/NBFS) | PNG + PVR |
| Audio | SDAT (NDS native) | AIFF |
| Display | 256x192 dual screen | iPad resolution |
| Wonders | 21 | 41 (iOS added 20 more) |
| Unique units | 63 (no Bowman, Camel Archer, Chu-Ko-Nu, etc.) | 70 |
| Multiplayer | NDS WiFi/Wireless | Game Center turn-based |
| Text.ini | Identical format | Identical format |

## NDS-Specific Formats

| Extension | Count | Description |
|-----------|-------|-------------|
| `.nbfs` | 763 | NDS bitmap frame sprite (pixel data) |
| `.nbfc` | 763 | NDS bitmap frame cell (sprite layout) |
| `.nbfp` | 759 | NDS bitmap frame palette |
| `.NCLR` | 105 | Nitro Color Resource (palette) |
| `.NCGR` | 105 | Nitro Character Graphic Resource (tiles) |
| `.NCER` | 105 | Nitro Cell Resource (sprite cells) |
| `.NANR` | 105 | Nitro Animation Resource |
| `.ntft` | 18 | Nitro texture data |
| `.ntfp` | 18 | Nitro texture palette |
| `.nftr` | 1 | Nitro font resource |
| `.nsbmd` | 1 | Nitro 3D model |
| `.sdat` | 1 | NDS sound data archive (23 MB) |
| `.STR` | 4 | Compiled string tables (DEU, ESP, FRA, ITA) |
| `.txt` | 45 | Localization text + config |

## Game Data

### Localization (5 languages: EN, DE, ES, FR, IT)
Same file naming as iOS: `CityNames_*.txt`, `CivNames_*.txt`, `UnitNames_*.txt`, etc.

### Civilizations (16 + Barbarians) — Identical to iOS
Romans, Egyptians, Greeks, Spanish, Germans, Russians, Chinese, Americans, Japanese, French, Indians, Arabs, Aztecs, Zulu, Mongols, English, Barbarians

### Leaders (17) — Identical to iOS
Caesar, Cleopatra, Alexander, Isabella, Bismarck, Catherine, Mao, Lincoln, Tokugawa, Napoleon, Gandhi, Saladin, Montezuma, Shaka, Genghis Khan, Elizabeth, Grey Wolf

### Technologies (47) — Identical to iOS/PS3
Same tech tree from Alphabet through Future Technology.

### Wonders (21) — Subset of iOS (41)
Great Pyramid, Great Wall, Hanging Gardens of Babylon, Stonehenge, Colossus of Rhodes, Oracle of Delphi, Great Library of Alexandria, East India Company, Oxford University, Shakespeare's Theatre, Himeji Samurai Castle, Leonardo's Workshop, Magna Carta, Trade Fair of Troyes, Military-Industrial Complex, Hollywood, Internet, Apollo Program, Manhattan Project, United Nations, World Bank

Note: NDS uses full names ("Hanging Gardens of Babylon", "Great Library of Alexandria", "Shakespeare's Theatre", "Military-Industrial Complex") where iOS shortened them.

### Units (63) — Fewer than iOS (70)
Same base units, but NDS has slightly different naming:
- "Modern Infantry" (NDS) vs "Infantry" (iOS)
- "Jaguar Warrior" (NDS) vs "Jaguar" (iOS)
- "Ashigaru Pikemen" (NDS) vs "Ashigaru" (iOS)
- "Longbow Archer" / "Crossbow Archer" (NDS) vs "Longbow" / "Crossbow" (iOS)
- "Cossack Horseman" / "Samurai Knight" (NDS) — more descriptive names
- NDS is missing: Bowman, Camel Archer, Chu-Ko-Nu, War-Chariot, French Cannon, War Elephant (added in iOS)

## Firaxis Engine Classes (confirmed in ARM9 strings)

Same engine as iOS with NDS-specific platform layer:
- `CcAppNDS` (vs `CcAppIphone` on iOS)
- `CcTimerNDS`
- `NDSPresentation`, `NDSCardCallback`
- `FINetLobbyNDS`, `FLNetLobbyNDS`, `FNetAccessNDS` — NDS WiFi networking
- `FNetPlayerNDS`, `FNetProfileNDS`, `FNetSessionNDS` — Multiplayer
- All `F*` Firaxis engine classes present: `FDataStream`, `FTextSystem`, `FStringA`, `FStringArray`, `FStringTable`, `FIOBuffer`, `FIOBufferSync`, `FMemoryStream`, `FMemoryStreamRLE`, `FFileIO`, `FIniParser`, `FTextFile`, `FTextKey`, `FCache`, `FLocaleInfo`, `FCRC`, `FCriticalSection`, `FGenderVariable`

## PRNG

Same MSVC LCG algorithm confirmed via strings:
- `"orig seed="`, `"cur seed="`, `"Random Map"`
- `"7NetSeed"`, `"14NetRequestSeed"`, `"Synch Err: Seed"`

Constants 0x343FD and 0x269EC3 expected in ARM9 binary (same as PS3 and iOS).

## Key Investigation Tools

- **ROM extraction**: `extract_nds.py` (ndspy library) — already extracted to `../NDS_UNPACK/`
- **Binary analysis**: Ghidra (ARM:LE:32:v4t processor for ARM9)
- **radare2**: Function listing and quick analysis
- **NDS graphics**: Tinke, Nitro Explorer, or custom scripts for NBFC/NBFP/NBFS/NCLR/NCGR/NCER/NANR
- **NDS audio**: VGMTrans or NDSEditor for SDAT extraction

## Notes

- The ROM is exactly 64 MB (67,108,864 bytes) — standard NDS maximum
- Game code "YS6P54" — "YS6P" is the game ID, "54" is the maker code (2K Games)
- ARM9 binary is BLZ-compressed in the ROM; `extract_nds.py` decompresses it
- 17 overlays provide code hot-swapping (screen-specific code loaded on demand)
- The `dwc/utility.bin` file is the Nintendo Wi-Fi Connection utility library
- Building sprites use era+culture naming: `BLDG_00_anc_afr` = building 0, ancient era, African style
- All localization text files are identical format to iOS (direct copy during port)
