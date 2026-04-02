# GameSpy Protocol Details

## Protocol Overview

GameSpy uses a mix of:
- **Backslash-delimited text** (GP, Server Browsing, QR2) — key-value pairs like `\key\value\key2\value2`
- **IRC** (Peerchat) — modified IRC protocol for lobbies/chat
- **SOAP/HTTP** (Auth, Competition, Sake) — XML web services
- **Binary UDP** (NAT Negotiation, game data)

## 1. GP (Presence) Protocol

Connects to `gpcm.gamespy.com` (TCP port 29900) and `gpsp.gamespy.com` (TCP port 29901).

### Authentication Fields
```
\login\
\challenge\      -- Server challenge
\response\       -- Client challenge response (MD5-based)
\proof\          -- Server proof
\authtoken\      -- Auth token from SOAP login
\loginTicket\    -- Login ticket
\preauth\        -- Pre-authentication
\cdkey\          -- CD key
\cdkeyenc\       -- Encrypted CD key
\passwordenc\    -- Encrypted password
\passenc\        -- Encrypted password (alt)
```

### Profile Fields
```
\nick\           -- Nickname
\uniquenick\     -- Unique nickname
\email\          -- Email address
\profileid\      -- Profile ID
\userid\         -- User ID
\pid\            -- Player ID
\firstname\      -- First name
\lastname\       -- Last name
\birthday\       -- Birthday
\sex\            -- Sex
\countrycode\    -- Country code
\zipcode\        -- Zip code
```

### Buddy/Social Operations
```
\addbuddy\       -- Add friend
\delbuddy\       -- Remove friend
\addblock\       -- Block user
\removeblock\    -- Unblock user
\bdy\            -- Buddy list entry
\bm\             -- Buddy message
\msg\            -- Message content
\status\         -- Status update
\rstatus\        -- Remote status
\locstring\      -- Location string
\inviteto\       -- Game invitation
\pinvite\        -- Player invite
```

### Profile Operations
```
\newuser\        -- Create user
\newprofile\     -- Create profile
\getprofile\     -- Get profile data
\updatepro\      -- Update profile
\updateui\       -- Update user info
\registercdkey\  -- Register CD key
\registernick\   -- Register nickname
\delprofile\     -- Delete profile
\search\         -- Search profiles
\searchunique\   -- Search unique nicks
\uniquesearch\   -- Unique search
```

### Connection Fields
```
\connectionid\   -- Connection ID
\connectionspeed\ -- Connection speed
\sessflags\      -- Session flags
\hasnetwork\     -- Has network capability
\firewall\1      -- Behind firewall
\sdkrevision\    -- SDK version
```

### System Info (reported to server)
```
\cpubrandid\     -- CPU brand
\cpuspeed\       -- CPU speed
\memory\         -- RAM
\videocard1string\ -- GPU name
\videocard1ram\  -- GPU RAM
\videocard2string\ -- Second GPU
\videocard2ram\  -- Second GPU RAM
\osstring\       -- OS string
```

### Protocol Control
```
\final\          -- Message terminator
\err\            -- Error indicator
\errmsg\         -- Error message
\error\          -- Error code
\fatal\          -- Fatal error
\ka\             -- Keepalive
\lc\1            -- Login challenge step 1
\lc\2            -- Login challenge step 2
\id\1            -- Message ID
\len\            -- Length
\valid\          -- Validation result
\check\          -- Check value
\echo\test       -- Echo test
```

## 2. Peerchat (IRC) Protocol

Connects to `peerchat.gamespy.com` (TCP port 6667, with GameSpy encryption).

Uses modified IRC with GameSpy extensions. The connection is encrypted using RSA keys:
- `peerkeyexponent` — RSA public exponent
- `peerkeymodulus` — RSA modulus
- `peerkeyprivate` — RSA private key

**Encryption Keys (from EBOOT binary)**:
- Key 1: `qJ1h4N9cP3lzD0Ka` (16 bytes)
- Key 2: `aFl4uOD9sfWq1vGp` (16 bytes)

