# Save/Load System

Analysis of the save format from Ghidra decompilation of `Unit.c`, `City.c`, `Tech.c`, `Mission.c`, and related files.

## Overview

The game uses a versioned binary serialization format via `FDataStream`. Save format version is tracked globally and checked during deserialization to maintain backward compatibility with older saves.

## Save Format Versioning

The save system tracks a load version number. Code paths branch on version thresholds:

| Version | Changes |
|---------|---------|
| < 5 | Old city format without string names |
| < 6 | Old landmark format |
| < 7 | Old unit format (no extended combat data) |
| 7+ | Current format with all extensions |

## Data Structure Sizes

| Structure | Base Size | Notes |
|-----------|-----------|-------|
| Unit | 0x54 bytes | Extended in version 7+ |
| City | 0x101 bytes | Extended in version 5+ for string names |
| Tech | 0x6a bytes | Plus research tracking fields |
| Mission | 5 x 4 bytes | Fixed array of 5 mission entries |
| Achievement | 0x304 bytes | ID + name + description + icon + progress |
| Save header | Variable | Via `RWHeaderCiv` (68 blocks) |
| Full save | Variable | Via `RWFileCiv` (153 blocks) |

## Unit Save Format (0x54 bytes, version 7+)

From Unit.c decompilation:

| Offset | Size | Field |
|--------|------|-------|
| 0x00-0x0b | 12 | Header (type, flags) |
| 0x0c | 4 | Field A (possibly position) |
| 0x10 | 4 | Field B |
| 0x14 | 4 | Field C |
| 0x18-0x3a | ~34 | 2-byte numeric properties (health, XP, movement, etc.) |
| 0x40 | 4 | Extended field D |
| 0x44-0x53 | 16 | Version 7+ combat extension data |

## City Save Format (0x101 bytes, version 5+)

From City.c decompilation:

| Offset | Size | Field |
|--------|------|-------|
| 0x00-0x0d | 14 | Header |
| 0x0e-0x23 | 22 | Citizen and resource counts (1 byte each) |
| 0x24-0x4b | 40 | Production tracking (4-byte base + 8x 2-byte entries) |
| 0x4c-0x57 | 12 | Building array (6x 2-byte entries) |
| 0x58-0x77 | 32 | Land classification data |
| 0x78-0xa7 | 48 | Additional properties |
| 0xa8-0xe7 | 64 | Building/feature extension data |
| 0xe8-0xf0 | 8 | Flags and counts |
| 0xf1-0x100 | 16 | Version 5+ string name (FStringA with gender) |

For saves version < 5, the city name is stored differently (no FStringA wrapper).

## Tech Save Format (0x6a bytes)

From Tech.c decompilation:

| Offset | Size | Field |
|--------|------|-------|
| 0x00-0x69 | 0x6a | Base tech state data |
| + | Variable | Research progress tracking |

## Mission Save Format

From Mission.c: Fixed array of 5 mission entries, each 4 bytes:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Mission 0 data |
| 0x04 | 4 | Mission 1 data |
| 0x08 | 4 | Mission 2 data |
| 0x0c | 4 | Mission 3 data |
| 0x10 | 4 | Mission 4 data |

## Save/Load Functions

| Function | Blocks | Description |
|----------|--------|-------------|
| `RWHeaderCiv` | 68 | Read/write save header (metadata, version) |
| `RWFileCiv` | 153 | Read/write full game state |
| `LoadGames` | — | Load saved game from storage |
| `SaveGames` | — | Save game state to storage |

## Game Options File

Game options stored in `GameOption.txt` (from NDSGameOptions.c):
- Each option slot: 0x68 bytes
- Marker/version value: `0x44774f70`
- Multiple slots spaced 0x44 bytes apart (offsets: 0x74, 0xb8, 0xfc, 0x140, 0x184...)
- Audio source count: 0x20 (32) allocated

## iCloud Save Sync

From `iCloudHandler` and `iCloudSaveDocument` classes:
- Saves synchronized via iCloud using `NSFileCoordinator` and `NSFileVersion`
- Document-based save model (`UIDocument` subclass)
- Conflict resolution for multi-device saves
- Uses `loadFromContents:ofType:error:` and `saveToURL:forSaveOperation:completionHandler:`

## Game Center Integration

Turn-based multiplayer saves handled through Game Center:
- `TurnBaseMode::GameIOManager` — Turn data I/O
- `TurnBasedGameMessage` / `TurnBasedGameGCMessage` — Message serialization
- `GKTurnBasedMatch` — Match state management
- `loadMatchDataWithCompletionHandler:` — Load match save data

## Scenario Files (.civscen)

The `.civscen` format is a complete game state snapshot used for custom maps and scenarios:
- Same format as CivRev 2 Android
- Contains: map data, player positions, starting conditions, victory parameters
- 2-player scenarios: ~36 KB
- 4-player scenarios: ~91 KB
- Loaded via `CustomMap::LoadCustomMap` (@ 0x160a28)
