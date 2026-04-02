# Custom Server Requirements for CivRev PS3 Online

## Overview

To restore CivRev PS3 online multiplayer, we need to implement replacement servers for the GameSpy services the game connects to. This document outlines what each service does and what a custom server must provide.

## Architecture Options

### Option A: Full Custom Server
Implement all GameSpy services from scratch. Maximum control but most work.

### Option B: OpenSpy Integration
Use existing OpenSpy infrastructure (openspy.net) which already implements the GameSpy protocol. The game needs DNS/binary patches to redirect `*.gamespy.com` → `*.openspy.net`. There's already an RPCS3 "Openspy Online" patch for BLES00238 (EU version).

### Option C: Hybrid
Use OpenSpy for the complex services (auth, GP, peerchat) and implement only game-specific logic custom.

## Required Services

### 1. Availability Check Service
- **Purpose**: Game checks if online services are available before proceeding
- **Endpoint**: `<gamename>.available.gamespy.com` (DNS A record)
- **Protocol**: DNS lookup + HTTP response
- **Complexity**: Low — just needs to resolve and return "available"

### 2. Authentication Service (SOAP/HTTPS)
- **Purpose**: Authenticate PS3 player using PSN NP ticket
- **Endpoint**: `<gamename>.auth.pubsvs.gamespy.com`
- **Operations**: `LoginPs3Cert` (PS3-specific), `LoginProfile`, `LoginUniqueNick`, `LoginRemoteAuth`
- **Flow**:
  1. Game sends PSN NP certificate/ticket via SOAP
  2. Server validates and returns auth token + profile ID
  3. Auth token is used for subsequent GP/peerchat logins
- **Complexity**: High — needs PS3 NP ticket validation (or can be faked for custom server)

### 3. GP (Presence) Server
- **Purpose**: Buddy list, profiles, presence status, game invitations
- **Endpoints**: `gpcm.gamespy.com:29900` (TCP), `gpsp.gamespy.com:29901` (TCP)
- **Protocol**: Backslash-delimited text (`\key\value\final\`)
- **Operations**: Login (with auth token), profile management, buddy operations, status updates
- **Complexity**: Medium — well-documented GameSpy protocol

### 4. Peerchat (Lobby) Server
- **Purpose**: IRC-based game lobby, chat, matchmaking
- **Endpoint**: `peerchat.gamespy.com:6667` (TCP with GameSpy encryption)
- **Protocol**: Modified IRC with RSA encryption layer
- **Operations**: Login, join channels, list games, send/receive messages, UTM game data
- **Key Features**: RSA key exchange, GameSpy-specific commands (UTM, CDKEY, USRIP, GETUDPRELAY)
- **Complexity**: Medium-High — IRC base is simple but encryption and extensions add complexity

### 5. Server Browsing / QR2 (Game Listing)
- **Purpose**: Register hosted games, browse available games, query game details
- **Endpoints**:
  - `<gamename>.master.gamespy.com:28910` (TCP, browsing)
  - UDP port 27900 (QR2 heartbeat)
- **Protocol**: Binary (server browsing), backslash-delimited text (QR2)
- **Custom Keys**: hostname, gameType, gameVnt, gameMn, pmatch, numplayers, maxplayers, etc.
- **Complexity**: Medium — needs both TCP list server and UDP heartbeat handler

### 6. NAT Negotiation
- **Purpose**: Establish peer-to-peer connections through NATs/firewalls
- **Endpoints**: `natneg1.gamespy.com`, `natneg2.gamespy.com`, `natneg3.gamespy.com` (UDP 27901)
- **Protocol**: Binary UDP
- **Flow**:
  1. Both peers register with NAT neg server
  2. Server facilitates NAT hole-punching
  3. Peers establish direct UDP connection
- **Complexity**: Medium — critical for actual gameplay connectivity

### 7. Competition Service (SOAP/HTTPS)
- **Purpose**: Ranked match session management and result reporting
- **Endpoint**: `<gamename>.comp.pubsvs.gamespy.com`
- **Operations**: CreateSession, CreateMatchlessSession, SetReportIntention, SubmitReport
- **Complexity**: Low-Medium — SOAP service, can be stubbed for basic functionality

### 8. Sake (Persistent Storage) Service
- **Purpose**: Leaderboards, statistics, persistent records
- **Endpoint**: `<gamename>.sake.gamespy.com`
- **Operations**: CRUD on records (Create/Get/Update/Delete/Search), file upload/download
- **File Server**: `http://<gamename>.sake.<domain>/SakeFileServer/upload.aspx?gameid=<id>&pid=<id>`
- **Complexity**: Medium — database-backed SOAP service

## Game Flow Requiring Server Support

### Connection Flow
```
1. PSN Sign-in (handled by PS3/RPCS3)
2. Network check (cellNetCtlInit)
3. Available check → availability service
4. SOAP Login (LoginPs3Cert) → auth service
5. GP Connect → gpcm:29900
6. GP Login with auth token
7. Ready for multiplayer menu
```

### Quick Match Flow
```
1. Player selects Quick Match
2. Server browsing query → master:28910
3. If games found: NAT negotiation → natneg:27901
4. Join via NAT-punched connection
5. If no games: Create new game via QR2 heartbeat
6. Wait for other players
```

### Hosting Flow
```
1. Player creates game
2. QR2 heartbeat registration → master (UDP 27900)
3. Game appears in server browser
4. Other players join via NAT negotiation
5. Staging screen (set options, ready up)
6. Host launches → SynchCheck seeds broadcast
7. Game begins with deterministic lockstep
```

### Game Session Protocol
```
1. Host broadcasts: SEEDS syncrand=%d, game=%d, map=%d
2. All clients initialize with same seeds
3. Player actions → Broadcast/SendMsg messages
4. Each client applies messages in order
5. Periodic SynchCheck/Checksum verification
6. Turn management: BeginTurn → actions → ImDone → EndTurn
7. Desync detected → Resynchronization
```

## Minimum Viable Server

For the simplest possible custom server that enables multiplayer:

1. **DNS redirect**: Point `*.gamespy.com` to custom server IP
2. **Availability**: Simple HTTP server responding "available"
3. **Auth**: Accept any login, return valid auth token
4. **GP**: Minimal presence server (login, keepalive)
5. **NAT Neg**: NAT negotiation relay (essential for P2P)
6. **Server Browsing**: Basic game list server

Peerchat, Competition, and Sake can potentially be stubbed or omitted for basic functionality, but lobby chat and leaderboards would be non-functional.

## Alternative: Direct IP Connect

The game supports `Multiplayer Init(Join IP)` — direct IP connection without matchmaking. If this can be triggered, it could bypass the need for most server infrastructure. Only NAT negotiation (or being on the same LAN/using port forwarding) would be needed.

## DNS Requirements

All GameSpy services use hostnames that must resolve to the custom server:
```
civconps3.available.gamespy.com
civconps3.auth.pubsvs.gamespy.com
civconps3.comp.pubsvs.gamespy.com
civconps3.sake.gamespy.com
civconps3.master.gamespy.com
civconps3.ms1.gamespy.com (and ms2, ms3...)
gpcm.gamespy.com
gpsp.gamespy.com
peerchat.gamespy.com
natneg1.gamespy.com
natneg2.gamespy.com
natneg3.gamespy.com
```

Custom server must accept these credentials:
- **gamename**: `civconps3`
- **secretkey**: `hn53vx`
- **gameid**: 1616
- **partnerid**: 11000
- **productid**: 28

Alternatively, patch the EBOOT binary to replace `gamespy.com` with a custom domain (as the RPCS3 OpenSpy patch does for `openspy.net`).
