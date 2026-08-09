# CivRev Map Editor — Verified Approach

*2026-08-09. Findings below were re-derived this session from the raw binaries/assets (PS3 EBOOT v1.00 + v1.30 disassembly, Misc0/Misc1/Pak9/Level contents, X360 FPKs, port/emulator traces) by opus/sonnet research agents, with the load-bearing claims spot-checked independently. Prior repo docs were treated as unverified leads; several are wrong (see "Corrections" at the end).*

## TL;DR

There is **no procedural terrain-texture generation in the retail game**. Every map you have ever seen in CivRev — including "random" ones — renders from a **pre-baked texture triple** (heights 512×512 L16, mountainhill_blends 2048×2048 DXT1, lightmap 4096×4096 DXT1, all mip-less) shipped on disc. "Random map" means: pick one of **277 numbered pre-generated maps**; the tile grid is re-derived at runtime deterministically from the map ID, and the matching pre-baked textures are streamed in by ID.

Therefore a map editor **must supply the texture triple** for any custom tile layout, and the **DLC named-map route (PS3 v1.30 + Pak9) is the only place the game accepts both custom tiles (`.map`) and custom art** — exactly the route the existing `map_editor_2` uses. The right investment is not a new injection mechanism but a **high-fidelity texture generator**, and the game hands us the solution: the 277 shipped map triples are a massive corpus of real examples. The recommended editor workflow is **clone-and-patch**: start from a real map's textures, edit tiles, and re-synthesize only the changed tiles' texture cells by harvesting real per-tile blocks from the corpus.

---

## 1. Verified architecture

### 1.1 Two map systems

**Built-in "random" maps** (base game, PS3 = X360):

| Step | Mechanism | Evidence |
|---|---|---|
| Map choice | New game: `GameSeed = rand(0..0xFFFF)`; map ID (a.k.a. **MapSeed**) = `MapList[GameSeed % 277 + 1]` | `FUN_00031350` → `FUN_0015acb4` → `FUN_0002f96c` (v1.00); field names proven by the `"BAD RIVER STATE … MapSeed=%d, GameSeed=%d, CivSeed=%d"` format call |
| MapList | `Pregame/ccglobaldefines.xml:228` — ranges over 1–300 with 23 gaps = **exactly 277 IDs**, matching shipped `map<N>_*.dds` sets in both directions with zero mismatch (verified by set arithmetic) | Misc0.FPK = IDs 1–149 (133 sets), Misc1.FPK = 150–300 (144 sets); identical inventory on X360 |
| Tile grid | Generated **at runtime, deterministically from MapSeed**. No tile data ships for built-ins (Misc0/Misc1 contain *only* DDS; brute-force scan of the ELF for embedded 32×32 grids with the ice-border signature: 0 hits). Generator function not yet located — see §4 experiment E4. | inference; everything else confirmed |
| Visuals | Pre-baked triple streamed by ID: `Map%d_Heights.dds`, `Map%d_MountainHill_Blends.dds`, `Map%d_Lightmap.dds`. The gaps in MapList = maps rejected during production (whose art was never shipped). | format strings + `FUN_00aad264` / `FUN_0013b7c8` |

**DLC named maps** (PS3 v1.30 only — v1.00 lacks the code; X360 base disc has zero `.map` files, marketplace-DLC route unverified):

- `<name>.map` (1088 B: 1024 tile bytes column-major + 64×0xFF footer) supplies the tile grid — loaded via `"%s.map"` (`FUN_009d800c` v1.30).
- Textures resolved by **name** instead of number: v1.30's `FUN_00ab8cd4` builds `"Map%s"` + `"%s_Heights.dds"` → `Mapthe_world_Heights.dds` etc. — same loader, unified with the numbered path.
- Registered by `dlcscenariodata5.xml` (`DLCScenarioData`): `EntryType PACK_MPMAPS2`, `EntryTag`, `MAP` (bare name), `bMultiplayer`, `ID` (28–31), localized `TITLE`/`DESCRIPTION`, `VARIATOR` (display-card tech bitmask). **No size/players/spawn fields** — spawns are computed at runtime from tile data (river flags required, per earlier in-game verification).

