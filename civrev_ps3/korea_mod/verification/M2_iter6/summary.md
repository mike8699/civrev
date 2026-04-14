# M2 iter-6 diagnostic — leaderheads.xml is NOT the civ-select source

## Experiment

Temporarily changed `xml_overlays/leaderheads.xml` entry at slot 15:

```
- <LeaderHead Nationality="15" Text="Elizabeth" File="GLeng_Elizabeth.xml" .../>
+ <LeaderHead Nationality="15" Text="SejongTest" File="GLchi_Mao.xml" .../>
```

Rebuilt `Common0.FPK`, reinstalled, ran `docker_run.sh --headless korea`.

## Result: CIV-SELECT STILL SHOWS "Elizabeth / English"

Screenshot `slot15_still_elizabeth.png` confirms that slot 15 on the
civ-select carousel renders **"Elizabeth / English"** with the same
stock portrait and bonus text, **not our edited `SejongTest`**. The
EBOOT patch hash remained identical — the only change in Common0.FPK
was the single leaderheads.xml byte swap.

## Implication

The civ-select carousel does NOT read its display strings from
`leaderheads.xml`'s `Text` attribute. leaderheads.xml is only used
by:
- The leaderhead 3D renderer (for picking `File` / `TexName`)
- Possibly the civilopedia pages (which we didn't test here)

This means adding a 17th `<LeaderHead Nationality="16" .../>` entry
is semantically useless for the v1.0 goal. The civ-select display
strings live in the data segment at `0x1939xxx` (the leader display-
name pool we found in iter-3). That pool is statically compiled into
the EBOOT and can only be extended via **EBOOT binary patches**, not
XML overlays.

## Correct path forward

1. **Retire the §6.3 leaderheads.xml overlay as a v1.0 mechanism.** It
   might still be useful for leaderhead-asset pointer changes in later
   versions, but it's not the lever we need for M2.
2. **Inventory the live data-segment leader pool** (`0x1939000..
   0x193a288`) and find the 16-entry pointer array that the civ-select
   carousel reads from. Extending that array to 17 entries is the
   equivalent of what we did for ADJ_FLAT in iter-4.
3. **Re-confirm** (with a diagnostic EBOOT byte patch) that editing one
   of the leader name strings in the data pool does change the civ-
   select display. If YES: we have the right lever; extend to 17
   entries. If NO: the live pool itself is populated at runtime from
   yet another source we haven't found.

## What this iteration did NOT invalidate

- **M1 green** (patched EBOOT boots + plays stock civs) still holds.
- **ADJ_FLAT relocation** (the iter-4 EBOOT patch) is still correct
  and running — the 78-byte binary patch continues to execute without
  crashing.
- **Dead-rodata discovery** — 4 of 5 parallel arrays are still dead.
- **Xbox 360 decompression pipeline** — still works.

The leaderheads.xml overlay ships as a no-op: it doesn't hurt the
mod, it just doesn't help.
