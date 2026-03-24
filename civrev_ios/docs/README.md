# Civilization Revolution iOS - Technical Documentation

Reverse-engineering findings for **Sid Meier's Civilization Revolution for iPad** (iOS).

- **App**: CivIPAD v2.4.6
- **Developer**: Firaxis Games / 2K Games
- **Platform**: iOS (armv7, Mach-O)
- **Engine**: Native C++ (ported from Nintendo DS codebase)
- **Executable**: `CivIPAD` (3.4 MB, ~6,762 functions via radare2, ~5,454 decompiled via Ghidra)
- **Origin**: Nintendo DS CivRev -> iPad port -> later became basis for CivRev 2 Android (Unity wrapper)

## Documents

| Document | Description |
|----------|-------------|
| [app-structure.md](app-structure.md) | IPA/app bundle layout, file types, asset organization |
| [binary-analysis.md](binary-analysis.md) | Mach-O executable analysis, key functions, class hierarchy |
| [game-constants.md](game-constants.md) | Game limits, unit types, civilizations, technologies, wonders |
| [combat-system.md](combat-system.md) | Combat resolution, defense bonuses, terrain modifiers |
| [map-system.md](map-system.md) | Map generation, PRNG, custom maps, terrain encoding |
| [save-format.md](save-format.md) | Save/load system, data structure versioning |

## Tools Used

- **Ghidra 11.3.1** (headless mode) — Full decompilation of CivIPAD binary (5,454 functions -> 315 .c files, 22 MB)
- **radare2 5.5.0** — Function listing, ObjC class extraction, imports/exports/sections
- **strings** — Raw string extraction from binary (~49,894 strings)

## Key Difference from PS3 Version

The PS3 version (EBOOT.ELF) is a 26 MB statically-linked PowerPC binary with ~69,479 functions. The iOS version is a 3.4 MB dynamically-linked ARM binary with ~6,762 functions — roughly 10x smaller. This is the same game but the iOS port is significantly more compact, likely due to:
- Dynamic linking (system libraries not embedded)
- Simpler rendering pipeline (2D sprites vs 3D models)
- Fewer visual effects and lower asset complexity
- Single-platform target (no multi-console abstraction)

## Relationship to Other Versions

```
Shared Firaxis engine (F* classes, PRNG, game rules)
  ├─> CivRev PS3/Xbox 360 (June 2008) — console version, 26 MB binary
  └─> CivRev NDS (Nov 2008) — handheld port, 1.6 MB ARM9
        └─> CivRev iOS/iPad (this version, ~2009-2013) — direct port of NDS code
              └─> CivRev 2 Android (2014) — Unity wrapper (path: "civrev1_ipad_u4")
```

The PS3/Xbox 360 was the first release. The NDS was a separate handheld port. This iOS version descends from the NDS code (hence `NDS*` class prefix), not from the PS3 version.
