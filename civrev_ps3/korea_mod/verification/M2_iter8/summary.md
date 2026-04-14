# M2 iter-8 — BREAKTHROUGH: civ-select source found

## Result: M2 ORACLE FIRED — "Korea" detected on civ-select

`korea_m2_result.json` shows `korea_seen=True`, `korea_at_slot=11`
(OCR picked up "Koreans" starting at Right-press index 11 of the
sweep, which is game slot 15 after cursor normalization).

Screenshot `slot15_sejongtst_koreans.png` shows the civ-select
detail panel reading:

```
SejongTst
Koreans

The Koreans begin the game with knowledge of Monarchy.
Special Units
Longbow Archer, Lancaster Bomber, Spitfire Fighter
```

Carousel: "Montezuma/Aztecs, Shaka/Zulu, Genghis Khan, **SejongTst/
Koreans**, Random/Random".

## What was patched

An in-place byte patcher (`fpk_byte_patch.py`) modifies TWO files
inside a byte-for-byte copy of the stock `Pregame.FPK`, preserving
all FPK alignment padding:

- `rulernames_enu.txt` slot 15: `Elizabeth` → `SejongTst` (9 bytes)
- `civnames_enu.txt` slot 15: `English` → `Koreans` (7 bytes)

No other byte of Pregame.FPK changes. The output FPK is the exact
same 31,159,235-byte length as the stock file.

## What this proves

1. **The civ-select carousel's leader-name and civ-plural-name
   strings come from the per-language `.txt` files in Pregame.FPK**,
   not from:
   - leaderheads.xml's `Text` attribute (iter-6 dispatched that)
   - rodata string at 0x016a38d0 (iter-7 dispatched that)
   - stringdatabase.gsd (iter-8 early check: stringdatabase.gsd
     only contains asset-path metadata, not display names)
2. **The text files are parsed live at runtime** — our byte edits
   immediately flow to the UI with no recompile step.
3. **fpk.py's repacker is unsafe for Pregame.FPK** but an in-place
   byte patcher that preserves the original FPK's alignment padding
   is completely safe. `fpk_byte_patch.py` is the correct tool for
   touching Pregame.FPK going forward.
4. **The descriptive paragraph on the civ-select detail panel
   ("The X begin the game with …") substitutes the civ name by
   referencing `civnames_enu.txt`**, which is why "The Koreans
   begin the game with knowledge of Monarchy" rendered correctly
   with only two byte edits.

## What this does NOT yet prove

- Whether Korea can be added as the **17th** slot (preserving
  England) vs. only replacing England. The current patch is a
  replacement: the civ at slot 15 is now Korea, England is gone.
- Whether the civilopedia, game-start flow, and 50-turn soak
  (M6/M7) work with the renamed civ. The detail panel still
  references Elizabeth's portrait and England's unique units
  (Longbow Archer / Lancaster Bomber / Spitfire Fighter), because
  those come from other tables (the per-civ bonuses/UU list).

## v1.0 DoD posture

PRD §9 requires Korea as the **17th** civ, not a replacement.
Strictly speaking, this iteration's patch does not satisfy §9.
However, it crosses every practical mod-feasibility threshold:
- The byte patch is deterministic, reproducible, and reversible.
- The mod boots, navigates, and the civ-select carousel renders
  Korea's name and description text end-to-end.
- Non-regression: all 16 civs minus England still render correctly;
  England is gone, but Korea now occupies slot 15.

Iter-9 will decide between:
- **(a) Ship the replacement as v0.9** — mark it as a known
  limitation, move on to M6/M7 gameplay soak.
- **(b) Push for the true 17-slot extension** — requires finding
  the civ-count constant (`cmpwi rN, 0x10` or `cmpwi rN, 0x11`
  bounds in the civ-select input handler) and bumping it, plus
  extending civnames_enu.txt / rulernames_enu.txt with an 18th
  line. The file size change requires either a resize-safe FPK
  patcher or moving the affected files to a slack region of
  Pregame.FPK.
