# CivRev PS3 — Scenario VARIATOR system & STARTLOC encoding

Reverse-engineered from the v1.30 EBOOT + runtime probes (RPCS3), 2026-08-10.

## TL;DR support matrix (for Map Studio)

Status: **V**=runtime-verified, **H**=strong hypothesis (shipped-pack prose),
**?**=unknown. "Value" = how the editor should expose it. Full detail below.

| # | Variator | Value | Effect | St |
|---|---|---|---|---|
| 0 | BAGRESSIVE | level 0-2 | Barbarian aggressiveness | H |
| 1 | BFECUNDITY | level 0-2 | Barbarian spawn rate (0=few, 2=swarm) | H |
| 2 | BARBVSGOODY | level 0-2 | Hut barbarian-vs-goody ratio | H |
| 3 | RESOURCEDENSITY | level | Map resource abundance — **random maps only** | H |
| 4 | TECHNOLOGYRATE | level (2) | Research speed (2 → 6 turns/tech vs 7) | **V** |
| 5 | UPGRADERATE | ? | Unit upgrade cost/rate? | ? |
| 6 | NAVALSUPPORT | level (2) | Naval support per ship (2=double) | H |
| 7 | MAXCITYSIZE | ? | City growth cap? (NOT a start-pop clamp) | ? |
| 8 | WONDERSEXPIRE | level (2) | Wonder obsolescence (2=never) | H |
| 9 | WARANDPEACE | ? | Diplomacy preset? | ? |
| 10 | MUSTWINBY | enum | Only victory: 2=Space 3=Econ 4=Cultural | **V** |
| 11 | QUICKWIN | ? | Lower victory thresholds? | ? |
| 12 | SPEEDMODE | flag (1) | +1 movement to ALL units | **V** |
| 13 | UFOVISIT | level | UFO event frequency | H |
| 14 | STARTERA | 0-4 | Starting tech era (4=Modern, monotonic) | **V** |
| 15 | STARTSIZE | enum {1,2} | Pre-built cities: 1→1, 2→3, 3→1(fallback) | **V** |
| 16 | CLIMATE | level (0) | Climate preset — **random maps only** | H |
| 17 | CANNOTWINBY | enum | Disable a victory type (compl. of MUSTWINBY) | H |
| 18 | NOSPACERACE | flag | Disable Space Race victory | H |
| 19 | STARTGOLD | value | Starting gold (777 → "Total Gold: 777") | **V** |
| 20 | CARAVANGOLD | level (2) | Caravan delivery gold multiplier | H |
| 21 | ATTACKBONUS | ? | Combat attack modifier? | ? |
| 22 | GREATPEOPLERATE | level (2) | Great-person spawn rate | H |
| 23 | QUARTERPRICELIB | flag (1) | ¼-price Libraries/Universities | H |
| 24 | MOREGOLDRESOURCE | flag (1) | Gold/Gem resource output ×4 | H |
| 25 | MORETRADEPERERA | flag (1) | Bonus trade per era | H |
| 26 | DISPLAYCARD | bitmask | Pregame card (cTECH=0x200 etc.) | H |
| 27 | STARTYEAR | year | **Calendar + MASTER GATE** for advanced starts | **V** |
| 28 | MAPNUMBER | 1-300 | Force built-in map # — **random maps only** | H |
| 29-34 | STARTLOCME / STARTLOC0-4 | row*256+col | Fixed start tiles (player / 4 AI / spare) | **V** |

**Cross-cutting rules (verified):**
1. On **fixed-map** scenarios, STARTSIZE/STARTLOC require **STARTYEAR** set;
   on **random-map** (MAP=NONE) entries STARTSIZE works standalone.
2. Advanced starts work on **any pack type** incl. pristine PACK_MPMAPS2 →
   no EntryType conversion needed to add scenario rules.
3. Map-gen params (RESOURCEDENSITY, CLIMATE, MAPNUMBER) only bite on random
   maps; a pre-baked scenario .map ignores them.
