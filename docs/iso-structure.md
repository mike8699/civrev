# ISO Structure

The PS3 disc image contains the executable and game assets packaged in FPK archives.

## Executable

- **EBOOT.ELF** (decrypted) / **EBOOT.BIN** (encrypted) — 26 MB
- 64-bit PowerPC (PPU), big-endian, statically linked, stripped
- Contains all game logic (C++ native code, no scripting layer)
- ~69,479 functions identified via Ghidra analysis

## FPK Archives

Assets are packaged in `.FPK` archives (see [File Formats](file-formats.md) for the binary format).

| Archive | Contents |
|---------|----------|
| Common0.FPK | General assets: audio (.wav, .mp3), textures (.dds), 3D models (.nif, .gr2, .nxb), configs (.xml, .csv, .json), UI (.gfx, .swf). ~4800 files, 159 MB |
| Pregame.FPK | Game configuration: ccglobaldefines.xml (master constants), audio configs, visual effect definitions, bloom profiles |
| Level.FPK | In-game textures and 3D models (~53 MB): terrain tiles, building textures, unit textures, UI elements. Formats: .dds (textures), .gr2 (Granny 3D models/animations) |
| Misc0.FPK | Pre-rendered map textures for built-in maps 1-149 (3 DDS files per map) |
| Misc1.FPK | Pre-rendered map textures for built-in maps 150-300 (3 DDS files per map) |
| buildings.FPK | Building model/texture assets |
| units.FPK | Unit model/texture assets |
| leaderhead.FPK | Leader portrait 3D models and textures |
| pedia.FPK | Civilopedia encyclopedia data — XML files covering buildings, units, concepts, leaders, resources, techs, terrains, wonders |
| hoa.FPK | Hall of Achievements — trophy room models and leaderhead display configs |

## Pregame Configuration

`ccglobaldefines.xml` (442 lines) is the master configuration file containing all tunable game constants as typed name/value pairs. See [Game Constants](game-constants.md) for the full breakdown.

## Civilopedia Data

The pedia archive contains structured XML data for every game object:

- `console_pediainfo_*.xml` — Stats, requirements, and mechanical data
- `console_pedia_text_*.xml` — Display text and flavor descriptions
- `console_pedia_structure.xml` / `console_pedia_objects.xml` — UI organization

Categories: Buildings, Civilizations, Concepts, Governments, GreatPeople, Leaders, Resources, Techs, Terrains, Units, Wonders.

## DLC

DLC map packs are distributed as `.edat` containers wrapping FPK archives. See [DLC Map Packs](dlc-map-packs.md).
