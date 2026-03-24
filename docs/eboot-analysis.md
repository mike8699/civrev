# EBOOT Analysis

## Binary Details

| Property | Value |
|----------|-------|
| File | EBOOT.ELF |
| Size | 26 MB |
| Architecture | 64-bit PowerPC (PPU), big-endian |
| Linking | Statically linked |
| Symbols | Stripped (no function names) |
| Functions identified | 69,479 (via Ghidra) |
| Successfully decompiled | 69,183 (99.6%) |
| Failed to decompile | 73 |

All game logic is native C++ — there is no scripting layer, VM, or managed runtime.

## Key Functions

### Map Generation

| Address | Size | Description |
|---------|------|-------------|
| `0x009d9ce0` | 4,580 B | Main procedural map generation — terrain placement, river generation, island cleanup, spawn scoring |
| `0x009ba798` | — | Tile spawn quality scoring |
| `0x009ba6ec` | — | Tile evaluation / neighbor analysis |
| `0x009ba904` | — | Position scoring for spawn candidate ranking |
| `0x009c03c4` | — | Called during river generation phase; gate check before river placement begins |
| `0x009bffa4` | — | Map generation finalization |

### Map Loading

| Address | Size | Description |
|---------|------|-------------|
| `0x000d42fc` | — | DLC map loading entry point (map type 10) |
| `0x000d2cc4` | 344 B | LoadDLCMapFromXML — loads .map tile data from DLC pack |
| `0x000d2bb8` | — | Lower-level map data parser (called by LoadDLCMapFromXML) |
| `0x0002f96c` | 156 B | Map number selection — picks from MapList via `(seed % count) + 1` |
| `0x00031704` | 148 B | Alternative map selection using game RNG state |

### Game Initialization

| Address | Size | Description |
|---------|------|-------------|
| `0x001b77a8` | 2,460 B | Game world initialization — calls map generator, allocates tile arrays (0x400 = 1024 tile bytes, 0x440 = 1088 map size), creates subsystems |
| `0x00010830` | 16 B | Map generation trampoline — sets up TOC base, calls `0x009d9ce0` |

### Texture Loading

| Address | Size | Description |
|---------|------|-------------|
| `0x009a2b18` | 168 B | Lightmap texture load/unload (`Map%d_Lightmap.dds`) |
| `0x0013b7c8` | 1,532 B | Terrain texture resource loading — loads height maps, blend textures, terrain type textures in loop (0-14 terrain types) |
| `0x00594408` | 104 B | Resource loading coordinator using MapList |

### PRNG

| Address | Size | Description |
|---------|------|-------------|
| `0x000317d0` | 76 B | Core LCG: `state = state * 214013 + 2531011` (MSVC algorithm) |
| `0x0003181c` | 76 B | Float conversion: `(double)raw * scale` |
| `0x00031868` | 88 B | Bounded random: `(double)rng() * max_value` truncated to int |
| `0x009e5334` | 48 B | Game-level RNG wrapper — calls through global game state pointer |
| `0x000c60cc` | 40 B | `rand()`-style: `(rng() >> 16) & 0x7FFF` |

### Utility

| Address | Size | Description |
|---------|------|-------------|
| `0x009b5f80` | — | `memset` equivalent (fill buffer with value) |
| `0x009b64a0` | — | `memcpy` equivalent (copy buffer) |
| `0x009b4fc0` | — | Distance/magnitude calculation (used in map gen for placement scoring) |
| `0x00a20e88` | — | Bit population count (counts set bits, used for river adjacency scoring) |

## PRNG Details

The game uses the **Microsoft Visual C++ LCG** (Linear Congruential Generator):

```c
uint32_t next_state(uint32_t *state, uint32_t modulo) {
    *state = *state * 214013 + 2531011;  // 0x343FD, 0x269EC3
    if (modulo != 0) {
        *state = *state % modulo;
    }
    return *state;
}
```

The RNG state struct contains at least 3 fields:
- `[0]`: Current state value (the seed)
- `[1]`: Call counter (incremented each call)
- `[2]`: Modulo value (0 = no modulo)

Higher-level wrappers convert to float (0.0-1.0) or bounded integer ranges.

## Data Section Strings

Interesting strings found in the EBOOT data section (not function names — the binary is stripped):

### Map Generation
```
SEEDS syncrand=%d, game=%d, map=%d
BAD RIVER STATE: ... Riverbits=%d, Tile X=%d, Y=%d, MapSeed=%d, GameSeed=%d, CivSeed=%d
GameSeed
Set the random seed to any value. 0==Random
orig seed=
cur seed=
SEED
```

### Map Types
```
CONTINENTS AND ISLANDS
MOSTLY ISLANDS
LARGE CONTINENT
RANDOM WORLD TYPE
NORMAL
LARGE
EXTRA-LARGE
COLD
TEMPERATE
WARM
```

### Map System
```
MapList
WorldType
TotalIslands
PrGenerateIslands
PrAfterGenerateIslands
Disable Terrain PreBuilts
Load Terrain from preprocessed file
```

### Texture Loading
```
Map%d_Heights.dds
Map%d_Lightmap.dds
Map%d_MountainHill_Blends.dds
Map%d_Normals.dds
```

### Scenario
```
Disabled_in_this_scenario
Choose_Scenario
Play_Scenario
GFX_ScenarioScreen_gfx
```

## Memory Layout (Map Generation)

The map generation function at `0x009d9ce0` accesses several arrays via offsets from a base pointer (likely a game state struct). Key offsets identified:

| Offset | Purpose |
|--------|---------|
| `-0x1e54` | Terrain type array (32x32, stride 0x28 = 40 bytes per row) |
| `-0x1e74` | Tile attributes array (32x32, stride 0x50 = 80 bytes per row, 16-bit entries) |
| `-0x1e80` | Climate/biome zone array |
| `-0x1e84` | Terrain desirability lookup table |
| `-0x1e8c` | Pointer to map width |
| `-0x1e9c` | Pointer to map height |
| `-0x1e4c` | X-offset table for 8-directional neighbors |
| `-0x1e48` | Y-offset table for 8-directional neighbors |
| `-0x1ef8` | Tile visit counter array (for map gen random walk) |
| `-0x1c5c` | River bit flags array |
| `-0x1954` | Distance-from-coast array (for terrain assignment) |
| `-0x1f10` | Output/result pointer |

## Ghidra Project

Analysis was performed with Ghidra 11.0.3. The existing project contains full auto-analysis of the EBOOT.ELF. Bulk decompilation was done via Ghidra 11.3 headless mode using the `ExportDecompiledC.py` script, producing one `.c` file per function (69,183 files, ~304 MB total).