**Metadata Formats**:
- `@@@GML %s/OLD` — Group member list
- `@@@NFO \$flags$\` — Game info/flags

### Connection & Auth
```irc
NICK <nickname>
USER <user> <mode> <unused> :<realname>
LOGIN <profileid> <authtoken> <challenge>
LOGIN <profileid> * <challenge> :<response>@<proof>
LOGINPREAUTH <authtoken> <challenge>
CRYPT des <value> <key>              -- Encryption negotiation
CDKEY <cdkey>                         -- CD key validation
USRIP                                 -- Get user's IP
```

### Lobby/Channel Operations
```irc
JOIN <channel> [key]                  -- Join lobby room
NAMES <channel>                       -- List users in channel
LIST [filter]                         -- List channels
MODE <channel> +/-[b|o|v|k|l|q] [args]  -- Channel modes
KICK <channel> <user> :<reason>       -- Kick user
TOPIC <channel> :<topic>              -- Set channel topic
INVITE <user> <channel>               -- Invite to channel
QUIT :Later!                          -- Disconnect
PONG <value>                          -- Keepalive
```

### Messaging
```irc
PRIVMSG <target> :<message>           -- Send message
NOTICE <target> :<message>            -- Send notice
UTM <target> :<message>               -- GameSpy-specific message (used for game data)
```

### Queries
```irc
WHO <mask>                            -- User query
WHOIS <nick>                          -- Detailed user info
GETCHANKEY                            -- Get channel key data
GETCKEY                               -- Get client key data
GETKEY                                -- Get key data
```

### Special
```irc
GETUDPRELAY <channel>                 -- Request UDP relay (for NAT traversal)
LISTSAVE                              -- Save channel list
REGISTERNICK                          -- Register nickname
```

## 3. Server Browsing / QR2 Protocol

Master server at `%s.master.gamespy.com` (TCP port 28910 for browsing, UDP port 27900 for heartbeat).

### Server Query Fields
```
\hostname\       -- Server/game name
\hostip\         -- Host IP address
\hport\          -- Host port
\hprivip\        -- Host private IP (for LAN)
\port\           -- Game port
\bport\          -- Browse port
\qport\          -- Query port
\publicport\     -- Public port
\localport\      -- Local port
\gamename\       -- Game name identifier
\gameType\       -- Game type (FFA, H2H, Teams)
\gameVnt\        -- Game variant
\gameMn\         -- Game mode name
\pmatch\         -- Private match flag
\numwaiting\     -- Players waiting
\maxwaiting\     -- Max waiting slots
\numservers\     -- Number of servers
\numplayers\     -- Current players
\maxplayers\     -- Max players
```

## 4. SOAP Web Services (Auth, Competition, Sake)

### Authentication Service (`%s.auth.pubsvs.gamespy.com`)
```
LoginProfile        -- Login with profile credentials
LoginPs3Cert        -- Login using PS3 NP certificate (PS3-specific!)
LoginRemoteAuth     -- Remote authentication
LoginUniqueNick     -- Login with unique nickname
```

### Competition Service (`%s.comp.pubsvs.gamespy.com`)
```
CreateSession             -- Create game session
CreateMatchlessSession    -- Create session without matchmaking
SetReportIntention        -- Declare intent to report results
SubmitReport              -- Submit match results/statistics
```

### Sake Service (`%s.sake.gamespy.com`)
```
CreateRecord      -- Create persistent record
DeleteRecord      -- Delete record
UpdateRecord      -- Update record
GetMyRecords      -- Get own records
GetSpecificRecords -- Get specific records
GetRandomRecords  -- Get random records
GetRecordCount    -- Get record count
GetRecordLimit    -- Get record limit
SearchForRecords  -- Search records
RateRecord        -- Rate a record
```

### Sake File Server
```
Upload:   http://%s.sake.%s/SakeFileServer/upload.aspx?gameid=%d&pid=%d
Download: http://%s.sake.%s/SakeFileServer/download.aspx?fileid=%d&gameid=%d&pid=%d
```

### Sake Data Types
Records support these field types:
```
byteValue, shortValue, intValue, int64Value, floatValue,
asciiStringValue, unicodeStringValue, booleanValue,
dateAndTimeValue, binaryDataValue
```

### Sake Error Codes
```
Success, SecretKeyInvalid, ServiceDisabled, DatabaseUnavailable,
LoginTicketInvalid, LoginTicketExpired, TableNotFound, RecordNotFound,
FieldNotFound, FieldTypeInvalid, NoPermission, RecordLimitReached,
AlreadyRated, NotRateable, NotOwned, FilterInvalid, SortInvalid,
TargetFilterInvalid
```

## 5. NAT Negotiation Protocol

Binary UDP protocol on ports 27901 (natneg1), 27901 (natneg2), 27901 (natneg3).

Used to establish peer-to-peer connections through NATs/firewalls. Three servers are used for redundancy and for different NAT detection techniques.

## 6. Peerchat Channel Naming

GameSpy Peerchat uses IRC channels with a specific naming convention for game lobbies:
```
#GSP!<gamename>!<type><roomname><type>
```
Format string: `#GSP!%s!%c%s%c`

Game data is encoded in channel messages using:
```
X<gamename>X|<data>
```
Format string: `X%sX|%d`

### Custom Server Browsing Keys
The game registers these custom keys for server browsing:
```
openstaging      -- Whether staging is open for joining
b_flags          -- Game flags/settings bitfield
gsi_am_rating    -- GameSpy skill rating
numwaiting       -- Number of players waiting
maxwaiting       -- Max waiting slots
numservers       -- Number of servers
```

## 7. HTTP Details

- User-Agent: `GameSpyHTTP/1.0`
- SOAP calls use standard HTTP POST with XML bodies
- File transfers via Sake file server use HTTP GET/POST

## Key Implementation Notes

1. All GameSpy text protocols use `\final\` as message terminator
2. Peerchat uses RSA encryption layer on top of IRC
3. PS3 authentication uses NP ticket → `LoginPs3Cert` SOAP → GameSpy auth token → GP login
4. Server browsing uses both TCP (list retrieval) and UDP (heartbeat/query)
5. NAT negotiation is essential for peer-to-peer game connectivity
