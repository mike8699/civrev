# Binary Analysis

## Executable Details

| Property | Value |
|----------|-------|
| File | `CivIPAD` |
| Size | 3.4 MB |
| Format | Mach-O armv7 executable |
| Flags | NOUNDEFS, DYLDLINK, TWOLEVEL, BINDS_TO_WEAK, PIE |
| Linking | Dynamically linked |
| Functions (radare2) | 6,762 |
| Functions decompiled (Ghidra) | 5,454 (1 failed) |
| Strings | 49,894 total, 4,820 game-related |
| ObjC classes | 442 |
| Game-related functions | 1,517 |

## Architecture

All game logic is compiled into the single `CivIPAD` binary. There is no scripting layer, no managed runtime, no decompilable C# assemblies. The codebase is pure C++ with Objective-C for iOS platform integration.

### Codebase Origin: Nintendo DS

Class names retain the `NDS*` prefix from the Nintendo DS version:
- `NDSWorldScreen`, `NDSCombat`, `NDSCityScreen`, `NDSTechTree`
- `NDSRenderer`, `NDSTexture`, `NDSVRAMManager`
- `NDSTouchPad`, `NDSCellAnimation`

The DS-specific naming (NDS = Nintendo Dual Screen) persists throughout the entire codebase.

## Key Functions

### Game Core

| Address | Name | Blocks | Description |
|---------|------|--------|-------------|
| `0x0001ecd8` | `CivStrategy` | 1004 | Main AI strategy (largest function, ~151 KB) |
| `0x000338b0` | `AddTech` | 508 | Research/grant technology (~101 KB, 2nd largest) |
| `0x00036f7c` | `CaptureCity` | 223 | City capture logic |
| `0x0003bc40` | `DoCity` | 312 | City production processing |
| `0x00035c94` | `AddCity` | 115 | Create new city |
| `0x00034ebc` | `qCombat` | 316 | Combat execution |
| `0x00033000` | `qBeginTurn` | 220 | Turn begin processing |
| `0x00032e04` | `qDoTurn` | 209 | Turn processing |
| `0x0003a5a0` | `VictoryCheck` | 176 | Victory condition evaluation |
| `0x0002bf94` | `MakeCMap` | 153 | Procedural map generation |
| `0x0002bdbc` | `CivilizeStartLocs` | — | Civilization starting positions |
| `0x0003d3cc` | `ResetUnits` | 224 | Reset all units |
| `0x00034ac8` | `CombatAI` | 404 | Combat resolution AI |

### Map & Terrain

| Address | Name | Description |
|---------|------|-------------|
| `0x0002bf94` | `MakeCMap` | Procedural map generation using FRandom |
| `0x0002bdbc` | `CivilizeStartLocs` | Spawn location assignment |
| `0x001609a8` | `GenerateRandomMapping` | Custom map random seeding (Fisher-Yates) |
| `0x00160a28` | `LoadCustomMap` | Load custom map from file |
| `0x000f768` | `CcTerrain::CreateInstance` | Terrain system init (0xd55e0 bytes) |

### Random Number Generation

| Address | Name | Description |
|---------|------|-------------|
| `0x0000fc24` | `FRandom::Roll` | Core LCG PRNG |
| `0x0000d234` | `CcApp::SetRandomSeed` | Seeds both RandomA and RandomS |

### Save/Load

| Address | Name | Blocks | Description |
|---------|------|--------|-------------|
| — | `RWHeaderCiv` | 68 | Save/load header |
| — | `RWFileCiv` | 153 | Full game state save/load |
| — | `LoadGames` | — | Load saved game |
| — | `SaveGames` | — | Save game state |

### Unit & City Operations

| Address | Name | Description |
|---------|------|-------------|
| — | `AddCUnit` | Create unit |
| — | `DelCUnit` | Remove unit |
| — | `HealUnit` | Heal damaged unit |
| — | `ConvertUnit` | Unit type conversion |
| — | `UnitValue` | Evaluate unit strategic value |
| — | `UnitOrder` | Execute unit command |
| — | `DelCity` | Delete/capture city |
| — | `AbsorbCity` | City culture conversion |
| — | `CityValue` | Evaluate city strategic value |
| — | `CityDefender` | Assign city defender |

### Technology & Wonders

| Address | Name | Description |
|---------|------|-------------|
| `0x000338b0` | `AddTech` | Grant technology (508 blocks) |
| — | `HasTech` | Check if civ has technology |
| — | `ChooseATech` | AI tech selection |
| — | `AddWonder` | Build/grant wonder (105 blocks) |
| — | `CanWonder` | Check if wonder can be built |
| — | `NewExecuteWonder` | Execute wonder effect |

## PRNG Algorithm

The game uses the **Microsoft Visual C++ Linear Congruential Generator**, identical to the PS3 version:

```c
// FRandom::Roll @ 0xfc24
state = state * 214013 + 2531011;  // 0x343FD, 0x269EC3
result = state % param;            // bounded output
```

Two separate RNG instances are used:
- `RandomA` (PTR at 0x1fc0d8) — Game/AI randomization
- `RandomS` (PTR at 0x1fc0dc) — Synchronization

Both are seeded with the same value via `CcApp::SetRandomSeed`:
```c
// @ 0xd234
*(uint *)PTR__RandomA_001fc0d8 = seed;
*(uint *)PTR__RandomS_001fc0dc = seed;
_srand(seed);  // also seed C runtime
```

