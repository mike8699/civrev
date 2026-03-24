# Civilization Revolution - Reverse Engineering

Reverse engineering and modding research across all versions of Sid Meier's Civilization Revolution.

## Platforms

| Directory | Platform | Engine | Status |
|-----------|----------|--------|--------|
| [civrev_ps3/](civrev_ps3/) | PS3 (BLUS-30130) | Native C++ (Firaxis) | EBOOT fully decompiled (69K functions), map generation and spawn algorithm documented, DLC/update patching confirmed working |
| [civrev2/](civrev2/) | Android (v1.4.4) | Unity 4.5.3f3 (Mono) | C# DLLs decompiled, architecture documented (thin C# wrapper over native `libTkNativeDll.so`) |
| [civrev_ios/](civrev_ios/) | iOS / iPad (v2.4.6) | Native (Mach-O) | Binary analyzed, combat system, map system, save format documented |
| [civrev_nds/](civrev_nds/) | Nintendo DS | Native (ARM9) | ROM structure and binary analyzed, game constants documented |

## Documentation

Each platform directory contains detailed technical documentation:

- **PS3**: [civrev_ps3/docs/](civrev_ps3/docs/)
- **iOS**: [civrev_ios/docs/](civrev_ios/docs/)
- **Android**: [civrev2/CLAUDE.md](civrev2/CLAUDE.md)
- **NDS**: [civrev_nds/docs/](civrev_nds/docs/)
