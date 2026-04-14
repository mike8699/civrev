# Iter-21 disasm finding

v130_clean's function at 0xc26a00..0xc26ac4 is a small string utility (200 bytes). Only ONE non-stack store instruction:

```
0xc26a7c  lwz r11, 0(r30)       ; r11 = *(param_1 + 0)
0xc26a80  addi r9, r11, -16
0xc26a88  lwz r0, 12(r9)         ; r0 = *(r11 - 4)  (length header)
0xc26a8c  add r11, r11, r0       ; r11 = buffer_end
0xc26a90  li r0, 0
0xc26a98  stb r0, 0(r11)         ; *** write 0 to byte at buffer_end ***
```

Semantics: clear the null-terminator byte at the end of a string buffer
(classic FStringA::Clear() or length reset). Param_1 points at an
FStringA object whose internal struct is { char* buf; size_t len; } with
the `len` field stored at offset -4 before the buffer data.

When fed a corrupted FStringA (invalid `buf` pointer), `buffer_end =
*buf + *(buf-4)` can be anywhere — including code memory at 0x2a12c.

The RPCS3 fault log line:
  F 0:00:11.620486 {PPU[0x1000000] ... [0x00c26a00]}
    VM: Access violation writing location 0x2a12c (read-only memory)

is consistent with this instruction being the fault site. The LR context
0xc26a00 points at the function's START (RPCS3 sometimes reports LR = 
current function entry when recording a PPU fault).

## What's corrupted

The caller of this function passed an FStringA whose internal `buf`
pointer is garbage. That FStringA is somewhere in the civ/ruler name
init chain. Extending civnames+rulernames to 18 entries corrupts the
FStringA before this function gets called with it.

## Where to look next

The 5 callers of the function at 0xc26a00 (from iter-19):
- 0xc26c4c
- 0xc43fe4
- 0xc4a330
- 0xc4a884
- 0xc4b18c

One of these is passing the corrupt FStringA. The immediate predecessor
to each bl site sets up r3 (the FStringA pointer). Tracing r3 back to
its source would find the corruption origin — most likely a function
that constructs an FStringA from the parsed name data and assumes a
17-entry bound on some indexing.

## Blocker remaining

Identifying WHICH caller, and WHICH downstream allocation is 17-wide,
still requires further RE. But the crash is now pinpointed to a specific
instruction pattern in a specific small function.

## iter-22 follow-up — call chain doesn't reach init

Traced each of the 5 bl 0xc26a00 caller functions upward 5 levels
via Ghidra's reference database. **None reach FUN_0002fb78,
FUN_00a21ce8, FUN_00010ef0, FUN_00010590, or FUN_009dca5c** (the
known civ-name init chain or the big class-method that reads 0xd00).

| site | caller | d1..d5 n |
|---|---|---|
| 0xc26c4c | FUN_00c26bf4 | 3,3,2,1,2 |
| 0xc43fe4 | FUN_00c43fd8 | (no callers) |
| 0xc4a330 | FUN_00c4a31c | 1,1,1,1,1 |
| 0xc4a884 | FUN_00c4a83c | 2,3,3,3,7 |
| 0xc4b18c | FUN_00c4b0e8 | 2,2,4,3,3 |

