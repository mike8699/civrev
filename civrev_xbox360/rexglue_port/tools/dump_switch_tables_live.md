# Regenerating `civrev/switch_tables_manual.toml` (live-memory switch-table dump)

## Why this exists

ReXGlue's static analysis under-populates the jump tables of a family of
middleware "message dispatcher" functions (`cmplwi rIDX,N; bgt <other-fn>;
lis/addi rB,<table>; rlwinm r0,rIDX,2,0,29; lwzx r0,rB,r0; mtctr; bctr`, with
the table data placed **immediately after the bctr**). The generated C++ then
contains a `switch` with only the case(s) the analyzer proved, and
`default: __builtin_trap()`.

Symptom when the game hits an unproved case: the thread executes `ud2`, the
runtime exception handler returns without advancing the PC, and the thread
**silently spins forever** at one instruction. First observed: starting any
game hangs on the Loading screen — `CivConsole` thread spinning in
`sub_82DAD720` (knew case 0 of 221; the game sent a different message id).
Diagnosis artifacts: gdb `thread apply all bt` shows the thread ON-CPU in guest
code (not in a futex wait); `x/i $pc` shows `ud2`.

XenonRecomp also failed on these tables (`// ERROR 82DAD720` in its corpus),
so the XenonAnalyse `switch_tables.toml` has no entry either — the only
authoritative source found is **the mapped module in a running process**.

## Procedure

1. Decode every trap-default dispatcher's `(bctr address, table address,
   count=guard+1, index register)` from the generated sources by walking the
   1:1 instruction comments (see the session script; the shape is the
   lis/addi + lwzx + mtctr + bctr idiom above; count comes from the
   `cmplwi cr?,rIDX,BOUND` guard).
2. Boot the port headlessly (`run_port.sh --timeout 120`) and wait for
   `Preparing module launch` in run.log — the XEX sections are then mapped at
   host address `0x100000000 + guest_addr`.
3. `gdb -p $(cat /output/game.pid) -batch -x dump.gdb` inside the container,
   where dump.gdb is one `x/<count>wx 0x1<table_addr>` per table.
4. Byteswap each dumped word (gdb shows little-endian words of big-endian
   data). Validate every label: word-aligned and within `[0x82000000,
   0x83000000)`; skip the dispatcher entirely on any failure.
5. Emit `[[switch_tables]]` entries (`address` = bctr, `register`, `labels`),
   dedup by bctr address; include the file from `civrev_manifest.toml`.

Verified invariants from the 2026-07-12 run: 884 dispatchers decoded, 877
unique bctr sites, ZERO validation failures; `sub_82DAD720` = 221 labels of
which only 2 targets (0x82DAE52C for id 2300, 0x82DAD564 for everything else).