## Class Hierarchy

### ObjC / App Lifecycle
- `CivIPADAppDelegate` — iOS app delegate, game loop control
- `CivIPADViewController` — Main view controller
- `EAGLView` — OpenGL ES rendering surface
- `RootViewController` — Root UI controller

### Game Simulation (C++)
- `GameInstance` — Core game state singleton
- `City` — City data (0x101 bytes per city)
- `Unit` — Unit data (0x54 bytes per unit)
- `Tech` — Technology state (0x6a bytes)
- `Mission` — Objectives/victory tracking
- `Achievement` / `AchievementManager` — Achievement system (max 64)
- `LandMark` — Map landmarks
- `SpecialUnit` — Civilization-specific unique units
- `CombatPreview` — Pre-combat calculation
- `CustomMap` / `CustomMapInfo` — Custom map support
- `CivGameOptions` — Game settings

### Game UI (NDS-prefixed)
- `NDSWorldScreen` — Main game map
- `NDSCombat` — Combat visualization
- `NDSCityScreen` / `NDSCityReport` — City management
- `NDSTechTree` — Technology tree
- `NDSUnitScreen` — Unit info/orders
- `NDSDiplomacy` — Diplomacy interface
- `NDSGeneratorScreen` — Map generation settings
- `NDSMainMenu` / `NDSMainMenuScreen` — Main menu
- `NDSLoadGameScreen` / `NDSLoadSaveScreen` — Save/load
- `NDSScenarioScreen` — Scenario selection
- `NDSTutorialScreen` — Tutorial
- `NDSHistograph` — Historical timeline
- `NDSVictory` — Victory screen
- `NDSSpaceStation` — Space race victory
- `NDSNewGameScreen` / `NDSChooseCiv` / `NDSDifficultyScreen` — New game setup
- `NDSOverlay` — HUD overlay
- `NDSAdvisorMenu` — Advisor system
- `NDSGameOptions` / `NDSGameOptionsScreen` — Options
- `NDSCreditsScreen` — Credits
- `NDSReplay` — Game replay

### Firaxis Engine (F-classes)
- `FRandom` — PRNG (MSVC LCG)
- `FStringA` / `FStringW` — String handling
- `FTextSystem` / `FTextFile` / `FTextKey` — Localization
- `FFileIO` / `FDataStream` / `FMemoryStream` — File I/O
- `FIniParser` — INI file reader
- `FCache` — Generic caching
- `FLocaleInfo` — Locale handling
- `FCRC` — CRC checksums
- `FCriticalSection` — Threading
- `FGenderVariable` — Gendered text substitution

### Rendering
- `NDSRenderer` — Main renderer
- `NDSTexture` / `PVRTexture` / `Texture2D` — Texture management
- `NDSPalette` — Color palettes
- `NDSVRAMManager` / `NDSVRAMBlock` — Video memory
- `NDS3DObject` — 3D rendering
- `NDSCellAnimation` / `AnimationManager` — Animation
- `RSprite` — Sprite rendering
- `CcFont` — Bitmap font rendering

### Audio (Phono engine)
- `Phono::AudioManager` — Audio system
- `Phono::AudioPlayer` / `Phono::Sound` / `Phono::Sound3D` — Playback
- `Phono::AudioFile` / `Phono::AudioBuffer` — Audio data
- `Phono::AudioTag` / variants — Tagged audio effects
- `CcAudioNDS` — Platform audio bridge
- `SysSoundManager` — System sounds

### Multiplayer / Network
- `NDSWiFiScreen` / `NDSStagingScreen` — WiFi multiplayer
- `TurnBaseMode` / `TurnBasedGameMessage` — Game Center turn-based
- `GameCenter` / `GameCenterWrapper` — Game Center integration
- `NetProxy` / `NetCcMessage` — Network messaging
- `iCloudHandler` / `iCloudSaveDocument` — iCloud sync

### Setup & Configuration
- `CcApp` / `CcAppIphone` — App abstraction
- `CcSetupData` — Player/game setup (max 6 players)
- `CcLocalizer` — Localization
- `CcTerrain` — Terrain system (instance size: 0xd55e0 bytes)
- `CcTimer` / `CcTurnTimer` — Timing
- `GamePad` / `NDSTouchPad` — Input

## System API Usage

From imports analysis:

- **Graphics**: OpenGL ES (glLoadIdentity, glLoadMatrixf), Core Graphics (CGContextDrawImage, CGBitmapContextCreate)
- **Audio**: Audio Services, ExtAudioFile, AVAudioPlayer
- **Storage**: NSFileManager, NSKeyedArchiver, SQLite
- **Crypto**: CC_MD5, CC_SHA1 (CommonCrypto), Keychain
- **Network**: GameKit (GKTurnBasedMatch, GKLeaderboard, GKAchievement)
- **UI**: UIKit, custom OpenGL ES via EAGLView

## Ghidra Decompilation Output

- **315 .c files** organized by class/namespace
- **_all_functions.c**: 333,911 lines (11 MB) — complete decompilation in one file
- **_summary.txt**: Decompilation statistics
- Key files: `GameInstance.c`, `City.c`, `Unit.c`, `Tech.c`, `NDSCombat.c`, `CcTerrain.c`, `_global.c` (contains `MakeCMap`, `CivilizeStartLocs`)
