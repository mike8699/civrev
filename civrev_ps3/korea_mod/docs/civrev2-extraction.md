# CivRev 2 APK extraction — iter-226 §5.7 step 1

PRD §5.7 step 1 deliverable: minimal APK extract of the
human-readable XML/text files needed to seed v1.1 Korea
gameplay differentiation.

## What was extracted

From `civrev2/Civilization-Revolution-2-v1-4-4.apk` into
`civrev2/extracted_apk/`:

| file | source path inside APK | size | purpose |
|---|---|---|---|
| `CivNames_enu.txt` | `assets/GameSrc/civrev1_ipad_u4/data/rom/Localization/` | 313 B | civ display names (17 civs + alt-leaders + Barbarians) |
| `RulerNames_enu.txt` | (same dir) | ~? B | leader display names (parallel index to CivNames) |
| `Mobile_PediaInfo_Civilizations.xml` | `assets/.../data/rom/Pedia/` | 17.6 KB | per-civ pediainfo window structure (CIV_KOREA included) |
| `Mobile_PediaInfo_Leaders.xml` | (same dir) | 20.1 KB | per-leader pediainfo (LEADER_SEJONG included) |
| `Mobile_PediaInfo_Units.xml` | (same dir) | ? KB | per-unit pediainfo (NO Hwacha entry — see below) |

## Key findings

### CivRev 2 has 17 civs at the data layer

CR2's `CivNames_enu.txt` lists exactly 17 base civs:

```
Romans, Egyptians, Greeks, Spanish, Germans, Russians,
Chinese, Americans, Japanese, French, Indians, Arabs,
Aztecs, Zulu, Mongols, English, Koreans, [+ alt-leader
duplicates: English, Americans, French, Russians, Chinese,
+ Barbarians at end]
```

Korea is index 16 (zero-based), exactly matching the PS3
shipping state's iter-198 `civnames_enu.txt` overlay
(`Koreans, MP` at row 17). The `, MP` (Male Plural)
gender/number tag is also identical between CR2 and PS3.

### Sejong is at rulers index 16

CR2's `RulerNames_enu.txt`:

```
Caesar, Cleopatra, Alexander, Isabella, Bismarck, Catherine,
Mao, Lincoln, Tokugawa, Napoleon, Gandhi, Saladin, Montezuma,
Shaka, Genghis Khan, Elizabeth, Sejong, [+ alt: Churchill,
JFK, de Gaulle, Lenin, Taizong of Tang, + Grey Wolf]
```

Index 16 = Sejong, with `, M` (Male) tag — also identical to
PS3's iter-198 `rulernames_enu.txt` overlay.

**This validates the iter-198 overlay byte-for-byte** —
our Korean/Sejong rows in the PS3 Pregame.FPK overlays match
the CR2 source exactly. No surprise discrepancies.

### Hwacha is NOT in Mobile_PediaInfo_Units.xml

Searched `Mobile_PediaInfo_Units.xml` for `Hwacha` /
`HWACHA` — **no matches**. CR2's data layer has Hwacha as a
`UCivUnitType` enum value (per `civrev2/CLAUDE.md`) but its
pediainfo entry isn't in this XML file.

Possible locations:
- `libTkNativeDll.so` (the native ARM binary) — Hwacha stats
  may be hardcoded there as a struct rather than data-driven
  XML.
- A different XML file (e.g. `Console_Pedia_Text_Units.xml`
  or similar) that wasn't extracted in this minimal pass.

For v1.1 Hwacha implementation, step 4 of PRD §5.7 (native
cross-check via Ghidra on `libTkNativeDll.so`) is now the
forward path.

### Korea pediainfo entries are MINIMAL in CR2

CR2's `CIV_KOREA` `<EntryInfo>` has only 2 windows:

```xml
<EntryTag>CIV_KOREA</EntryTag>
<WINDOW>
    <title text="TXT_KEY_PEDIA_TITLE_HISTORY_DESC"/>
    <content type="text" text="TXT_KEY_CIV_KOREA_PEDIA"/>
</WINDOW>
<WINDOW>
    <title text="TXT_KEY_PEDIA_TITLE_FUN_DESC"/>
    <content type="funfacts" text1="TXT_KEY_CIV_KOREA_FUN1"/>
</WINDOW>
```

No `<content type="image">` window for the civ portrait,
no media references — CR2's mobile pediainfo is much sparser
than PS3's console pediainfo (which has 4-5 windows per
entry). For v1.0 PS3 reuses China's pediainfo wholesale,
which is a richer fallback than copying CR2's directly.

LEADER_SEJONG has 3 windows:

```xml
<EntryTag>LEADER_SEJONG</EntryTag>
<WINDOW>
    <title text="TXT_KEY_MEDIA_IMAGE_DESC"/>
    <content type="image" file="PEDIA_SEJONG_1.dds" caption="TXT_KEY_CAPTION_SEJONG_1"/>
</WINDOW>
<WINDOW>
    <title text="TXT_KEY_PEDIA_TITLE_HISTORY_DESC"/>
    <content type="text" text="TXT_KEY_LEADER_SEJONG_PEDIA"/>
</WINDOW>
<WINDOW>
    <title text="TXT_KEY_PEDIA_TITLE_FUN_DESC"/>
    <content type="funfacts" text1="TXT_KEY_LEADER_SEJONG_FUN1" text2="TXT_KEY_LEADER_SEJONG_FUN2" text3="TXT_KEY_LEADER_SEJONG_FUN3" text4="TXT_KEY_LEADER_SEJONG_FUN4" text5="TXT_KEY_LEADER_SEJONG_FUN5"/>
</WINDOW>
```

Note `PEDIA_SEJONG_1.dds` and `TXT_KEY_LEADER_SEJONG_*` —
these would be the v1.1 asset/string targets if a Korean-
themed pediainfo replaces the China-as-Korea fallback.

## What's NOT in this extraction

Per PRD §5.7 step 2, the v1.1 mining work that is still
unfinished:

1. **TXT_KEY values** — `Text.ini` is a variable-substitution
   dictionary, not a TXT_KEY table. The actual string values
   for `TXT_KEY_LEADER_SEJONG_PEDIA` etc. live somewhere else
   in the APK and weren't extracted in this pass. Likely
   candidates: `assets/.../data/rom/Localization/enu/` (which
   wasn't extracted) or a binary string blob inside the OBB.
2. **Hwacha stats** — pediainfo isn't enough; need native
   binary cross-check (PRD §5.7 step 4).
3. **Civ-bonus / leader-bonus mapping** — the `<EntryInfo>`
   blocks above only carry pedia text references, not the
   actual gameplay enum values. Those are in the C# layer
   (`UCiv.cs`, `UCivUnitType` enum) per `civrev2/CLAUDE.md`,
   already partially analyzed.

## v1.0 status

This extraction is a **v1.1 reference**. v1.0 ships Korea
identical to China byte-for-byte (per PRD §1.1) and does not
need any of the above. The §5.7 step 1 deliverable is
satisfied; the loop can now declare §5.7 step 1 closed even
though §5.7 itself remains DEFERRED to v1.1+.

## Next steps if v1.1 starts

1. Extract `Localization/enu/` from the APK (the per-key
   English string table, if it exists in plaintext form).
2. Decompile `civrev2/main.19.com.t2kgames.civrev2.obb` to
   find the binary string blob (already partially done in
   `civrev2/native_analysis/`).
3. Run Ghidra on `libTkNativeDll.so` and locate Korea's
   civ-record by string-ref to "Sejong" / "Korean".
4. Cross-reference with PS3's civ-record layout from
   `korea_mod/docs/civ-record-layout.md`.
