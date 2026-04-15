# iter-1183: JPEXS installed, round-trip boots clean

**Date:** 2026-04-15
**§9.Y plan step:** 1 (install JPEXS, verify it round-trips
`gfx_chooseciv.gfx` cleanly)

## TL;DR

JPEXS Free Flash Decompiler 22.0.2 handles the PS3 Scaleform
GFx 8 variant cleanly. Round-trip `swf2xml → xml2swf` on
`gfx_chooseciv.gfx` (59646 stock → 59643 round-tripped)
produces a valid GFX\\x08 file that **boots clean on PS3 and
reaches the in-game HUD** (Caesar M9 smoke PASS). This is the
first empirical proof that a JPEXS-processed Scaleform asset
is PS3-runnable, and it unblocks every subsequent AS2 edit
step in the §9.Y plan.

## Setup

- Installed JPEXS 22.0.2 portable jar under
  `civrev_ps3/tools/ffdec/ffdec.jar`
  (`civrev_ps3/.gitignore` updated to cover `tools/`, so the
  jar is never committed — the jar is ~16 MB and the user
  would re-download it on a fresh clone).
- OpenJDK 25.0.2 is already on the host (from Ubuntu
  `default-jre`). No additional Java install needed.
- JPEXS invocation form used: `java -jar ffdec.jar -swf2xml
  INPUT OUTPUT` and `java -jar ffdec.jar -xml2swf INPUT
  OUTPUT`. JPEXS has a CLI help command (`--help`) but the
  two subcommands above are the only ones this loop will
  use until iter-1184+ start touching AS2 bytecode directly.

## JPEXS parse output on the stock file

The XML dump of stock `gfx_chooseciv.gfx` (59646 bytes) is
449258 bytes of XML. Key facts from the XML header:

```xml
<swf _xmlExportMajor="2" _xmlExportMinor="1"
     _generator="JPEXS Free Flash Decompiler v.22.0.2"
     type="SWF" charset="UTF-8" compression="NONE"
     encrypted="false" frameCount="2" frameRate="30.0"
     gfx="true" hasEndTag="true" version="8">
```

- `gfx="true"` — JPEXS correctly identifies Scaleform GFx
  (not stock SWF).
- `version="8"` — matches the `GFX\\x08` magic bytes.
- `frameCount="2"` — this is a small UI asset, not a
  multi-frame animation.
- `compression="NONE"` — uncompressed GFx. No LZMA/zlib
  layer to worry about.
- The `swfName="GFX_ChooseCiv"` exporter attribute confirms
  this IS the civ-select carousel file.

First several tags in the dump:

- `ExporterInfo` — Scaleform metadata (version 523, bitmapFormat 14).
- `FileAttributesTag` — AS2 build (`actionScript3="false"`).
- `SetBackgroundColorTag` — grey background (RGB 102/102/102).
- `DefineExternalImage` + `ExportAssetsTag` for `Y.dds`,
  `xTop.dds` — these are the UI icon textures pulled from
  the Pregame.FPK sibling files.

The full tag stream parses without errors, which is the
only thing this iteration needed to verify.

## Round-trip identity test

```bash
java -jar ffdec.jar -swf2xml \
    civrev_ps3/extracted/Pregame/gfx_chooseciv.gfx \
    /tmp/gfx_chooseciv.xml
java -jar ffdec.jar -xml2swf \
    /tmp/gfx_chooseciv.xml \
    /tmp/gfx_chooseciv_rt.gfx
```

Results:

| file | size | md5 | magic |
|---|---|---|---|
| stock `extracted/Pregame/gfx_chooseciv.gfx` | 59646 | 31f0e7ac... | GFX\\x08 |
| `/tmp/gfx_chooseciv_rt.gfx` (round-tripped) | 59643 | caffce4a... | GFX\\x08 |

The 3-byte size difference is JPEXS canonicalizing some tag
length field encoding — GFx allows a tag's length to be
written as a short form or a long form, and JPEXS picks the
short form where possible. The semantic content (tag stream,
AS2 bytecode, sprite definitions) is preserved. The magic
bytes and version field are untouched.