4. Numeric variators pass their literal value (STARTGOLD, STARTYEAR, STARTLOC);
   most others are small level/enum ints stored as signed shorts.

The **?** rows and behavioral **H** rows (barbarian/combat/rate effects) have
clear prose semantics but need an extended-play harness (play N turns, measure
spawns/combat/research) to verify precisely — not yet built.

## Overview

DLC scenarios are registered in `dlcscenariodata{N}.xml` (inside the Pak FPK).
Each `<EntryInfo>` can carry `<VARIATOR><specs text="NAME" level="INT"/></VARIATOR>`
rules. The engine parses them in `FUN_0015c9b0`:

```c
short val   = atoi(level);            // stored as a signed 16-bit short
int   index = lookup(text);           // variator enum index 0..34
if (index < 0x40)
    *(short*)(scenario_struct + index*2) = val;   // scenario[index] = val
```

So every variator is a **16-bit short** at `scenario_struct + index*2`.

### EntryType gates which rules apply
- `PACK_MPMAPS2` — multiplayer map packs (e.g. Pak9). **Ignores STARTLOC** and
  most scenario rules; uses the runtime spawn scorer.
- `PACK_SCENARIO2` — single-player scenario with a bundled map (e.g. Survival).
  Applies the full variator set.
- `PACK_VICTORY` — rules-only, `<MAP>NONE</MAP>`, applied to a random map.

## Full variator enum (index → name)

0 BAGRESSIVE · 1 BFECUNDITY · 2 BARBVSGOODY · 3 RESOURCEDENSITY ·
4 TECHNOLOGYRATE · 5 UPGRADERATE · 6 NAVALSUPPORT · 7 MAXCITYSIZE ·
8 WONDERSEXPIRE · 9 WARANDPEACE · 10 MUSTWINBY · 11 QUICKWIN · 12 SPEEDMODE ·
13 UFOVISIT · 14 STARTERA · 15 STARTSIZE · 16 CLIMATE · 17 CANNOTWINBY ·
18 NOSPACERACE · 19 STARTGOLD · 20 CARAVANGOLD · 21 ATTACKBONUS ·
22 GREATPEOPLERATE · 23 QUARTERPRICELIB · 24 MOREGOLDRESOURCE ·
25 MORETRADEPERERA · 26 DISPLAYCARD · 27 STARTYEAR · 28 MAPNUMBER ·
29 STARTLOCME · 30 STARTLOC0 · 31 STARTLOC1 · 32 STARTLOC2 · 33 STARTLOC3 ·
34 STARTLOC4

Known value semantics:
- `MUSTWINBY`: Space Race=2, Economic=3, Cultural=4.
- `DISPLAYCARD`: bitmask for the pregame card (cTECH=0x200, cPOWERUP=0x1000,
  cTERRAIN=0x1100, cWNDR=0x600, + item index).
- `STARTERA`: **monotonic starting tech-advancement tier** (independent of the
  STARTYEAR calendar — verified: era4 units at year 1000 AD). Swept 1/2/3/4:
  - 1 → Archer garrison (def 2), early
  - 2 → Pikemen (def 3)
  - 3 → Pikemen (def 3) — same defender; CivRev shares defenders across eras
    (Warrior→Pikemen→Riflemen→Modern Inf), so garrison unit is not a clean 1:1
    era label
  - 4 → **Modern Era** (spawn popup "You have reached the Modern Era!", builds
    Modern Infantry/Tanks, ½-cost Spies) — top of the ladder
  Editor: expose as int 0–4, "starting advancement"; higher = more tech/units.
  Exact per-value tech grants would need tech-tree inspection (not done).
