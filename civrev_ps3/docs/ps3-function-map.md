# PS3 EBOOT Function Map — Networking

## Identified Functions by Port Usage

### GameSpy Availability Check (Port 27900 / 0x6cfc)
| Address | Function | Notes |
|---|---|---|
| `0x00ebd590` | **AvailabilityCheck_Init** | Creates UDP socket to `%s.available.gamespy.com:27900`, DNS resolve via `gethostbyname` |
| `0x00ebd3a0` | **AvailabilityCheck_Poll** | Polls `recvfrom()` for response, checks IP/port match, 2-second timeout with retry |
| `0x00ebd2f0` | **AvailabilityCheck_Close** | Closes UDP socket |
| `0x00ebd340` | **AvailabilityCheck_SendQuery** | Sends availability query packet |
| `0x00064174` | (Uses 0x6cfc) | Possibly QR2 heartbeat function |

### GP Search (Port 29901 / 0x74cd)
| Address | Function | Notes |
|---|---|---|
| `0x00ed58d8` | **GPSearch_Connect** | TCP connection to `gpsp.gamespy.com:29901` |

### Peerchat (Port 6667 / 0x1a0b)
| Address | Function | Notes |
|---|---|---|
| `0x00ee6920` | **Peerchat_Connect** | TCP connection to `peerchat.gamespy.com:6667` |

### NAT Negotiation (Port 27901 / 0x6cfd)
| Address | Function | Notes |
|---|---|---|
| `0x00edf820` | **NatNeg_Init** | Creates 2 UDP sockets, sends init packets to all 3 natneg servers |
| `0x00edf4f0` | **NatNeg_PreInit** | Pre-initialization check |
| `0x00f1bb38` | **NatNeg_SendPacket** | Send packet to natneg server (with server index 1/2/3) |
| `0x00f1ba68` | **NatNeg_SendProbe** | Send probe packet with cookie values |

### Server Browsing (Port 28910 / 0x70ee)
| Address | Function | Notes |
|---|---|---|
| `0x00ece420` | (Uses 0x70ee) | Master server browsing connection |
| `0x00edde80` | (Uses 0x70ee?) | Server query/response handler |

### PSN / NP Functions
| Address | Function | Notes |
|---|---|---|
| `0x00bda790` | **CheckPSNStatus** | Checks `sceNpManagerGetStatus()`, shows network dialog if offline |
| `0x00bda630` | **CheckParentalControls** | Content rating + chat restriction check |
| `0x00bdcd4c` | **InitGameSpy** | Called when PSN status=3 (signed in) |
| `0x00ed4d80` | **ProcessNPLookups** | Async NP lookup polling |
| `0x00ed5168` | **GetBlockListCount** | NP block list |
| `0x00ed5338` | **InitNP** | Initialize NP subsystems |
| `0x00ed5478` | **ShutdownNP** | Terminate NP subsystems |

### Other Network Functions
| Address | Function | Notes |
|---|---|---|
| `0x00712e98` | Socket wrapper | Low-level socket operations |
| `0x00712fb0` | Socket wrapper | Low-level socket operations |
| `0x00a34eac` | Network function | Contains socket/connect calls |
| `0x00a4ad08` | Network function | Contains socket/connect calls |
| `0x00ebe128` | Network function | UDP operations |
| `0x00ec45d8` | Network function | Socket operations |
| `0x00ecd030` | Network function | Socket operations |
| `0x00eef6f8` | Network function | Socket operations |
| `0x00f08b90` | Network function | Socket operations |

### GameSpy Configuration Init
| Address | Function | Notes |
|---|---|---|
| `0x0019ad38` | **InitGameSpyConfig** | Sets gamename=`civconps3`, secretkey=`hn53vx`, gameId=1616, partnerId=11000, productId=28 |
| `0x001a39a4` | **AllocConfig** | Allocates 0xAC-byte config struct |
| `0x00be29c0` | **ConfigConstructor** | Zeroes config fields +0x78 through +0x9c |

### GameSpy SOAP / Auth
| Address | Function | Notes |
|---|---|---|
| `0x00f01a20` | **wsLoginPs3Cert** | SOAP LoginPs3Cert — sends gameID=1616, namespace=19, productID=28 + PS3 ticket |
| `0x00f01ed0` | **wsLoginRemoteAuth** | SOAP LoginRemoteAuth variant |
| `0x00f02848` | **wsLoginUniqueNick** | Login with hashed password |
| `0x00f0e630` | **SoapHttpSendAsync** | Async SOAP HTTP request dispatcher |
| `0x00f148c0` | **SoapXmlBuild** | XML/SOAP document builder |
| `0x00f12e68` | **XmlOpenElement** | Opens `<ns:elementName>` |
| `0x00f134f0` | **XmlWriteInt** | Writes `<ns:field>value</ns:field>` |
| `0x00f13860` | **XmlWriteBase64** | Writes base64-encoded binary data |

