# Civilization Revolution 2 - Android APK/OBB Investigation

### Read First
Don't modify or delete original obb or apk files when working on this.

## Overview

- **Game**: Civilization Revolution 2 (com.t2kgames.civrev2) v1.4.4
- **Engine**: Unity 4.5.3f3 (Mono scripting backend)
- **Platform**: Android (armeabi / armeabi-v7a)
- **APK**: `Civilization-Revolution-2-v1-4-4.apk` (25 MB, 447 files)
- **OBB**: `main.19.com.t2kgames.civrev2.obb` (429 MB, 7282 files when extracted)
- **Extracted OBB dir**: `main.19.com.t2kgames.civrev2/` (1.2 GB uncompressed, gitignored)

## APK Structure

### Native Libraries (`lib/`)
- `libunity.so` - Unity engine runtime (~10.5 MB)
- `libmono.so` - Mono runtime (~3.7 MB)
- `libTkNativeDll.so` - 2K Games native plugin (~1.4 MB) - custom game logic
- `libmain.so` - Unity bootstrap (~28 KB)
- Duplicate copies for armeabi and armeabi-v7a

### Managed Assemblies (`assets/bin/Data/Managed/`)
- **`Assembly-CSharp.dll`** (1.1 MB) - main game logic, decompilable with dnSpy/ILSpy/dotPeek
- `Assembly-CSharp-firstpass.dll` (21 KB) - early-load game scripts
- `Assembly-UnityScript-firstpass.dll` (62 KB) - UnityScript plugins
- `LitJson.dll` - JSON parsing library
- `ICSharpCode.SharpZipLib.dll` - compression library
- Standard Mono/Unity DLLs: mscorlib, System, System.Core, System.Xml, UnityEngine, Boo.Lang, UnityScript.Lang

### Unity Data (`assets/bin/Data/`)
- `mainData` (3.4 MB) - main Unity serialized asset file
- `Resources/unity_builtin_extra` - Unity built-in resources

### Game Data (`assets/GameSrc/civrev1_ipad_u4/data/rom/`)
Human-readable game data files, originally from the CivRev 1 iPad codebase (note the path: "civrev1_ipad_u4"):

#### Achievement/ - Achievement definitions
- `ACHV.bin` + CSV files for categories: General, Domination, Culture, Economy, Technology, etc.
- `AchievementPack.exe` - achievement packing tool (Windows binary shipped in APK)

#### CustomMapData/ - Scenario maps and config
- `map_config.ini` - registers 5 custom maps (Earth, Rivalry, Squadron, TwistedIsle, FourCorners)
- `.civscen` files - scenario save files (~35-91 KB each)
- `_thumbview.png` files - map preview thumbnails
- Tutorial save files and live events data

#### Localization/ - Multi-language text data
- 8 languages: English (enu), German (DEU), Spanish (ESP), French (FRA), Italian (ITA), Japanese (JPN), Korean (KOR), Russian (RUS)
- Categories: CityNames, CivNames, FamousNames, LandmarkNames, RulerNames, TechNames, UnitNames, WonderNames
- `Text.ini` - main localization strings
- Scenario text files

#### Objective/ - Game objectives/missions
- Victory condition data: Culture, Domination, Economy, Technology
- Both `.bin` (compiled) and `.xml` (readable) formats

#### Pedia/ - Civilopedia encyclopedia data
All XML, covering: Buildings, Civilizations, Concepts, Governments, GreatPeople, Leaders, Relics, Resources, Rewards, Techs, Terrains, Units, Upgrades, Wonders
- `Mobile_PediaInfo_*.xml` - structured data (stats, requirements)
- `Mobile_Pedia_Text_*.xml` - display text and descriptions
- `Mobile_Pedia_Structure.xml` / `Mobile_Pedia_Objects.xml` - Civilopedia UI structure
- `Pedia_*.bin` / `Pedia_*.xml` - compiled and source pedia lookup tables

## OBB Structure

All files live under `assets/bin/Data/`. This is a standard Unity asset bundle layout:

### Unity Serialized Files (7204 files, ~1129 MB)
- Hash-named files (e.g., `264cf64a2cc36ea4a8a43099c93d4538`) - Unity asset bundles
- Each contains serialized Unity objects: textures, meshes, animations, audio, shaders, prefabs, etc.
- `level0` (8.5 KB) - level/scene data
- `sharedassets1.assets.split0` through `split14` (~15 MB total) - split shared asset file

### Streaming Resources (78 `.resS` files, ~24 MB)
- Raw resource data referenced by the serialized asset files (typically audio/texture data too large for the main bundle)