### 1.2 The terrain loader (v1.00 addresses; +0x58 vtable getter returns the map ID)

`FUN_00aaeac8` (terrain Load):

1. Prebuilt path is **ON by default** (`+0x54`; ctor `FUN_00aad70c` zeroes it, then it's set unless the debug var flips it). Runtime debug var `"Debugging" / "Disable Terrain PreBuilts"` (label `"Load Terrain from preprocessed file"`) toggles the path.
2. Prebuilt loader `FUN_00aad264`: loads `Map%d_Heights.dds` — **on failure returns 0 and the game falls back to the degenerate runtime path** (= the "modded map renders flat" failure mode). Then `PBTerrainZScale` (7.0), the shared detail textures `Hills1.dds` / `Mountain2.dds` / `Snow.dds`, then blends + lightmap.
3. **Pixels-per-tile is derived, not hardcoded**: `pptX = heightsTex.dim / mapDim` (16 px heights, 64 px blends, 128 px lightmap at 32×32). Map dimensions arrive via ctor args, not literals — other sizes are *plausible* but no shipped content ever uses them; treat ≠32×32 as untested.
4. Fallback runtime generator `FUN_00aae3b8`: composites a heightfield from stamp libraries (`Flat_%02d_L16`, `Ocean_`, `Hill1x1_`, `Hill1x2_`, `Hill2x2_`, `CoastTilesXENON`). **Only flat/ocean/coast stamps shipped** → the path can only produce flat land. The hill stamps were dev-tool assets that never shipped.
5. Always-runtime pieces (both paths): per-tile **normal maps generated on GPU** (`CCon_Terrain_NormalGen`) — `Map%d_Normals.dds` is dead code (zero callers, zero shipped files); a 512×512 `CCon_Terrain_ColorMapGen` render target (minimap/world color).

### 1.3 Texture semantics (measured on `the_world` against its own `.map`)

Orientation `display[r][c] = file[c][r]` holds against the DDS content.

- **heights** (L16): per-tile-type means — ocean ≈15.6k, grass ≈28.9k, hills(3) ≈29.2k, ice ≈31.8k, forest ≈33.9k, mountains(6) ≈42k. (Third independent confirmation of the corrected mapping **3=Hills, 6=Mountains**.)
- **blends** (DXT1): **R = forest mask** (mean 221 on forest tiles), **G = mountain mask** (mean 216 on type 6); hills get ~no blend. The claim that blend patterns also drive prop/NIF placement (rocks/grass) comes from a `map_editor_2` comment and remains an assertion.
- **lightmap** (DXT1): the painted diffuse layer — per-terrain base color + baked shading; this is most of what you "see" as terrain.

Shared per-terrain-type detail textures/props live in `Level/` (`grass_*`, `mountain2.dds`, `hills1.dds`, vegetation `.gr2`) — one library for all maps; the per-map triple is the elevation/color/mask data laid over it.

---

## 2. Route decision

### Route A — DLC-slot editor (PRIMARY; proven end-to-end)
Replace one of the 4 Pak9 slots (`the_world`, `equal_opportunity`, `south_pacific`, `the_uk`): write `.map` + the 3 DDS + repack FPK (Pak9 tolerates **replacement only**, not added entries). Already demonstrated in-game (`invasion_usa_with_visible_mountains.png`). Everything below (§3) is about making this route's textures *good*.

### Route B — ReXGlue PC port as the test bench (SECONDARY; high leverage)
The recomp port runs the same asset pipeline (`fpk.py` parses X360 FPKs unmodified; same 277 triples). Use it for fast iteration: `run_port.sh --game-dir <modified tree>` with a repacked `Misc0.FPK`/`Misc1.FPK`, OCR-verified navigation, `compare_screens.py` diffing, `CIVREV_TEXDIAG`/`CIVREV_TEXKILL` texture identification. Because we own the runtime, gdb/hooks can force a MapSeed, dump live tile grids, or eventually load arbitrary `.map` files host-side — no console, no RPCS3 boot-time tax, no sequential-emulator constraint. Caveats: file traces are blind inside FPKs (verify visually/TEXDIAG); the GPU plugin is dlopen'd from the staging dir next to the binary — restage rebuilt `.so`s.

### Route C — resurrect the runtime generator (STRETCH; research)
The fallback path is degenerate only because `Hill*_L16.dds` stamps never shipped. Authoring stamp files and flipping `Disable Terrain PreBuilts` could make the game build heightfields **directly from tile data**, eliminating heights authoring (color/lightmap quality unknown — the runtime color path exists but its output has never been seen). Cheap to A/B on the port once the debug-var/menu plumbing is reachable. Do not block the editor on this.

**Not a route**: reskinning numbered built-in maps (swap `map<N>_*.dds` in Misc0/Misc1). Tiles stay seed-locked, so art would disagree with gameplay — useful only as a pipeline smoke test (see E3).

---

## 3. The editor design: clone-and-patch with a 277-map corpus

The existing `map_editor_2` pipeline (PyQt5 grid editor → dds_generator → patcher → FPK repack → RPCS3 install) is the right skeleton. Its weakness is synthesis fidelity: heights are gaussian-bump approximations, lightmaps are flat per-terrain colors, and blends are one reference block per terrain type tiled everywhere. Replace the generator with:

**3.1 Build the corpus.** For each of the 277 built-in maps, recover its tile grid, giving 277 real (tiles, triple) pairs ≈ 283k tile examples with authentic textures:
- *Preferred*: classify each map's 1024 tiles **from its own DDS** — the measured statistics (heights level + blends R/G + lightmap color) separate all 8 terrain types cleanly. Validate the classifier on the 4 DLC maps, where ground-truth `.map` exists; require ~100% before trusting it. River flags can't be recovered this way (rivers live in the lightmap art + a runtime river system) — for corpus purposes rivers don't matter; for *importing* a built-in map as an editable start, river flags must be re-authored anyway (spawn algorithm needs them).
- *Upgrade later*: dump exact grids from the port (E4) or locate/replicate the seed→tiles generator; this converts the corpus from "classified" to "exact" and enables perfect import of all 277 layouts.

**3.2 Clone-and-patch synthesis.** A new map starts as a **clone of a chosen real map** (its triple copied verbatim, tiles imported or hand-picked to match). When the user edits tiles, re-synthesize **only the affected texture cells** (16×16 px heights / 64×64 blends / 128×128 lightmap per tile — all multiples of the 4-px DXT1 block grid, so cells cut cleanly on block boundaries):
- For each changed tile, find corpus examples with a matching neighborhood (terrain type + 4/8-neighbor context, e.g. coastline orientation) and copy the real blocks — lightmap and blends by DXT1 block copy (bit-authentic patterns, which also sidesteps the possible prop-placement sensitivity), heights as raw L16 with edge blending into neighbors so the mesh stays continuous.
- Neighborhood matching matters most at coastlines (beach gradients in the lightmap, height ramp into ocean) and mountain/forest mask edges; interior tiles of a terrain patch are nearly context-free.
- Deterministic per-tile hash for example selection → reproducible builds.

**3.3 Validation loop.**
- *Offline*: the editors already ship a never-run `compare_heights`/`compare_dxt1` harness — run it: regenerate each DLC map from its own `.map` and score against the shipped originals. This is the objective fidelity metric for the generator; record scores in-repo.
- *In-game*: RPCS3 docker scenario runs (one emulator at a time) and/or the port (Route B) with screenshot comparison.

**3.4 Keep from the current editors**: 32×32 grid model + bit encoding, DLC_SLOTS targeting, dlcscenariodata5.xml handling (ISO-8859-1 + CRLF), FPK repack via ordering.json, river-flag authoring (spawn placement requires river flags on land). Fix the half-migrated terrain-mapping leftovers (§5).

---

## 4. Verification experiments (ordered by cost; none block starting §3)

- **E1 (pure python, do first)**: tile classifier on the 4 DLC maps vs their `.map` ground truth. Gate: ~100% on non-river bits.
- **E2 (pure python)**: corpus-regenerate a DLC map's triple from its `.map`; score with the compare harness vs shipped originals; then eyeball in RPCS3/port.
- **E3 (port, no code changes)**: garish-lightmap swap for one numbered map in a copied game tree + repacked Misc0.FPK; Play Now until it appears (or force the ID, E4) → proves prebuilt-path liveness and slot targeting on the port.
- **E4 (port + gdb)**: force MapSeed / hook the +0x58 getter; dump the runtime tile grid for map N; compare its coastline against `mapN_lightmap.dds`. Repeat with a different GameSeed → confirms tiles are keyed to map ID alone; harvesting loop turns this into exact corpus grids.
- **E5 (PS3 parity)**: repeat E3 under RPCS3 with file-access logging (also directly logs `map<N>_*.dds` reads on a random start).
- **E6 (stretch, Route C)**: author a `Hill1x1_01_L16.dds` stamp, enable `Disable Terrain PreBuilts`, observe whether runtime-generated relief appears.

## 5. Corrections to prior repo docs (rot found this session)

- `docs/file-formats.md` terrain table and `docs/map-system.md` §"default land", and `map_generator/generate_map.py` (`MOUNTAINS=3/HILLS=6` + its "iOS decompilation" justification) all carry the **disproven** mapping. Correct: **3=Hills (passable), 6=Mountains (impassable)** — verified in-game 2026-03-24 and now twice more (DDS statistics, blends masks).
- `map_editor*/dds_generator.py` comments (lines ~56/218-220) and `map_canvas.py:196` (mountain-peak glyph on type 3) are stale-mapping leftovers; code tables are correct.
- "Adding entries to an FPK crashes the game" (`file-formats.md:81`, `dlc-map-packs.md:49`) is overgeneralized — **Pak9-specific**; Pregame.FPK tolerates added entries.
- `docs/map-system.md`'s "pre-computed offline using the same seeds" claim — previously unverified — is now **confirmed** (this was the one big thing the old docs got right).
- `civrev_ps3/decompiled/` was exported from **EBOOT_v100.ELF**, *not* `EBOOT.ELF` (which is v1.30). v1.00: vaddr = fileoff + 0x10000; v1.30: vaddr = fileoff. All decompiled-C addresses in this doc are v1.00.
- The EBOOT is **multi-TOC** (three TOC bases; Ghidra assumed one). The terrain module (0x00aaxxxx–0x00abxxxx) uses TOC 0x1939d98, so its `DAT_0192xxxx` labels are wrong by −0xFF78. Corrected-xref tool: `civrev_ps3/tools/eboot_xref.py`. v1.30 TOCs: 0x193a288 / 0x194a1f8 / 0x195a1a8.
- X360 traces (Xenia + port) cannot see reads inside opened FPKs — absence of `.dds` reads in `file_trace.txt` is a tooling artifact, not evidence of runtime generation.

## 6. Function/address quick reference (v1.00 unless noted)

| What | Where |
|---|---|
| New-game seed roll → map select | `FUN_00031350` → `FUN_0015acb4` (GameSeed +0x12C, MapSeed +0x130, CivSeed +0x134) |
| MapList lookup | `FUN_0002f96c` |
| Map-ID vtable getter (+0x58) | `FUN_0007c6a4` |
| Terrain Load / path branch | `FUN_00aaeac8` (flag +0x54; debug var "Disable Terrain PreBuilts") |
| Prebuilt triple loader | `FUN_00aad264` (v1.30 unified named/numbered: `FUN_00ab8cd4`) |
| Streaming preloader (per-map DDS + Level assets) | `FUN_0013b7c8` (from `FUN_0007d4a0`) |
| Runtime fallback generator / stamps | `FUN_00aae3b8` / `FUN_00aae054` |
| GPU normal-gen | `FUN_00aabc00` (`CCon_Terrain_NormalGen`) |
| DLC `.map` load (v1.30) | `FUN_009d800c` (`"%s.map"` @ 0x16da128); `DLCScenarioData` @ 0x16a22f0 (`FUN_0015bb24`) |
| RNG helper | `FUN_000318d0(range)` |