### GameSpy GT2 Reliable UDP
| Address | Function | Notes |
|---|---|---|
| `0x00edc0d0` | **GT2ProcessDatagram** | Main reliable UDP processing (2476 bytes, largest net function). Sliding window, ACKs, reordering |

### GameSpy QR2 Server Reporting
| Address | Function | Notes |
|---|---|---|
| `0x00ef48e8` | **QR2Init** | Sends `\xfe\xfd\x02` init packet, creates UDP socket |
| `0x00ef4b58` | **ServerBrowserLogin** | TCP connect to master:28910, sends game credentials + random 8-byte challenge |
| `0x00ef5ba8` | **ServerBrowserMainLoop** | Receives server list, parses length-prefixed messages |
| `0x00ef0e20` | **QR2HeartbeatInit** | Sets up heartbeat with 8-byte secret key |
| `0x00ef0320` | **QR2SendHeartbeat** | Builds + sends heartbeat with player counts |
| `0x00ef07a0` | **QR2ReceiveQueries** | Processes type 0x00 (query) and 0x09 (challenge) packets |

### GameSpy NatNeg Protocol
| Address | Function | Notes |
|---|---|---|
| `0x00f1bb38` | **NatNegSendInit** | Sends 0x49-byte packet with magic `\xfd\xfc\x1e\x66\x6a\xb2\x03` |
| `0x00f1ba68` | **NatNegSendProbe** | Same format with cookie field |
| `0x00f1b620` | **NatNegReceive** | Validates 6-byte magic, processes type 0x02 (connect) and 0x0B (address check) |
| `0x00edecb0` | **NatNegNegotiateProbe** | Builds structured probe with local IP/port, sends to 4 natneg addresses |
| `0x00edefe0` | **NatNegMainLoop** | State machine: states 0-5, handles probing/data/timeout/retry |

### DNS Resolution
| Address | Function | Notes |
|---|---|---|
| `0x00bdb240` | **DNSResolveThread** | Background thread resolving 5+ GameSpy hostnames |
| `0x00bdaf50` | **LaunchDNSThread** | Creates PPU thread for DNS resolution |

### Stats/Reporting TCP
| Address | Function | Notes |
|---|---|---|
| `0x00f0acc8` | **StatsConnect** | TCP with SO_REUSEPORT for game result reporting |
| `0x00f0a998` | **StatsIOLoop** | Send/recv with optional decryption |

### Socket Utilities
| Address | Function | Notes |
|---|---|---|
| `0x00ebe128` | **SocketSelect** | `socketselect(0x400, ...)` wrapper |
| `0x00ebe6e8` | **SetNonBlocking** | `setsockopt(SO_NBIO)` |
| `0x00ebe760` | **GetLocalIP** | `cellNetCtlGetInfo(0x10)` → `inet_addr()` |
| `0x00ebefa0` | **GetMACAddress** | `cellNetCtlGetInfo(2)` → format as hex |
| `0x00ecbea0` | **TCPSendRetry** | `send()` in loop with EWOULDBLOCK handling |
| `0x00ecc158` | **TCPRecvDynamic** | `recv()` with auto-expanding buffer (16KB increments, 128KB max) |
| `0x00ecd030` | **ConnectionShutdown** | `shutdown(fd,2)` + `socketclose()` + buffer cleanup |

## Address Range Analysis

The networking code is clustered in specific address ranges:

| Range | Likely Contents |
|---|---|
| `0x00190000-0x001A0000` | GameSpy config initialization |
| `0x00060000-0x000A0000` | Game code with network callbacks |
| `0x00A10000-0x00A60000` | Multiplayer menu/lobby UI, network utility functions |
| `0x00BB0000-0x00BE0000` | PSN integration, GameSpy init, DNS resolution |
| `0x00EB0000-0x00ED0000` | Socket utilities, availability check, GT2 transport |
| `0x00ED0000-0x00EE0000` | NatNeg UDP, GP connections, NP lookup |
| `0x00EE0000-0x00F00000` | QR2/Server Browser, NatNeg protocol, voice chat |
| `0x00F00000-0x00F20000` | SOAP auth, stats reporting, NatNeg packet builders |
| `0x01150000-0x01200000` | Multiplayer match type UI, hosting/joining |
| `0x01400000+` | PS3 SDK stubs (sceNp*, cellNet*, sys_net*) |

## Key Data Structures

### Availability Check State (at PTR_s_S_S___RULER_01926148)
```
+0x00: int socket_fd (-1 = closed)
+0x05: byte address_family (2 = AF_INET)
+0x06: uint16 port (0x6cfc = 27900)
+0x08: uint32 server_ip
+0x14: byte[?] query_data
+0x19: char[?] gamename_string
+0x54: int data_length
+0x58: uint32 timestamp
+0x5C: int retry_count
+0x60: int state (0=idle, 1=error, 2=available, 3=unavailable)
+0x68: char[?] hostname_override
+0xA8: char[?] ip_override
```
