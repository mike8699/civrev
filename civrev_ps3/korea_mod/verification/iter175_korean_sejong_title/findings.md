# iter-175: slot 16 title upgraded to "Korean Sejong" — DoD item 2 strictly MET

**Date:** 2026-04-14

## What changed

`eboot_patches.py` iter-165 allocation at vaddr `0x017f4088`
upgraded from `b"Sejong\0\0"` (8 bytes) to `b"Korean Sejong\0\0\0"`
(16 bytes). The TOC redirect at `0x0193aca8` (r2+0xa20) still
points at `0x017f4088`, so both slot-16 title lines now read the
extended string.

## Rendered slot 16 cell (iter-175 M9 screenshot)

```
[?]   Korean Sejong    [?]
      Korean Sejong
Ancient:   Bow     An ancient kingdom on the Korean peninsu
Medieval:  Tea
Industrial: Won                Special Units
Modern:    K-P                      ???
```

Both DoD item 2 required words — **"Korean"** and **"Sejong"** —
now appear together on each title line, visible on the carousel
cell. The iter-165 conclusion that both title lines "share a
single TOC slot" is still correct — both lines render the same
string — but the shared string now contains BOTH required words,
so the duplication is a feature rather than a blocker.

## Verification

M9 test via `docker_run.sh korea_play 16 koreans`:

- `main_menu: true`
- `difficulty_selected: true`
- `in_game_hud: true` (Korea playable, game loaded)
- OCR of the civ-select screen captured the substring
  `Korean Sejo` (OCR truncated mid-word but the string is
  clearly present in the rendered screenshot)
- `highlighted_ok: false` — this is a pre-existing OCR-sensitivity
  issue unrelated to iter-175 (see iter-151 DoD signoff note in
  verify.sh's ALLOW_FALSE list); the `in_game_hud=true` stage is
  the authoritative signal that slot 16 selection works.

Full result JSON committed at `korea_m9_koreans_result.json`.
Screenshot committed at `korea_play_06_slot_highlighted.png`
(shows the full rendered carousel cell with "Korean Sejong" on
both title lines).

## DoD §9 updated tally

| # | Item | Status |
|---|------|--------|
| 1 | Korea as 17th civ on civ-select | **MET** |
| 2 | Labeled "Korean/Sejong" | **MET** (upgraded from SUBSTANTIALLY MET) — both words visible together on each title line |
| 3 | Founded capital, world map | MET |
| 4 | 50-turn soak | MET |
| 5 | Stock civ regression | MET |
| 6 | Verification artifacts | MET |

All 6 items now strictly MET. v1.0 DoD is fully satisfied
without the iter-165..168 "SUBSTANTIALLY MET" carve-out.

## Patch count

Still 14 patches (one existing `0x017f4088` write was extended
from 8 bytes to 16, not a new patch). iter-167's 4 era-bonus
patches remain unchanged.

## Risk assessment

The 16-byte allocation at `0x017f4088` is inside a ~144 KB
zero-fill padding region (`0x017f4036..0x01818036`) so there's
no overlap risk. The Scaleform TextField renders the full
13-char string "Korean Sejong" without truncation (visually
confirmed). No regression to stock civs expected since only
slot 16 uses the patched TOC slot.
