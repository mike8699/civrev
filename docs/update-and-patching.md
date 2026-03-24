# Update & Patching Mechanism

## Overview

CivRev 1 PS3 has a mandatory HDD install system and a patch/update mechanism that provides multiple vectors for modding game content.

## Mandatory HDD Install

On first launch, a `PS3InstallThread` copies FPK archives from the Blu-ray disc (`/dev_bdvd/PS3_GAME/USRDIR/`) to the PS3 hard drive. The game displays a `GFX_InstallOverlay.gfx` UI during this process. After installation, all asset loading happens from HDD, not disc.

Debug strings in the binary show the install phases:
```
STARTING PS3 INSTALL
***Prepping for install!
INSTALLING
***Post Install!
```

Error handling includes disc ejection detection, retry logic, and space checks:
```
PS3HDDCopy:  read fail due to disc ejection detected!
PS3InstallThread:  not enough space, exiting!
INSTALL:  failed copying file '%s' due to disc eject!  Retrying...
Content file '%s' is corrupted!  Recopying.
```

## v1.30 Update

The v1.30 update (APP_VER `01.30`, installed to `/dev_hdd0/game/BLUS30130/`) replaces a subset of game files and adds new content.

### Replaced FPK Archives

The update replaced 7 of the 12 FPK archives:

| Updated (on HDD) | Disc-only |
|-------------------|-----------|
| buildings.FPK | Misc0.FPK |
| Common0.FPK | Misc1.FPK |
| hoa.FPK | pedia.FPK |
| leaderhead.FPK | Pregame.FPK |
| Level.FPK | ps3_misc.FPK |
| music.FPK | |
| units.FPK | |

The update also replaced the EBOOT.BIN (26.8 MB vs 26.7 MB disc version).

### The `patch/` Directory

The update added a `patch/` subdirectory under `USRDIR/` containing loose files:

**New wonder assets** (added by v1.30):
- `Camelot.xml`, `Camelot_model.gr2`, `Camelot_DIFF.dds`, `Camelot_LIGHT.dds`, `Camelot_NORM.dds`, `Camelot_SREF.dds`
- `Sphinx.xml`, `Sphinx_model.gr2`, `Sphinx_DIFF.dds`, `Sphinx_LIGHT.dds`, `Sphinx_NORM.dds`, `Sphinx_SREF.dds`

**Updated UI** (Scaleform .gfx files):
- `GFX_MainMenuPS3.gfx`, `GFX_GameSelector.gfx`, `GFX_ScenarioScreen.gfx`
- `GFX_StagingScreen.gfx`, `GFX_MPGameType.gfx`, `GFX_Leaderboards.gfx`
- `GFX_ErrorOverlayCompressed.gfx`

**Updated localization**:
- `pstr_DEU.STR`, `pstr_ESP.STR`, `pstr_FRA.STR`, `pstr_ITA.STR`

## Loose File Override Mechanism

The Firaxis engine's resource loader checks for **loose files in `patch/`** before looking inside FPK archives. When loading an asset named `foo.xml`, the engine:

1. Checks if `patch/foo.xml` exists (via `cellFsStat`)
2. If found, loads the loose file
3. If not found, loads from the relevant FPK archive

This is proven by the Camelot and Sphinx wonder assets: their `.xml`, `.gr2`, and `.dds` files exist only as loose files in `patch/` and are not present in any FPK archive, yet the game loads and renders them correctly.

The override applies to any asset type the engine loads by name: `.xml`, `.dds`, `.gr2`, `.gfx`, `.nif`, and likely others.

## DLC System

### DLC Detection

DLC availability is checked via bitmask flags from a virtual method call (`vtable + 0x1d8`):

| Bit | Pack | Map Slot Range |
|-----|------|---------------|
| 0x001 | Mythic Pack | 0x15-0x18 (4 maps) |
| 0x010 | Iconic Pack | 0x19-0x1C (4 maps) |
| 0x100 | Eternal Pack | 0x1D-0x20 (4 maps) |

The game tracks 5 custom map slot counters: `CUSTOMMAP00COUNT` through `CUSTOMMAP04COUNT`.

### DLC Packaging

DLC is distributed as `.edat` containers (PS3 DRM-wrapped files). License `.rap` files in the user's `exdata/` directory authorize access:

```
UP1001-BLUS30130_00-SMCIVREVOLUTDLC4.rap  (Iconic Pack?)
UP1001-BLUS30130_00-SMCIVREVOLUTDLC7.rap  (Eternal Pack?)
UP1001-BLUS30130_00-SMCIVREVOLUTDLC9.rap  (Terrestrial Pack)
```

