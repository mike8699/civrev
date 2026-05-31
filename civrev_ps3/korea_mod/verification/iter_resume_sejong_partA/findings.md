# Sejong carousel portrait (PRD §9.AA part A) — verification

Date: 2026-05-30 (resume iteration). Branch: korea-civ-mod.

## What was actually broken before this iteration

Every prior "Sejong portrait" commit (6a16bde / e0a1c00 / 93bfc98) was
**inert**: no `ldr_korea.dds` was ever produced or shipped.

1. `extract_cr2_sejong.py` imports UnityPy and exits if absent — and
   **UnityPy was never installed**, so the extractor always failed. `build.sh`
   swallowed the failure with `|| echo WARNING`, so no artifact, no error.
2. Even had the DDS existed, `pack_korea.sh` copied it into the FPK staging
   dir without the `.extradata` companion or the `ordering.json` entry that
   `fpk.py` requires — the repack would have raised before producing an FPK.

So the carousel had no Sejong portrait and the pipeline could not run to
completion. The working tree was also mid-pivot (verify_portrait.py deleted,
M0c removed, SetUpUnits switched to `SetPortraitImage("16")`).

## What this iteration did

- Installed UnityPy via `uv run --with UnityPy` (no system-Python install).
- Validated the face crop visually against the rendered `Kor_Sejong_DIFF`
  atlas; settled on `FACE_CROP = (585, 50, 885, 362)` (forehead→beard + gat),
  dark-slate fill of the pure-black UV void, fully opaque output.
- Produced `ldr_korea.dds` (128x128, 65664 B) — byte-exact match to the stock
  small-portrait format (`ldr_china.dds`).
- Fixed `pack_korea.sh` to add the one new FPK entry correctly: copy
  `ldr_china.dds.extradata` -> `ldr_korea.dds.extradata`, register in
  `ordering.json` (293 entries).
- Kept the AS2 wiring: GetImageName "16" -> "korea"; SetUpUnits slot-16
  override `SetPortraitImage("16")` (confirmed a real method by decompiling the
  stock GFX — the portrait is an *external* `loadClip("LDR_korea.dds")`, not an
  SWF-embedded bitmap, so no JPEXS bitmap embedding is needed).

## Static verification (verify.sh --tier=static, M0f) — GREEN

- `ldr_korea.dds` present (128x128 / 65664 B / +extradata / in ordering).
- Repacked GFX routes GetImageName "16" -> "korea" and carries
  `SetPortraitImage("16")`.
- FPK pack->unpack round-trip: `ldr_korea.dds` byte-identical, all four AS2
  edits survive.

## Runtime verification (docker M9) — PASS

`M9_korea_slot16_result.json` (this dir): `pass: true`, stages
main_menu / difficulty_selected / highlighted_ok / in_game_hud all true.
`select_ocr` contains "Sejong".

**Critical result:** the game **boots cleanly with the new `ldr_korea.dds`
FPK entry** and Korea is reachable at slot 16. The MEMORY caveat "adding FPK
entries crashes the game" was learned on the DLC map FPK (Pak9); it does NOT
apply to Pregame.FPK — adding one externally-referenced file is boot-safe.

`korea_play_korea_06_slot_highlighted.png`: Korea centered — label
"Sejong / Koreans", China's bonus text, and the centered **3D leaderhead is
still Mao** (PRD §9.AA part B — the 3D model swap — is not done; the centered
cell is driven by slotData16[0]="6").

`korea_play_korea_09_in_game.png`: real game at 4000 BC, Settlers, China start
(Korea-plays-as-China per iter-1188).

## Note on the small-thumbnail visual

Part A is the *small* 2D carousel thumbnail, which renders only when Korea is a
non-centered (flanking) cell — when Korea is centered the 3D Mao leaderhead
(Part B) occupies the large central slot. A follow-up flanking run
(`korea_play 15 elizabeth`, Korea as right-flank thumbnail) captures the
Sejong thumbnail directly; see `korea_play_elizabeth_06_slot_highlighted.png`.
