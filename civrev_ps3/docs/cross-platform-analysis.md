# Cross-Platform Analysis for CivRev Multiplayer

## Platform Comparison

| Aspect | PS3 (2008) | iOS/iPad (2009-2013) | NDS (2008) | CivRev 2 Android (2014) |
|--------|-----------|---------------------|-----------|------------------------|
| Engine | Firaxis C++ (26MB binary, LTO) | Firaxis C++ (NDS port, 3.4MB) | Firaxis C++ (1.6MB ARM9) | Unity + native C++ |
| Online | GameSpy SDK (full suite) | Game Center (turn-based) | Nintendo WiFi Connection (GameSpy) | REST API (2K servers) |
| MP Type | Real-time P2P | Turn-based async | Real-time P2P (WiFi) | Async tournaments/challenges |
| Decompilation | Very hard (PPC, LTO, 69K functions) | Good (named classes, 316 files) | Minimal (4 files) | Good (C# decompile) |

## Key Finding: Shared Game Logic

All versions share the same core game logic and network message protocol. The iOS version is the **Rosetta Stone** — it has the same message types and format as the PS3 version but with readable class/function names.

### Shared Components (PS3 ↔ iOS)
- **NetProxy** class — Network abstraction layer (stubbed on iOS, full on PS3)
- **SendMsg/Broadcast/BroadcastImmediate/LocalMsg/DoNetMsg/DoNetMsgQ** — Message dispatch system
- **NetMsgTxt** — Message type name lookup (69 message types, 0x00-0x44)
- **NetCcMessage** — Network message container (40 bytes)
- **AMsg** — Message structure (type + 5 int params)
- **AMsgMutableArray** — Message queue
- **SynchCheck** — Deterministic sync verification
- **CcSetupData** — Game setup configuration

### iOS-Specific (Game Center)
- **TurnBaseMode / TurnBaseMode_Manager** — Async turn-based multiplayer
- **GameCenterWrapper** — Game Center integration
- **TurnBasedGameGCMessage** — Game Center message wrapper
- Compact binary message packing for Game Center matchData

### PS3-Specific (GameSpy)
- **GameSpy GP** — Profile/presence/buddy system
- **GameSpy Peerchat** — IRC lobby
- **GameSpy QR2/Server Browsing** — Game listing
- **GameSpy NAT Negotiation** — P2P connectivity
- **GameSpy Sake** — Leaderboards/stats
- **GameSpy Competition** — Ranked sessions
- **PSN Integration** — NP ticket authentication via LoginPs3Cert

## Using iOS Code to Understand PS3

### Strategy
1. **Identify function by behavior in iOS** (named functions with debug strings)
2. **Find equivalent PS3 function** by matching:
   - String references (many are shared)
   - Call patterns and structure
   - Parameter counts and types
3. **Cross-reference** to build a map of PS3 function addresses → names

### Already Identified Cross-References

| iOS Function | Purpose | PS3 Equivalent |
|---|---|---|
| `NetMsgTxt(int)` | Get message type name | Same string table exists in PS3 |
| `SendMsg(int,int,int,int,int,int)` | Send network message | TBD |
| `DoNetMsg(AMsg&)` | Process message queue | TBD |
| `DoNetMsgQ(AMsg&)` | Execute single message | TBD (largest function, main game logic) |
| `Broadcast(int,int,int,int)` | Broadcast to all players | TBD |
| `BroadcastImmediate(int,int,int,int)` | Broadcast immediately | TBD |
| `LocalMsg(int,int,int,int)` | Process locally | TBD |
| `Human(int)` | Check if player is human | TBD |
| `NetProxy::GetLocalPlayerID()` | Get local player index | TBD |
| `NetProxy::IsHost()` | Check if local player is host | TBD |
| `NetProxy::PlayerLeft(int)` | Handle player disconnect | TBD |
| `NetProxy::HotDrop(int,bool)` | Handle mid-game disconnect | TBD |
| `NetProxy::BroadcastGame(LobbyType)` | Register game for browsing | TBD |
| `NetProxy::FindGames(LobbyType)` | Search for games | TBD |
| `NetProxy::JoinGame(long)` | Join a game session | TBD |
| `NetProxy::CreateSession(LobbyType)` | Create game session | TBD |

### Key Global Variables (from iOS)
- `_NCIV` — Number of civilizations in game
- `_PActive` — Active player index
- `_RandomS` — Random seed
- `_XMAP` — Map data pointer
- `_g_bMultiplayer` — Multiplayer mode flag
- `_g_bInMainMenu` — In main menu flag
- `_g_bInEndScreens` — In end screens flag
- `_g_bMoveInProgress` — Move animation in progress
- `_MessageQueue` — Network message queue
- `_LastMessageImmediate` — Last message was immediate flag
- `_blockedMsgRef` — Blocked message reference (for move animation sync)
- `_un` — Unit data array (0x58 bytes per unit, indexed by player*0x100+unitID)

## CivRev 2 Android — Limited Usefulness

CivRev 2 uses a completely different online system:
- **No GameSpy** — Uses 2K Games REST API with OAuth authentication
- **No real-time multiplayer** — Only async tournaments and challenges
- **Unity wrapper** — Game logic is in native `libTkNativeDll.so`, C# is thin wrapper
- **UCivNetwork.cs** — Handles tournaments, leaderboards, downloadable content (not real-time MP)

However, CivRev 2's C# code confirms some shared constants:
- `kMaxCiv = 6` (max 6 players)
- `kMaxUnit = 256` per player
- `kMaxCity = 128` total
- Same 17 civilizations (with minor name differences)
- Same unit types and tech tree