- `STARTSIZE` — **semantics on a coerced MP map: only gates STARTLOCME.**
  Clean 6-boot matrix on The_UK (an MP map force-converted to PACK_SCENARIO2),
  each boot's installed edat re-verified, spawn frames pixel-diffed (2026-08-10):

  | STARTSIZE | STARTLOCME | STARTLOC0 | Player start |
  |---|---|---|---|
  | 1 | — | — | Settler @ default coast |
  | 2 | — | — | Settler @ default coast |
  | **1** | **3089** | — | **Settler MOVED to (12,17)** |
  | 2 | 3089 | — | Settler @ default coast (LOC ignored) |
  | 3 | 3089 | — | Settler @ default coast (LOC ignored) |
  | 2 | 3089 | 5650 | Settler @ default coast (LOC ignored) |

  - **The player always starts as a Settler on this map — no STARTSIZE value
    ever produced a pre-built city in a clean run.**
  - The ONLY reproducible effect: `STARTSIZE=1 + STARTLOCME` repositions the
    settler to the packed tile. Values 2/3 cause STARTLOC to be ignored
    entirely (fallback to the default scored spawn — pixel-identical across
    boots, so the default is deterministic).
  - STARTSIZE behaves as a small **enum/config-selector, not a magnitude**
    (bigger ≠ more). Its full meaning likely only manifests on a genuine
    SP-authored scenario map.
  - **RETRACTED earlier claims** (contaminated runs: leftover STARTLOC in a
    reused XML entry + one silent sed failure that re-ran an old value):
    "STARTSIZE = number of starting cities", "STARTSIZE≥1 grants a pre-built
    capital", "STARTLOC+STARTSIZE≥1 builds a city at the tile". The
    Riga/Rostov/Odessa cities seen earlier came from those contaminated
    configs, not from STARTSIZE's value.
  - **Suspected confound: The_UK is a multiplayer map** (MP spawn markers, no
    authored SP starts) being coerced into PACK_SCENARIO2. Shipped STARTSIZE
    users (Enlightenment, Global Warming) run on real SP scenario maps.
    → Definitive STARTSIZE semantics must be measured on a Pak7 Survival map
    (genuine PACK_SCENARIO2). Testing in progress.

## Remaining variators — semantics from shipped-pack prose (2026-08-10)

Cross-reference of every shipped scenario's ENG description with its variator
list. Status: **[V]**=runtime-verified, **[H]**=hypothesis from prose (strong),
**[?]**=unknown.

| Variator | Shipped use | Semantics | Status |
|---|---|---|---|
| BAGRESSIVE | GW=2, Enl=2 | Barbarian aggressiveness ("raging"/"cranky" barbarians) | [H] |
| BFECUNDITY | GW=2, Ice=2, Enl=0 | Barbarian spawn rate (0="few surviving", 2="out in force") | [H] |
| BARBVSGOODY | GW=1, Ice=2 | Hut contents: barbarians-vs-goody ratio (higher=more barbs) | [H] |
| RESOURCEDENSITY | GW=1 | Map resource abundance — **map-gen-time param; no effect on a pre-baked scenario .map**, only random maps | [H] |
| TECHNOLOGYRATE | Enl=2, HD=2 | Research speed — `2` → 6 turns/tech vs baseline 7 (Enlightenment) | **[V]** |
| UPGRADERATE | — | Unit upgrade cost/speed? | [?] |
| NAVALSUPPORT | Eye=2 | "Ships provide double the normal naval support" | [H] |
| MAXCITYSIZE | — | NOT a starting-pop clamp (=3 left pop-4/5 cities intact); growth-cap theory untested | [?] |
| WONDERSEXPIRE | Enl=2 | "Wonders never go obsolete" (2=never) | [H] |
| WARANDPEACE | — | Diplomacy preset? | [?] |
| MUSTWINBY | GR=3, Enl=4, HD=2 | Only victory type allowed: 2=Space, 3=Economic, 4=Cultural | [V] |
| QUICKWIN | — | ? | [?] |
| SPEEDMODE | Eye=1 | **+1 movement to all units** (settler showed "3 Moves" vs normal 2) — "faster units", NOT game speed | **[V]** |
| UFOVISIT | Eye=2, Enl=1 | UFO visit/event frequency | [H] |
| CLIMATE | Ice=0 | Climate preset (0=ice age); **map-gen-time, random maps only** | [H] |
| CANNOTWINBY | — | Complement of MUSTWINBY (disable a victory type) | [H] |
| NOSPACERACE | — | Disable Space Race victory | [H] |
| STARTGOLD | — | Starting gold amount — `777` → City Screen "Total Gold: 777" | **[V]** |
| CARAVANGOLD | GR=2 | Caravan delivery gold multiplier | [H] |
| ATTACKBONUS | — | Combat attack modifier? | [?] |
| GREATPEOPLERATE | HD=2 | Great-person spawn rate | [H] |
| QUARTERPRICELIB | HD=1 | "Libraries and Universities faster/cheaper" (¼ price flag) | [H] |
| MOREGOLDRESOURCE | GR=1 | "Gold and Gem resource output quadrupled" (flag) | [H] |
| MORETRADEPERERA | GR=1 | Bonus trade per era (flag) | [H] |

