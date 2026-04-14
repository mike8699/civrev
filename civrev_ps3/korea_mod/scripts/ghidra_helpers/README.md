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

Jython 2.7 — use `%`-formatting, never f-strings.