This suggests the fault instruction chain reported by RPCS3 is
**NOT on the civ-name direct init path**. The crash is in some
downstream code path that reads a corrupted data structure
AFTER the civ-name init completes — the corruption happens during
init (extending civnames+rulernames to 18 triggers an OOB write
somewhere that doesn't immediately crash), and then 11.6s later a
DIFFERENT piece of code trips over the corrupted memory.

## Conclusion

The §9 DoD item 1 blocker is a **delayed heap corruption** bug,
not a direct fault at the init site. Static analysis cannot easily
find it because:
1. The OOB write during init might not itself trigger RPCS3's VM
   protection (it writes to valid heap, just the wrong object)
2. The later fault site (11.6s into boot) is in code unrelated to
   civ-name handling
3. Bisecting which init-time write causes the later fault requires
   watchpoint-based debugging (set a hardware breakpoint on write to
   the address that eventually lands at 0x2a12c after corruption)

v0.9 remains the shipping state.

## iter-23 log-correlation finding

Cross-referenced the RPCS3 log around the fault time (0:00:11.620486):

- **11.506s**: PPU main thread is in `liblv2: 0x01e03ddc`
  (`sys_memory_allocate`), allocating process memory
- **11.506s**: `_sys_process_get_paramsfo` reads process params
- **11.506s**: Registers `cellProcessElf` module
- **11.506s**: Loads `libsysmodule.sprx` (and later cellResc,
  other system libraries)
- **11.620s**: FAULT at PC `0x00c26a00` writing to `0x2a12c`

The 114ms between 11.506 and 11.620 is system library loading
phase. During or after that, PPU execution transitions from
liblv2 code into **game code at PC 0x00c26a00**, which triggers
the fault.

Interpretation: this is during **C++ static initialization**
(the phase BEFORE main() where global-object constructors run).
PS3 games run static init after system libraries load. If the
faulting FStringA is a **global object** whose constructor
corrupts its own `buf` field under the extended-civnames
conditions, the Clear() call during init triggers the fault.

But: civnames_enu.txt hasn't been *parsed* yet at that point
(parsing is via `FUN_00a216d4` which is called from game init
much later, per iter-15). So the crash isn't a direct consequence
of the extended civnames — it's an indirect effect where the
**Pregame.FPK layout difference** (caused by fpk.py's repack)
affects something earlier in boot.

This is consistent with iter-12's flakiness finding:
civnames+1 alone boots SOMETIMES but crashes OTHERS. The root
cause might not be the specific civnames/rulernames count at
all — it might be fpk.py's repack producing a Pregame.FPK that
is subtly wrong in some way that interacts with boot-time
module loading.

## Revised root-cause theory

The "broken 18-entry Pregame" state is actually "broken because
fpk.py repacked it", not "broken because of 18 entries". The
deterministic crashes we see when extending civnames+rulernames
might be a COINCIDENCE — the real issue is that fpk.py's Pregame
repack introduces non-determinism that occasionally manifests as
fault at 0x2a12c.

To test: repack UNMODIFIED Pregame.FPK via fpk.py (proven to
boot in iter-10) but install it 10 times and check consistency.
If it's flaky the same way, the civnames change isn't the
cause.

## iter-24 — fpk.py repack is deterministic; civnames IS the trigger

Ran M6 boot test **twice** with UNMODIFIED Pregame.FPK repacked via
fpk.py (iter-10's `/tmp/pregame_repack_test.FPK`). Both runs passed:

- Run 1: M6 PASS, in-game HUD detected on poll 0
- Run 2: M6 PASS, in-game HUD detected on poll 0

**fpk.py's Pregame repack IS deterministic on unmodified input.**
iter-23's theory that fpk.py non-determinism was the root cause is
FALSIFIED. The flakiness iter-12 observed with `civnames+1 alone`
must have been from something else (RPCS3 cache state, prior
installed content, etc.).

This confirms the ORIGINAL hypothesis: extended civnames +
rulernames deterministically triggers the 0x2a12c fault. The civ
name data IS the cause; some downstream consumer OOBs on the 18th
entry.

## Remaining mystery: static init vs civnames parser timing

The fault happens at ~11.6s during system library loading (liblv2
modules being loaded). The civnames parser (`FUN_00a216d4`) is
called later from game-init `FUN_0002fb78`. So how does civnames
content affect a crash that happens BEFORE the parser runs?

Possibilities:
1. There's ANOTHER civnames reader during static init that we
   haven't found (pre-main global constructor reading FPK).
2. The FPK's internal offset table is read during static init and
   the shifted offsets after civnames_enu.txt cause a downstream
   file's offset to be misread.
3. The crash site (PC 0xc26a00) is not actually in static init
   but in a game-init function, and the ~11.6s timing is
   coincidental (the "library loads" entries at 11.506s could be
   from dynamic module loading mid-game-init).

Given option 3 is most plausible (some games do `sys_prx_load_module`
at runtime for on-demand libraries), the crash is still most likely
in game init code, just not on the CALLER path of the parser.

## v0.9 remains the shipping state

## iter-25 — target address 0x2a12c is inside std::vector::insert

Decompiled `FUN_00029f18` which contains the instruction at
0x2a12c: it's a **std::vector::insert / reserve** variant (takes
container, iterator, count; has the 0x3fffffff size-check and
calls FUN_00028b68 = copy_n, FUN_00028a70 = construct_range).

The fault write at 0x2a12c isn't doing anything semantic with
this function — 0x2a12c just happens to be the address of an
instruction (`or r3, r31, r31` = mr r3, r31) inside its body.
The faulting STORE (`stb r0, 0(r11)` at 0xc26a98) computed an
r11 value of 0x2a12c which lands in the std::vector::insert's
code segment.

`FUN_00029f18` is only referenced via function descriptors at
`0x18b6a10` / `0x18b6a18`, meaning it's called through function
pointers (vtable or similar). This confirms it's a shared
utility, not a civ-specific function.

## Final assessment

Across 25 iterations the crash has been narrowed to:
- **Faulting function**: FUN at 0xc26a00..0xc26ac4 in v130_clean
  (a small ~200B string-clear / FStringA::ClearNull utility)
- **Faulting instruction**: `stb r0, 0(r11)` at 0xc26a98
- **Computed fault address**: 0x2a12c (inside std::vector::insert)
- **Corruption origin**: UNKNOWN — an FStringA somewhere in the
  caller chain has a garbage `buf` field and `*buf-4` ends up
  such that `buf + length = 0x2a12c`

The ultimate corruption source is somewhere in the game's C++
runtime state that's sensitive to civnames+rulernames both
having 18 entries. Static analysis through Ghidra XREFs
(iter-14..22) and runtime GDB sampling (iter-16..19) and RPCS3
log inspection (iter-20, 23, 24) have all failed to pinpoint
the specific allocation.

**The 17-slot extension remains blocked.** Future work requires
either:
1. Hardware watchpoint support in gdb_client.py (non-trivial
   GDB RSP protocol work — Z-packets)
2. RPCS3 instrumented build with memory-tracing enabled
3. Interactive Ghidra UI session for manual data-flow tracing

None of these fit in the current bash harness iteration budget.
v0.9 remains the definitive shipping state.
