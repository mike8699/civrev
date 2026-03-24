# ROM Structure

## NDS ROM Header

| Field | Value |
|-------|-------|
| Game title | `CIVREV` |
| Game code | `YS6P` |
| Maker code | `54` (2K Games) |
| Format | Nintendo DS ROM image (decrypted) |
| Total size | 64 MB (67,108,864 bytes) — NDS maximum |

## Binary Components

### ARM9 (Main CPU)

| Property | Value |
|----------|-------|
| Raw size | Compressed in ROM (BLZ) |
| Decompressed | 1.6 MB (`arm9_original.bin`) |
| Header | 16 KB (`arm9_header.bin`, first 0x4000 bytes) |
| Architecture | ARMv4T (ARM9TDMI), 32-bit, little-endian |
| Purpose | All game logic, rendering, I/O |

The ARM9 binary contains the entire game engine: Firaxis `F*` classes, `NDS*` UI classes, `Cc*` platform layer, game simulation, AI, combat, map generation.

### ARM7 (Sub CPU)

Not extracted separately. The ARM7 handles sound, WiFi, touchscreen, and RTC on the DS. It's a smaller binary embedded in the ROM.

### Overlays (17 total)

Code overlays are loaded/unloaded at runtime to work within NDS RAM constraints (4 MB main RAM):

| Overlay | Size | Purpose (estimated) |
|---------|------|---------------------|
| overlay_0000 | 32 B | Stub/placeholder |
| overlay_0001 | 9 KB | |
| overlay_0002 | 6.4 KB | |
| overlay_0003 | 6.9 KB | |
| overlay_0004 | 6.4 KB | |
| overlay_0005 | 9.6 KB | |
| overlay_0006 | 9.9 KB | |
| overlay_0007 | 3.3 KB | |
| overlay_0008 | 7.9 KB | |
| overlay_0009 | 6.4 KB | |
| overlay_0010 | 6.9 KB | |
| overlay_0011 | 5.6 KB | |
| overlay_0012 | 13.4 KB | |
| overlay_0013 | 6.3 KB | |
| overlay_0014 | 76.1 KB | Largest — likely main game screen |
| overlay_0015 | 31.1 KB | Second largest — possibly combat or city screen |
| overlay_0016 | 18.9 KB | |
| overlay_0017 | 0 B | Empty (created by extract_nds.py) |

Total overlay code: ~225 KB. Combined with the 1.6 MB ARM9, total game code is ~1.8 MB.

## Filesystem Layout

```
data/
├── advisors/              # Advisor portrait sprites
├── audio/
│   └── CIV_sound_data.sdat  # All game audio (23 MB, NDS SDAT format)
├── dwc/
│   └── utility.bin        # Nintendo Wi-Fi Connection library
├── font/
│   ├── Arial14.nftr       # Nitro font resource
│   └── FontPalette.nbfp   # Font color palette
├── interface/             # UI screen sprites
│   ├── AdvisorScreen/     # Advisor backgrounds (per leader)
│   ├── CityScreen/        # City management UI
│   ├── CombatScreen/      # Combat display UI
│   ├── Credits/           # Credits screen
│   ├── Eras/              # Era transition graphics
│   ├── GameReplay/        # Replay screen
│   ├── GameScreen/        # Main game HUD
│   ├── GibbonScreen/      # Edward Gibbon historical quotes
│   ├── Histograph/        # Historical graph/timeline
│   ├── LeaderPics/        # Leader selection portraits
│   ├── LogoScreen/        # 2K/Firaxis logos
│   ├── MainMenu/          # Title/main menu
│   ├── OptionsScreen/     # Options/settings
│   ├── ReportScreen/      # Reports UI
│   ├── Resources/         # Shared UI resources
│   ├── SpaceShip/         # Space race victory graphics
│   ├── TechTree/          # Technology tree UI
│   ├── TerrainBackdrops/  # Terrain background images
│   ├── Wifi/              # WiFi multiplayer UI
│   └── Wireless/          # Local wireless UI
├── leaders/               # Leader animated sprites (17 leaders x 4 files)
├── Localization/          # Text data (5 languages + string tables)
│   ├── CityNames_*.txt
│   ├── CivNames_*.txt
│   ├── FamousNames_*.txt
│   ├── LandmarkNames_*.txt
│   ├── RulerNames_*.txt
│   ├── TechNames_*.txt
│   ├── UnitNames_*.txt
│   ├── WonderNames_*.txt
│   ├── Text.ini           # Master text system config
│   ├── Credits_*.txt
│   └── str_*.STR          # Compiled string tables (DEU, ESP, FRA, ITA)
├── structures/
│   ├── buildings/         # Building sprites (era x culture variants)
│   ├── cities/            # City sprites + nav view
│   └── wonders/           # Wonder sprites (21 wonders)
├── terrain/
│   ├── 3dtilesets/        # Terrain tile textures (ntft/ntfp)
│   └── Borders/           # Border/territory markers
├── title/
│   └── CivLOGO_DS.*      # DS title screen logo
├── units/
│   ├── Combat/            # Unit combat animation sprites (NANR/NCER/NCGR/NCLR)
│   └── Poses/             # Unit idle/move sprites (nbfc/nbfp/nbfs)
└── Version.Txt            # Build version: 103780
```