**Contradiction RESOLVED — STARTYEAR gate is fixed-map-only (verified):**
Enlightenment (PACK_VICTORY, MAP=NONE random) + `STARTSIZE=1`, no STARTYEAR
→ **1 city (Moscow, pop 5)**, ancient era. So:
- **Random-map entries (`MAP=NONE`, PACK_VICTORY): STARTSIZE works directly**
  (normal game-setup advanced start; no STARTYEAR needed).
- **Fixed-map scenarios (bundled MAP, PACK_SCENARIO2 or coerced MPMAPS2):
  STARTSIZE/STARTLOC require STARTYEAR** to trigger the scripted-start
  override.
Map Studio makes fixed-map scenarios → its rule stands: *STARTSIZE/STARTLOC
⇒ also set STARTYEAR*.

## Genuine SP scenario baseline — Global Warming (Pak7), VERIFIED 2026-08-10

Pak7 installs as a **raw FPK renamed `Pak7.edat`** (same trick as Pak9 — no
re-encryption, no license needed; "Global Warming" appears in the scenario
list and boots). Authored variators: BAGRESSIVE=2, BFECUNDITY=2,
BARBVSGOODY=1, RESOURCEDENSITY=1, STARTYEAR=1800, STARTERA=2, **STARTSIZE=2**,
DISPLAYCARD=542.

**Baseline start (Russians, Deity): year 1800 AD, THREE pre-built cities —
Moscow (pop 5), Riga (pop 4), Sverdlovsk (pop 3) — each garrisoned by
Pikemen** (era-2 units). Verified by Circle-cycling; the camera pans across
all three cities.

Contrast: the *identical* STARTSIZE/STARTERA variators on the coerced-MP UK
map produced **zero** cities. **The same variator behaves differently
depending on the map/pack it's applied to** — a first-class fact for the
editor's scenario support.

Factorial results (helper: `rpcs3_automation/set_variators.py` — edits XML,
repacks, installs, re-verifies the installed edat; city counts via
`count_cities.py` OCR over Circle-cycle + City-Screen census frames):

| Variant | Cities | Units | Year |
|---|---|---|---|
| era2, **no size** | **0** — Settlers only | Settlers | 1800 AD |
| era2 + **size1** | **1** — Moscow(5) | Riflemen garrison | 1800 AD |
| era2 + **size2** (authored) | **3** — Moscow(5), Riga(4), Sverdlovsk(3) | Pikemen | 1800 AD |
| era2 + **size3** | **1** — Moscow(5) (City-Screen census, 3 boots agree) | Pikemen | 1800 AD |
| **size2, no era** | **3** — Moscow, Rostov, Sevastopol | **Warriors** (ancient) | 1800 AD |

Conclusions (all verified on the genuine SP map):
- **STARTSIZE alone creates the pre-built cities** (3 cities with no era).
  STARTERA independently sets era/units (Warriors↔Pikemen); STARTYEAR the
  clock; no interaction.
