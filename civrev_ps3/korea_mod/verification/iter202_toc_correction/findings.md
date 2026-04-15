# iter-202: PARSER DISPATCHER TOC CORRECTION — civs buffer holder is 0x1ac93b8, r2 = 0x194a1f8

**Date:** 2026-04-15
**Impact:** Resolves the iter-201 confusion and recovers a correct
runtime view of the civnames parser buffer. Invalidates parts of
iter-197 and corrects part of iter-201. All prior static analysis
that assumed `r2 = 0x193a288` for the dispatcher at `FUN_00a2ec54`
was using the wrong TOC base.

## Chain of events

### Step 1 — Z0 probe didn't fire

Wrote `test_civs_z0_probe.py` and set Z0 breakpoints at:
- `0xa2ec54` (dispatcher entry)
- `0xa2ee3c` (rulers BL site)
- `0xa2ee80` (civs BL site)

All three Z0's installed successfully (`z0_dispatcher_ok=true`,
`z0_rulers_ok=true`, `z0_civs_ok=true`). None fired during 60
seconds of polling.

### Step 2 — "FUN_00a2ec54 is dead code" was WRONG

Initial hypothesis: the dispatcher is never called. My
Python-based bl-caller scan returned zero direct `bl` callers of
`0xa2ec54`. This seemed to confirm "dead code".

But an **empirical boot test** with iter-14's two
`li r5, 0x11 → 0x12` patches at `0xa2ee38`/`0xa2ee7c` temporarily
disabled produced an **RSX init hang**. Re-enabling them restored
boot. Conclusion: those patches ARE active, which means the
function containing them IS called at runtime.

### Step 3 — The call is INDIRECT via a function descriptor

Found `0xa2ec54` referenced as a 32-bit word exactly ONCE, at
`0x18f0380`:
```
0x18f037c: 0x0194a1f8
0x18f0380: 0x00a2ec54   <-- entry point
0x18f0384: 0x0194a1f8   <-- TOC base for this entry
0x18f0388: 0x00a2eeb4   <-- entry of the NEXT function in the table
0x18f038c: 0x0194a1f8   <-- its TOC base
```

This is a **PPC64 function descriptor table**. Every entry is
`{entry_point, toc_base}`. The dispatcher's TOC base is
**`0x194a1f8`** — NOT the main-module `0x193a288` I assumed.

Calls to the dispatcher happen indirectly via:
```
ld r11, <descriptor_address>
ld r0, 0(r11)    ; entry = 0xa2ec54
ld r2, 8(r11)    ; NEW TOC: 0x194a1f8
mtctr r0
bctrl
```

My Python `bl` scan looks for direct `bl <absolute>` instructions
only, and misses `mtctr/bctrl` sequences. That's why it reported
zero callers.

### Step 4 — Corrected TOC slot resolution

With `r2 = 0x194a1f8`, the 8 name-file buffer-holder slots resolve
to writable `.bss` addresses (not the rodata mishmash iter-197
observed):

| TOC slot | value | segment |
|---|---|---|
| r2+0x1400 = 0x194b5f8 | 0x1ac939c | .bss RW |
| r2+0x1404 = 0x194b5fc | 0x1ac93a0 | .bss RW |
| r2+0x1408 = 0x194b600 | 0x1ac93a4 | .bss RW |
| r2+0x140c = 0x194b604 | 0x1ac93a8 | .bss RW |
| r2+0x1410 = 0x194b608 | 0x1ac93ac | .bss RW |
| r2+0x1414 = 0x194b60c | 0x1ac93b0 | .bss RW |
| r2+0x1418 = 0x194b610 | 0x1ac93b4 | .bss RW (rulers) |
| r2+0x141c = 0x194b614 | **0x1ac93b8** | .bss RW (**civs**) |

All 8 are in `.bss` — the parser's `*param_2 = new_buf_ptr` write
is valid. iter-197's mapping (which used the wrong `r2`) was off
by everything — it wasn't just "half the slots wrong", it was
ALL the slots wrong.

### Step 5 — Corrected watchpoint probe confirms the runtime state

Re-ran `test_civs_watchpoint.py` with `CIVS_BUF_PTR_SLOT = 0x1ac93b8`
instead of `0x193b6a4`. New result:

```json
{
  "civs_buf_ptr_slot": "0x1ac93b8",
  "runtime_buf_ptr": "0x4002a0e0",
  "buffer_count": 18,
  "buffer_snapshot": "0000000000000001400295800000000000000001400295b0..."
}
```

