# Civilization Revolution NDS - Technical Documentation

Reverse-engineering findings for **Sid Meier's Civilization Revolution** (Nintendo DS).

- **ROM**: `civrev.nds` (64 MB, game code YS6P54)
- **Developer**: Firaxis Games / 2K Games
- **Platform**: Nintendo DS (ARM9 + ARM7)
- **Engine**: Native C++ (Firaxis custom engine)
- **ARM9 binary**: 1.6 MB (decompressed), ARMv4T
- **Data files**: 2,796 files (45 MB)
- **Release**: November 2008 (5 months after PS3/Xbox 360 launch in June 2008)
- **Significance**: Origin of the iOS/Android lineage — the iOS port was built directly from this NDS code

## Documents

| Document | Description |
|----------|-------------|
| [rom-structure.md](rom-structure.md) | NDS ROM layout, filesystem, asset formats |
| [binary-analysis.md](binary-analysis.md) | ARM9 binary analysis, engine classes, overlay system |
| [game-constants.md](game-constants.md) | Civilizations, units, techs, wonders, cross-version comparison |

## Codebase Lineage

```
Shared Firaxis engine (F* classes, PRNG, game rules)
  ├─> CivRev PS3/Xbox 360 (June 2008) — console version, 26 MB binary
  └─> CivRev NDS (Nov 2008) — handheld port, 1.6 MB ARM9
        └─> CivRev iOS/iPad (~2009-2013) — direct port of NDS code
              └─> CivRev 2 Android (2014) — Unity wrapper
```

The PS3/Xbox 360 version was the first release (June 2008). The NDS version followed 5 months later as a separate handheld port. Both share the same Firaxis engine (`F*` classes), identical PRNG, tech tree, and game rules, but have different rendering pipelines, binary structure, and asset formats. The iOS version was ported specifically from the NDS code (hence the surviving `NDS*` class prefix), not from the PS3 version.
