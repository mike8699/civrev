# CivRev PS3 Multiplayer Protocol Overview

## Architecture Summary

CivRev PS3 uses the **GameSpy SDK** (copyright 1999-2008 GameSpy Industries, Inc.) as its entire online multiplayer backend. Since GameSpy shut down in 2014, all online functionality is dead. Restoring it requires replacement servers (e.g., OpenSpy, Retro Tracker, or a custom implementation).

The game uses **deterministic lockstep** synchronization — all clients share random seeds and execute the same game logic, with resync capability and hot-join support.

## GameSpy Modules Used

| Module | Purpose | Server Hostname |
|--------|---------|-----------------|
| GP (Presence) | Buddy list, profiles, presence | `gpcm.gamespy.com`, `gpsp.gamespy.com` |
| Peerchat | IRC-based lobby/chat | `peerchat.gamespy.com` |
| Server Browsing / QR2 | Game listing & queries | `%s.master.gamespy.com`, `%s.ms%d.gamespy.com` |
| NAT Negotiation | Peer-to-peer connectivity | `natneg1.gamespy.com`, `natneg2.gamespy.com`, `natneg3.gamespy.com` |
| Sake | Persistent storage / leaderboards | `%s.sake.gamespy.com` |
| Competition (SC) | Ranked sessions & reporting | `%s.comp.pubsvs.gamespy.com` |
| Auth | Authentication | `%s.auth.pubsvs.gamespy.com` |
| GHTTP | HTTP web service calls | (SOAP endpoints on above hosts) |
| Availability | Service availability check | `%s.available.gamespy.com` |

`%s` = game name identifier (e.g., "civrev" or similar — exact value TBD from data section).

## Match Types

- **Quick Match** — Automatic matchmaking
- **Player Match** — Browse/select games
- **Ranked Match** — Ranked competitive play
- **Custom Match** — Custom settings
- **Create Private Match** — Private game creation

## Game Modes (Multiplayer)

- Free-For-All
- Head-to-Head
- Teams

## Connection Flow

1. PSN sign-in check (requires online account, not guest)
2. Parental control checks (`sceNpManagerGetChatRestrictionFlag`, content rating)
3. GameSpy availability check (`%s.available.gamespy.com`)
4. GameSpy authentication via SOAP (`LoginPs3Cert` using PSN NP certificate/ticket)
5. GP connection (presence/buddy server at `gpcm.gamespy.com`)
6. Lobby/matchmaking (varies by match type)
7. NAT negotiation for peer-to-peer connection
8. Game session creation and synchronization

## Initialization Paths

- `Multiplayer Init(Host)` — Host a game
- `Multiplayer Init(Join IP)` — Direct IP join
- `Multiplayer Init(Join via Lobby)` — Lobby-based join

## Synchronization Model

**Deterministic lockstep** with shared seeds:
- `SEEDS syncrand=%d, game=%d, map=%d` — Three random seeds shared at game start
- `SynchCheck` — Periodic sync verification
- `GFX_OutOfSync.gfx` — Out-of-sync detection UI
- `Resynchronizing` / resync data transfer capability
- Hot-join support: `Receiving hot join data`, `Waiting to hot join`

## PS3-Specific Integration

- **Title ID**: `BLUS30130` (North America), `UP1001-BLUS30130_00`
- **PSN Auth**: Uses `LoginPs3Cert` SOAP call with NP ticket
- **Network Init**: `sys_net_initialize_network()`, `cellNetCtlInit()`
- **Error handling**: `SCE_NP_ERROR_OFFLINE`

## Key Error Messages

- `A network error has occurred. Unable to connect to other players.`
- `Socket creation error` / `DNS lookup error`
- `Could not authenticate server.`
- `Could not connect to the search manager.`
- `Failed to broadcast game information!` / `Failed to host a game!`
- `Packet is larger than allocated buffer:`
- `Unauthorized Player`

## GameSpy Game Mode States

The game registers its current state with the master server via QR2:
- `LobbyLogin` — In lobby, authenticating
- `staging` — In staging room (private/setup)
- `openstaging` — Open for joining (visible in server browser)
- `openplaying` — Game in progress, hot-join possible

## Resolved Questions

- **GameSpy game name**: `civconps3` (confirmed from decompiled config init at 0x0019ad38)
- **Game ID**: 1616 (0x650)
- **Secret Key**: `hn53vx` (6 chars)
- **Partner ID**: 11000
- **Product ID**: 28
- **Namespace ID**: 2 / Login namespace: 19
- **Ports**: 27900 UDP (availability/QR2), 27901 UDP (NatNeg), 28910 TCP (master server), 29900 TCP (GP login), 29901 TCP (GP search), 6500-6600 UDP/TCP (game ports)
- **NatNeg magic**: `\xfd\xfc\x1e\x66\x6a\xb2\x03`
- **QR2 magic**: `\xfe\xfd`

## Remaining Open Questions

- [ ] Exact hot-join data transfer format (what's in `NetHotSync`/`NetHotJoin` messages)
- [ ] Full SOAP request/response XML schemas
- [ ] Peerchat RSA key values (modulus/exponent from auth response)
- [ ] GT2 reliable UDP sequence/ack window sizes
- [ ] Voice chat protocol details
