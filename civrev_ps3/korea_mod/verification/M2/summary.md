# M2 result — iter-5

**Status:** FAIL (Korea not visible on civ-select)

## Key finding: the civ-select carousel has 17 slots natively

The game's civ-select screen has **16 civs + 1 "Random" slot = 17 total
positions**. The "Random" slot lives at index 16 and displays a question-
mark silhouette with text "Random / Random / This will randomly choose a
civilization".

Screenshots:
- `slot_15_elizabeth.png` — Elizabeth/English at slot 15 (last real civ)
- `slot_16_random.png` — Random slot at slot 16, clamps cursor; Right
  presses from this position are no-ops

## What this means for the mod

Our `xml_overlays/leaderheads.xml` adds `<LeaderHead Nationality="16"
Text="Sejong" .../>` but **slot 16 is already used by the Random slot**.
The leaderheads.xml parser probably drops our 17th entry (or renders it
somewhere we can't reach), and the cursor treats Random as the terminal
slot.

Also: our EBOOT patch extended `ADJ_FLAT` to 17 entries, adding "Korean"
at index 16. If any live adjective lookup uses index 16 right now, it
would now read "Korean" instead of whatever the Random slot's placeholder
string is. This may produce visible bugs — not yet verified.

## Next steps (iter-6)

1. **Reindex Korea to slot 17.** Change leaderheads.xml
   `Nationality="16"` → `Nationality="17"` and move the EBOOT patch's
   extra adjective to index 17 (requires extending ADJ_FLAT to 18 entries
   — 16 real civs + 1 Random placeholder + 1 Korea).
2. **OR** find and patch the civ-select screen's loop that decides how
   many slots are reachable. If it's a hardcoded `< 17` upper bound
   anywhere, bump it to `< 18`.
3. **Verify whether leaderheads.xml's 17th entry is actually parsed** by
   looking for "Sejong" in the live runtime data. Attach RPCS3 GDB stub
   after the XML loader runs and grep memory for `Sejong\0`.

Also worth investigating: is there a separate `CcRandomCiv` or similar
enum constant that tells the game slot 16 is special? If so, the game
may use `NumCivs = 16` with `Random = 16` as a sentinel, and extending to
17 real civs needs to push Random to 17 and update the sentinel.

## Oracle

OCR on 25 Right presses from the initial civ-select cursor position. The
OCR output never contained "Korea", "Korean", or "Sejong". Full text
capture in `korea_m2_result.json`.
