# Civilization Revolution 1 - Technical Documentation

Reverse-engineering findings for Sid Meier's Civilization Revolution (PS3).

## Contents

| Document | Description |
|----------|-------------|
| [ISO Structure](iso-structure.md) | PS3 disc layout, FPK archives, asset organization |
| [File Formats](file-formats.md) | .map tile format, FPK archive format, DDS texture specs |
| [Map System](map-system.md) | Built-in map generation, seeds, MapList, pre-rendered textures |
| [Spawn Algorithm](spawn-algorithm.md) | How starting positions are determined, river flag requirement |
| [Game Constants](game-constants.md) | All values from ccglobaldefines.xml |
| [EBOOT Analysis](eboot-analysis.md) | Decompiled functions, key addresses, RNG, native code architecture |
| [DLC Map Packs](dlc-map-packs.md) | DLC structure, constraints, dlcscenariodata format |
| [Update & Patching](update-and-patching.md) | v1.30 update mechanism, patch/ directory, DLC system, modding vectors |

## Game Identity

- **Title**: Sid Meier's Civilization Revolution
- **Product Code**: BLUS-30130 (US)
- **Developer**: Firaxis Games / 2K Games
- **Platform**: PS3 (Cell PPU), also Xbox 360
- **Executable**: EBOOT.ELF — 26 MB, 64-bit PowerPC big-endian, statically linked, stripped
- **Notable**: Debug strings left in binary include a Firaxis developer's email address in a river state bug report template
