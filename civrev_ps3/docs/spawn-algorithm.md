# Spawn Algorithm

## Overview

Civilization starting positions (settler placement) are determined by the native C++ code in the EBOOT. The algorithm differs between procedurally generated maps and DLC maps.

## Key Finding: River Flags Are Required

**The single-player spawn algorithm requires river flags (0x20/0x40/0x80) on land tiles to function correctly.**

- Without any river flags on land tiles, settlers spawn on ice (the algorithm fails to find a valid position and falls through to border tiles)
- The 0x10 bit (spawn marker) does NOT control single-player spawns — it is only used for multiplayer predetermined spawn points
- This was proven experimentally: moving/removing 0x10 flags had no effect on single-player placement, but removing all river flags caused spawns to break

## Spawn Algorithm Location

| Address | Function | Purpose |
|---------|----------|---------|
| `0x009d9ce0` | `FUN_009d9ce0` | Main map generation including spawn scoring (procedural maps) |
| `0x009ba798` | `FUN_009ba798` | Tile spawn quality scoring function |
| `0x009ba6ec` | `FUN_009ba6ec` | Tile evaluation helper (neighbor analysis) |
| `0x009ba904` | `FUN_009ba904` | Position scoring for spawn candidate ranking |
| `0x000d42fc` | `FUN_000d42fc` | DLC map loading entry point |
| `0x000d2cc4` | `FUN_000d2cc4` | LoadDLCMapFromXML |

## How Spawn Scoring Works

Within the map generation function (`0x009d9ce0`), spawn position scoring happens in the final phase:

1. **Candidate identification** — The algorithm iterates all non-edge tiles (skipping 2-tile border on each side) looking for suitable land tiles
2. **River adjacency check** — Tiles with river flags in the river map (`0x1c5c` offset array) score significantly higher. The `FUN_00a20e88` function counts river bits (using `popcount`-like logic on byte `0x10`), and tiles with 2+ adjacent river segments get prioritized
3. **Neighbor analysis** — For each candidate, 8 neighbors are checked. The algorithm counts how many neighbors share the same terrain type, weighted by cardinal (N/S/E/W) vs diagonal adjacency
4. **Scoring thresholds** — A tile needs 4+ matching neighbors (adjusted by terrain desirability) to qualify. Tiles meeting this threshold are passed to `FUN_009ba798` for final scoring
5. **0x20 flag placement** — Qualifying tiles get the 0x20 flag set in the tile attribute array (`0x1e74` offset), marking them as spawn candidates for the game's settler placement logic

## Terrain Desirability for Spawning

From the decompiled scoring logic:

- Grassland and plains tiles score highest (food + production potential)
- Forest tiles score moderately (production bonus)
- Hill tiles score lower but acceptable
- Desert and mountain tiles are generally avoided
- Ocean and ice tiles are invalid

## DLC Map Spawning

For DLC maps (map type 10), the loading flow is:

```
Map type 10 detected
  → FUN_000d42fc (DLC entry point)
    → FUN_000d2cc4 (LoadDLCMapFromXML)
      → Parses .map file tile data
      → Applies same spawn scoring algorithm to loaded tiles
```

The same spawn scoring logic runs on the loaded tile data, so DLC maps must also have river flags on land tiles for spawns to work correctly.

## Minimum Requirements for Custom Maps

For a custom .map file to produce valid spawn positions:

1. **Varied terrain** — Need sufficient non-ocean, non-ice, non-mountain land tiles
2. **River flags on land** — At least some land tiles must have river flags (0x20, 0x40, 0x80). The specific direction doesn't matter much; what matters is that the flags exist for the scoring algorithm to detect
3. **Contiguous landmasses** — Spawns need enough neighboring land tiles (4+) of similar terrain
4. **Avoid edge tiles** — The algorithm skips the 2-tile border on each side of the 32x32 grid
