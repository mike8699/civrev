# Map System

## Overview

CivRev 1 uses two distinct map systems:

1. **Built-in maps (277 maps)** — Procedurally generated at runtime from deterministic seeds. No tile data is stored on disc.
2. **DLC maps (4+ maps)** — Hand-crafted with explicit `.map` tile data files. See [DLC Map Packs](dlc-map-packs.md).

## Built-in Map Generation

### How It Works

1. A map number is selected from the **MapList** (see below)
2. The map number seeds a deterministic PRNG
3. The map generation function (`FUN_009d9ce0`, 4580 bytes) produces a 32x32 tile grid
4. Pre-rendered DDS textures for that map number are loaded from Misc0/Misc1 FPK archives for 3D rendering

Because the PRNG is deterministic (same seed = same output), every player gets the same map for a given map number. The DDS textures were pre-computed offline using the same seeds during development.

### MapList

Defined in `ccglobaldefines.xml`:

```
MapList = "1-4,6-6,8-12,14-18,20-27,29-33,35-53,55-65,67-81,83-87,
           89-93,95-114,116-123,125-129,131-136,138-147,149-159,
           162-211,213-225,227-254,256-264,266-295,297-300"
```

**277 valid map numbers** out of the range 1-300. The 23 gaps (5, 7, 13, 19, 28, 34, 54, 66, 82, 88, 94, 115, 124, 130, 137, 148, 160-161, 212, 226, 255, 265, 296) are seeds that likely produced unplayable or unbalanced maps during development and were removed.

### Map Selection

The function at `0x0002f96c` selects a map:
1. Loads the MapList string
2. Parses it into valid map numbers
3. Picks one via `(param % count) + 1`

### Seed System

The game uses three seeds (from debug string `"SEEDS syncrand=%d, game=%d, map=%d"`):

| Seed | Purpose |
|------|---------|
| syncrand | Synchronization random (multiplayer determinism) |
| game | Game session seed (AI behavior, events) |
| map | Map generation seed (terrain, rivers, spawns) |

A separate debug string reveals the full seed naming:
```
BAD RIVER STATE: ... Riverbits=%d, Tile X=%d, Y=%d, MapSeed=%d, GameSeed=%d, CivSeed=%d
```

### PRNG Algorithm

The RNG (`FUN_000317d0`) is the Microsoft Visual C++ linear congruential generator:

```
state = state * 214013 + 2531011
```

Constants: multiplier = `0x343FD` (214013), increment = `0x269EC3` (2531011).

The higher-level wrapper (`FUN_00031868`) converts to a bounded range:
```
result = (double)raw_state * scale_factor * max_value
```

### Map Types

Strings found in the EBOOT indicate these world type options:

- `CONTINENTS AND ISLANDS`
- `MOSTLY ISLANDS`
- `LARGE CONTINENT`
- `RANDOM WORLD TYPE`

Map size options: `NORMAL`, `LARGE`, `EXTRA-LARGE`

Climate options: `COLD`, `TEMPERATE`, `WARM`

### Generation Algorithm Summary

The function at `0x009d9ce0` (~600 lines of decompiled C) performs:

1. **Initialization** — Zeroes out terrain grid (0x28 = 40 bytes per row stride), river map, and scoring arrays
2. **Landmass placement** — Random walk using the PRNG, placing terrain types 0-7 on a 32x32 grid. Uses tile value `6` (hills) and `4` (forest) as default land, `7` (ice) for polar borders, `0` (ocean) for water
3. **Island cleanup** — Iterates neighbors (8-directional) to remove single-tile peninsulas and smooth coastlines. Checks bitmask patterns against adjacency to decide removal
4. **River generation** — Random walk algorithm starting from inland tiles, flowing toward ocean. Rivers are stored as directional bit flags (1=east, 2=south, 4=west, 8=north on the internal river map, later encoded as 0x20/0x40/0x80 in the .map format)
5. **Terrain type assignment** — Assigns final terrain types based on distance from coast, latitude (for climate), and randomization
6. **Spawn scoring** — Evaluates tiles for starting position quality using the `FUN_009ba798` scoring function. River-adjacent tiles score higher. The 0x20 flag is set on candidate spawn tiles.

### Pre-Rendered Textures

Each map number has three DDS textures pre-computed for 3D rendering:

| Texture | Resolution | Format | Size |
|---------|-----------|--------|------|
| `map<N>_heights.dds` | 512x512 | 16-bit luminance | 524 KB |
| `map<N>_lightmap.dds` | 4096x4096 | DXT1 | 8.4 MB |
| `map<N>_mountainhill_blends.dds` | 2048x2048 | DXT1 | 2.1 MB |

Total: ~11 MB per map, ~3 GB total for all 277 maps across Misc0 and Misc1 FPK archives.

These are visual-only — the actual gameplay tile grid is generated at runtime from the seed.

### Other Map Generation Strings

Found in the EBOOT data section, suggesting named phases of generation:

- `TotalIslands`
- `PrGenerateIslands`
- `PrAfterGenerateIslands`
- `WorldType`
- `Disable Terrain PreBuilts`
- `Load Terrain from preprocessed file`

The last two suggest a debug/development toggle between procedural generation and loading pre-built terrain data.
