# CivRev Network Message Types

## Message Format

Messages are sent between players using a `SendMsg(type, param1, param2, param3, param4, target)` function.

The message structure (`AMsg`) is:
- `type` (int) — Message type ID (0x00-0x44)
- `param1` (int) — First parameter (meaning varies by type)
- `param2` (int) — Second parameter
- `param3` (int) — Third parameter
- `param4` (int) — Fourth parameter
- `target` (int) — Target player ID (-1 = all, -2 = all but self, specific ID = that player only)

Messages are processed by `DoNetMsg()` and can be sent via:
- `Broadcast(type, p1, p2, p3)` — Send to all players (target=-2)
- `BroadcastImmediate(type, p1, p2, p3)` — Send to all, processed immediately
- `LocalMsg(type, p1, p2, p3)` — Process locally only
- `SendMsg(type, p1, p2, p3, p4, target)` — Full send with target

## Message Type Enumeration (0x00-0x44)

| ID | Hex | Name | Description |
|----|-----|------|-------------|
| 0  | 0x00 | Combat | Initiate combat |
| 1  | 0x01 | Combated | Combat result |
| 2  | 0x02 | CombatedAI | AI combat result |
| 3  | 0x03 | Govt | Government change |
| 4  | 0x04 | Research | Research technology |
| 5  | 0x05 | Build | Build unit/building |
| 6  | 0x06 | Rush | Rush production |
| 7  | 0x07 | Road | Build road |
| 8  | 0x08 | Working | Set city tile working |
| 9  | 0x09 | UBits | Unit bit flags |
| 10 | 0x0A | MakeArmy | Create army (merge units) |
| 11 | 0x0B | DisbandA | Disband army |
| 12 | 0x0C | Settle | Found city |
| 13 | 0x0D | Fortify | Fortify unit |
| 14 | 0x0E | Sentry | Set unit to sentry |
| 15 | 0x0F | Famous 'K' | Great person (Famous person action) |
| 16 | 0x10 | DelUnit | Delete/disband unit |
| 17 | 0x11 | Move | Move unit |
| 18 | 0x12 | Convoy | Caravan/convoy action |
| 19 | 0x13 | CFocus | City production focus |
| 20 | 0x14 | CTrade | City trade route |
| 21 | 0x15 | PowerUp | Activate power-up / era ability |
| 22 | 0x16 | Heal | Heal unit |
| 23 | 0x17 | AddFame | Add fame/culture points |
| 24 | 0x18 | AddGeneral | Add great general to unit |
| 25 | 0x19 | CCapture | City capture |
| 26 | 0x1A | Landmark | Discover landmark |
| 27 | 0x1B | Contact | Make contact with civilization |
| 28 | 0x1C | SSLaunch | Space station launch (component) |
| 29 | 0x1D | MeetKing | Meet leader (diplomacy screen) |
| 30 | 0x1E | Dialog | Diplomacy dialog |
| 31 | 0x1F | Response | Diplomacy response |
| 32 | 0x20 | DipTimeOut | Diplomacy timeout |
| 33 | 0x21 | Treaty | Treaty (peace/alliance/etc) |
| 34 | 0x22 | RUBusy? | Are you busy? (diplomacy check) |
| 35 | 0x23 | Stealth | Stealth/spy action |
| 36 | 0x24 | Obligation | Treaty obligation |
| 37 | 0x25 | Gold | Gold transfer |
| 38 | 0x26 | AddTech | Add technology (trade/steal) |
| 39 | 0x27 | AddGeneralH | Add great general (historical) |
| 40 | 0x28 | BeginTurn | Begin turn |
| 41 | 0x29 | BeginTurnReload | Begin turn after reload |
| 42 | 0x2A | BeginTurnAI | Begin turn for AI player |
| 43 | 0x2B | BuildDone | Build complete |
| 44 | 0x2C | ImDone | Player finished turn |
| 45 | 0x2D | ImNotDone | Player not done with turn |
| 46 | 0x2E | AIDone | AI finished turn |
| 47 | 0x2F | ImDoneAI | Player done (AI processing) |
| 48 | 0x30 | EndTurn | End of turn |
| 49 | 0x31 | SynchCheck | Synchronization check |
| 50 | 0x32 | Team | Team assignment |
| 51 | 0x33 | Handicap | Difficulty/handicap setting |
| 52 | 0x34 | WorldType | World/map type setting |
| 53 | 0x35 | TurnTime | Turn timer value |
| 54 | 0x36 | Checksum | Game state checksum |
| 55 | 0x37 | ImBusy | Player is busy (in diplomacy, etc) |
| 56 | 0x38 | NotBusy | Player is no longer busy |
| 57 | 0x39 | GameOver | Game over condition |
| 58 | 0x3A | CityName | Set city name |
| 59 | 0x3B | SetCiv | Set civilization |
| 60 | 0x3C | CTBits | City tile bits |
| 61 | 0x3D | Mini Combat | Mini/auto combat |
| 62 | 0x3E | Merry Christmas | Special event? |
| 63 | 0x3F | Super People | Super great people? |
| 64 | 0x40 | (Unknown 0x40) | |
| 65 | 0x41 | (Unknown 0x41) | |
| 66 | 0x42 | (Unknown 0x42) | |
| 67 | 0x43 | (Unknown 0x43) | |
| 68 | 0x44 | (Unknown 0x44) | |

