# File Formats

## Map File (.map) — 1088 bytes

Used only by DLC maps. Built-in maps are procedurally generated (see [Map System](map-system.md)).

### Layout

| Offset | Size | Description |
|--------|------|-------------|
| 0x000 | 1024 | Tile data: 32x32 grid, 1 byte per tile, column-major order |
| 0x400 | 64 | Footer: all 0xFF bytes |

### Coordinate Transform

File stores tiles column-major. To convert to display (screen) coordinates:

```python
display = np.rot90(np.fliplr(file_grid), k=1)
# Equivalent: display[row][col] = file[col][row]
```

Ice border tiles occupy file columns 0-1 and 30-31, which map to display rows 0-1 and 30-31 (top/bottom poles).

### Tile Byte Encoding

```
Bit 7 (0x80): River south
Bit 6 (0x40): River east
Bit 5 (0x20): River west
Bit 4 (0x10): Spawn marker (multiplayer only — NOT used for single-player)
Bits 0-2:     Terrain type
```

Terrain types:

| Value | Terrain |
|-------|---------|
| 0 | Ocean |
| 1 | Grassland |
| 2 | Plains |
| 3 | Mountains |
| 4 | Forest |
| 5 | Desert |
| 6 | Hills |
| 7 | Ice |

River flags can be combined. Examples:
- `0x00` = Ocean, no rivers
- `0x01` = Grassland
- `0x61` = Grassland + river west + river east
- `0xE4` = Forest + all three river directions
- `0x17` = Ice (border tile)

---

## FPK Archive

Custom archive format for packaging game assets.

### Header

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 10 | Magic: `06 00 00 00 46 50 4B 5F 00 00` (contains "FPK_") |
| 0x0A | 4 | Item count (little-endian uint32) |

### Per-Entry Structure

| Field | Type | Description |
|-------|------|-------------|
| Name length | uint32 LE | Filename string length |
| Name | bytes | Filename (no null terminator) |
| Unknown | bytes | Metadata/padding |
| File size | uint32 LE | Size of file data |
| File offset | uint32 LE | Absolute offset to file data |

### Constraints

- Each file has a companion `.extradata` metadata blob
- **Adding new entries to an FPK crashes the game** — only replacement of existing entries works
- Duplicate entries are allowed (e.g. placeholder.txt appears multiple times)

---

## DDS Texture Formats (Map Rendering)

Each map has three pre-rendered textures used for 3D terrain visualization:

### Heights (`Map%d_Heights.dds`)

| Property | Value |
|----------|-------|
| Dimensions | 512x512 |
| Format | 16-bit luminance (R16, `DDPF_LUMINANCE`) |
| File size | 524,416 bytes |
| Purpose | Terrain mesh elevation |

Values are continuous 16-bit (40K+ unique values across 262K pixels). Ocean sits low (~0.15 normalized), mountains high (~0.80). This is purely a rendering texture — it does not encode game tile data.

### Lightmap (`Map%d_Lightmap.dds`)

| Property | Value |
|----------|-------|
| Dimensions | 4096x4096 |
| Format | DXT1 compressed RGB |
| File size | 8,388,736 bytes |
| Purpose | Pre-baked terrain lighting |

### Mountain/Hill Blends (`Map%d_MountainHill_Blends.dds`)

| Property | Value |
|----------|-------|
| Dimensions | 2048x2048 |
| Format | DXT1 compressed RGBA |
| File size | 2,097,280 bytes |
| Purpose | Terrain type blending at tile boundaries |

### Naming

- Built-in maps: `map<number>_heights.dds`, stored in Misc0 (1-149) and Misc1 (150-300)
- DLC maps: `map<name>_heights.dds`, stored in Pak9
- EBOOT references format strings: `Map%d_Heights.dds`, `Map%d_Lightmap.dds`, `Map%d_MountainHill_Blends.dds`, `Map%d_Normals.dds`

---

## Other Formats

| Extension | Format | Description |
|-----------|--------|-------------|
| .dds | DirectDraw Surface | Textures (various: DXT1, DXT5, R16, ARGB) |
| .gr2 | Granny 3D | Models and skeletal animations |
| .nif | NetImmerse/Gamebryo | Older 3D model format (lighting rigs) |
| .nxb | Unknown | Additional 3D data |
| .gfx / .swf | Scaleform | UI elements (Flash-based) |
| .xml | XML | Configuration, pedia data, effects |
| .csv | CSV | Tabular game data |
