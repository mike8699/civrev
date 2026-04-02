# PS3 Authentication & Network Initialization Flow

## PSN / Network Initialization

The PS3 version goes through several initialization stages before connecting to GameSpy:

### Stage 1: System Network Init
```
sys_net_initialize_network()    -- Initialize PS3 BSD socket layer
cellNetCtlInit()                -- Initialize network control
```

### Stage 2: PSN Status Check
```c
// FUN_00bda790 - Check PSN status and show network dialog if needed
sceNpManagerGetStatus(&status)
if (status == 3) {
    // PSN is signed in, proceed to GameSpy init
    FUN_00bdcd4c(...)  // GameSpy initialization
} else {
    // Show network connection dialog
    cellNetCtlNetStartDialogLoadAsync(...)
}
```
PSN status values:
- 0 = Not initialized
- 1 = Signed out
- 2 = Signing in
- 3 = Signed in (online)

### Stage 3: Parental Controls Check
```c
// FUN_00bda630 - Check content rating and chat restrictions
sceNpManagerGetContentRatingFlag(...)  // Check if online content is allowed
sceNpManagerGetChatRestrictionFlag(...)  // Check if chat is allowed
```
Returns:
- 1 = Allowed
- 3 = Blocked (shows error dialog)
- Error `-0x7ffd55f4` = `SCE_NP_ERROR_OFFLINE` (PSN is offline)

### Stage 4: NP Basic Init (Friends/Presence)
```c
// FUN_00ed5338 region - Initialize NP subsystems
sceNpInit()
sceNpBasicInit()
sceNpBasicRegisterHandler(...)  // Register callback for NP events
sceNpLookupInit()
sceNpLookupCreateTitleCtx(...)  // Create title context for lookups
```

### Stage 5: GameSpy Availability Check
```c
// Check if GameSpy services are running
// DNS lookup: <gamename>.available.gamespy.com
// GSIStartAvailableCheck(gamename)
// If available → proceed to login
// If unavailable → show error
```

### Stage 6: GameSpy Authentication (SOAP)
```c
// PS3-specific authentication via SOAP
// 1. Get NP ticket from PSN
sceNpManagerGetTicket(...)           // Get current NP ticket
sceNpManagerRequestTicket2(...)      // Request new ticket if needed

// 2. Send to GameSpy auth service
// SOAP call: LoginPs3Cert
// Endpoint: https://<gamename>.auth.pubsvs.gamespy.com/AuthService/AuthService.asmx
// SOAPAction: "http://gamespy.net/AuthService/LoginPs3Cert"
// Body: PS3 NP ticket (field: "npticket")
// Response fields:
//   - responseCode (0 = success)
//   - authToken (used for subsequent GP login)
//   - partnerChallenge
//   - peerkeyprivate (RSA private key for peerchat encryption)
//   - peerkeymodulus (RSA modulus)
//   - peerkeyexponent (RSA exponent)
//   - serverdata (server-specific data)
//   - signature (verification signature)
```

Debug string: `wsLoginRemoteAuth returned %d (%d)!`

#### Auth SOAP Endpoints (from binary strings)
```
LoginPs3Cert         -- SOAPAction: "http://gamespy.net/AuthService/LoginPs3Cert"
LoginRemoteAuth      -- SOAPAction: "http://gamespy.net/AuthService/LoginRemoteAuth"
LoginUniqueNick      -- SOAPAction: "http://gamespy.net/AuthService/LoginUniqueNick"
LoginProfile         -- SOAPAction: "http://gamespy.net/AuthService/LoginProfile"
```

#### Auth Response Fields
```
authToken            -- Token for GP/peerchat login
partnerChallenge     -- Challenge for partner validation
peerkeyprivate       -- RSA private key (for peerchat encryption)
peerkeymodulus       -- RSA modulus
peerkeyexponent      -- RSA public exponent
responseCode         -- 0 = success
```

#### Lobby Login
There's also a separate lobby login endpoint:
```
https://<host>/AuthService/AuthService.asmx  (via format string at offset 23941328)
```
With `LobbyLogin` operation (string at 23941744).

### Stage 7: GP Connection
```c
// Connect to GameSpy Presence server
// TCP connection to gpcm.gamespy.com:29900
// Login with auth token from step 6
// Establish presence, load buddy list
```

### Stage 8: Ready for Multiplayer
Player can now access multiplayer menu options.

## NP Cleanup / Shutdown

```c
// FUN_00ed5478 - Cleanup NP subsystems
sceNpLookupDestroyTitleCtx(...)
sceNpLookupTerm()
sceNpBasicUnregisterHandler()
sceNpTerm()
```

## PS3 NP Functions Used

### Core NP
| Function | Purpose |
|---|---|
| `sceNpInit()` | Initialize NP library |
| `sceNpTerm()` | Terminate NP library |
| `sceNpManagerGetStatus()` | Get PSN sign-in status |
| `sceNpManagerGetTicket()` | Get current NP ticket |
| `sceNpManagerRequestTicket2()` | Request new NP ticket |
| `sceNpManagerGetContentRatingFlag()` | Check content rating restrictions |
| `sceNpManagerGetChatRestrictionFlag()` | Check chat restrictions |

### NP Basic (Presence)
| Function | Purpose |
|---|---|
| `sceNpBasicInit()` | Initialize basic NP |
| `sceNpBasicRegisterHandler()` | Register event callback |
| `sceNpBasicUnregisterHandler()` | Unregister callback |
| `sceNpBasicSetPresence()` | Set online presence |
| `sceNpBasicAddBlockListEntry()` | Block a user |
| `sceNpBasicGetBlockListEntryCount()` | Get block list count |

### NP Lookup
| Function | Purpose |
|---|---|
| `sceNpLookupInit()` | Initialize lookup service |
| `sceNpLookupTerm()` | Terminate lookup |
| `sceNpLookupCreateTitleCtx()` | Create title context |
| `sceNpLookupDestroyTitleCtx()` | Destroy title context |
| `sceNpLookupCreateTransactionCtx()` | Create lookup transaction |
| `sceNpLookupDestroyTransactionCtx()` | Destroy transaction |
| `sceNpLookupPollAsync()` | Poll async lookup result |

### NP Matching (not used?)
No `sceNpMatching` calls found — the game uses GameSpy for matchmaking instead of PSN's built-in system.

## Key PS3 Functions Map

| Address | Probable Name | Purpose |
|---|---|---|
| `0x00bda630` | CheckParentalControls | Content rating + chat restriction check |
| `0x00bda790` | InitOnline / CheckPSNStatus | Check PSN status, show dialog, init GameSpy |
| `0x00bdcd4c` | InitGameSpy | GameSpy SDK initialization (called when PSN status=3) |
| `0x00ed4d80` | ProcessNPLookups | Process async NP lookup operations |
| `0x00ed4ef0` | (NP related) | NP subsystem function |
| `0x00ed5168` | GetBlockListCount | Get NP block list entry count |
| `0x00ed5338` | InitNP | Initialize NP subsystems |
| `0x00ed5478` | ShutdownNP | Cleanup/terminate NP subsystems |
| `0x00ed5528` | (NP related) | NP subsystem function |
| `0x00ed5720` | (NP related) | NP subsystem function |

## Custom Server Auth Implications

For a custom server, the authentication can be simplified:

1. **Skip NP ticket validation** — Accept any login, generate profile ID
2. **Return valid auth token** — Any token the GP server will accept
3. **GP login** — Accept auth token, create session

The NP ticket is only validated by the GameSpy auth SOAP service, not by the game itself. So a custom auth server can simply accept any request and return success.
