# iter-203: all 18 civs + 18 rulers verified in runtime buffer; Korea at index 16

**Date:** 2026-04-15
**Tool:** new `test_civs_dump.py` via `docker_run.sh civs_dump`.

## What iter-203 verified at runtime

Using the iter-202-corrected `.bss` buffer holders
(`0x1ac93b8` for civs, `0x1ac93b4` for rulers), connected GDB at
main menu and walked each buffer's 18 × 12-byte entries. The entry
layout is confirmed to be `{u32 gender, u32 plurality, u32 fstring_ptr}`.
FStringA data is **inline at offset 0** (small-string optimization
— read bytes directly at the FStringA address, no indirection).

**Full civs table (buffer @ `0x4002a0e0`, count=18):**

| idx | flags | FStringA ptr | name |
|---|---|---|---|
| 0  | MP | 0x40029580 | Romans |
| 1  | MP | 0x400295b0 | Egyptians |
| 2  | MP | 0x400295e0 | Greeks |
| 3  | MP | 0x40029610 | Spanish |
| 4  | MP | 0x40029640 | Germans |
| 5  | MP | 0x40029670 | Russians |
| 6  | MP | 0x400296a0 | Chinese |
| 7  | MP | 0x400296d0 | Americans |
| 8  | MP | 0x40029700 | Japanese |
| 9  | MP | 0x40029730 | French |
| 10 | MP | 0x40029760 | Indians |
| 11 | MP | 0x40029790 | Arabs |
| 12 | MP | 0x400297c0 | Aztecs |
| 13 | MP | 0x400297f0 | Zulu |
| 14 | MP | 0x40029820 | Mongols |
| 15 | MP | 0x40029850 | English |
| **16** | **MP** | **0x40029880** | **Koreans** |
| 17 | MP | 0x400298b0 | Barbarians |

**Full rulers table (buffer @ `0x4002a004`, count=18):**

| idx | flags | FStringA ptr | name |
|---|---|---|---|
| 0  | MS | 0x40029250 | Caesar |
| 1  | FS | 0x40029220 | Cleopatra |
| 2  | MS | 0x40029280 | Alexander |
| 3  | FS | 0x400292b0 | Isabella |
| 4  | MS | 0x400292e0 | Bismarck |
| 5  | FS | 0x40029310 | Catherine |
| 6  | MS | 0x40029340 | Mao |
| 7  | MS | 0x40029370 | Lincoln |
| 8  | MS | 0x400293a0 | Tokugawa |
| 9  | MS | 0x400293d0 | Napoleon |
| 10 | MS | 0x40029400 | Gandhi |
| 11 | MS | 0x40029430 | Saladin |
| 12 | MS | 0x40029460 | Montezuma |
| 13 | MS | 0x40029490 | Shaka |
| 14 | MS | 0x400294c0 | Genghis Khan |
| 15 | FS | 0x400294f0 | Elizabeth |
| **16** | **MS** | **0x40029520** | **Sejong** |
| 17 | MS | 0x40029550 | Grey Wolf |

Korea and Sejong are **both** at their expected index 16, with
correct gender/plurality flags derived from the "MP" / "M" tags
in the overlay .txt files. This is the first end-to-end runtime
verification that iter-198's 18-row overlay flows all the way
through the parser to the output buffer exactly as designed.

## Main-menu memory scan result

Scanned `.data` (`0x1870000..0x198be78`, ~1.1 MB) and `.bss`
(`0x198be78..0x1bd5f38`, ~3.4 MB) for any 4-byte-aligned u32 BE
equal to:
- Korea's FStringA pointer `0x40029880`
- Sejong's FStringA pointer `0x40029520`
- Civs buffer base `0x4002a0e0`
- Rulers buffer base `0x4002a004`

**Hits:**
- Korea FStringA ptr: **0 unique**
- Sejong FStringA ptr: **0 unique**
- Civs buffer base: **1 unique** (`0x1ac93b8` — the known holder)
- Rulers buffer base: **1 unique** (`0x1ac93b4` — the known holder)

At main menu, **no memory location outside the known parser
buffer holders stores a cached pointer to the civnames buffer or
to any individual civ's FStringA.** The carousel and any other
consumer haven't touched this data yet.

(Earlier reports of "6 hits" were from a scanning bug where
overlapping 32 KB chunks counted each match multiple times. Fixed
by deduplicating.)

## Civ-select scan: attempted, hung

Attempted to extend the probe to reconnect GDB after navigating
to civ-select and re-scan. The probe hung in `poll_s` (waiting on
a socket) partway through navigation. Root cause not yet
identified — possibilities include a PSN sign-in popup stealing
focus, RPCS3 input drop, or an OCR subprocess hang. The 2-phase
scan result is NOT captured for this iteration. iter-204 will
retry with a more resilient navigator (or skip navigation and
use Z0 code breakpoints instead).

## Current anchors

Known good, from iter-202 + iter-203:

```python
KOREA_MOD_PARSER_DISPATCHER = 0xa2ec54
KOREA_MOD_PARSER_WORKER     = 0xa2e640
KOREA_MOD_PARSER_DISPATCHER_TOC_BASE = 0x0194a1f8
KOREA_MOD_PARSER_DISPATCHER_DESCRIPTOR = 0x018f0380

KOREA_MOD_CIVS_BUFFER_HOLDER   = 0x01ac93b8   # .bss
KOREA_MOD_RULERS_BUFFER_HOLDER = 0x01ac93b4   # .bss
```

Runtime (at main menu with iter-198 shipping build):

```
*(0x1ac93b8) = 0x4002a0e0   # civs buffer base, heap
*(0x1ac93b4) = 0x4002a004   # rulers buffer base, heap
count @ (civs - 4)   = 18
count @ (rulers - 4) = 18
entry layout: {u32 gender, u32 plurality, u32 fstring_ptr}  // 12 bytes
FStringA layout: inline ASCII at offset 0 (SSO)
```

## iter-204 plan

1. Fix the probe's civ-select phase. Make navigation non-hanging
   (add per-step timeouts, guard against PSN popup, flush stdout
   so progress is visible in docker logs).
2. Run the full 2-phase scan and observe what caches appear
   AFTER the civ-select carousel loads. If new caches appear in
   .data/.bss, those are the carousel's state. If not, the
   carousel holds its state only on the heap.
3. If nothing cached in .data/.bss: fall back to Z0 breakpoints
   at specific candidate code sites that dereference
   `*(0x1ac93b8)` → buffer base. Those sites can be found by
   searching the binary for lwz loads of 0x1ac93b8 either
   directly (as u32 immediate) or via TOC with the corrected r2.

## Files

- `civs_dump_main_menu.json` — the complete 18-entry dump of both
  buffers with gender/plurality/FString contents for each
- `findings.md` — this
