# Ghidra Jython helpers

Headless post-scripts used by iter-11..26 of the 17-slot extension
investigation. Run via `analyzeHeadless` against `civrev.gpr`.

- `FindLi17Sites.py` — walks `FUN_00a21ce8` (name-file init dispatcher),
  finds every `bl FUN_00a216d4`, and dumps the preceding `li r5, N`
  count argument. Used to locate the two `li r5, 0x11` sites at
  `0xa2ee38` / `0xa2ee7c` that iter-14 patched.
- `DecompFn.py` — decompiles a hardcoded candidate list and greps the
  C output for name-file / count-constant keywords. Iter-15 tool.
- `FindCityInit.py` — scans for the city-init consumer of
  `RulerNames_`. Iter-22 tool; came up empty (consumer path doesn't
  match static cmpwi-17 pattern).
- `TraceCallers.py` — for each candidate "fault-site" address in
  v130_clean, walks reference-to chains up to depth 5 looking for
  any caller that connects back to a known init function entry.
  Iter-26 tool; came up empty (the v130_clean caller graph doesn't
  reach the init code path via static call references — the link
  must be via function-pointer / vtable indirection that Ghidra's
  static refs miss).

Jython 2.7 — use `%`-formatting, never f-strings.