## File Type Summary

| Extension | Count | Description |
|-----------|-------|-------------|
| `.nbfs` | 763 | Bitmap frame sprite — raw pixel data for 2D sprites |
| `.nbfc` | 763 | Bitmap frame cell — cell/OAM layout defining sprite regions |
| `.nbfp` | 759 | Bitmap frame palette — 256-color palette for sprites |
| `.NCLR` | 105 | Nitro Color Resource — animation palette data |
| `.NCGR` | 105 | Nitro Character Graphic Resource — animation tile data |
| `.NCER` | 105 | Nitro Cell Resource — animation cell definitions |
| `.NANR` | 105 | Nitro Animation Resource — animation sequence data |
| `.txt` | 45 | Localization text, credits, config |
| `.ntft` | 18 | Nitro texture format data (terrain tiles) |
| `.ntfp` | 18 | Nitro texture format palette |
| `.STR` | 4 | Compiled binary string tables (per language) |
| `.nftr` | 1 | Nitro font resource (Arial 14pt) |
| `.nsbmd` | 1 | Nitro 3D model (possibly terrain/water) |
| `.sdat` | 1 | NDS sound data archive (23 MB, contains all music/SFX) |
| `.bin` | 1 | Nintendo DWC utility library |
| `.ini` | 1 | Text.ini localization config |
| `.Txt` | 1 | Version.Txt |

**Total**: 2,796 files, 45 MB

## NDS Sprite Format (.nbfc/.nbfp/.nbfs)

The game uses a custom Firaxis sprite format (not standard Nitro):
- `.nbfs` — Raw pixel data (bitmap frame sprite)
- `.nbfc` — Cell/region definitions (bitmap frame cell)
- `.nbfp` — 256-color palette data (bitmap frame palette)

Each unit/building/UI element consists of this triplet. Example:
- `Archer.nbfs` + `Archer.nbfc` + `Archer.nbfp` = Archer unit sprite

## Nitro Animation Format (.NANR/.NCER/.NCGR/.NCLR)

Standard Nintendo DS animation resources used for combat animations and leader portraits:
- `.NANR` — Animation sequence definitions (frame timing, loops)
- `.NCER` — Cell definitions (sprite sub-regions within tile data)
- `.NCGR` — Character/tile graphic data
- `.NCLR` — Color palette

Combat units have both regular and `_FX` variants (e.g., `Archer.NANR` + `Archer_FX.NANR`).

## Audio (SDAT)

`CIV_sound_data.sdat` (23 MB) contains all game audio in NDS SDAT format:
- Sequence data (SSEQ) — Music tracks
- Wave archives (SWAR) — Sound effect samples
- Bank data (SBNK) — Instrument definitions

Can be extracted with VGMTrans, NDSEditor, or custom SDAT parsers.

## Building Asset Naming Convention

Buildings use an era+culture naming scheme:
```
BLDG_{index}_{era}_{culture}[_SM]
```

| Component | Values |
|-----------|--------|
| index | 00-07+ (building type) |
| era | `anc` (ancient), `med` (medieval), `ind` (industrial), `mod` (modern) |
| culture | `afr` (African), `asi` (Asian), `eur` (European), `med` (Mediterranean) |
| suffix | `_SM` = small/zoomed-out variant |

## Comparison with iOS App Bundle

| Aspect | NDS | iOS |
|--------|-----|-----|
| Sprites | NBFC/NBFP/NBFS (custom) | PNG + PVR |
| Animations | NANR/NCER/NCGR/NCLR (Nitro) | PNG sprite sheets + INI |
| Textures | NTFT/NTFP (Nitro texture) | PNG + PVR |
| Audio | SDAT (NDS native, 23 MB) | AIFF files (loose, ~50 MB) |
| Font | NFTR (Nitro font) | System + bitmap fonts |
| 3D models | NSBMD (1 file) | None (pure 2D on iOS) |
| Localization | Identical .txt format | Identical .txt format |
| Text.ini | Identical | Identical |
| String tables | 4 languages (DE/ES/FR/IT) | 5 (+ JPN) |