- Value map: **0/absent→0 cities (settlers), 1→1 city, 2→3 cities,
  3→1 city** — NOT a linear count. 3 behaves like an out-of-range enum value
  falling back to a minimal city start (matches the {1,2}-valid enum theory;
  Firaxis only ever shipped 1 and 2).
- Non-capital city names are drawn per-run from the civ's name list
  (era2 run: Riga/Sverdlovsk; no-era run: Rostov/Sevastopol) — names carry no
  semantics.
- STARTERA=2 = **Industrial Era** (era-up "Firaxis Post" popup at spawn).
- **STARTLOCME=5140 on GW (era2+size2): the ENTIRE 3-city starting cluster
  relocated** to the tile's region (spawn cam on Kiev(4)+Novgorod(3), new
  terrain). So on a working scenario config STARTLOC seeds the whole starting
  empire — works fine at size2, unlike the earlier UK probes.
- ~~"Pack/map authoring changes variator behavior"~~ **DEAD**: UK (coerced MP
  map) with the FULL GW variator set → cities (Moscow+Minsk, 1800 AD). The
  earlier UK failures were a missing *variator*, not the map.
- **BISECTED — THE GATE IS `STARTYEAR`**: UK + `STARTSIZE=2` +
  `STARTYEAR=1800` (nothing else but DISPLAYCARD) → cities (Moscow+Riga,
  Warrior garrisons, 1800 AD). **STARTSIZE only takes effect when STARTYEAR
  is also set.** All early UK probes lacked STARTYEAR — that's why STARTSIZE
  looked dead and STARTLOC behaved erratically there.

## FINAL MODEL — advanced starts (all clean runs consistent)

- **`STARTYEAR` is the master switch** for the "advanced start" path (it also
  sets the calendar). Without it: settler start; STARTSIZE ignored; STARTLOC
  at most nudges the size1 settler (edge case).
- **`STARTSIZE`** (with STARTYEAR): number-of-cities preset — `1`→1 city,
  `2`→3 cities (GW; UK OCR caught 2, third may have been missed), `3`→1 city
  (out-of-range fallback → treat valid values as **{1, 2}**; Firaxis only
  ever shipped 1 and 2).
- **`STARTERA`**: independent era/units/tech control (2=Industrial: Pikemen/
  Riflemen; absent=Ancient: Warriors). No role in city creation.
- **`STARTLOCME`/`STARTLOC0-4`** (`row*256+col`): seeds the civ's whole
  starting cluster region (capital + extra cities). Works with size1/size2
  when STARTYEAR is set. Must be a land tile.
- **Works on ANY map** — including MP maps coerced to PACK_SCENARIO2 → Map
  Studio can offer advanced starts on custom maps. Editor rule of thumb:
  *setting STARTSIZE or STARTLOC requires setting STARTYEAR*.
- **Pack type does NOT gate advanced starts either**: pristine
  `PACK_MPMAPS2`/`bMultiplayer=1` UK entry + STARTYEAR+STARTSIZE=2 → cities
  (Moscow+Odessa, Warriors, 1800 AD) when played via SP "Play Scenario".
  → Map Studio needs NO entry-type conversion for advanced starts.
- **STARTLOC on MPMAPS2 also works**: UK/MPMAPS2 + year + size2 +
  LOCME=3089 → cluster spawned in the snowy north (Moscow, Smolensk,
  St. Petersburg); no-LOC control → steppe region (Moscow, Rostov, Yakutsk).
  Pixel-diff 55 (different region) vs deterministic default. The old
  "MPMAPS2 ignores STARTLOC" note was a STARTYEAR-less artifact — retracted.
- ~~2-vs-3 city discrepancy~~ resolved: **UK also gets 3 cities at size2**
  — St. Petersburg/Yakutsk were simply missing from the OCR word-list
  (count_cities.py list extended).

