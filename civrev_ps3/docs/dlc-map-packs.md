# DLC Map Packs

## Overview

DLC maps are the only maps with explicit `.map` tile data files. They are hand-crafted maps that cannot be reproduced from seeds, unlike the 277 built-in procedural maps.

The DLC is distributed as an `.edat` container wrapping an FPK archive.

## Known DLC Maps (Pak9 — "Terrestrial Pack")

| Map | File | Description |
|-----|------|-------------|
| The World | `the_world.map` | Earth — global conquest |
| Equal Opportunity | `equal_opportunity.map` | Balanced starting positions |
| South Pacific | `south_pacific.map` | Archipelago (NZ, Australia, Indonesia) |
| The United Kingdom | `the_uk.map` | Regional (England, Ireland, Scotland, Wales) |

## Files Per Map

Each DLC map requires:

| File | Size | Format |
|------|------|--------|
| `<name>.map` | 1,088 bytes | Tile data (see [File Formats](file-formats.md)) |
| `map<name>_heights.dds` | 524,416 bytes | 512x512, 16-bit luminance heightmap |
| `map<name>_lightmap.dds` | 8,388,736 bytes | 4096x4096, DXT1 compressed |
| `map<name>_mountainhill_blends.dds` | 2,097,280 bytes | 2048x2048, DXT1 compressed |

Each file also requires a companion `.extradata` file (copy from an existing one when creating new maps).

## DLC Registration (dlcscenariodata5.xml)

Maps are registered with the game via this XML config file.

**Critical encoding requirements:**
- **ISO-8859-1** encoding (NOT UTF-8 — corruption breaks the game)
- **CRLF** line endings (Windows-style)

Each map entry specifies:
- Unique numeric ID
- Entry type: `PACK_MPMAPS2`
- Multi-language title and description (EN, DE, ES, FR, IT)
- Display parameters (thumbnail reference, layout position)

## FPK Packing

Maps are packed into an FPK archive. An `ordering.json` file lists all files that should be included.

**Critical constraint: You cannot add new entries to an FPK.** The game crashes if the FPK contains entries it doesn't expect. You can only **replace** existing map data within the existing entry slots.

This means to add a custom map, you must overwrite one of the 4 existing DLC maps.

## Loading Flow

When the game loads a DLC map (map type 10):

```
Map type 10 detected
  → 0x000d42fc  (DLC entry point)
    → 0x000d2cc4 (LoadDLCMapFromXML)
      → Reads "Corrupt Game Options" validation string
      → Loads map file path and scenario file path
      → Branches on param_1 == 0 for different file paths
      → 0x000d2bb8 (parse map data from loaded file)
```

The loaded tile data is then processed by the same spawn scoring algorithm used for procedural maps. See [Spawn Algorithm](spawn-algorithm.md).

## Creating Custom Maps

### Requirements

1. **Tile data** — Create a valid 1088-byte `.map` file with:
   - Varied terrain types (not just ocean)
   - River flags (0x20/0x40/0x80) on land tiles near intended spawn areas
   - Ice borders on the outer 2 columns/rows
   - At least enough contiguous land for the number of players

2. **Rendering textures** — Generate matching DDS files:
   - Heights: 512x512 16-bit, terrain elevation mapping (ocean ~0.15, mountains ~0.80)
   - Lightmap: 4096x4096 DXT1, pre-baked lighting
   - Blends: 2048x2048 DXT1, terrain transition blending

3. **Extradata** — Copy `.extradata` companion files from existing maps

4. **Replace, don't add** — Overwrite an existing map slot in the FPK

5. **Preserve XML encoding** — If editing dlcscenariodata5.xml, maintain ISO-8859-1 + CRLF

### Testing

Test custom maps using the RPCS3 PS3 emulator:
- Docker container with `--memory=8g --shm-size=2g` (prevents OOM kills)
- VNC at `localhost:5900` for visual monitoring
