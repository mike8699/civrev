# Iter-12 — civnames / rulernames pair-dependency pinned

## Experiments

Five boot tests against `EBOOT_korea.ELF` + different `Pregame.FPK`
variants (fpk.py repack from unmodified `extracted/Pregame/` + an
edit applied to one or more text files):

| Variant | civnames | rulernames | famousnames | Boots? |
|---|---|---|---|---|
| stock_repack | 17 | 17 | 46 | **yes** |
| famousnames +1 | 17 | 17 | 47 | **yes** |
| civnames +1 | 18 | 17 | 46 | yes (first run); flaky on retry |
| civnames +2 | 19 | 17 | 46 | **yes** |
| rulernames +1 | 17 | 18 | 46 | **yes** |
| **civnames +1 AND rulernames +1** | **18** | **18** | 46 | **NO — 300s RSX timeout** |

## Finding

The crash signature is **specific to simultaneous civnames +
rulernames extensions**, not to either file alone:

- `famousnames_enu.txt` accepts a 48th entry fine — the name-file
  parser is generic and handles variable counts.
- `civnames_enu.txt` alone accepts up to 19 entries (one tested) and
  boot succeeds, though the test sometimes times out on re-runs
  (cache flakiness?).
- `rulernames_enu.txt` alone accepts 18 entries and boot succeeds.
- **Only the combination of civnames≥18 AND rulernames≥18 crashes
  RSX init consistently.** iter-7 (text.ini with "Value = Korean"
  appended to [CIVNAMEP]) and iter-10 (both files extended by one)
  hit the same signature.

## Hypothesis

Somewhere in the boot-time civ-table initialization, the game pairs
`civnames[i]` with `rulernames[i]` in lockstep. When both files
have 18 entries, the loop iterates to index 17 and writes to some
other per-civ table (leaderhead, portrait, bonuses, AI
personality — any of our iter-4 "dead rodata" candidates) which is
only 17-wide, producing an out-of-bounds write that corrupts the
graph subsystem (hence RSX init timeout rather than a clean
assertion crash).

When only ONE file has 18 entries, the count-mismatch check gates
the pair-init loop at `min(civ_count, ruler_count) = 17` and we
never touch index 17 of the downstream table.

## Consequence for v1.0 DoD

This finding does not unblock the true 17-slot extension. To land
a §9 DoD-compliant Korea mod, the following must all happen
in one atomic EBOOT patch set:

1. Bump the civ-select cursor's right-clamp from 17 → 18 slots
   (instruction address unknown).
2. Bump whichever per-civ table is 17-wide to 18 slots — either
   relocate and extend it to avoid the pair-init OOB, or bump the
   pair-init loop's upper bound so it doesn't touch index 17.
3. Extend civnames_enu.txt and rulernames_enu.txt together (now
   safe, because (2) removed the OOB write).
4. Clone England's per-civ bonus/UU data into the new slot 16.

Step (2) is the hard one. We don't know which table is the 17-wide
gate, and without Ghidra UI XREFs we can't locate the pair-init
function. The candidate tables are the five rodata arrays mapped
in §5.2 (LEADER_NAME_PTR_ARRAY, CIV_TAG_ARRAY, LDR_TAG_ARRAY,
ADJ_PAIR_ARRAY, and ADJ_FLAT) — four of which we confirmed "dead
rodata" in iter-4 but which might actually be accessed via the
pair-init path we haven't located.

## v0.9 still ships

Restoring the iter-8 byte-patched Pregame.FPK still boots cleanly
(verified at the end of iter-12), so v0.9's Korea-replaces-England
form remains the shipping state for the mod.

## §7.7 stop maintained

iter-12 has produced additional diagnostic detail but has NOT
unblocked the 17-slot extension. Three iterations (iter-7,
iter-10, iter-12) now show the same boot-timeout signature under
the "extend both civnames and rulernames" approach. Per PRD §7.7,
this is a stop condition — continuing blind-patching without
Ghidra UI or live GDB will not produce progress.
