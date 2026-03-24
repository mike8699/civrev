# App Bundle Structure

## Overview

The IPA is a standard iOS application archive (ZIP). All game content lives in a flat `CivIPAD.app/` bundle with minimal subdirectory hierarchy.

- **IPA size**: 185 MB (2,948 files)
- **App bundle**: 254 MB uncompressed (2,940 files)
- **File dates**: Sep 14, 2013

## Directory Layout

```
Payload/CivIPAD.app/
├── CivIPAD                    # Main executable (3.4 MB, Mach-O armv7)
├── Info.plist                 # App metadata (binary plist)
├── Entitlement.plist          # Code signing entitlements
├── PkgInfo                    # Package type identifier
├── _CodeSignature/            # Code signing data
│   ├── CodeResources
│   └── ResourceRules
├── en.lproj/                  # PlayHaven localization nibs
├── NewAmb/                    # 165 ambient/music audio files (.aif)
├── Vox/                       # 361 voice acting audio files (.aif)
├── *.nib                      # Interface Builder UI files (10 total)
├── *.png                      # Textures, sprites, UI (1,078 files)
├── *.pvr                      # PowerVR GPU-compressed textures (611 files)
├── *.aif                      # Audio effects (1,098 total incl. subdirs)
├── *.txt                      # Game data, localization (58 files)
├── *.ini                      # Animation/config files (37 files)
├── *.inl                      # C++ source headers - Firaxis engine (17 files)
├── *.civscen                  # Scenario save files (5 files)
├── *.STR                      # Compiled string tables (5 files)
├── *.json                     # Ad SDK config (3 files)
└── *.xml                      # Audio depot config (1 file)
```

## File Type Summary

| Type | Count | Description |
|------|-------|-------------|
| `.aif` | 1,098 | Audio: music, SFX, voice acting (AIFF format) |
| `.png` | 1,078 | Textures: UI, sprites, leader portraits, map thumbnails |
| `.pvr` | 611 | PowerVR compressed textures (iOS GPU-native) |
| `.txt` | 58 | Game data, localization text, config |
| `.ini` | 37 | Unit animation configs, game settings, text system |
| `.inl` | 17 | Firaxis C++ engine source (shipped accidentally) |
| `.nib` | 10 | Interface Builder compiled UI layouts |
| `.civscen` | 5 | Scenario save files |
| `.STR` | 5 | Compiled binary string tables (per language) |
| `.json` | 3 | PlayHaven ad SDK configuration |
| `.xml` | 1 | Audio depot manifest |
| `.plist` | 3 | App metadata / entitlements |

## Game Data Files

### Localization (5 languages: EN, DE, ES, FR, IT)

| Pattern | Contents |
|---------|----------|
| `CityNames_*.txt` | City names per civilization |
| `CivNames_*.txt` | Civilization display names |
| `FamousNames_*.txt` | Great people names |
| `LandmarkNames_*.txt` | River/mountain/landmark names per civ |
| `RulerNames_*.txt` | Leader names |
| `TechNames_*.txt` | Technology names |
| `UnitNames_*.txt` | Unit + army names |
| `WonderNames_*.txt` | Wonder names (full + short) |
| `Text.ini` | Master text system with variable substitution rules |
| `str_*.STR` | Compiled binary string tables (DEU, ESP, FRA, ITA, JPN) |

Note: Japanese has a compiled `.STR` file but no `.txt` data files.

### Scenario Configuration

| File | Purpose |
|------|---------|
| `Scenario.txt` | Full scenario options (6 pages: General, Victory, Resource, Technologies, Barbarians, Combat) |
| `CustomScenario.txt` | Reduced option set for custom games |
| `TurnBaseScenario.txt` | Turn-based multiplayer options (adds Map Size, Production Rate, Fog of War, Turn Limit) |
| `CustomTurnBaseScenario.txt` | Custom turn-based variant |
| `map_config.ini` | Registers 5 custom maps |
| `*.civscen` | Scenario save data (Earth, Rivalry_2P, Squadron_4P, TwistedIsle_2P, Cabinet_4P) |

### Animation Configuration

37 `.ini` files define frame-by-frame animation data for units:
- `Animation*F.ini` — Unit movement/idle frame sequences (Archer, Armor, Artillery, Barbarian, Battleship, etc.)
- `Animation*F_fx.ini` — Combat VFX frame data
- `fortest.ini` — Master sprite animation definitions for all units and decorative objects (Fish, Whale, Seagull, water tiles)

### Audio

- `AudioDepot.xml` — Master audio manifest with two player channels: `NewAmb` (ambient/music) and `Vox` (voice)
- Era-specific tracks: Ancient, Medieval, Industrial, Modern (Calm/Agitated/Combat/Wonder)
- Per-civilization themes: 16 civilizations x full + short variants
- Leader voice lines: Alarmed, Friendly, Mad, Neutral, Condescend moods

### Shipped C++ Source (.inl files)

17 Firaxis Games C++ template headers (copyright 2007), accidentally included in the build:

| File | Purpose |
|------|---------|
| `FCache.inl` | Generic template cache |
| `FDataStream.inl` | Binary data serialization |
| `FFileIO.inl` | File I/O abstraction |
| `FIOBuffer.inl` / `Async` / `Sync` | Buffered I/O variants |
| `FLocale.inl` | Localization/locale system |
| `FMemoryStream.inl` | Memory stream operations |
| `FStringA.inl` / `FStringW.inl` | ASCII and wide string classes |
| `FStringArray.inl` / `FStringTable.inl` | String collections |
| `FTextFile.inl` / `FTextKey.inl` / `FTextSystem.inl` | Text/localization engine |
| `FCriticalSection.inl` | Threading primitives |
| `FFileErrorHandler.inl` | Error handling |

### Third-Party SDKs

- **PlayHaven**: Ad/promotion SDK (`content-*.json`, `PH*` classes, `PublisherContentViewController.nib`)
- **Localytics**: Analytics SDK (`LocalyticsSession`, `LocalyticsDatabase`)
- **SBJson**: JSON parsing library
- **TinyXML**: XML parsing
- **SDURLCache**: URL caching

### Interface Builder NIBs

| File | Purpose |
|------|---------|
| `MainWindow.nib` | Main window |
| `CivIPADViewController.nib` | Primary game view |
| `StoreFront.nib` | In-app purchase UI |
| `URLLoaderViewController.nib` | Web content loading |
| `PublisherContentViewController.nib` | PlayHaven ad display |
| `PublisherIAPTrackingViewController.nib` | IAP tracking |
| `PublisherOpenViewController.nib` | PlayHaven session |
| `ExampleViewController.nib` | Likely dev leftover |

## Comparison with CivRev 2 Android

| Aspect | CivRev 1 iOS | CivRev 2 Android |
|--------|-------------|------------------|
| Asset format | Flat bundle (PNG/PVR/AIF) | Unity asset bundles (hash-named) |
| Textures | PNG + PVR (PowerVR) | DDS + Unity serialized |
| Audio | AIFF | WAV + Unity audio |
| Config | INI + TXT + XML | INI + XML (in `GameSrc/civrev1_ipad_u4/data/rom/`) |
| UI | Native NIB + OpenGL ES | NGUI framework |
| Scenarios | `.civscen` (same format) | `.civscen` (same format) |
| Languages | 5 (EN, DE, ES, FR, IT) + JPN binary | 8 (added JPN, KOR, RUS) |
| Map config | `map_config.ini` (identical structure) | `map_config.ini` (identical structure) |