## Wire Format (Turn-Based / Compact)

For the turn-based (Game Center) mode, messages are packed into a compact binary format. Each message starts with a 1-byte opcode, followed by variable-length parameters that are bit-packed for efficiency.

### Parameter Packing by Message Type

Based on the `EnqueMessages` deserialization in TurnBaseMode:

| Opcode(s) | Packed Size | Packing |
|-----------|-------------|---------|
| 0x00 (Combat), 0x16 (Heal), 0x2B (BuildDone) | 2 bytes | p1=byte[1]&0xF, p3=byte[1]>>4 |
| 0x01 (Combated), 0x2A (BeginTurnAI) | 8 bytes | p1=byte[1], p2=uint16(byte[2..3]), p3=uint32(byte[4..7]) |
| 0x02 (CombatedAI), 0x25 (Gold) | 2 bytes | p1=byte[1]&0xF, p2=byte[1]>>4 |
| 0x03, 0x2E, 0x2F, 0x30, 0x36, 0x3F | 1 byte | No params (opcode only) |
| 0x04 (Research) | 3 bytes | p1=byte[1], p2=byte[2] (0xFF→-1) |
| 0x05, 0x06, 0x13, 0x19, 0x1C, 0x2C | 5 bytes | p1=byte[1], p2=byte[2], p3=uint16(byte[3..4]) |
| 0x07 (Road) | 4 bytes | p1=byte[1], p2=uint16(byte[2..3]) |
| 0x08 (Working) | 7 bytes | p1=byte[1], p2=byte[2], p3=uint32(byte[3..6]) |
| 0x0A-0x0E, 0x10, 0x15, 0x17, 0x1A, 0x1B, 0x41, 0x44 | 2 bytes | p1=byte[1] |
| 0x0F, 0x12, 0x18 | 4 bytes | p1=byte[1], p2=byte[2], p3=byte[3] |
| 0x11 (Move) | 3 bytes | p1=uint16(byte[1..2])&0xF, p3=uint16>>4 |
| 0x14 (CTrade) | 2 bytes | p1=byte[1]&0xF, p3=byte[1]>>4 (0xF→-1) |
| 0x1D, 0x1E | 3 bytes | p1=uint16(byte[1..2])&7, p2=(byte<<24)>>27, p3=byte[2] |
| 0x1F, 0x31-0x34, 0x3B, 0x3D, 0x3E | 2 bytes | p1=byte[1] |
| 0x20, 0x29 | 4 bytes | p1=byte[1], p2=uint16(byte[2..3]) |
| 0x21, 0x23 | 2 bytes | p1=byte[1]&7, p2=(byte[1]<<26)>>29, p3=byte[1]>>7 |
| 0x22 | 3 bytes | p1=byte[1], p2=byte[2]&0xF, p3=byte[2]>>4 |
| 0x24 | 2 bytes | p2=byte[1] |
| 0x26 (AddTech) | 3 bytes | p1=byte[1]&0xF, p2=byte[1]>>4, p3=byte[2] (0xFF→-1) |
| 0x27 | 2 bytes | p1=byte[1]&7, p2=(byte[1]<<26)>>29, p3=byte[1]>>6 |
| 0x28 (BeginTurn) | 6 bytes | p1=byte[1], p2=byte[3], p3=uint16(byte[4..5]) |
| 0x2D | 3 bytes | p1=byte[1]&7, p3=byte[1]>>3, p2=byte[2] |
| 0x35, 0x3C | 6 bytes | p1=byte[1], p3=uint32(byte[2..5]) |
| 0x37 | 9 bytes | p1=uint32(byte[1..4]), p3=uint32(byte[5..8]) |
| 0x38, 0x39, 0x40 | 2 bytes | p1=byte[1]&7, p2=byte[1]>>3 |
| 0x3A | 2 bytes | p1=byte[1]&0x3F, p2=byte[1]>=0x40?-1:0 |
| 0x43 | 4 bytes | p1=uint16(byte[1..2])&7, p3=uint16>>3, p2=byte[3] |