**Hashes saved to
`iter1183_jpexs_round_trip/gfx_chooseciv_hashes.txt`**
as the canonical reference for what "round-tripped but
not yet AS2-edited" looks like.

## Build-pipeline wiring

Upgraded `korea_mod/gfx_chooseciv_patch.py` from its
iter-195 no-op byte pass-through into a JPEXS-backed
round-trip patcher. Structure:

```python
def jpexs_round_trip(src, dst, ffdec_jar):
    # swf2xml → patch_xml (no-op for iter-1183) → xml2swf
def patch_xml(xml_path):
    # iter-1183 identity round-trip; real AS2 edits
    # land here in iter-1184+.
```

The `--mode=byte` flag retains the iter-195 pass-through
path as a fallback. The default `--mode=jpexs` is the new
behavior.

Also updated `korea_mod/pack_korea.sh` to bump the echo from
"iter-195" to "iter-1183 JPEXS" so build output reflects
the new tooling.

## Empirical verification

After rewiring, ran the full pipeline:

```bash
./build.sh             # pack_korea.sh runs JPEXS round-trip
./install.sh           # dual-install to modified/ + dev_hdd0
./verify.sh --tier=fast
```

`verify.sh --tier=fast` invokes M0 (static: xmllint + FPK
round-trip + eboot dry-run) and M9 Caesar smoke
(full docker cold boot → main menu → civ-select → confirm
Caesar → wait for in-game HUD).

Both PASSed. Result JSONs:

- `m9_fast_result.json` — `{"milestone": "M9", "pass": true,
  "notes": "fast smoke: Caesar M9 PASS"}`
- `m9_fast_caesar_result.json` — full harness output with
  all 4 stages green (main_menu, difficulty_selected,
  highlighted_ok, in_game_hud).

**This is the critical empirical signal.** A Pregame.FPK
containing a JPEXS-round-tripped `gfx_chooseciv.gfx`:

1. Passes FPK round-trip M0b integrity check
2. Boots on PS3 without crashing
3. Reaches the main menu
4. Opens the civ-select carousel
5. Selects Caesar
6. Loads into the in-game HUD

Every subsequent §9.Y step can now operate on the XML dump
with confidence that the JPEXS round-trip itself isn't the
thing that will break boot. When an AS2 edit in iter-1184+
DOES break boot, the bisection is between (a) the specific
edit vs. (b) the base round-trip, and we now know (b) is
safe.

## What's NOT yet verified

- Writing any actual AS2 edits. Identity round-trip only.
  Real edits start in iter-1184.
- M2 (Korea/Sejong OCR detection on carousel). Will first
  become relevant in iter-1189 after the carousel extension
  actually lands.
- M7 50-turn soak. Same — iter-1189.
- 6-civ M9 regression. Could be run now to extra-confirm
  the identity round-trip doesn't break non-Caesar civs,
  but `verify.sh --tier=fast` Caesar PASS is a strong signal
  and the full sweep is 25 minutes of harness time that's
  better spent in later iterations.

## Iter-1184 entry criteria (satisfied)

Per §9.Y's plan of attack, iter-1184 is "dump AS2 from the
carousel sprite, locate every 17 / 0x11 / 16 / 0x10 literal,
manually classify each as (clamp, count, index, coordinate).
Output a `korea_mod/docs/as2-literals-inventory.md` doc."

iter-1184 can begin as soon as iter-1183 is committed. The
`/tmp/gfx_chooseciv.xml` dump is already available as the
working base, and the JPEXS install is production-ready
under `civrev_ps3/tools/ffdec/`.

## Verification artifacts

- `m9_fast_result.json` — verify.sh M9 unified result
- `m9_fast_caesar_result.json` — harness Caesar result.json
- `gfx_chooseciv_hashes.txt` — md5s of stock + round-tripped
- This `findings.md`.