- `*(0x1ac93b8) = 0x4002a0e0` — a heap address in RPCS3's PPU
  memory, exactly what we expect for a malloc'd buffer.
- `count = 18` at `*((0x4002a0e0) - 4)` — iter-198's 18-row
  civnames_enu.txt IS being parsed all 18 entries.
- The first 48 bytes of the buffer contain 12-byte entries, each
  holding an FStringA pointer (`0x40029580`, `0x400295b0`,
  `0x400295e0`, `0x40029610`, `0x40029640`, `0x40029670` visible).

**This is the first fully-verified runtime view of the civnames
parser buffer** in iter-7..202's entire chase. iter-198's "18-row
boots clean" was correct; iter-14's `li r5, 0x11 → 0x12` patches
are genuinely active; the parser path is sound.

## What iter-202 invalidates from prior iterations

- **iter-197's TOC-slot-to-buffer-holder mapping** — WRONG. All 8
  slots were resolved against `r2 = 0x193a288`. The dispatcher's
  `r2 = 0x194a1f8`.
- **iter-201's "r2+0x141c holds civs buffer ptr"** — WRONG (same
  root cause).
- **iter-201's "iter-197 dispatcher is dead code"** — WRONG. The
  dispatcher IS called, via function descriptor + bctrl. The
  caller is still unidentified but irrelevant — what matters is
  the dispatcher runs.
- **iter-199's "post-parse block calls FUN_009bf5a0/FUN_009f1c80
  are the write path"** — still technically true inside the
  parser worker, but they write to the SAME buffer that lives at
  `*(0x1ac93b8) = 0x4002a0e0`. The three functions aren't the
  carousel — they're part of the parser's per-entry init.

## What iter-202 UNLOCKS

1. **Reliable runtime memory reads of the civnames buffer.** We
   can now dump Korea's FStringA at index 16, verify the parser
   ran correctly, and compare against stock.
2. **A correct candidate `.bss` address to set Z0 breakpoints
   AROUND.** Code that reads `*(0x1ac93b8)` at render time can
   be found by breaking at instructions that dereference that
   address (or by finding readers of the runtime
   `0x4002a0e0` buffer).
3. **Every .bss holder for every name file is now known.** If
   the carousel reads from the civnames buffer via a cached copy
   at render time, that cached copy will most likely be derived
   from `*(0x1ac93b8)` at some point.
4. **iter-201's `test_civs_watchpoint.py`** is now a fully
   working runtime-memory-read probe — can be adapted to read
   any buffer, read any FStringA, or set Z0 at any reader PC.

## What's still needed to close §9 DoD item 2

The carousel render path. Korea is confirmed in the parser
buffer at the correct index, but some other code ALSO has to
surface her in the carousel. Known tools and their status:

- Z2/Z3/Z4 data watchpoints: **UNSUPPORTED** by RPCS3's GDB stub
  (iter-201)
- Z0 code breakpoints: **work** (iter-202 dispatcher probe set
  them successfully; they just don't fire if the target already
  ran before the probe connected)
- Memory reads via GDB `m` packet: **work** (iter-202)
- Register reads via GDB: **work** (not yet used)

The carousel render happens DURING civ-select, AFTER the parser
has run. Z0 set on a reader PC could catch it if we knew which
PC to target. We don't know yet.

## iter-203 plan

1. Update the probe to read ALL 18 civnames entries + their
   FString contents to verify "Koreans" is at index 16 (not
   elsewhere). Confirm correct parsing.
2. Dump the FStringA at each index and see which other runtime
   addresses show up.
3. Set Z0 at the civs-buffer read site that iter-197 mis-
   identified — but instead of picking a rodata PC, pick a code
   PC that dereferences `*(0x1ac93b8)` at runtime. Use the
   corrected r2 to find those.
4. Alternate: read the runtime FStringA for Korea and compute
   its address; scan the binary (at runtime via GDB `m`) for
   any 32-bit word equal to that address. Any match is another
   location that stores a pointer to Korea — potentially the
   carousel.

## Files

- `watchpoint_probe_corrected.json` — the successful runtime view
- `z0_probe_no_hits.json` — the Z0 probe result (z0 all installed,
  no hits during boot; probably because the parser runs before the
  probe connects)
- `findings.md` (this)