## NetCcMessage Container

Messages are wrapped in a `NetCcMessage` structure for network transmission:
- Size: 0x28 (40) bytes
- Contains: message type + 5 int parameters
- Serialized to NSData for GameCenter, or to GameSpy packet for PS3

## Broadcast Semantics

From the code analysis, here's how different messages are typically broadcast:

- **Unit actions** (Move, Combat, Build, etc.): Broadcast to all with unit/player/position params
- **Diplomacy** (MeetKing, Dialog, Response, Treaty): Sent to specific player targets
- **Turn management** (BeginTurn, ImDone, EndTurn): Broadcast to all
- **Sync** (SynchCheck, Checksum): Broadcast to verify deterministic lockstep
- **Setup** (Team, Handicap, WorldType, SetCiv): Broadcast during game setup

## Deterministic Lockstep

The game uses deterministic lockstep synchronization:
1. All players share random seeds at game start: `SEEDS syncrand=%d, game=%d, map=%d`
2. Game actions are broadcast as messages (not game state)
3. Each client executes messages in the same order to maintain identical state
4. `SynchCheck` and `Checksum` messages verify clients are in sync
5. If desync detected: `GFX_OutOfSync.gfx` screen shown, resynchronization initiated

## Hot Drop (Mid-Game Disconnect)

The `HotDrop` function sends a message (type 0x0E) with player ID when a player disconnects:
```c
msg.type = 0x0E;  // Sentry? / HotDrop marker
msg.param1 = localPlayerID;
msg.param2 = droppedPlayerID;
// Sent via GameCenterWrapper::SendNetworkData
```

## Message Handler Details (from iOS DoNetMsgQ analysis)

Key message behaviors from the 2400-line DoNetMsgQ switch statement:

- **Combat (0x00)**: Looks up unit, computes destination tile, calls `BestDefender()` + `qCombat()`. On capture, sends Contact (0x1B) + Move (0x11).
- **Combated (0x01)**: Finalizes combat via `qCombated()`, moves victorious unit, handles city capture.
- **Govt (0x03)**: Sets `Govt[player] = newType`, fires `AddEvent()`. Democracy triggers diplomatic contact with all civs.
- **Research (0x04)**: Sets `Researching[player] = techIndex`, transfers accumulated research points.
- **Move (0x11)**: Handles normal movement via `qMove()`, ICBM strikes (`NuclearStrikeProduction()`), and spy infiltration.
- **Famous'K (0x0F)**: Master handler for 7 Great Person types — Scientist (complete research), Humanitarian (+1 pop all cities), Explorer (gold bonus), Builder (rush wonder), Artist (absorb city), Leader (veteran upgrade), Tycoon (complete buildings).
- **Settle (0x0C)**: Validates via `CanBuildCity()`, calls `AddCity()`, deletes settler, shows founding animation.
- **BeginTurn (0x2E)**: Major handler — calls `SetHuman()`, `qBeginTurn()`, `qDoTurn()` for each human player, sends SynchCheck.
- **EndTurn (0x30)**: Calls `SynchCities()`, runs AI turns (`qBeginTurn` + `qDoTurn` for each AI), computes checksum.
- **ImDone (0x32)**: Sets TurnDone bit, calls `VictoryCheck()`, host sends EndTurn when all done.
- **Checksum (0x36)**: Calls `qEndTurn()` to finalize. Auto-saves if not multiplayer.
- **ImBusy (0x37)**: Compares checksums — sets desync flag if mismatch.
- **GameOver (0x3F)**: Sets `State |= 0x10000` (game over).

## Global State Modified by Messages

| Global | Purpose |
|--------|---------|
| `un[]` | Unit array (0x58 bytes per unit, 0x5800 per player) |
| `ct[]` | City array (0x110 bytes per city, 128 max) |
| `Govt[]` | Government type per player |
| `Research[]` / `Researching[]` | Tech research state |
| `Gold[]` | Player gold amounts |
| `Treaty[]` | Bilateral treaty table (6x6x4 bytes) |
| `TurnDone` / `DoneSent` / `TurnBegun` | Turn management bitmasks |
| `State` | Global game state flags |
| `Fame[]` / `NFame[]` / `FBurned[]` | Great person tracking |
| `Busy[]` / `ABBusy` / `CBBusy` / `MKBusy` | Subsystem busy counters |
| `Handicap[]` | Difficulty per player |
| `XMAP` / `YMAP` | Map dimensions |
