# CivRev Map Studio

Desktop editor for Civilization Revolution (PS3) DLC maps. Edits the four
Pak9 map slots (Earth, Equal Opportunity, South Pacific, The UK), regenerates
the three per-map DDS textures, repacks `Pak9.FPK`, and installs to RPCS3 —
one button.

![tests](https://img.shields.io/badge/selftest-31%2F31-brightgreen) *(run
`selftest.py`)*

## Run

```bash
cd civrev_ps3/map_studio
../../.venv/bin/python main.py     # repo venv has PyQt5 + numpy + PIL
```

## Why this replaces map_editor / map_editor_2

The old editors synthesized all three textures from scratch (gaussian bumps,
flat colors, one reference block per terrain). Map Studio's **smart patch**
mode instead starts from the slot's pristine textures and replaces only the
cells of tiles you actually edited, harvesting replacement art from a donor
corpus built from all four original DLC maps — the donor is a same-terrain
tile with the closest ocean/ice/land neighborhood, so coasts get coastal art.
Unchanged tiles keep their original art **byte-for-byte** (verified by
`selftest.py`). Fully new maps (wizard/random) work the same way — nearly every
cell comes from authentic Firaxis art.

The texture pipeline is numpy-vectorized: a typical patched build takes well
under a second (the old pure-Python DXT1 encoder took minutes).

## In-Game 3D Preview

The **In-Game Preview** tab (press `P`) renders the map the way the game
does, live while you edit: the generated 512×512 heights DDS displaces a
terrain mesh, the 4096×4096 lightmap modulates tiled per-terrain ground
textures from the game's own `Level/` assets (warm/temperate/cold latitude
bands, `mountain2` on hills, `hills1` + blends-G rock overlay on mountains,
altitude snow), depth-graded water covers the painted ocean floor, rivers
run along flagged edges, and forest tiles get conifer clusters. Every
texture payload shown is the exact bytes a build would write — what you see
is what the game loads. Edits in the Design tab re-render in ~½ s
(smart-patch + background thread). Drag orbits, wheel zooms, Shift+drag
pans, double-click resets the camera. Requires OpenGL 4.1 (any desktop GPU;
Mesa software rendering works).

## Features

- Paint terrain with brush sizes 1/3/5, fill, line, rectangle; right-click or
  Alt+click picks the terrain under the cursor
- **Edge-accurate river tool**: click or drag along tile edges (the format's
  west/east/south flags, with north clicks mapped to the tile above) —
  important because the game's spawn algorithm requires rivers on land
- Spawn markers (multiplayer), tile inspector with raw byte view
- Live validation: land count, rivers-on-land (spawn requirement), polar ice
  borders, spawn placement — failures warn before you build
- New Map wizard: blank ocean / random continents (seeded, previewed) / clone
  an original / import `.map`
- Texture preview dialog: see the heights (hillshade), lightmap, and blend
  masks a build will produce, before building
- Build & Install: save `.map` → generate DDS → repack FPK → install to RPCS3,
  on a background thread with step progress; export-to-folder mode too
- Restore-original per slot from `Pak9_original`
- Undo/redo (100 levels), dirty-state guards, cursor-anchored zoom,
  space/middle-drag pan, minimap

## Keyboard

| Key | Action | Key | Action |
|---|---|---|---|
| B/F/L/T | brush/fill/line/rect | 0–7 | select terrain |
| R/S/E/I | river/spawn/eraser/picker | [ ] | brush size |
| Ctrl+Z/Y | undo/redo | G | toggle grid |
| Ctrl+S | save .map to slot | Ctrl+B | build & install |
| Ctrl+N | new map | Ctrl+0 | fit map |

## File format notes (verified — see ../../MAP_EDITOR_APPROACH.md)

- `.map`: 1088 bytes = 32×32 tile bytes column-major (`display[r][c] =
  file[c][r]`) + 64×`0xFF` footer
- Tile byte: bits 0–2 terrain (0 Ocean, 1 Grassland, 2 Plains, **3 Hills**,
  4 Forest, 5 Desert, **6 Mountains**, 7 Ice), 0x10 spawn, 0x20/0x40/0x80
  river W/E/S
- Textures per map: heights 512×512 L16, lightmap 4096×4096 DXT1, blends
  2048×2048 DXT1 (R = forest mask, G = mountain mask), all mip-less
- If the game can't load a map's heights DDS it falls back to a degenerate
  runtime path and renders **flat terrain** — that's the failure signature of
  a bad texture build

## Testing

```bash
../../.venv/bin/python selftest.py
```

Checks `.map` round-trips, byte-exact DDS headers, the smart-patch identity
invariant (zero edits → byte-identical originals), edit locality, and
full-synth output sizes. All against `Pak9_original`; nothing writes to the
real Pak9.

## Layout

| File | Role |
|---|---|
| `main.py` | entry point, app/theme setup |
| `editor.py` | main window, panels, menus, build orchestration |
| `canvas.py` | map canvas: tools, rendering, pan/zoom |
| `model.py` | tile grid, bit encoding, validation, map ops |
| `texgen.py` | DDS generation: smart patch + full synth (numpy) |
| `build.py` | background build/preview workers, FPK repack, install |
| `newmap.py` | New Map wizard + random continent generator |
| `preview.py` | texture preview + settings dialogs |
| `widgets.py`, `theme.py` | UI pieces and the single-source palette |
| `assets/blend_refs/` | authentic DXT1 blend cells from the Firaxis originals |