The content ID prefix is `UP1001-BLUS30130_00`. DLC pack names (Pak1, Pak9, etc.) are NOT hardcoded as strings in the EBOOT — they are discovered dynamically at runtime, likely by scanning the DLC directory.

### DLC Content Validation

The game validates DLC content integrity and re-copies from the install source if corruption is detected:
```
Content file '%s' is corrupted!  Recopying.
PS3CopyContentFiles:  cellFsUtime failed with error code %d!
This save game cannot be loaded due to unavailable or corrupt downloaded content.
```

## Modding Vectors (Tested)

### 1. Binary-Patching Disc FPK Archives (confirmed working)

The most reliable approach. Binary-patch values directly in FPK files on the extracted disc image. This preserves exact file size and internal structure.

**Confirmed by test**: Binary-patching `Pregame.FPK` on the disc image to change water color hex values (`#477EB6` → `#FF0000`, etc.) successfully changed in-game water rendering. All five water/fog color constants were confirmed to take effect.

The disc image must be extracted (not an ISO) for RPCS3 to load modified files. The game disc path in RPCS3 is configured via `~/.config/rpcs3/games.yml`.

**Key detail — PB (Pre-Built) overrides**: DLC/pre-built maps use separate `PB*` constants (e.g. `PBDeepWaterColor`, `PBShallowWaterColor`) that override the regular values. Both sets must be patched to affect all map types.

### 2. Loose File Override via `patch/` (limited)

The v1.30 update added a `patch/` directory under the HDD install's `USRDIR/` with loose files that override FPK-packed assets. This works for the Firaxis asset/resource system (3D models, textures, UI).

**Known working**: `.xml` (asset definitions), `.dds` (textures), `.gr2` (3D models), `.gfx` (Scaleform UI), `.STR` (localization) — proven by the Camelot/Sphinx wonder assets shipping this way in the v1.30 update.

**Does NOT work for**: `ccglobaldefines.xml` and other early-init config files loaded directly from FPK archives before the resource system initializes.

### 3. FPK Replacement on Disc (confirmed working)

Replace an entire FPK archive on the extracted disc image. The repacker (`fpk.py repack`) can rebuild FPK files from extracted directories, though minor size differences from repacking may occur. Binary patching (vector #1) is preferred when only changing existing values.

Constraint: the FPK must contain the same entries (adding new entries crashes the game).

### 4. EBOOT Replacement (untested)

RPCS3 can load decrypted ELF executables. A binary-patched EBOOT.ELF placed in the disc image enables code-level modifications: changing the spawn algorithm, adding new map loading code, modifying game constants in code, etc.

### 5. DLC Injection (untested)

Custom `.edat` packages can potentially be placed in the DLC directory. On RPCS3, DRM enforcement may be relaxed, allowing custom DLC content without valid signatures.

## PS3 Filesystem Paths

| Path | Purpose |
|------|---------|
| `/dev_bdvd/PS3_GAME/USRDIR/` | Blu-ray disc game data (read-only on real PS3) |
| `/dev_hdd0/game/BLUS30130/USRDIR/` | HDD install + update (overlays disc) |
| `/dev_hdd0/game/BLUS30130/USRDIR/patch/` | Loose asset overrides (resource system only) |
| `/dev_hdd0/home/00000001/exdata/` | DLC license (.rap) and data (.edat) files |

On RPCS3, the disc path maps to an extracted folder configured in `games.yml`. The HDD path maps to `~/.config/rpcs3/dev_hdd0/`.

## Disc Image Structure

The extracted disc image (mapped as `/dev_bdvd/`) has FPK archives under subdirectories:

```
PS3_GAME/USRDIR/
  EBOOT.BIN
  Resource/
    Common/           ← most FPK archives (Pregame, Common0, Level, etc.)
      Art/            ← additional art assets
    PS3/              ← platform-specific (music.FPK, ps3_misc.FPK)
```

## Loading Priority

```
1. HDD update EBOOT.BIN     (takes precedence over disc EBOOT)
2. HDD USRDIR/*.FPK         (update-replaced archives)
3. HDD USRDIR/patch/*       (loose asset overrides, resource system only)
4. Disc Resource/Common/*.FPK  (disc-only archives like Pregame, Misc0, Misc1)
5. Disc Resource/PS3/*.FPK     (platform-specific disc archives)
```

The mandatory HDD install copies some FPK archives from disc to HDD. The v1.30 update then replaces those HDD copies. Disc-only FPKs (Pregame, Misc0, Misc1, pedia, ps3_misc) are always read from the disc image.
