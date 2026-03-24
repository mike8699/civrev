# Binary Analysis

## ARM9 Executable

| Property | Value |
|----------|-------|
| File | `arm9_original.bin` (decompressed from ROM) |
| Size | 1.6 MB (1,623,992 bytes) |
| Architecture | ARMv4T (ARM9TDMI), 32-bit, little-endian |
| Compression | BLZ-compressed in ROM, decompressed by `extract_nds.py` |
| Header | 16 KB secure area (`arm9_header.bin`) |
| Strings | ~4,571 extractable strings |
| Ghidra processor | `ARM:LE:32:v4t` |

## Overlay System

Unlike the iOS version (single binary) or PS3 (single 26 MB ELF), the NDS version uses **code overlays** — segments loaded/unloaded at runtime to fit within the DS's 4 MB main RAM.

17 overlays total, ranging from 32 bytes to 76 KB. The largest (overlay_0014 at 76 KB) likely contains the main game world screen logic, while overlay_0015 (31 KB) may be combat or city management.

The ARM9 base binary (1.6 MB) contains:
- Firaxis engine (`F*` classes)
- Game simulation core (combat, cities, units, tech, AI)
- Platform abstraction (`Cc*` classes)
- NDS hardware interface (`NDS*` classes)

Overlays contain screen-specific code hot-swapped as the player navigates between screens (world map, city screen, tech tree, combat, etc.).

## Engine Classes

### Firaxis Engine (F-classes) — Identical to iOS

Confirmed present via string references in ARM9:

| Class | Purpose |
|-------|---------|
| `FDataStream` | Binary serialization |
| `FTextSystem` | Localization engine |
| `FStringA` | ASCII string class |
| `FStringArray` | String array |
| `FStringTable` | String lookup table |
| `FFileIO` | File I/O abstraction |
| `FIniParser` | INI config parser |
| `FIOBuffer` / `FIOBufferSync` | Buffered I/O |
| `FMemoryStream` / `FMemoryStreamRLE` | Memory I/O + RLE compression |
| `FTextFile` / `FTextKey` | Text file parsing |
| `FCache` | Generic template cache |
| `FLocaleInfo` | Locale/i18n |
| `FCRC` | CRC checksums |
| `FCriticalSection` | Threading primitives |
| `FGenderVariable` | Gendered text substitution |

Source file references in strings: `FFileErrorHandler.cpp`, `FFileIO.cpp`, `FIniParser.cpp`, `FIOBuffer.cpp`, `FIOBufferSync.cpp`

The `.inl` template headers shipped in the iOS app bundle also originated from this codebase: `FCache.inl`, `FDataStream.inl`, `FFileIO.inl`, `FStringA.inl`, `FStringW.inl`, `FLocale.inl`, `FMemoryStream.inl`, `FTextFile.inl`, `FTextKey.inl`, `FTextSystem.inl`.

### Platform Layer (NDS-specific)

| Class | Purpose |
|-------|---------|
| `CcAppNDS` | App lifecycle (NDS platform, vs `CcAppIphone` on iOS) |
| `CcTimerNDS` | NDS timer hardware |
| `NDSPresentation` | Screen rendering manager |
| `NDSCardCallback` | NDS card/save I/O |

### Networking (NDS WiFi)

| Class | Purpose |
|-------|---------|
| `FINetLobbyNDS` / `FLNetLobbyNDS` | WiFi lobby (interface + implementation) |
| `FNetAccessNDS` / `FINetAccessNDS` / `FLNetAccessNDS` | Network access |
| `FNetPlayerNDS` | Player networking |
| `FNetProfileNDS` | Network profile |
| `FNetSessionNDS` | Game session |
| `FSessionSetup` | Session configuration |

### Game Setup

| Class | Purpose |
|-------|---------|
| `CcSetupData` | Player/game configuration |

## PRNG

Confirmed via strings:
- `"orig seed="`, `"cur seed="` — Seed state debugging
- `"Random Map"` — Map generation mode
- `"7NetSeed"`, `"14NetRequestSeed"` — Network seed sync
- `"Synch Err: Seed"` — Seed synchronization error

The PRNG uses the same **Microsoft Visual C++ LCG** as PS3 and iOS:
```
state = state * 214013 + 2531011   // 0x343FD, 0x269EC3
```

This is expected — the `FRandom` class is part of the shared Firaxis engine.

## Game Strings

Key strings found in ARM9 binary revealing game mechanics:

### Combat & Unit Mechanics
- `"+100% city attack"`, `"+100% city defense"`
- `"+100% defend if with other units"`
- `"50% combat bonus"`
- `"+1 attack for military units."`

### City & Production
- `"+1 Culture in each city."`, `"+1 Production in each city."`, `"+1 Science in each city."`
- `"+2 Production in each city."`, `"+2 Science in each city."`, `"+2 Trade in each city."`
- `"+5 Gold in each city."`
- `"2x city gold production"`, `"4x city gold production"`
- `"2x science in city"`, `"4x science in city"`
- `"Add one population to each city."`
- `"Activate fortified units."`

### Victory Conditions
- `"DOMINATION Victory"`, `"Technology Victory"`, `"Cultural Victory"`, `"Economic Victory"`
- `"The @CIVNAMEP space station has arrived at Alpha Centauri - they win a Technology Victory!"`
- `"The @CIVNAME have won a Technology Victory by discovering Atomic Theory."`
- `"The @CIVNAME have won a Technology Victory by discovering the Railroad."`
- `"If we develop @NUM additional Great People or Wonders, we will be ready to build the United Nations and win a Cultural Victory!"`

### Scenarios
- `"Attack of the Huns"` — Barbarian scenario with domination-only victory
- Scenario description strings reveal: lone city start, enhanced barbarians, capital capture victory

### Debug
- `"AddTech"` — Tech granting function name
- `"Display neutral combat, (ON)"` / `"(OFF)"` — Debug toggle
- `"Warning: the game will end in 5 turns."` — End-game countdown

## Comparison with Other Versions

### ARM9 vs iOS CivIPAD vs PS3 EBOOT

| Property | NDS ARM9 | iOS CivIPAD | PS3 EBOOT |
|----------|----------|-------------|-----------|
| Size | 1.6 MB | 3.4 MB | 26 MB |
| Architecture | ARMv4T (32-bit LE) | ARMv7 (32-bit LE) | PPC64 (64-bit BE) |
| Overlays | 17 (225 KB total) | None | None |
| Total code | ~1.8 MB | 3.4 MB | 26 MB |
| Linking | Static (NDS has no OS) | Dynamic | Static |
| Symbols | Stripped (some RTTI) | Stripped (ObjC metadata) | Stripped |
| PRNG | MSVC LCG | MSVC LCG | MSVC LCG |
| Engine classes | F* (identical) | F* (identical) | F* (identical) |
| Game classes | NDS* (original) | NDS* (inherited) | Different naming |

The NDS binary is ~14x smaller than PS3, yet implements the same game — a testament to the handheld port's efficient code. The PS3 version was released first (June 2008), with the NDS following in November 2008. Both were built on the same shared Firaxis engine.
