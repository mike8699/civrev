# iter-214: §6.3 leaderheads.xml overlay shipped + §6.4 closed as N/A

**Date:** 2026-04-15

Walking the PRD §6 for unfinished implementation work,
`korea_mod/xml_overlays/` was missing two files the PRD spec
called out:
1. `leaderheads.xml` — §6.3 item 1
2. `gfxtext.xml` — §6.4

## §6.3 leaderheads.xml — SHIPPED

Stock `civrev_ps3/extracted/Common0/leaderheads.xml` has 16
`<LeaderHead>` entries (Nationality 0..15). New overlay
inserts a 17th entry between Elizabeth and `</Leaders>`:

```xml
<LeaderHead Nationality="16" Text="Sejong"
            File="GLchi_Mao.xml" TexName="GLchi_Mao_" />
```

Per PRD §6.3 item 1, the entry **reuses the existing
`GLchi_Mao.xml` / `GLchi_Mao_` Mao leaderhead assets** —
no new binary assets ship.

`xmllint --noout` validates clean. Common0_korea.FPK SHA
changes from `88b5bbeb...` to `6dfba344...` confirming the
overlay landed in the repacked FPK.

**Romans M9 PASS** with the new overlay active — boot,
civ-select, in-game HUD all green. The 17th LeaderHead entry
doesn't break the parser, doesn't crash the carousel, and
doesn't break stock-civ playability.

## §6.4 gfxtext.xml — CLOSED as N/A

Inspection of `gfxtext.xml` shows it is a Scaleform
variable→text localization file (mapping `theMenu.t0_txt`
etc. to display strings, organized per `swf=` panel), NOT a
`TXT_KEY_*` lookup table. PRD §6.4's spec to add
`TXT_KEY_CIV_KOREA` / `TXT_KEY_CIV_KOREAP` /
`TXT_KEY_LEADER_SEJONG` keys is **based on a wrong assumption
about the file format**.

The "Korean" / "Sejong" display strings are provided by the
**`civnames_enu.txt` / `rulernames_enu.txt` overlays already
shipping since iter-198**, which is the actual mechanism the
PS3 binary uses for civ/ruler name lookup.

§6.4 is therefore CLOSED as "satisfied by §6.3 / iter-198
mechanism, not the PRD-spec'd gfxtext.xml mechanism".

## Cumulative shipping state

`korea_mod/xml_overlays/`:
- `civnames_enu.txt` — Koreans at row 17
- `rulernames_enu.txt` — Sejong at row 17
- `console_pediainfo_civilizations.xml`
- `console_pediainfo_leaders.xml`
- **`leaderheads.xml`** (NEW iter-214)

`korea_mod/eboot_patches.py`:
- iter-4: ADJ_FLAT pointer table extension (16→17)
- iter-14: parser-count `li r5, 0x11→0x12` at
  `0xa2ee38`/`0xa2ee7c`

§6.3 is now fully shipping (4 XML edits per PRD spec, all in
`xml_overlays/`, with leaderheads.xml the last addition).
**§6.3 is COMPLETE.**

## What's left in §6

- §6.5 cosmetic tiers — descriptive, not implementation
- §6.6 Korea gameplay — DEFERRED to v1.1+
- §6.2 EBOOT patches — most done; remaining items blocked
  by iter-212 structural blocker

iter-215 should walk §7 verification.

## Files

- `findings.md` — this
- `m9_romans_with_leaderheads.json` — boot test result
