# Map System

Analysis of map generation, terrain encoding, and custom map loading from Ghidra decompilation.

## Overview

The iOS version uses the same map system as the PS3 version:
- **Procedural maps**: Deterministic generation from seed via PRNG
- **Custom maps**: Hand-crafted `.civscen` scenario files
- **Map grid**: 32x32 tiles (0x20 stride in memory, 0x400 = 1024 bytes total tile data)

## PRNG Algorithm

Identical to the PS3 version — **Microsoft Visual C++ LCG**:

```c
// FRandom::Roll @ 0xfc24
state = state * 214013 + 2531011;   // multiplier: 0x343FD, addend: 0x269EC3
result = state % param;              // bounded to [0, param)
```

Two RNG instances seeded identically via `CcApp::SetRandomSeed` (0xd234):
- `RandomA` (at PTR 0x1fc0d8) — Game/AI randomization
- `RandomS` (at PTR 0x1fc0dc) — Sync randomization

Also seeds C runtime via `_srand(seed)`.

This is the same PRNG as the PS3 EBOOT (constants 0x343FD and 0x269EC3 confirmed in decompiled FRandom.c).

## Procedural Map Generation

### MakeCMap (@ 0x2bf94)

The `MakeCMap` function (153 basic blocks) generates the 32x32 terrain grid:

1. **Initialization** — Zero terrain arrays
2. **Continent placement** — Uses `FRandom::Roll()` to place landmasses, calls `DoContinents()` to validate layout
3. **Terrain assignment** — Based on zone type parameters:
   - `DAT_0021076c`: Continent/zone type (-1, 0, 1, 2)
   - `DAT_00210768`: Climate/temperature zone (-1, 1)
4. **River generation** — Random walk with bit flags:
   - `0x1` = east, `0x2` = south, `0x8` = north, `0x20`/`0x40`/`0x80` = directional variants
5. **Spawn scoring** — Evaluates tile quality for starting positions

The 0x20 byte stride per row is visible throughout the decompiled code: `puVar[index * 0x20]`.

### CivilizeStartLocs (@ 0x2bdbc)

Assigns starting positions to civilizations:
- Uses `DAT_00252410` and `DAT_00252428` arrays for player start X/Y coordinates
- References TeamMap data (`PTR__TeamMap_001fc0ec`)
- Analyzes terrain around candidate positions using 8-direction neighbor checks
- Same approach as PS3: river-adjacent tiles score higher

## Terrain Encoding

From map generation analysis and fortest.ini sprite data:

| Value | Terrain | Notes |
|-------|---------|-------|
| 0 | Ocean | Water tile |
| 1 | Grassland | High food |
| 2 | Plains | Balanced food/production |
| 3 | Mountains | High production, impassable |
| 4 | Forest | Production bonus |
| 5 | Desert | Low resources |
| 6 | Hills | Defense bonus, moderate production |
| 7 | Ice | Impassable (map borders) |

### River Bit Flags

River data stored separately from terrain type, using directional bit flags:
- `0x1` = River east
- `0x2` = River south
- `0x8` = River north
- `0x20`, `0x40`, `0x80` = Additional directional variants

These match the PS3 encoding pattern where bits 5-7 (0x20/0x40/0x80) encode river direction in the tile byte.

### Spawn Placement

From the PS3 analysis (confirmed applicable here via shared PRNG and algorithm):
- **River flags are REQUIRED** for single-player spawn placement
- Without river flags on land tiles, settlers spawn on ice (algorithm fails)
- The 0x10 bit is multiplayer-only spawn marker, NOT used for single-player
- Tiles need 4+ matching terrain neighbors to qualify as spawn candidates

## Custom Maps

### map_config.ini

Registers 5 custom maps:

```ini
[custom_map0]
FILE_NAME=Earth.civscen
MAP_TITLE=The World
MAP_PIC=Earth_thumbview
MAP_DESCRIPTION=Take on the globe in this new standardized map.
PLAYER=4
```

### .civscen Format

Scenario save files containing full game state:
- `Earth.civscen` — 91 KB (4 players)
- `Rivalry_2P.civscen` — 36 KB (2 players)
- `Squadron_4P.civscen` — 91 KB (4 players)
- `TwistedIsle_2P.civscen` — 36 KB (2 players)
- `Cabinet_4P.civscen` — 91 KB (4 players)

These are the same `.civscen` format used in CivRev 2 Android, with identical `map_config.ini` structure.

### Custom Map Loading

From CustomMap.c decompilation:

1. **`LoadCustomMap`** (@ 0x160a28) — Reads custom map data from file
2. **`ConvertBasicTerrain1/2`** — Converts terrain data with 0x20 stride per row
3. **`ConvertRiver`** — Processes river flag data
4. **`GenerateRandomMapping`** (@ 0x1609a8) — Fisher-Yates shuffle for random position mapping with retry logic (max 10 attempts per position)

### CustomMapInfo Loading

`CustomMapInfo.c` reads `map_config.ini`:
- Singleton pattern via `GetInstance()` (@ 0x16131c)
- Parses INI groups indexed `[custom_map0]` through `[custom_mapN]`
- Stores as `MapElement` structures with name and metadata

## Rendering

Unlike the PS3 version (which uses pre-rendered DDS textures for each map seed), the iOS version uses:
- **PVR textures** (PowerVR compressed) for terrain tiles
- **PNG sprites** for units, UI, and overlays
- **Sprite-based rendering** via `NDSRenderer`, `RSprite`, `NDSCellAnimation`

Terrain sprites from CcTerrain.c:
- 3 water sprites (offsets 0x3550-0x355c)
- 13 terrain sprites (offsets 0x355c-0x3590)
- Additional: rivers/lakes (0x3590), roads (0x3594), overlays (0x3598)

## Map Types

From scenario configuration:

| Setting | Options |
|---------|---------|
| Map Size (turn-based) | Big, Medium, Small |
| World Climate | Freezing, Cold, Standard, Warm, Hot |

The PS3 version's map type strings ("CONTINENTS AND ISLANDS", "MOSTLY ISLANDS", "LARGE CONTINENT", "RANDOM WORLD TYPE") and size options ("NORMAL", "LARGE", "EXTRA-LARGE") may not all be present in the iOS version, which appears to have a simpler generator UI.

## Comparison with PS3 Map System

| Aspect | PS3 | iOS |
|--------|-----|-----|
| PRNG | MSVC LCG (0x343FD, 0x269EC3) | Same |
| Map grid | 32x32 | 32x32 |
| Tile byte | 8-bit (terrain + river flags) | Same encoding |
| Generation function | `FUN_009d9ce0` (4,580 bytes) | `MakeCMap` @ 0x2bf94 (smaller) |
| Spawn scoring | River-flag dependent | Same algorithm |
| Pre-rendered textures | DDS (Heights/Lightmap/Blends per seed) | None (sprite-based rendering) |
| Custom map format | `.map` (1,088 bytes) + DDS textures | `.civscen` (scenario saves) |
| Map seeds (built-in) | 277 valid from MapList | TBD (not yet confirmed) |