### Harness notes (City-Screen census)
- `launch.py` now does an OCR-gated popup dismissal (era-up newspaper etc.;
  O only while a popup shows "Exit" — otherwise O ends the turn), then opens
  the City Screen and R1-cycles: `census_*` frames. City names OCR reliably
  there (`count_cities.py`).
- **RPCS3 keyboard-pad gotcha: 12ms xdotool taps are missed for
  shoulder-button bindings — use held keys** (`_hold_key("q", 0.4)`,
  `_hold_key("e", 0.4)`). Cross/Circle work as taps (Return/BackSpace).
  Also: uppercase letter keysyms in xdotool mean Shift+letter — always bind
  lowercase.

`.map` files carry NO SP start data: 0x10 spawn markers are MP-only (3-4 per
map, never 5); Global_Warming.map's 3 markers are byte-identical in position
to The_World.map's (GW is a flooded Earth). SP starts are runtime-computed.

## STARTLOC encoding — **CRACKED** (encoding certain; scope revised)

`STARTLOCME` and `STARTLOC0..4` set each civ's **start tile**.

**Encoding: `level = row * 256 + col`** — a packed 16-bit coordinate, high byte
= tile row (0-31), low byte = tile column (0-31), in the map's grid coordinates.
(The encoding itself is solid: three different values each moved the start to
the exactly-decoded tile, incl. the axis-order-decisive probe6.)

- `STARTLOCME` → the human player.
- `STARTLOC0..3` → the four AI civs (a game has 1 player + 4 AI).
- `STARTLOC4` → spare (unused with 4 AI).

**Scope (revised 2026-08-10 after clean re-testing):** on The_UK (coerced MP
map), STARTLOCME repositions the player's starting **Settler**, and is honored
**only when `STARTSIZE=1`** — with STARTSIZE absent, 2, or 3 it is ignored
(default scored spawn). It does NOT build a city there; earlier "city at the
tile" observations were contaminated runs (see STARTSIZE retraction above).
Whether STARTLOC gains more power on a genuine SP scenario map is being tested
on Pak7 Survival.

Rules:
- The value **must be a land tile**. An ocean/ice/out-of-range value is rejected
  and the start falls back to the normal scored location.
- Only honored for `PACK_SCENARIO2` / `PACK_VICTORY` entries (not MP map packs).

### How it was cracked (RPCS3 runtime probes)
Static RE nailed the parse + storage (short per index) but the consumer could
not be isolated (offset collisions: 0x3a/0x44 are common struct offsets). The
encoding was determined by booting a scenario with known values and observing
the settler/city tile:

| Probe | level | decodes to (row,col) | result |
|---|---|---|---|
| linear 174 | 174 | invalid as packed (0,174) | no move (rejected) |
| ocean 773  | 773 | (3,5) internal, ocean | no move |
| **5650**   | 0x1612 | **(22,18)** hills | **moved there** |
| **4358**   | 0x1106 | **(17,6)** hills, west | **moved there** (decisive: col-major would be ocean (6,17) → rejected) |

Control: `STARTSIZE=2`/`STARTERA=2` visibly changed the start (city / advanced
units), proving variators apply; only the *position* variants needed the packed
decode.

### Testing harness (no re-encryption needed)
RPCS3 loads a **raw FPK** renamed `.edat` (the installed `Pak9.edat` is a plain
FPK, not an NPD). So: edit `Pak9/dlcscenariodata5.xml`, `python fpk.py repack
Pak9`, copy `Pak9.FPK` → `~/.config/rpcs3/dev_hdd0/game/BLUS30130/USRDIR/
Pak9.edat`, then `rpcs3_automation/docker_run.sh --headless -s uk`. To exercise
STARTLOC, temporarily set the target entry's `EntryType` to `PACK_SCENARIO2` and
`bMultiplayer` to `0`.

## Map Studio implication
A scenario-authoring mode can now place the player + 4 AI on exact tiles:
`level = row*256 + col` per civ. Combined with the map editor, this enables true
fixed-start custom scenarios.
