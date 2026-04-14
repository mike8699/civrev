# iter-173: definitive static search for Special Units "???" fallback

**Date:** 2026-04-14
**Goal:** find the source of the `???` string that renders next to
the "Special Units:" label on slot 16 of the civ-select carousel,
so it can be statically patched to a Korean unit list.

## Search method

1. Full byte-grep of `EBOOT_v130_decrypted.ELF` for every occurrence
   of the three-byte sequence `???`. Total: 17 matches.
2. Filter to **standalone** `???\0` (three question marks followed
   by a null terminator, NOT preceded by another `?`, so C-string
   sized). Result: 3 matches only.
3. Full byte-grep of every file under `civrev_ps3/extracted/Common0/`
   and `civrev_ps3/extracted/Pregame/` (excluding `.dds/.png/.jpg/
   .tga/.nif/.mp3` binary formats) for `???`.

## Result: the 3 standalone `???\0` strings in the EBOOT

| file offset | vaddr | context | meaning |
|---|---|---|---|
| `0x16883a8` | `0x16983a8` | `shield\0\0sword\0\0\0???\0\0\0\0\0@FLOAT2\0this.flag.SetAttackIcon` | `GFX_UnitFlag.gfx` icon-class fallback — in-game unit flag, NOT civ-select |
| `0x16970e3` | `0x16a70e3` | `Industrial:\n???\nModern:\n???\0\0This will randomly` | slot 16 era bonus block — **already patched by iter-167** |
| `0x174536a` | `0x175536a` | `, TEST\0\0, OP\0\0\0\0, ???\0\0\0Profile option` | shader-profile option tag list — unrelated subsystem |

None of the three `???\0` strings in the EBOOT are reachable from
the civ-select carousel's Special Units field. The era-bonus `???`
block (iter-167 range) is the only civ-select-adjacent one, and
those four slots are already patched to `Bow`/`Tea`/`Won`/`K-P`.

## Cross-referencing "Special Units"

The label `Special Units` exists in the EBOOT at two locations:

- file `0x1697118` (vaddr `0x16a7118`) — Scaleform field name in a
  block containing `emptySlot`, `ShowHandicap`, `this.slotData%d`,
  `theActiveArray`, `this.theMainPanel.ShowPortrait`. This is the
  key used by PPU code to set an ActionScript field.
- file `0x1697d68` (vaddr `0x16a7d68`) — `Starting Technology:\0\0\0\0
  Special Units:\0\0@ERA Era Bonus:` — a colon-labelled UI caption
  group for the `SetDescription` / `SetInfoBar` Scaleform methods.

Neither has a nearby `???` that would be the displayed value.

## Cross-referencing Pregame `str_*.str` localization files

The French/German/Spanish/Italian localization files
(`str_fra.str`, `str_deu.str`, `str_esp.str`, `str_ita.str`) each
contain exactly ONE length-prefixed `???` standalone string
(`\x03\x00\x00\x00???`) plus ONE 64-byte era-bonus template
(`Antiquité:\n???\nMédiévale:\n???\nIndustrielle:\n???\nModerne:\n???`).

- The era-bonus template is the French equivalent of the English
  block at EBOOT vaddr `0x16a70b9`. iter-167 patched the English
  copy; the French copy remains unpatched because the game runs
  in English (`_enu` variants).
- The standalone `???` in the French file comes right after the
  `@UNITNAME__FEMALE_PLURAL0 françaises` template. This is the
  French "default plural form" fallback — a grammatical gender
  helper, not a Special Units fallback.

**There is no English `str_enu.str` in the game disc** — English
strings are embedded directly in the EBOOT. Every standalone
`???\0` in the EBOOT has been accounted for above.

## Conclusion

The slot 16 `Special Units: ???` display is **definitively not
statically patchable without editing the Scaleform `.gfx` binary**.
The `???` is one of the following at runtime:

1. A default value set inside the `GFX_StagingScreen.gfx`
   ActionScript 2 bytecode (not present in any constant pool I can
   read — the AS2 VM stores some short strings as compact opcodes).
2. The `toString()` result of an undefined/null field dereference
   from within the AS2 VM (`"undefined"` → collapsed to `???` by a
   display helper), also not statically reachable.
3. Constructed at PPU runtime from a function that checks if any
   civ unique-unit entries exist and emits `???` when the count
   is 0 — but no "???" or "%s" template fitting that pattern is
   present in the EBOOT.

**Marking permanent: this is v1.1 polish territory.** Unblocking it
requires either JPEXS/ffdec to edit the `.gfx` file, or a live-
memory patch sequence that runs after `GFX_StagingScreen.gfx` has
booted and sets the slot 16 `SpecialUnits_txt.text` field via a
runtime hook. Both are out of scope for v1.0.

## Patches applied this iteration

None. This iteration is a findings-only documentation iteration
that closes a remaining v1.0 investigation thread. iter-169 already
documented the dead end; iter-173 adds the exhaustive byte-grep
evidence that iter-169 did not have.