### Largest Asset Bundles
Several bundles are 16-22 MB each - likely contain high-resolution textures (leader portraits, map textures, UI backgrounds).

## Decompiled C# Code

`decompiled/Assembly-CSharp/` contains 474 decompiled C# files from `Assembly-CSharp.dll` (via ilspycmd). Gitignored.

### Architecture: C# Thin Wrapper over Native C++

The critical finding is that **nearly all game logic lives in `libTkNativeDll.so` (native C++), not in the C# layer**. The C# classes are thin wrappers that use P/Invoke (`DllImport("TkNativeDll")`) to call into native code.

Pattern used throughout:
- Each `UCiv*` class defines a `CppMethods` interface with game logic methods
- A `_CppMethodsImp` inner class implements it via `DllImport` calls to `CsToCpp_*` functions
- A `_CppDelegates` struct defines callbacks from C++ back to C# via `CppToCs_*` functions
- Classes inherit from `UCivCppMonoBehaviour` which handles C++/C# object binding via `IntPtr`

### Key Game Constants (from C#)
- `kMaxCiv = 6` (max players in a game), `kNumCiv = 17` (total civilizations)
- `kMaxUnit = 256`, `kMaxCity = 128`
- `kTileSize = 2.2f` (world units per tile)
- 17 civilizations: Romans, Egyptians, Greeks, Spanish, Germans, Russians, Chinese, Americans, Japanese, French, Indians, Arabs, Aztecs, Africans, Mongols, English, Korean (+ alternates for English_1, Americans_1, French_1, Russians_1, Chinese_1)
- 56 unit types (Settler through Great_Leader, including unique units: Cataphract, Bowman, Cannon_France, Panzer_Germany, Bomber_B52, WarElephant, Cossack, Hwacha)
- 43 wonders (Pyramids through Kremlin)
- 8 terrain types: Ocean, Grass, Plain, Forest, Hill, Desert, Mountain, Iceberg (+ virtual: City, River, NTER)

### Key Decompiled Files for Game Mechanics
- `UCivGame.cs` - Main game loop, native bridge (~130 DllImport functions)
- `UCivGameUI.cs` - UI/game state bridge, event dispatching
- `UCivCheat.cs` - Cheat system (SetTech, AddBuilding, AddWonder, AddUnit, AddGold, InstantVictory, etc.)
- `UCivTile.cs` - Tile rendering, rivers, roads, fog of war
- `UCivTerrain.cs` - Terrain/map system
- `UCivUnit.cs` - Unit movement, combat, pathfinding
- `UCivCity.cs` / `UCivCityControl.cs` - City management
- `UCivCombatDisplay.cs` - Combat visualization
- `UCivSaveData.cs` - Save/load system
- `UCivNetwork.cs` - Multiplayer/online features
- `UCivObjective.cs` - Victory conditions
- `UCivCivilopedia.cs` - Encyclopedia data loading
- `UCivPowerup.cs` - Power-up/bonus system
- `CombatTest.cs` - Combat testing harness
- `TestGame.cs` - Game testing utilities

### What's in C# vs Native
**C# side handles**: Unity rendering, UI (NGUI framework), audio, animation, camera, touch input, asset loading, save file I/O, social features (Facebook/Google), store/IAP
**Native C++ side handles**: Core game simulation, AI, combat resolution, map generation, tech tree, city production, diplomacy, victory conditions, unit stats, turn processing

## Key Investigation Tools

- **Unity asset extraction**: [AssetStudio](https://github.com/Perfare/AssetStudio) or [UABE](https://github.com/SeriousCache/UABE) for browsing/extracting the hash-named Unity bundles
- **C# decompilation**: dnSpy, ILSpy, or dotPeek on `Assembly-CSharp.dll` to read game logic
- **Native analysis**: Ghidra/IDA on `libTkNativeDll.so` for custom native code
- **APK extraction**: `unzip` or apktool for full APK contents
- **OBB extraction**: Already extracted to `main.19.com.t2kgames.civrev2/`

## Notes

- The game internally references "civrev1_ipad_u4" suggesting CivRev 2 Android was built on top of the CivRev 1 iPad Unity 4 codebase
- The APK contains a Windows executable (`AchievementPack.exe`) - dev tool accidentally shipped
- Custom map data uses a `.civscen` format (scenario save format, not the `.map` format from CivRev 1 PS3)
- Unity version 4.5.3f3 is from mid-2014, consistent with the Dec 2014 OBB timestamps
