# iter-201: RPCS3 GDB stub rejects Z2/Z3/Z4 watchpoints; TOC mapping from iter-197 is wrong

**Date:** 2026-04-15
**Tool:** new `test_civs_watchpoint.py` driven via `docker_run.sh
civs_watch`.

## What the probe did

1. Launched RPCS3 with the iter-198 build (18-row civnames +
   Korea at expected index 16).
2. Reached the main menu (parser guaranteed to have run).
3. Attached the GDB stub, paused.
4. Read the alleged civs-buffer-pointer TOC slot at
   `r2 + 0x141c` = `0x193b6a4` to capture the runtime buffer
   pointer.
5. Tried to install an access (Z4), then read (Z3), then write
   (Z2) watchpoint on Korea's entry at `buf + 16*12`.
6. Resumed and drove navigation to civ-select.
7. Polled all threads during civ-select for watchpoint hits
   and thread PCs.

## Results

```json
{
  "civs_buf_ptr_slot": "0x193b6a4",
  "runtime_buf_ptr": "0x1695660",
  "buffer_count": 0,
  "korea_entry_addr": "0x1695720",
  "korea_fstring_ptr": "0x626c6974",
  "watchpoint_kind": null,
  "watchpoint_set": false
}
```

Two big takeaways:

### 1) RPCS3's GDB stub rejects ALL three Z-packet watchpoint types

Z4 (access), Z3 (read), and Z2 (write) ALL returned "not OK" when
sent against `0x1695720` (Korea's expected entry address). None
of them installed. The stub accepts `m` (memory read), `g` / `p`
(register read), and `\x03` (break) but not Z-packet watchpoints.
This is a **hard** capability gap, not a parameter mistake —
iter-201 tried all three addresses in fallback order.

PRD §6.2 EXECUTE block said "extend `gdb_client.py` with Z2
watchpoint support" — that's already in the file. The wrapper is
correct; the stub just rejects the packet.

**Implication for further dynamic work:** only **software
breakpoints (Z0)** and pause/read memory are available. Watchpoint
observation of data reads/writes isn't. Every dynamic probe must
be a Z0-breakpoint-at-a-known-PC trace, not a data-address
tripwire.

### 2) iter-197's TOC-slot mapping was wrong for at least half the slots

The runtime value of `*(0x193b6a4)` came back as `0x1695660`. I
assumed this was the civs parser-buffer-holder global. But reading
the bytes at `0x1695660` returned `"CANCEL\0\0%d%s%s\0\0SetCredits
\0\0\0\0\0\0\0\0GFX_CreditsScreen.gfx\0\0\0this.theLeaderNu..."` —
raw rodata string literals (one null-terminator after another in a
constant pool).

Cross-checked against the ELF: `0x1695660` is the start of a
rodata literal `"CANCEL"` (preceded by `"...ollerDisplay\0\0\0\0"`
and followed by `"%d%s%s"` etc.). It is NOT a writable data global.

Worse — a segment-permissions scan of all 8 supposed "buffer
holder" TOC slots (`r2 + 0x1400..0x141c`) finds only 4 pointing
to writable regions (.bss/.data) and 4 pointing into R-X rodata:

| TOC slot    | value       | segment   |
|-------------|-------------|-----------|
| `r2+0x1400` | `0x198bf10` | .bss RW   |
| `r2+0x1404` | `0x188c258` | .data RW  |
| `r2+0x1408` | `0x1886610` | .data RW  |
| `r2+0x140c` | `0x169c910` | rodata R-X |
| `r2+0x1410` | `0x1693fd0` | rodata R-X |
| `r2+0x1414` | `0x1694a80` | rodata R-X |
| `r2+0x1418` | `0x1b1e4b4` | .bss RW   |
| `r2+0x141c` | `0x1695660` | rodata R-X |

The 4 slots pointing at rodata cannot be the destinations of the
parser worker's `*param_2 = new_buf_ptr` write. iter-197's
identification of "civs buffer holder at `r2+0x141c`" is wrong.

**Most likely correct mapping:** only `0x1400`, `0x1404`, `0x1408`,
`0x1418` are actual buffer holders. The other 4 TOC slots
(including the one I called "civs") are pointers to Scaleform
variable-name strings or similar, and the dispatcher at `0xa2ec54`
is polymorphic — sometimes `bl 0xa2e640` is a parser call, other
times it's a string-pool lookup or something similar.

**Or** `0xa2e640` isn't actually the parser worker at all for the
civs call site. The `li r5, 0x11` pattern near `0xa2ee7c` might
belong to a completely different function, and iter-14's "civs
count" patch at `0xa2ee7c` might have zero effect on the real
civnames parser.

Either way: **the iter-197 decompile of "real_parser_dispatcher"
was misread.** iter-198's success at booting with 18-row civnames
suggests the iter-14 patch at `0xa2ee7c` is a no-op for the real
parser, and the real civnames parser lives elsewhere (perhaps the
one at `0xa21ce8` / `0xa216d4` that the addresses.py file
references as `KOREA_MOD_INIT_GENDERED_NAMES_DISPATCH` /
`_WORKER` — the one iter-14 ORIGINALLY found, not the "real
dispatcher" renaming from iter-18..22 era).

## iter-202 plan

**Pivot #1: re-ID the parser.** Go back to
`FUN_00a21ce8` / `FUN_00a216d4` (addresses.py's original naming)
as the primary candidates. Decompile both, confirm they're what
iter-14 was patching. The `KOREA_MOD_RULERNAMES_COUNT_LI_R5_SITE`
at `0xa2ee38` and `KOREA_MOD_CIVNAMES_COUNT_LI_R5_SITE` at
`0xa2ee7c` may be inside a DIFFERENT function than I decompiled
in iter-197. iter-197 decompiled 0xa2e640 and 0xa2ec54 naming them
"real_parser_worker" and "real_parser_dispatcher", but the
addresses.py comment points at `0xa21ce8` / `0xa216d4`.

**Pivot #2: use Z0 breakpoints for dynamic probing.** Set a code
breakpoint at `0xa2ee80` (the supposed "civs" BL site) and read
r4 at the hit — see what argument is actually passed at runtime.
If r4 = `0x1695660` (the rodata string), the call isn't parsing
civnames at all. If r4 is a different dynamic address, follow it
to find the real civs buffer.

**Pivot #3: set Z0 on the ACTUAL civnames parser.** If iter-14's
original finding at `0xa21ce8` is correct, set Z0 there, capture
what r4/r5/r6 are when it's called, and trace the write path.

## What iter-201 DID unblock

The test harness now has a working `test_civs_watchpoint.py`
template for any future "launch RPCS3, attach GDB, read memory
by virtual address, drive UI" probe. The GDB attach + memory
read + screenshot pipeline all work end-to-end. Future probes
can fork this file without re-plumbing the Docker glue.

Also: `docker_run.sh civs_watch` is now a registered test mode.

## Files

- `iter201_result.json`
- `findings.md` (this)
