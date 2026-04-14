# PRD: Korea Civilization Mod for PS3 Civilization Revolution

## 1. Summary

Add Korea (leader: Sejong) as a 17th civilization in the PS3 release of
Sid Meier's Civilization Revolution (BLUS-30130). The **v1.0
deliverable is intentionally minimal**: Korea must appear as a
selectable option on the civ-selection menu, and selecting it must
allow the game to boot into normal gameplay on the world map without
crashing. That is the entire scope. The mod ships as a patched EBOOT
plus replacement XMLs in `Common0.FPK` / `Pregame.FPK`.

### 1.1 v1.0 scope (the only thing that matters right now)

**In scope:**
1. Korea is the 17th entry on the civ-selection screen, with the civ
   name "Korea" / "Korean" and leader name "Sejong" rendered as
   real strings.
2. Selecting Korea routes the player into civ index 16 and starts a
   normal game — settler exists, capital can be founded, the map is
   playable, and the game runs for at least 50 end-turn cycles
   without crashing.
3. The 16 original civs continue to work (no regressions).

**Out of scope for v1.0** (deferred to v1.1+):
- Hwacha unique unit
- Sejong-specific civ trait or leader bonuses (Korea inherits China's
  trait/bonuses wholesale via byte-for-byte civ-record copy)
- Sejong-specific AI personality (also copied from China)
- Sejong-specific diplomacy quips, civilopedia entry, voice lines
- Custom Korean civ portrait or leaderhead (China assets reused via
  pointer)
- AI-controlled Korea showing differentiated behavior
- Multiplayer compatibility
- Full-game victory paths

In short: **Korea is a renamed China for v1.0**, with the only real
work being (a) the EBOOT binary patch that extends the civ table from
16 to 17 entries, and (b) the XML edits that surface "Korea"/"Sejong"
text in the menus. Everything beyond that is v1.1+ scope and the
agent should not pursue it.

This scope reduction is load-bearing for the verification plan:
every test in §7 below targets only the v1.0 deliverable. The
broader §6.6 gameplay-spec tables and §5.7 CivRev 2 extraction work
remain documented for v1.1+ reference, but **§5.7 is no longer a
prerequisite for shipping** and §6.6's TBDs do not need to be filled
in to declare v1.0 done.

## 2. Background

- PS3 CivRev ships **16 civs**. The leader/civ table is hardcoded into
  `EBOOT.ELF` as a `Civs` enum in class `CcCiv`. `extracted/Common0/leaderheads.xml`
  carries an explicit warning: *"Nationality is based on the 'Civs' enum in
  CcCiv. If that changes, this list must be updated."*
- CivRev 2 (Android, native `libTkNativeDll.so`) ships **17 civs** — the extra
  one is Korea, with leader Sejong and unique unit Hwacha (a stronger Catapult).
  Strings confirmed in `civrev2/native_analysis/all_strings.txt`.
- The PS3 binary is statically linked, stripped, 64-bit big-endian PowerPC,
  ~26 MB, with ~69k functions decompiled in Ghidra. All civ logic lives in
  native code — there is no scripting layer, so adding a civ requires binary
  patching plus asset injection. Pure XML edits are insufficient.
- Existing modding infrastructure already in this repo:
  - `fpk.py` — pack/unpack `.FPK` archives
  - `pack_dlc.sh` / `unpack_dlc.sh` — DLC `.edat`/Pak9 handling
  - `decompile_eboot.sh` + `ghidra/` project — full Ghidra decomp of EBOOT
  - `rpcs3_automation/` — Docker-based RPCS3 launcher with Xvfb, screenshot
    capture, and a GDB stub client (`gdb_client.py`)
  - `patch_debug.py` — example of patching EBOOT bytes at file offsets
  - `docs/debug-mode.md` — documented debug flags `0x200000` and `0x2000000`
    that enable in-game cheats and full map visibility (essential for testing)

## 3. Goals (v1.0)

1. **Selectable.** Korea appears as a 17th option on the civ-selection
   screen, with the civ name "Korea" / "Korean" and leader name
   "Sejong" rendered as real text. The portrait and leaderhead are
   the existing China assets — visual fidelity is explicitly out of
   scope. The selection slot exists, the strings resolve, and
   confirming the selection routes the player into civ index 16.
2. **Bootable.** Selecting Korea starts a normal single-player game.
   Settler exists, capital can be founded with normal input, the map
   renders, and the game runs for at least 50 end-turn cycles without
   crashing. Korea inherits China's civ-record contents byte-for-byte
   (trait, bonuses, AI personality) — we do not need any of those to
   be Korea-specific for v1.0.
3. **Non-regressive.** Selecting any of the 16 original civs still
   works — the same 50-turn end-turn loop must pass for at least one
   sample of pre-existing civs.
4. **Reversible.** Mod ships as a patch over a clean v1.30 install;
   original files are not destructively overwritten in the working
   tree.
5. **Verifiable.** Every goal above has a machine-checkable oracle in
   §7 that can be run headlessly via `rpcs3_automation/`. Pass/fail
   is JSON, not screenshots.

Goals deferred to v1.1+ (do not pursue these in v1.0): Hwacha, custom
trait/leader-bonus, custom AI personality, custom diplomacy text,
custom portrait/leaderhead, AI Korea behavioral correctness, full
victory-path validation.

## 4. Non-Goals

- **Online multiplayer.** GameSpy is dead, the custom server work in
  `civrev_ps3/custom_server/` is a separate track, and a 17-civ client cannot
  matchmake against stock 16-civ clients without protocol surgery. Korea will
  be flagged single-player only for v1.
- **Xbox 360 parity.** Out of scope; the 360 EBOOT is a different binary.
- **New leaderhead 3D animation set.** Reuse Mao's animation rig with
  recolored textures (see §6.5). A bespoke Sejong rig is a nice-to-have.
- **Korean localization.** Ship English-only strings; localization can layer on
  later via the existing `gfxtext.xml` mechanism.

## 5. Open Investigations (Do These First)

These unblock the implementation. Each item lists *what* and *how* — the latter
is concrete enough that a teammate can pick it up cold.

### 5.1 Locate `_NCIV` and the `CcCiv::Civs` enum users

**What:** Find every place in `EBOOT.ELF` that depends on the constant 16
(0x10) as a "number of civilizations" value. Candidates: loop bounds over the
civ table, `memset`/`memcpy` of fixed-size civ arrays, switch statements on
nationality.

**How:**
1. In Ghidra (`civrev_ps3/ghidra/` project), search for cross-references to any
   global that gets read with bound `< 0x10` immediately before being used as
   an index into an array of civ-shaped structs (look for stride matching the
   civ record size — see 5.2).
2. Cross-reference with the iOS `_NCIV` symbol from `cross-platform-analysis.md`
   — the iOS binary is symboled and gives us the *role* of the equivalent
   global. Find the matching unstripped function in iOS, then locate the
   structurally identical function in PS3 Ghidra by signature/string-ref
   matching ("Rosetta Stone" approach already used in this repo).
3. Record every hit (file offset, instruction, what 16 means there) in a new
   `docs/korea-civ/ncv-references.md`. Each reference is a candidate patch site.

**Why it matters:** Missing one reference means the 17th civ index will be
out-of-bounds and either crash or alias civ 0.

### 5.2 Reverse the civ data record layout

**What:** Determine the in-memory layout of one civ entry: leader name string
ptr, color, starting tech, unique unit ID, AI personality weights, voiceline
table pointers, etc. We need to know the stride before we can extend the table.

**How:**
1. Start from `extracted/Common0/leaderheads.xml`. The XML loader in EBOOT
   parses this file at boot — find it via string-ref to `"leaderheads.xml"` or
   `"Nationality"` in Ghidra. The function that consumes the parsed XML writes
   into the civ table; the offsets it writes to *are* the field offsets.
2. Cross-check with `console_pediainfo_civilizations.xml` and
   `console_pediainfo_leaders.xml` — same XML-loader pattern.
3. Live-verify by attaching `rpcs3_automation/gdb_client.py` to a running
   instance, breakpointing the loader, and dumping the table with
   `read_memory` once parsing finishes. Compare two adjacent civs (e.g. Caesar
   nationality 0, Cleopatra 1) — the byte delta is the stride.
4. Document layout in `docs/korea-civ/civ-record-layout.md`.

### 5.3 Find the unique-unit dispatch and bonus tables (DEFERRED to v1.1+)

> **v1.0 status: not in scope.** Korea uses China's unit list verbatim
> in v1.0, so the unique-unit dispatch never needs to be touched. This
> investigation is deferred until Hwacha lands in v1.1.

**What (for v1.1+):** Locate the function that decides "this civ can
build Hwacha instead of (or in addition to) Catapult" and the table
of per-civ bonuses.

**How:**
1. Search Ghidra strings for known existing UU names: "Cossack", "Legion",
   "Samurai", "War Elephant", "Flying Fortress". Each leads to the dispatch
   site.
2. From dispatch, walk back to the table. Confirm by patching one civ's UU
   pointer to another's, booting, and screenshotting the build menu (5.5
   workflow).

### 5.4 Map the asset-loading code paths the new civ will hit

**What:** When the game loads civ N, what files does it read? Specifically:
leaderhead `.gr2`/`.dds`, `civ_<name>.dds` portraits, voice `.wav` paks,
civilopedia text, AI personality.

**How:**
1. Run RPCS3 in the docker harness with file-system tracing
   (`fs_io_logging` config in `rpcs3_config_template.yml`) for one full game
   selecting an existing civ. Diff the open-file log against a control run.
2. The delta is the asset set we must clone for Korea.
3. Save the trace to `docs/korea-civ/asset-load-trace.md`.

### 5.5 Live verification harness

**What:** A scriptable loop: patch EBOOT → repack FPK → boot in docker →
screenshot a known UI state → assert. Needed before any patching begins so we
can iterate fast.

**How:**
1. Extend `rpcs3_automation/test_map.py` into `test_civ_select.py` that:
   - Boots to the civ-selection screen (use debug-mode `0x200000` flag from
     `docs/debug-mode.md` to skip intros if possible)
   - Screenshots `output/civ_select.png`
   - Optionally drives controller input via RPCS3's pad emulation to step
     through each civ slot and screenshot the leader portrait + name banner
2. Add a `test_korea_play.py` that uses GDB stub via `gdb_client.py` to set
   the active player's nationality to 16 (post-patch) and capture a
   screenshot of the in-game HUD.

### 5.6 Cross-reference the Xbox 360 executable as an RE aid

**Why:** PS3 CivRev and Xbox 360 CivRev were built from the same C++
codebase. The two binaries should share virtually all game logic — civ
table layout, `_NCIV` loop bounds, unique-unit dispatch, the `CcCiv` enum,
asset-load paths, etc. — but with different compilers (Sony's PPU GCC vs
Microsoft's Xenon compiler), different toolchain quirks, and crucially,
**potentially different debug-symbol survival**. If the Xbox 360 build
left more strings, RTTI, or symbol fragments in place than the PS3 build,
those become a free Rosetta Stone for the PS3 RE work — exactly the
trick `docs/cross-platform-analysis.md` already uses with the iOS port.

**When to reach for it:** any time a §5.1–§5.4 investigation gets stuck
on the PS3 binary alone — e.g. you've found 5 of 6 `< 16` loop bounds
but suspect a 7th, or you can't pin down the civ-record stride from the
PS3 XML loader. Cross-check against the 360 binary before brute-force
patching.

**Assets available in this repo:**
- `civrev_xbox360/Sid Meier's Civilization Revolution (USA) (En,Fr,De,Es,It).iso`
  — the full 360 disc image. The XEX executable inside can be Ghidra'd
  (Ghidra has native Xbox 360 XEX loader support).
- `civrev_xbox360/xenia_automation/` — Docker harness for running the
  game in Xenia (mirrors the structure of `civrev_ps3/rpcs3_automation/`).
  Use this for live runtime inspection of the 360 binary.
- `civrev_xbox360/xenon_recomp/` — the [xenon-recomp](https://github.com/sonicnext-dev/xenon-recomp)
  static-recompilation tool, which translates PowerPC XEX directly into
  C/C++ (vs Ghidra's heuristic decomp). For dense data structures like
  the civ table, recomp output is often easier to read than Ghidra's.
- `civrev_ps3/ghidra/` — there is also an Xbox 360 Ghidra config noted
  in the most recent commit (`7a2114d`) — use the same project
  conventions for the 360 binary.

**Concrete uses for this mod:**
1. **Locate `_NCIV` faster.** Load the XEX in Ghidra, find the constant
   16 used as a civ-loop bound, identify the function via context, then
   locate the structurally identical function in the PS3 Ghidra DB.
2. **Confirm civ-record stride.** Diff the in-memory civ tables on both
   platforms (Xenia GDB stub on 360, RPCS3 GDB stub on PS3) for the same
   savegame. Field offsets that hold the same logical value on both =
   confirmed offsets.
3. **Validate Hwacha-as-UU mechanics.** If the civ-record layout is
   confirmed identical, the same patch *strategy* applies to both
   binaries — and a successful mod prototype on whichever platform is
   easier to RE first becomes a working specification for the other.
4. **Sanity-check the table-relocation patch.** If the 360 binary has
   slack space immediately after the civ table where the PS3 binary
   doesn't (or vice versa), the easier platform tells us "yes, an
   in-place extend is possible at all" before we commit to relocation.

**How to run live tests on the 360 build:**
- `civrev_xbox360/xenia_automation/docker_run.sh` (mirrors the PS3
  harness). If it doesn't already expose Xenia's GDB stub / debugger,
  enable it via Xenia's `--debug` flag in `entrypoint.sh` and forward
  the port out of the container the same way `rpcs3_automation` does
  for RPCS3's `2345`.
- For memory inspection without GDB, the `process_vm_readv` helper
  pattern (`_read_ps3_u32` / `_find_rpcs3_pid` in
  `civrev_ps3/rpcs3_automation/test_autoplay.py` — note: lift only the
  memory-read helpers, *not* the autoplay-patch logic, which is broken
  and removed from this PRD) works on Xenia too. Xenia maps the 360
  guest memory into its own process address space at a known base, so
  the same trick (find the PID, scan for a known struct, compute the
  guest→host base offset) gives direct read access.
- Xenia's symbol export from XEX is much richer than RPCS3's from EBOOT;
  `xenia` will print function names from any embedded PDB-style data
  the build retained, which often pinpoints `CcCiv` methods directly.

**Important caveat:** the mod *itself* still ships only as PS3 patches.
The 360 binary is a debugging instrument, not a target. Do not put any
360-specific addresses or assumptions into `eboot_patches.py`. Track 360
findings separately under `korea_mod/docs/xbox360-cross-reference.md` so
they can inform PS3 patches without contaminating them.

### 5.7 Extract Korea's actual gameplay data from CivRev 2 (DEFERRED to v1.1+)

> **v1.0 status: not in scope.** §5.7 is no longer a v1.0 prereq. Korea
> uses China's civ record byte-for-byte for v1.0 (see §1.1 and §6.6),
> so we do not need any CR2-derived stats to ship. The investigation
> below stays documented for v1.1, when Korea will get its own civ
> trait, leader bonuses, and (eventually) Hwacha. Skip this in v1.0
> iterations.

**Why (for v1.1+):** §6.6 specifies the gameplay properties Korea
must have when the mod gains differentiation from China — civ trait,
leader bonuses, Hwacha stats, starting tech, AI personality, dialogue
lines. Inventing those values would produce a civ that *exists* but
doesn't *feel like Korea*. CivRev 2 ships Korea natively
with the same engine lineage (the path
`assets/GameSrc/civrev1_ipad_u4/data/rom/` in the CivRev 2 APK literally
points back at the CivRev 1 iPad codebase per `civrev2/CLAUDE.md`), so its
data files are the authoritative source. This investigation extracts them.

**Confirmed already from `civrev2/CLAUDE.md` and quick repo inspection:**
- `kNumCiv = 17` and Korea is the 17th civ (index 16) in `UCiv.cs`.
- Korean regional style is `Asian` (`UCiv.cs:civRegionalStyle_[16]`),
  same as China/Japan/Mongolia — so audio/UI fallbacks default to Asian
  variants for free.
- `Hwacha` is a value in the `UCivUnitType` enum.
- `Sejong` and `"Korean"`/`"A Korean Unique Unit"` strings exist in
  `civrev2/native_analysis/all_strings.txt`.

**What needs to be extracted (currently NOT in the repo):**
1. **APK contents.** Only the OBB has been unpacked (hash-named Unity
   asset bundles, not human-readable). The APK itself contains the
   human-readable `Pedia/` XML directory described in `civrev2/CLAUDE.md`
   (`Mobile_PediaInfo_Civilizations.xml`,
   `Mobile_PediaInfo_Leaders.xml`, `Mobile_PediaInfo_Units.xml`, etc.)
   which carry the actual stat blocks. Step 1 of this investigation:
   `unzip Civilization-Revolution-2-v1-4-4.apk` into a working dir,
   commit the relevant XMLs only.
2. **Localization strings.** APK includes `Localization/enu/` (English)
   for `CivNames`, `RulerNames`, `UnitNames`, plus `Text.ini` for
   dialogue lines. KOR is also there if we ever ship Korean localization.
3. **Native logic.** `libTkNativeDll.so` (~1.4 MB ARM binary) is where
   actual civ-bonus code lives — the C# layer is per-CLAUDE.md a thin
   P/Invoke wrapper. For values not in the XMLs, decompile the native lib
   in Ghidra (it's already partially analyzed; see
   `civrev2/native_analysis/`).

**How:**
1. **APK extract (10 minutes).**
   `unzip civrev2/Civilization-Revolution-2-v1-4-4.apk -d /tmp/civrev2_apk`,
   then copy `assets/GameSrc/civrev1_ipad_u4/data/rom/Pedia/` and
   `Localization/enu/` into `civrev2/extracted_apk/`. Add to .gitignore
   except for the specific files we cite.
2. **Pedia XML mining (1 hour).** From `Mobile_PediaInfo_*.xml` extract:
   - `<Civilization>` block for Korea: civ trait, color, starting tech,
     starting government, preferred attribute weights.
   - `<Leader>` block for Sejong: leader bonus list (CivRev gives each
     leader 1–4 bonuses from a fixed set), AI personality weights
     (aggression, expansion, science, culture, gold), portrait references.
   - `<Unit>` block for Hwacha: strength, cost, prerequisite tech,
     obsolete-at tech, movement, special abilities, available-to-civ flag.
3. **Localization mining (15 minutes).** From `Localization/enu/Text.ini`
   pull every key matching `KOREA*`, `SEJONG*`, `HWACHA*`, plus
   diplomacy quip patterns. Map them to PS3 `TXT_KEY_*` naming for
   §6.4's gfxtext.xml work.
4. **Native cross-check (2–4 hours, only if XMLs are insufficient).**
   Load `libTkNativeDll.so` in Ghidra; find Korea's civ-record by
   string-ref to "Sejong" or "Korean"; dump the surrounding struct;
   compare field offsets to the PS3 civ-record layout from §5.2 to map
   civrev2 fields to PS3 fields.
5. **Cross-reference with civrev2's running game (optional, only if
   Ghidra is ambiguous).** The civrev2 APK runs in standard Android
   emulators with `gdbserver`. Loading a save and dumping the live civ
   table at runtime is faster than chasing struct layout statically.
   Skip unless step 4 stalls.

**Deliverable:** `korea_mod/docs/civrev2-extraction.md` with a single
table per stat category, citing the source file and offset/line for each
value. This table feeds §6.6 directly.

**Risks:**
- **Engine drift between CR1 and CR2.** CivRev 2 may have re-tuned
  shared units (e.g. CR2 Catapult has different stats than CR1 Catapult).
  Mitigation: extract CR2 Catapult stats too, compute the
  Hwacha-vs-Catapult *delta*, and apply that delta to PS3's Catapult
  rather than copying CR2 Hwacha numbers verbatim. The delta is more
  meaningful than absolute values across engine versions.
- **CR2 may have leader bonuses or civ traits that don't exist in CR1.**
  E.g. if Sejong's bonus is "+1 Science from Libraries" and CR1's bonus
  enum has no slot for that, we have to substitute with the closest
  available bonus from the CR1 enum. Document substitutions in
  `civrev2-extraction.md`.

## 6. Technical Implementation

### 6.1 Workspace layout

```
civrev_ps3/
  korea_mod/
    eboot_patches.py        # writes patched EBOOT from EBOOT_v130_clean.ELF
    pack_korea.sh           # rebuilds Common0.FPK + Pregame.FPK (REPLACE-only)
    xml_overlays/           # all REPLACEMENTS of existing files in the FPKs
      leaderheads.xml       # +1 entry, Nationality="16", points at chi_mao_* assets
      console_pediainfo_civilizations.xml
      console_pediainfo_leaders.xml
      gfxtext.xml           # adds TXT_KEY_CIV_KOREA_*, TXT_KEY_LEADER_SEJONG_*, etc.
    docs/
      ncv-references.md         # §5.1 output
      civ-record-layout.md      # §5.2 output
      asset-load-trace.md       # §5.4 output
      xbox360-cross-reference.md # §5.6 output (only if needed)
      civrev2-extraction.md     # §5.7 output — Korea's stats from CR2
      patch-log.md
```

`civrev2/extracted_apk/` (gitignored except for the cited Pedia XMLs +
`Localization/enu/Text.ini`) is created by the §5.7 extraction step and
holds the source data for `civrev2-extraction.md`.

### 6.2 EBOOT patches

> **§5.2 finding (2026-04-13):** the PS3 EBOOT does NOT store civ data as
> a single struct-per-civ table. It uses **parallel pointer arrays**, each
> 16 × 4 bytes, indexed by the `CcCiv::Civs` enum. The confirmed arrays
> (bases listed in `korea_mod/addresses.py` and dumped in
> `korea_mod/docs/civ-record-layout.md`) are:
> - Leader display name pointer array — `0x0194b434`
> - Civ internal tag pointer array    — `0x0194b35c`
> - Civ adjective pointer array       — `0x0195fe28`
> - Civ adjective/plural pair table   — `0x0194b3c8` (irregular stride)
> - Leader internal tag pointer array — immediately before `0x0194b35c`
>   (head not yet scanned).
>
> This changes the §6.2 strategy: step 2 below ("extend the civ table") is
> replaced by "relocate and extend every parallel array in lockstep". The
> in-place-extend sub-option no longer applies — the arrays are adjacent
> in `.rodata` with no trailing padding. Step 4's leader-name pointer
> patch is now a pointer-table write at `leader_name_array[16]`, not a
> struct-field write.
>
> §5.1's work also changes scope: there is no single `_NCIV` global. The
> equivalent is a set of inline `0x10` immediates at every civ-loop site.
> Each of those compares is an independent patch candidate.

All offsets here are placeholders pending §5.1 / §5.2 completion. Use
`patch_debug.py` as the byte-patcher template — it already handles
file-offset-vs-virtual-address translation for this EBOOT.

1. **Bump `_NCIV` from 16 → 17.** Single-byte immediate patch in the
   initializer. Locate via the loop in `LoadLeaderheads` (5.2).
2. **Extend the civ table by one entry that is byte-for-byte China.**
   The table is statically sized at 16 × stride. Two options:
   - **In-place extend if there's slack.** If the next data symbol
     leaves ≥ stride bytes of padding, copy entry 6 (China) into the
     new slot 16 directly. Verify with Ghidra's memory map.
   - **Relocate the table.** Allocate space in the EBOOT's `.data`
     padding (the v1.30 EBOOT has multi-KB zero regions — find one
     big enough), copy the existing 16 entries there, then append a
     verbatim copy of entry 6 as entry 16, and patch every load that
     references the old base address. This is the more invasive but
     safer route. Track every patched LIS/ADDI pair in `patch-log.md`.

   **Important:** entry 16 is a *copy* of entry 6, not a hand-built
   Korea record. The only field that may differ is the leader-name
   pointer (see step 4). Civ trait, leader bonuses, AI personality,
   color, starting tech, and every other field are identical to
   China's. This is the entire scope of the v1.0 EBOOT data work.
3. **Patch every loop bound from `< 16` to `< 17`** identified in
   §5.1. Most will be `cmpwi rN, 0x10` → `cmpwi rN, 0x11`.
4. **Point entry 16's leader-name field at a "Sejong" string.** Two
   options here, pick whichever §5.2 makes easier:
   - The leader name comes from `leaderheads.xml` parsing, in which
     case no EBOOT patch is needed for the name — the §6.3 XML edit
     supplies it.
   - The leader name is a hardcoded pointer in the civ record, in
     which case allocate a "Sejong\0" string in the same `.data`
     padding region used in step 2 and patch the leader-name pointer
     in entry 16 to address it.
   Same applies if the civ name itself ("Korea"/"Korean") is in the
   civ record vs. in XML — find out in §5.2 which it is, and patch
   accordingly.

**Patches deferred to v1.1+** (do NOT attempt these in v1.0):
- ~~Wire Hwacha as Korea's UU~~ — out of scope; Korea uses China's
  unit list verbatim, which means it builds Catapult, not Hwacha.
- ~~Custom AI personality~~ — out of scope; Korea uses China's AI
  personality verbatim.
- ~~Custom civ trait / leader bonuses~~ — out of scope; Korea uses
  China's verbatim.

### 6.3 FPK / asset patches

**Hard constraint:** prior map-mod work (per `MEMORY.md`) confirms that
*adding* new entries to an FPK crashes the game — only *replacement* of
existing entries is safe. We assume the same constraint applies to
`Common0.FPK` and `Pregame.FPK` until proven otherwise, and design the v1.0
mod so it **never adds a single new file to any FPK**. Every change below is
either an in-place replacement of a file that already exists or a pure
EBOOT-side pointer change.

This makes the v1.0 cosmetic decision (Mao-as-Sejong) load-bearing rather
than just a shortcut: it lets us avoid shipping any new `.gr2`/`.dds` leader
assets at all.

1. **Common0.FPK — replacements only:**
   - `leaderheads.xml` — replaced. New version contains a 17th `<LeaderHead>`
     entry with `Nationality="16"`, `Text="Sejong"`, but **`File` and
     `TexName` point at the existing `GLchi_Mao.xml` / `GLchi_Mao_`** assets.
     No new leaderhead files needed.
   - `console_pediainfo_civilizations.xml` — replaced, with a new
     `<EntryInfo>` for `CIV_KOREA` whose `<content type="image">` references
     reuse existing `PEDIA_CHINA_*` DDS files. Pure XML edit.
   - `console_pediainfo_leaders.xml` — replaced, new `LEADER_SEJONG` entry,
     also reusing China/Mao media references.
2. **Pregame.FPK — replacements only:**
   - `gfxtext.xml` — replaced, with all `TXT_KEY_CIV_KOREA*`,
     `TXT_KEY_LEADER_SEJONG*`, `TXT_KEY_UNIT_HWACHA*` strings appended to the
     existing key list. Strings sourced from
     `civrev2/native_analysis/all_strings.txt`.
   - **No `civ_korea.dds` portrait file ships in v1.0.** The civ-select
     screen will show the China portrait for Korea. This is ugly but inside
     the v1.0 cosmetic-tier contract. Fixed in v1.1 by replacing
     `civ_barbairan.dds` (or another unused civ portrait slot) — still a
     replacement, never an add.
3. **Leaderhead 3D assets** — *no changes shipped*. The civ-record patch in
   §6.2 stores a pointer to the existing `chi_mao_*` filename prefix for
   civ 16. The game's leaderhead loader concatenates that prefix with the
   suffix list it already uses for Mao, so all the right files get loaded
   with zero duplication.
4. **Civilopedia DDS** — *no changes shipped*. Korea's civilopedia pages
   reference China's existing `civ_china.dds`, `PEDIA_CHINA_*.dds`, and any
   `.bik` cinematics. Acceptable for v1.0.
5. **Voice / dialogue audio** — *no changes shipped*. Korea reuses Mao's
   diplomacy `.wav` set via the same EBOOT-pointer mechanism as the
   leaderhead assets.

**Net FPK delta for v1.0:** four XML files replaced (`leaderheads.xml`,
`console_pediainfo_civilizations.xml`, `console_pediainfo_leaders.xml`,
`gfxtext.xml`). Zero new files. Zero binary-asset changes. This collapses the
asset-pipeline risk to "did our XML edits parse cleanly?", which is testable
in isolation before any EBOOT patching.

**Escape hatch if the assumption is wrong.** If we discover during M1/M2 that
replacements of these specific XMLs are also rejected, fall back to mounting a
new `Pak10` DLC pack at boot following the same `Pak9` pattern already used
for DLC maps in `civrev_ps3/dlc/`. Pak10 would carry only the modified XMLs
(still no genuinely new asset files), and the EBOOT patch would be extended
to register Pak10 in the boot mount list. Track this as a contingency in
`patch-log.md`; do not pre-build it.

### 6.4 String table (v1.0 minimal set)

For v1.0 we only need the strings that show up on the civ-select
screen and on any popup that fires during a normal game start. The
full diplomacy/civilopedia/funfact set is deferred to v1.1+.

Required v1.0 keys (added to `gfxtext.xml` as a replacement edit):
- `TXT_KEY_CIV_KOREA` — display: `"Korean"` (or `"Korea"`, match
  whatever CR1's existing pattern is — Caesar's civ uses
  `TXT_KEY_CIV_ROMAN`/`"Romans"`, so `"Koreans"` is the safe form)
- `TXT_KEY_CIV_KOREAP` — possessive form for `@CIVNAMEP`
  substitution: `"Korean"`
- `TXT_KEY_LEADER_SEJONG` — display: `"Sejong"`

Anything else can fall back to China's existing keys. If the game
uses `TXT_KEY_CIV_KOREA_PEDIA` (civilopedia entry) and we haven't
defined it, the worst case is that the civilopedia page shows the
key literal — that's a v1.1 cosmetic fix, not a v1.0 blocker. M7
oracle 7 only fails on `@CIVNAME`-style literals appearing in popups
during normal gameplay, not on missing pedia entries.

If a missing key turns out to *crash* the game (rather than
displaying the key literal), add it as a stub that points at the
equivalent China key, and document the crash trigger in
`patch-log.md`.

### 6.5 Cosmetic fidelity tiers

**v1.0 reuses China's full asset set, including its unit list.**
Korea is "China with a different name on the civ-select screen." The
success criterion is that the new civ shows up properly, the text
strings resolve, and the game boots into gameplay without crashing —
not visual originality and not unit differentiation.

| Tier | Leaderhead | Civ portrait | Voice | Unique Unit | New files in FPK? |
|------|-----------|--------------|-------|-------------|-------------------|
| **v1.0 (target)** | `chi_mao_*` (pointer reuse) | `civ_china.dds` (pointer reuse) | Mao `.wav`s (pointer reuse) | **None — uses China's unit list (Catapult, no Hwacha)** | **None** |
| v1.1 | `chi_mao_*` retextured (replace existing DDS in place) | Replace `civ_barbairan.dds` slot with Korean flag art | Mao `.wav`s | Hwacha added as Catapult clone with stat delta (per §6.6 / §5.7) | None (replacements only) |
| v1.2 | Custom Sejong head mesh | Custom portrait | Generated TTS lines | Hwacha mesh from CivRev2 if format-compatible | Likely yes — gated on Pak10 mount working |

Ship v1.0, iterate in place. Do not block v1.0 on any v1.1+ work.

### 6.6 Korea gameplay specification (DEFERRED to v1.1+)

> **v1.0 status: not in scope.** The entire §6.6 spec below is
> deferred. For v1.0, Korea inherits China's civ record byte-for-byte
> via the §6.2 step-2 copy. None of the TBD cells below need to be
> filled in to ship v1.0, and §5.7 (CivRev 2 data extraction) is no
> longer a v1.0 prerequisite. The tables remain documented here for
> v1.1 reference.
>
> **What v1.0 actually uses for civ stats:** whatever China currently
> uses. Sejong has Mao's leader bonuses, Korea has China's civ trait,
> Korea's AI plays like China's AI, Korea builds the same units China
> builds. The only differences from China that v1.0 ships are:
> 1. The civ shows up in slot 16 of the civ-select screen.
> 2. Its display name is "Korean" / "Koreans" instead of "Chinese".
> 3. Its leader display name is "Sejong" instead of "Mao".
>
> Everything below this line is v1.1+ planning.

---

#### Civilization: Korea

| Field | Source | Value |
|-------|--------|-------|
| Internal name | new key | `CIV_KOREA` |
| Display name | CR2 Localization `enu/CivNames` | TBD (likely "Korean" / "Koreans") |
| Possessive form (`@CIVNAMEP`) | CR2 Localization | TBD |
| Civ trait / starting bonus | CR2 `Mobile_PediaInfo_Civilizations.xml` `<Civilization name="Korean">` | TBD — must be expressible in PS3 CR1's bonus enum (see §5.7 risk) |
| Starting tech | CR2 pedia | TBD |
| Starting government | CR2 pedia | TBD (CR1 default: Despotism) |
| Civ color (RGB) | CR2 `_civColors[16]` from `UCiv.cs` plus regional style | TBD — pick a Korean-flag-evocative color (red/blue) that doesn't collide with existing 16 |
| Regional style | confirmed | `Asian` (matches China/Japan/Mongolia — audio fallbacks free) |
| Unique unit | confirmed | Hwacha (Catapult replacement) |
| City name list | CR2 Localization `enu/CityNames/Korean.txt` | TBD — extract verbatim, fall back to historical Korean cities (Seoul, Pyongyang, Busan, ...) if missing |
| Civilopedia entry | CR2 `Mobile_Pedia_Text_Civilizations.xml` | TBD — translate CR2 entry to PS3 `TXT_KEY_CIV_KOREA_PEDIA` |
| Fun facts (×2) | CR2 pedia | TBD |

#### Leader: Sejong (the Great)

| Field | Source | Value |
|-------|--------|-------|
| Internal name | new key | `LEADER_SEJONG` |
| Display name | CR2 `enu/RulerNames` | "Sejong" (confirmed in `all_strings.txt`) |
| Leader bonus 1 | CR2 `Mobile_PediaInfo_Leaders.xml` | TBD |
| Leader bonus 2 (if any — CR1 supports up to 2) | CR2 pedia | TBD |
| AI personality: aggression | CR2 native | TBD (default: low — Sejong is historically a builder/scientist archetype) |
| AI personality: expansion | CR2 native | TBD |
| AI personality: science weight | CR2 native | TBD (likely high) |
| AI personality: culture weight | CR2 native | TBD |
| AI personality: gold weight | CR2 native | TBD |
| Diplomacy quip set | CR2 `Text.ini` `SEJONG_*` | TBD — full greeting/threat/friendly/condescend/defeat/victory set; reuse Mao set as fallback for any missing line |
| Civilopedia entry | CR2 pedia | TBD |

If CR2's pedia confirms Sejong's archetype is "scientific builder," the
v1.0 substitute leader bonuses (until exact CR1-compatible mappings are
chosen) should be drawn from existing CR1 bonuses that lean
science/wonders, not military.

#### Unique unit: Hwacha

| Field | Source | Value |
|-------|--------|-------|
| Internal name | new key | `UNIT_HWACHA` |
| Display name | confirmed | "Hwacha" |
| Replaces | confirmed by CR2 description ("more powerful than normal catapult") | Catapult |
| Available to | new | Korea (civ index 16) only |
| Strength delta vs Catapult | CR2 `Mobile_PediaInfo_Units.xml` Hwacha vs Catapult | TBD — apply the **delta**, not absolute (see §5.7 risk on engine drift) |
| Cost | CR2 pedia | TBD (likely same as Catapult) |
| Prerequisite tech | CR2 pedia | TBD (likely Mathematics, same as Catapult) |
| Obsolete-at tech | CR2 pedia | TBD |
| Movement | CR2 pedia | TBD (likely 1, same as Catapult) |
| Special abilities | CR2 pedia | TBD (CR2 may give Hwacha siege/area damage flags that CR1 doesn't have — substitute or drop) |
| Model / icon | confirmed | Reuse Catapult model + Catapult icon for v1.0 (v1.2+ may swap to a Hwacha mesh from CR2 if format-compatible) |
| Description text | CR2 pedia | "A Korean Unique Unit, it is more powerful than normal catapult." (confirmed verbatim from `all_strings.txt`) |

#### What if a CR2 value can't be expressed in CR1?

CR1 and CR2 are not feature-equivalent. CR2 added some unit special
abilities, leader-bonus types, and diplomacy options that CR1's binary
data structures cannot represent. The substitution rule:

1. **Closest equivalent in CR1.** If CR2 says "Hwacha gets +50% vs
   units in mountains" and CR1 has no terrain-bonus flag for catapults,
   pick the closest existing flag (e.g. generic "+1 strength").
2. **Drop silently if no equivalent exists.** Don't invent new fields in
   the binary — that's a code patch, not a data patch, and it's outside
   the scope of v1.0.
3. **Document every substitution.** Each TBD cell that ends up as a
   substitution gets a footnote in `civrev2-extraction.md` recording the
   CR2 source value and the CR1 substitute, so a future modder knows
   where the fidelity gap is.

The spec's success criterion is **"plausibly Korean"**, not "byte-equal
to CivRev 2's Korea." A historically-flavored science-leaning civ with
the Hwacha as a stronger Catapult is the floor; matching CR2 exactly is
the ceiling.

## 7. Verification Plan

This section is written so an autonomous agent can iterate on the mod for
hours without supervision. Every check below has a **machine-checkable
oracle** — a value an automated test can compare to a known-good answer
without a human looking at a screenshot. Screenshots are also captured for
forensic review when something fails, but they are *never* the pass/fail
signal.

All tests run through the docker harness (`rpcs3_automation/docker_run.sh`)
so they work headless and are reproducible. Each milestone produces:
- `korea_mod/verification/<milestone>/screenshot.png` — capture for humans
- `korea_mod/verification/<milestone>/result.json` — machine-readable
  `{pass: bool, oracle: str, expected: ..., actual: ..., notes: ...}`
- `korea_mod/verification/<milestone>/rpcs3.log` — the emulator log for the run

The harness already exposes everything needed:
- `launch._send_ps3_button("X" | "O" | "start" | "Up" | "Down" | "Left" | "Right")` — input
- `launch._navigate_startup_to_main_menu(proc)` — boot-to-menu sequence (already working)
- `launch._wait_for_text_on_screen("Korea", timeout=15)` — pytesseract-backed OCR poll
- `launch._ocr_screen(region=(...))` — OCR a region of the current frame
- `launch._capture_display()` / `_frames_similar()` — pixel comparison + golden images
- `gdb_client.GDBClient.read_u32(addr)` / `read_memory(addr, len)` — memory inspection via RPCS3 GDB stub on `127.0.0.1:2345`
- `_read_ps3_u32(pid, addr)` / `_find_rpcs3_pid()` — direct `process_vm_readv` reads (no GDB stub pause needed). These helpers currently live in `rpcs3_automation/test_autoplay.py`; **lift them into a shared `rpcs3_memory.py` module** as part of §5.5 setup so the rest of the harness can use them without importing from a file whose primary purpose (autoplay debug mode) is broken and abandoned.

### 7.0 The autonomous iteration loop

The agent's inner loop is:

```
1. Edit eboot_patches.py / xml_overlays/*.xml
2. Run: ./korea_mod/build.sh
     - emits patched EBOOT.ELF + repacked FPKs
     - validates: dry-run patch report, FPK round-trip byte equality
     - if static checks fail → fix and goto 1
3. Run: ./korea_mod/verify.sh --tier=fast
     - runs M0..M3 only (≤6 minutes total)
     - reads result.json from each milestone
     - if any FAIL → diagnose using log + screenshot + GDB dumps, goto 1
4. Run: ./korea_mod/verify.sh --tier=full
     - runs M4..M9 (≤45 minutes total)
     - if any FAIL → goto 1
5. All green → tag commit, write build report, stop
```

`verify.sh` exits non-zero on any milestone failure and prints the failing
oracle's `result.json` to stdout. The agent decides "should I keep going?"
purely from `verify.sh`'s exit code and the JSON contents. **No screenshot
inspection is required to make progress** — screenshots are only for the
human reviewing artifacts after the run.

**M2 is a hard gate for all gameplay verification.** Korea must be
reachable from the civ-select screen via normal menu navigation before
M6 or M7 can run, because both gameplay milestones drive into a game by
**playing as Korea**, not as another civ. Until M2 is green, M6/M7
cannot start — `verify.sh --tier=full` will short-circuit with a
"M2 not green; gameplay tests blocked" failure rather than attempt
M6/M7 against a missing menu entry. This means the order of work is
strict:
- §6.2 EBOOT civ-table extension + §6.3 XML overlays must land first
  (so the menu shows Korea)
- M0–M3 must be green (so we can prove the menu shows Korea)
- only then do M4–M9 even attempt to run

In practice this means the agent will spend the first several
iterations entirely on the M0–M3 gate, and won't touch M6/M7 oracle
tuning until that gate is open. Don't try to GDB-poke past it — the
selection path is now part of the test surface.

### 7.1 Static checks (M0)

Run before any emulator boots, in <30 seconds:

- **M0a: EBOOT patch dry-run.** `eboot_patches.py --dry-run` walks every
  planned patch site, reads the current bytes, and prints `(offset,
  expected_old_bytes, new_bytes, status)`. **Oracle:** every site reports
  `status == "old bytes match"`. If any site reports a mismatch, we're
  patching the wrong offset (likely a Ghidra→file-offset translation bug).
- **M0b: FPK round-trip.** For each modified FPK, run `fpk.py unpack` →
  `fpk.py pack` → SHA-256 the result. **Oracle:** SHA matches a golden hash
  recorded the first time the round-trip succeeded for that file. Drift
  means the packer is not deterministic.
- **M0c: XML well-formedness.** `xmllint --noout` over every overlay XML.
  **Oracle:** exit code 0.
- **M0d: String key inventory.** Grep `gfxtext.xml` for every `TXT_KEY_*`
  referenced from the new pediainfo entries and `leaderheads.xml`.
  **Oracle:** zero missing keys. Catches "we added the entry but forgot to
  add its strings" before booting.

Failure here costs no emulator time. M0 must always pass before any later
milestone runs.

### 7.2 Boot-time checks (M1–M3)

**Always cold boot.** Every M1–M3 run starts from a fresh RPCS3 process
with no prior emulator state. Cold boot costs 60–90s per iteration but it
is the only way to guarantee that the *patched* EBOOT bytes are the ones
actually running.

**Why no savestates:** RPCS3 savestates serialize the emulated PS3 guest
memory, including all loaded code pages from the EBOOT. If a savestate is
captured under EBOOT version A and then loaded after the EBOOT on disk
has been patched to version B, the guest memory is restored from the
savestate — meaning **the old (unpatched) code runs**, while the new
EBOOT file is never re-read. Worse, this fails silently: the game boots
fine and the agent thinks the patch is live when it isn't, leading to
hours of "why isn't my patch working" iteration on a patch that already
worked. Even an "invalidate savestates whenever the EBOOT changes" rule
is one missed cleanup away from the same failure mode. The safer rule is
the one with no footgun: **never use savestates in the autonomous loop.**

If iteration speed becomes a real bottleneck (cold boot dominates the
wall-clock for the loop), the right optimizations are: parallelize M1/M2
across multiple docker containers; trim the boot sequence inside RPCS3
itself (see `docs/debug-mode.md` for boot-skip patches); or batch
unrelated patches into a single iteration. Don't reach for savestates.

- **M1: Patched EBOOT boots to main menu.**
  - **Setup:** `docker_run.sh` with patched EBOOT, no input scripted.
  - **Action:** call `_navigate_startup_to_main_menu(proc)` and
    `_wait_for_text_on_screen("Play Now", timeout=180)`.
  - **Oracle:** `_wait_for_text_on_screen` returns `True` AND the RPCS3
    process is still alive AND the log has zero lines matching
    `'F .*EBOOT'` or `'unmapped'`.
  - **On fail:** likely a missed `_NCIV` reference from §5.1 — bisect by
    reverting individual loop-bound patches one at a time.

- **M2: Civ-select screen lists 17 entries with "Korea"/"Sejong" present.**
  - **Setup:** cold boot, then run M1's navigation to reach the main menu.
  - **Action:** drive input: `X` (Play Now) → `X` (single player) → `X`
    through difficulty → arrive at civ-select. Use `_wait_for_text_on_screen`
    to confirm we landed on the right screen by waiting for known existing
    text like "Choose Your Civilization" or "Caesar" first.
  - **Oracle 1 (text):** `_wait_for_text_on_screen("Korea", timeout=15)`
    after pressing Right enough times to wrap past slot 16 (or, simpler:
    OCR the full screen and assert "Korea" and "Sejong" both appear in the
    OCR output).
  - **Oracle 2 (count):** OCR the civ name strip while pressing Right
    repeatedly; collect the unique civ names seen across 20 presses.
    **Oracle:** the set has exactly 17 elements and contains "Korea".
  - **Oracle 3 (log):** zero asset-load errors in `rpcs3.log` in the time
    window between menu entry and screen render.
  - **Forensic capture:** screenshot of the civ-select screen with Korea
    highlighted, saved to `verification/M2/`.

- **M3: Selecting Korea progresses to the next menu without crashing and
  loads the Mao-as-Sejong leaderhead asset.**
  - **Action:** with Korea highlighted, press `X`. Wait 10 seconds.
  - **Oracle 1 (process alive):** RPCS3 process still running.
  - **Oracle 2 (log):** zero `'F .*'` (fatal) lines and zero
    `'failed to load.*chi_mao'` lines in `rpcs3.log`. We *expect* the
    leaderhead loader to pull `chi_mao_*` files for civ 16 — assert by
    grepping for successful `chi_mao_model.gr2` open events.
  - **Oracle 3 (text):** OCR the next screen and assert it contains
    expected post-civ-select text (e.g. "Choose Your World" or whatever the
    map-pick screen's title is — confirm during §5.4 asset-load trace).

### 7.3 Live memory checks (M4–M6)

These run by attaching to RPCS3 mid-execution, either via the GDB stub
(`gdb_client.GDBClient`) or via direct `process_vm_readv` using the
helpers lifted into `rpcs3_memory.py` per §5.5 setup. Direct reads are
preferred because they don't pause emulation.

- **M4: `_NCIV == 17` at runtime.**
  - **Prereq:** §5.1 must have located `_NCIV`'s PS3 virtual address.
    Record it as `KOREA_MOD_NCIV_ADDR` in `korea_mod/addresses.py`.
  - **Action:** at any point after M1 succeeds, `_read_ps3_u32(pid,
    KOREA_MOD_NCIV_ADDR)`.
  - **Oracle:** value `== 17`. Hard-fail and bisect if `== 16` (patch
    didn't apply) or anything else (wrong address).

- **M5: Civ table entry 16 is well-formed.**
  - **Prereq:** §5.2 must have located the civ-table base address and
    record stride. Record as `KOREA_MOD_CIVTABLE_BASE` and
    `KOREA_MOD_CIVTABLE_STRIDE`.
  - **Action:** read `STRIDE` bytes at `BASE + 16*STRIDE`. Parse the leader
    name pointer field (offset known from §5.2), follow it, read the
    null-terminated string.
  - **Oracle 1:** string equals `"Sejong"`. Hard-fail otherwise.
  - **Oracle 2:** read entry 0 (Caesar) the same way and assert it still
    equals `"Caesar"` — catches a botched table relocation that corrupted
    the original entries (the M9 risk).
  - **Oracle 3:** read entries 1..15, assert each matches the
    `expected_leader_names` constant in `addresses.py`. Any mismatch =
    table relocation bug, hard-fail.

- **M6: Selecting Korea boots into a working game.**
  - **Prereq:** M2 must be green. M6 reaches the in-game state by
    walking the same menu path a human would: civ select → highlight
    Korea → confirm → through the rest of the new-game flow → in
    game. **No GDB poke of nationality.** If the menu doesn't route
    Korea correctly into civ slot 16, that is an M2 bug, not an M6
    workaround.
  - **Setup:**
    - Cold boot the patched EBOOT.
    - Drive the menu: from main menu, navigate to civ select, scroll
      to Korea, select. Use OCR to verify "Korea"/"Korean" or
      "Sejong" is highlighted before pressing confirm.
    - Pick deterministic difficulty / map / opponent settings.
  - **Action 1 (nationality routing):** read
    `_read_ps3_u32(pid, KOREA_MOD_PLAYER_NATIONALITY_ARR + 0*KOREA_MOD_PLAYER_SLOT_STRIDE)`.
    **Oracle 1:** value `== 16`. If this fails, the menu selection
    didn't route Korea to civ index 16 — that's an M2 regression that
    M2's oracles missed. Hard-fail and surface as a new M2 oracle gap.
  - **Action 2 (game world exists):** wait until the in-game HUD
    appears (OCR poll for any standard HUD text — "Turn", "Gold",
    "Science", whatever §5.4's asset-load trace shows is reliable).
  - **Oracle 2 (HUD up):** OCR finds in-game HUD text within 60s of
    selection confirm.
  - **Oracle 3 (process alive):** RPCS3 still running.
  - **Oracle 4 (no fatal log lines):** zero `'F .*'` in `rpcs3.log`
    between selection confirm and HUD-up.
  - **Oracle 5 (no Korea-specific asset load failures):** zero log
    lines matching `'failed to load.*korea\|sejong'`. (Nothing
    matches `hwacha` because Hwacha is out of v1.0 scope.)
  - **Action 3 (capital can be founded):** drive input through the
    standard "Settler → Found City" sequence. Document the exact
    button sequence in `korea_mod/scripts/found_capital.py`.
  - **Oracle 6 (city count):** read Korea's (player's) city count
    from civ-table entry 16. Pass = `>= 1` within 30 seconds of the
    found-city input. This proves the player slot really is civ 16
    AND the standard game-flow code path works for the new civ.

  M6 does NOT test Hwacha, leader bonuses, civ trait, AI behavior,
  diplomacy, or anything else differentiating Korea from China.
  Korea IS China for v1.0 — the test just confirms that the fact of
  the 17th slot existing doesn't break the boot-into-gameplay path.

### 7.4 In-game soak (M7)

**No AutoPlay.** Per `MEMORY.md` and prior investigation, the in-binary
AutoPlay debug mode does not function on PS3 RPCS3 in this environment
and we never got it stable — it crashes without tuner init that we
cannot emulate. **Do not use, attempt to fix, or reference
`test_autoplay.py`'s autoplay-patch path for M7.** The soak test
instead runs as a normal single-player game where the agent plays AS
Korea and presses "end turn" repeatedly. Between turns the game
advances all AI civs automatically — this is regular game flow, not
debug mode, so it actually works.

**Why play as Korea (not as China with Korea AI):** in CivRev you do
not meet other civilizations until exploration brings them into
contact, which can take 20+ turns. Playing AS Korea exercises the
new civ slot every single turn from turn 1, instead of waiting for
random contact. This is also the strictest test for v1.0's only real
correctness question — *does the game keep working when civ 16 is the
player?*

The trade-off is that M7 **requires the menu-selection path to
work** — it is gated on M2 the same way M6 is.

- **M7: 50-turn end-turn-loop playing AS Korea.**
  - **Prereq:** M2 and M6 green.
  - **Setup:** as in M6 — cold boot, menu-drive to civ select,
    select Korea, confirm, found capital. Record the full button
    sequence in `korea_mod/scripts/start_korea_game.py`.
  - **Action loop:** for 50 iterations after capital founding:
    1. Press the end-turn controller button via
       `launch._send_ps3_button` (record the exact PS3-button-name
       in `addresses.py` alongside the other constants).
    2. If a "you have units that haven't moved / no production set"
       confirm dialog appears (detect via OCR of standard prompt
       text), dismiss it by pressing confirm again.
    3. Wait until the turn counter at `KOREA_MOD_TURN_COUNTER_ADDR`
       advances by 1 (poll via `_read_ps3_u32`, 30-second timeout
       per turn).
    4. Every 5 turns: read Korea's (player's) city count from
       civ-table entry 16. Append to `result.json`.
    5. Every 5 turns: screenshot for forensics.
  - **Oracle 1 (alive):** RPCS3 process still running and turn
    counter reached 50.
  - **Oracle 2 (city persists):** city count from civ-table entry 16
    is `>= 1` at every read across the run. The capital must not
    vanish — that would indicate civ 16 is being treated as
    barbarian or some other degenerate state.
  - **Oracle 3 (no crashes):** zero `'F .*'` lines in `rpcs3.log`
    over the full run.
  - **Oracle 4 (no leaks):** RPCS3 RSS grows by less than 200 MB
    across the run.
  - **Oracle 5 (no Korea-specific asset failures):** zero log lines
    matching `'failed to load.*korea\|sejong'`.
  - **Oracle 6 (text substitution sanity):** if any popup dialog
    fires during the run that contains `@CIVNAME` or `@CIVNAMEP`
    *literally* (i.e. the substitution didn't happen), that's a
    fail — `gfxtext.xml` is missing the Korean civ-name keys.
    Detect by OCR-grepping captured screenshots for the literal
    string `@CIV`.
  - **Forensic:** screenshot every 5 turns, `rpcs3.log` saved, final
    civ-table dump saved.
  - **Wall-clock budget:** 50 turns at the harness's typical
    end-turn-to-end-turn interval is 10–20 minutes. If a run exceeds
    30 minutes, fail with "stuck" rather than waiting forever.

  M7 explicitly does NOT test: Hwacha, civ trait, leader bonuses, AI
  behavior, diplomacy, victory conditions, or any
  Korea-vs-China differentiation. Korea IS China byte-for-byte for
  v1.0 — M7 just proves the game stays alive when civ 16 is the
  player slot.

If the end-turn button cannot be reliably driven via
`_send_ps3_button` (e.g. focus-stealing issues with the RPCS3
window), fall back to GDB-writing the per-player "turn ended" flag
directly — but do this only after confirming the input-driven path
is truly broken, since input is a more faithful test of the live
game.

### 7.5 Regression (M9)

- **M9: Stock civs unchanged.** Re-run the full M5 leader-name dump
  AND M7's 50-turn end-turn-loop using a sample of 4 original civs as
  the player: Caesar (slot 0), Mao (slot 6 — exercises the leader
  whose assets we're reusing for Sejong, so any aliasing bug shows
  here), Lincoln (slot 7), and Catherine (slot 5). For each:
  - Drive the menu through new-game flow, select that civ, run M7's
    50-turn loop with all the same oracles.
  - **Oracle:** identical to M5 + M7 oracles, but with the
    nationality assertion checking the relevant slot 0/5/6/7 instead
    of 16.
  - **Special attention to Mao (slot 6):** because §6.3's v1.0 asset
    reuse points Korea's leaderhead/portrait/voice at `chi_mao_*`
    files AND §6.2's civ-record copy makes Korea a byte-for-byte
    duplicate of China, this run is the canary for any unintended
    cross-talk between the two civs (e.g. Mao's display name being
    overwritten by Sejong's, China crashing because the table copy
    corrupted slot 6, etc.). If Mao still works correctly while
    Korea also exists in slot 16, the §6.2 patch is sound.

This is the single most important regression check because the
table-relocation patch in §6.2 is the riskiest binary change, and
because v1.0's strategy of making Korea a byte copy of China
creates a real risk of collateral damage to the original China civ.

### 7.6 Manual final check (M8) — out of the autonomous loop

- **M8: Full human playthrough.** Explicitly **not** part of the
  autonomous iteration loop. After the agent has driven M0–M7 + M9 to
  green, surface a "ready for human smoke test" message and stop. A human
  plays Korea start-to-victory checking civilopedia, diplomacy popups,
  every UU, and end-game screens. M8 is the gate from "tests pass" to
  "shipped".

### 7.7 Stop conditions for the autonomous loop

The agent should keep iterating as long as:
- M0 fails — almost always cheaply fixable (typo, wrong offset).
- M1–M3 fails with a deterministic OCR/log signal — try one more patch.
- M4–M6 fails because an address constant is wrong — re-derive from Ghidra
  and retry.
- M2 isn't green yet — keep iterating; M2 is the gate to all gameplay
  tests, so failing it does NOT itself count as a stop condition.
  Just keep working until Korea is selectable.

The agent should **stop and surface a question** when:
- The same milestone fails 3 consecutive times with the same signature
  (avoid infinite loops on an unsolvable problem).
- M0a reports a mismatch on the *base* unpatched EBOOT (`EBOOT_v130_clean.ELF`
  has been corrupted — do not try to "fix" by patching different bytes;
  re-extract from the original source).
- RPCS3 itself fails to launch repeatedly (host-side problem, not a mod problem).
- A test passes its oracle but the screenshot artifact is "obviously
  wrong" in a way the oracle missed — surface for human review rather than
  silently pretending the test was meaningful.
- §5 investigations are blocked because the Ghidra database doesn't
  contain a needed function — needs a Ghidra session, not blind patching.
- M6's Action 1 ("nationality routed to 16 via menu") fails repeatedly:
  this is an M2 oracle gap (M2 thought it was green but selecting Korea
  doesn't actually route into civ slot 16). Strengthen M2's oracles to
  catch this directly, then resume — don't paper over by GDB-poking
  the nationality.

### 7.8 Required address constants (must be filled in by §5)

These are the values the verification harness reads. Until §5 is complete,
they're placeholders and M4–M7 will fail the "address valid" precheck.
Track them in `korea_mod/addresses.py`:

```python
KOREA_MOD_NCIV_ADDR              = 0x????????  # §5.1
KOREA_MOD_CIVTABLE_BASE          = 0x????????  # §5.2
KOREA_MOD_CIVTABLE_STRIDE        = 0x??        # §5.2
KOREA_MOD_CIV_LEADER_NAME_OFFSET = 0x??        # §5.2 — offset within civ record
KOREA_MOD_TURN_COUNTER_ADDR      = 0x????????  # §5.2 / §5.4
KOREA_MOD_PLAYER_NATIONALITY_ARR = 0x????????  # §5.2 — base of per-player nationality array
KOREA_MOD_PLAYER_SLOT_STRIDE     = 0x??        # §5.2 — bytes between consecutive player slots
KOREA_MOD_CIV_CITY_COUNT_OFFSET  = 0x??        # §5.2 — offset within civ record

EXPECTED_LEADER_NAMES = [
    "Caesar", "Cleopatra", "Alexander", "Isabella", "Bismarck",
    "Catherine", "Mao", "Lincoln", "Tokugawa", "Napoleon",
    "Gandhi", "Saladin", "Montezuma", "Shaka Zulu", "Genghis Khan",
    "Elizabeth", "Sejong",
]
```

When M4 first reads `KOREA_MOD_NCIV_ADDR` and gets a sane value, the
harness writes the actual addresses back into `addresses.py` as a sanity
check artifact. From that point forward, all later milestones can rely on
those constants.

## 8. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Hidden hardcoded `< 16` loop missed in §5.1 → out-of-bounds crash on civ 16 | High | Crash | Cross-reference iOS symbols; soak test M7 |
| Civ table can't be extended in place, padding too small | Medium | Forces relocation patch | Plan for relocation up front; identify .data padding regions early |
| FPK "no new entries" rule applies to Common0/Pregame XML replacements too (not just adds) | Low | Asset load failure | v1.0 design avoids adds entirely; if even replacements break, fall back to Pak10 DLC mount per §6.3 escape hatch |
| Mao leaderhead/portrait reuse looks obviously wrong on civ-select | Accepted | Cosmetic only | Explicitly inside the v1.0 contract — not a defect. v1.1 retextures via in-place replacement |
| Multiplayer protocol assumes 16 civs, mod-vs-stock desync | High in MP | Crash/desync | MP is non-goal for v1; gate Korea behind a "single-player only" check if reachable from MP code paths |
| Save format breaks between modded and unmodded EBOOT | Medium | Existing saves unusable | Bump save version byte in patched EBOOT; document |

## 9. Final Result — Definition of Done (v1.0)

A user with a clean BLUS-30130 install and v1.30 update can:

1. Run `civrev_ps3/korea_mod/install.sh` (wraps `eboot_patches.py` +
   `pack_korea.sh` + RPCS3 install path).
2. Launch the game and see **Korea** as the 17th option on the
   civ-selection screen, labeled "Korean" / "Sejong" in the UI text.
   The portrait and leaderhead shown are reused from China — this is
   expected for v1.0 and not a defect.
3. Select Korea, confirm civ choice, and reach the in-game world map
   without crashing. Found the starting capital with the settler.
4. Press end-turn 50 times in a row from the founded-capital state
   without the game crashing or freezing.
5. Pick any of the 16 original civs in a separate run and confirm
   that civ still works (regression check) — at minimum, sample
   Caesar (slot 0), Mao (slot 6, the canary for asset reuse),
   Lincoln (slot 7), Catherine (slot 5).
6. Verification artifacts (M0–M7 + M9 `result.json` files,
   screenshots, and `rpcs3.log`s) are committed under
   `korea_mod/verification/`, dated, and reproducible by re-running
   `./korea_mod/verify.sh --tier=full` against the committed patched
   EBOOT and FPKs. `verify.sh` exits 0 on a fully green run.

**Explicitly NOT required for v1.0 DoD** (deferred to v1.1+):
- Hwacha unique unit existing or being buildable
- Korea's AI or diplomacy behaving differently from China's
- Korea-specific civilopedia entries
- Korea-specific civ trait, leader bonuses, or starting tech
- Custom Korean portraits or leaderheads
- Reaching turn 200 or any victory condition
- Multiplayer compatibility

## 10. Progress Log

This section is the agent's persistent state across ralph-loop iterations.
Append a new dated entry at the **top** of the log on every iteration that
made meaningful progress (so the most recent state is always the easiest to
find). Each iteration's first action is to read the top of this log to
re-orient.

### Entry format

```
### YYYY-MM-DD HH:MM — <iteration tag>

**Status:** <one of: investigating | implementing | verifying | blocked | done>
**Working on:** <PRD section being addressed, e.g. §5.2 civ-record layout>
**Did this iteration:**
- <bullet — concrete action + outcome>
- <bullet — link to commit SHA if applicable>

**Verification:** <which verify.sh tier ran and what it returned, or "n/a">
**Open blockers:** <any §7.7 stop-condition triggers, missing data, etc.>
**Next iteration should:** <1–3 bullets of the immediate next steps>

**PRD changes made this iteration:** <list of §x.y subsections updated, or "none">
```

### Conventions
- **Most recent entry on top.** Old entries scroll down. Do not edit prior
  entries — append a new one if state changes.
- **One entry per iteration that did real work.** Skip the log if an
  iteration only re-oriented and decided to bail (note that in commit
  message instead).
- **Resolved TBDs go in the PRD body, not here.** When §6.6 cells get
  filled in or §5.x investigations complete, edit those sections directly.
  The Progress Log just records *that* it happened, not the values.
- **Commits referenced here must already be pushed.** Don't cite a SHA
  that only exists in your local working copy.
- **Blockers must be specific.** "Hard" is not a blocker — "M2 fails
  oracle 2 because the OCR misreads 'Sejong' as 'Sejorg' and we need
  either a font tweak or a fuzzy-match in `_wait_for_text_on_screen`"
  is a blocker.

### Status counters

Update these on every iteration. If a number changes, the iteration made
meaningful progress; if none change, ask whether the iteration should
have written to the log at all.

v1.0 counters (the only ones that matter for the current scope):

- **§5 investigations complete (v1.0 subset):** 0 / 5 — §5.2 partially
  done (four parallel arrays dumped end-to-end; LDR_* head and any
  additional arrays still pending). §5.1 restated for parallel arrays
  but call-site catalog not yet started. §5.4, §5.5, §5.6 untouched.
- **§6.2 EBOOT patches landed:** 4 / 4 (iter-4: "Korean" string
  allocation + 17-entry ADJ_FLAT copy + 2 TOC entry redirects).
  Dry-run passes; EBOOT_korea.ELF produced. NOT yet runtime-tested.
- **§6.3 XML overlays landed:** 3 / 4 (`leaderheads.xml`,
  `console_pediainfo_civilizations.xml`,
  `console_pediainfo_leaders.xml`). gfxtext.xml is the fourth slot per
  the PRD but is not semantically applicable on PS3 — see §6.4 note
  below.
- **§6.4 string keys defined:** 0 / 3 — note: gfxtext.xml on PS3 is a
  SWF-localization file, not the civ-name TXT_KEY_* store. The
  authoritative civ/leader display strings are the in-EBOOT pointer
  tables found in §5.2, not an XML key set. §6.4's "add three
  TXT_KEY_* rows" plan may not apply to this binary — pending
  investigation.
- **Verification milestones green:** M0 (static only — XML well-
  formedness). M1..M9 not yet wired.
- **§9 DoD items satisfied:** 0 / 6

---

### 2026-04-14 — iter-4 (XEX decompression + first real EBOOT patch)

**Status:** implementing
**Working on:** §5.1 final enumeration, §6.2 EBOOT patches, §5.6 360 Rosetta Stone

**Did this iteration:**
- **§5.6:** built `civrev_xbox360/xenon_recomp/tools/dump_xex_image.cpp`
  and `build_and_dump.sh` to link against libXenonUtils.a inside the
  civrev-xenonrecomp Docker image. Produces the decompressed 360
  image at `work/extracted/default_decompressed.bin` (18.8 MB, base
  0x82000000). XEX decompression pipeline now reproducible.
- **§5.6:** located the 360 civ adjective pointer table at VA
  `0x82f5a2e8` (structurally identical to PS3's 0x0195fe28 — 16 × 4
  byte pointers to "Roman"..."English"). Identified a 360 consumer
  (`sub_82538478` in `ppc_recomp.90.cpp`) whose inline `lis -32251 +
  addi -23832` pair loads exactly that base.
- **§5.1 BREAKTHROUGH:** scanned PS3 code for TOC-relative `lwz rN,
  offset(r2)` loads targeting 0x0195fe28 and found **9 call sites**
  at offsets -0x1f34 (0x1938354) and -0x9d8 (0x19398b0) from
  r2=0x0193a288. Logged in `addresses.py` as
  `KOREA_MOD_ADJ_FLAT_CALLSITES`.
- **§5.1 SIMPLIFICATION:** verified that of the five rodata tables
  mapped in §5.2, **only ADJ_FLAT is live**. The other four
  (LDR_TAG, CIV_TAG, ADJ_PAIR, LEADER_NAMES) have ZERO 32-bit or
  64-bit references anywhere in the 26 MB binary — they're C++
  static-init rodata that the runtime code path never touches. This
  collapses the §6.2 patch scope from "extend 5 parallel arrays"
  to "extend 1 array + redirect 2 TOC entries".
- **§6.2 SHIPPED:** first real EBOOT patch list in
  `eboot_patches.py`. Four patches:
  1. Allocate `Korean\0\0` at 0x017f4038 (in a 144 KB zero-fill
     padding region at 0x017f4036..0x01818036).
  2. Write a 17-entry extended ADJ_FLAT copy at 0x017f4040.
  3. Redirect TOC entry at 0x01938354 → 0x017f4040.
  4. Redirect TOC entry at 0x019398b0 → 0x017f4040.
  All 4 sites pass dry-run's expected-old-bytes gate; produces
  EBOOT_korea.ELF with exactly 78 bytes of difference from the
  clean base, every patched offset inside a valid PT_LOAD segment.
- **Scanned for bounds checks**: no `cmpi rN, 0x10` within ±20
  instructions of any of the 9 ADJ_FLAT call sites. The code does
  not bounds-check civ indices at these sites, so a 17th entry is
  safe without any additional loop-bound rewrites.

**Verification:** `./korea_mod/verify.sh --tier=static` → PASS.

**Open blockers:**
- **EBOOT patch is not runtime-tested.** The byte-level changes are
  correct but we haven't yet booted the patched EBOOT in RPCS3 to
  confirm the relocated table is actually read by the 9 call sites.
- `install.sh` still staged with the unpatched EBOOT — next iteration
  should rebuild with `eboot_patches.py`'s output and install.

**Next iteration should:**
1. Run `./korea_mod/build.sh` end-to-end (now that
   `eboot_patches.py` produces a real EBOOT) and `./install.sh` to
   stage the patched EBOOT + modded Common0.FPK into the docker
   disc image.
2. Boot via `civrev_ps3/rpcs3_automation/docker_run.sh` and capture
   M1 (cold-boot-to-main-menu) artifacts. If M1 passes, drive the
   menu to the civ-select screen and check M2.
3. If M2 shows Korea (17th slot) with "Korean" as the adjective, the
   core mod is functionally complete — move to M6/M7 for the full
   gameplay oracles.

**PRD changes made this iteration:** Progress Log entry added.

### 2026-04-14 — iter-3 (iOS _NCIV correction + Rosetta Stone pivot)

**Status:** investigating
**Working on:** §5.1 NCIV references, §5.6 Xbox 360 cross-ref

**Did this iteration:**
- **§5.1 correction:** revisited iOS cross-ref and found
  `*(int *)PTR__NCIV_001fc1e0 = 6;` in multiple iOS sites, proving
  `_NCIV` is the **current game's civ count** (dynamic, per-game),
  not a compile-time max. Iter-2's "single byte patch to flip 16→17"
  plan was wrong. Corrected
  `korea_mod/docs/ncv-references.md` with the right mental model:
  the real lever is extending the per-civ lookup arrays, not
  patching `_NCIV`.
- **§5.6 caveat surfaced:** `civrev_ios/CLAUDE.md` is explicit that
  the iOS build is a **Nintendo DS lineage** (NDS* class prefix),
  not the PS3/Xbox 360 lineage. PRD §5.6's Rosetta Stone assumption
  still holds for engine-level code but is weaker for civ-specific
  game logic — iOS has 16 civs with "Grey Wolf" as a 17th leader
  (barbarians), not Korea.
- **Xbox 360 path evaluated:** the real Rosetta Stone is the 360
  binary (shares the console C++ codebase with PS3). The repo has
  xenon_recomp output at
  `civrev_xbox360/xenon_recomp/work/recomp_output/` (251 `.cpp`
  files) but it's raw PPC-to-C without string literals, and the
  XEX itself is compressed so `leaderheads.xml` / `Nationality`
  / `Caesar` are not findable by a literal search of
  `extracted/default.xex`. Decompressing the XEX is the missing
  prerequisite for a string-ref-based pivot to the leaderheads.xml
  loader function.
- **False-positive rejection:** re-inspected iter-2's two
  `lwz r2-off / li 0x10 / stw` candidates (0x359300, 0x95e258).
  Both are false matches — 0x359300 is a cross-function boundary
  (the `lwz` is the tail of the previous function, returning via
  `blr`), and 0x95e258 has an intermediate `li r0, 1` that
  overwrites `r0=16` before the store. Neither is the `_NCIV`
  initializer (and after the iter-3 correction, the `_NCIV`
  initializer isn't even what we should be looking for).

**Verification:** unchanged — M0 static tier still green.

**Open blockers:**
- Need a decompressed 360 XEX to pivot the Rosetta Stone onto the
  leaderheads.xml loader function.
- OR need a live RPCS3 session with GDB to dump the runtime civ
  table layout directly.

**Next iteration should:**
- Decompress the 360 XEX (xenon_recomp typically has a
  `decompress_xex` helper; otherwise use `xextool -u`). Search the
  result for `leaderheads.xml` / `LeaderHead` / `Nationality` and
  follow the calling function's cross-refs to identify the live
  civ-array access pattern in 360 PowerPC code.
- Pattern-match that function's structure (number of parameters,
  string-refs, call pattern to the XML parser helpers) against the
  PS3 Ghidra DB to find the structurally identical function in the
  PS3 binary. That function's disassembly is the key to §6.2.

**PRD changes made this iteration:** Progress Log entry added.

### 2026-04-14 — iter-2 (FPK pipeline + eboot dry-run + pediainfo overlays)

**Status:** investigating
**Working on:** §5.1 NCIV init-site hunt, §6.3 overlay set, §5.5 harness

**Did this iteration:**
- **§6.3:** `pack_korea.sh` now stages `extracted/Common0/` +
  `extracted/Pregame/`, applies every `xml_overlays/*.xml` in place,
  and repacks via `civrev_ps3/fpk.py`. Replace-only by design.
- **§7.1:** M0b reimplemented as a content-level round-trip oracle —
  SHA match against the stock FPK is infeasible because `fpk.py`
  strips the original's alignment padding (~273KB smaller output from
  identical entries), so M0b now extracts the modded FPK and
  byte-compares every entry against the staging tree.
- **§6.3:** `console_pediainfo_civilizations.xml` +
  `console_pediainfo_leaders.xml` overlays land; both reuse Mao /
  China pedia string keys and DDS assets (no new files shipped).
- **§6.2:** `eboot_patches.py --dry-run` scaffolded with empty PATCHES
  list; M0a wired end-to-end and exits 0.
- **§5.1:** iOS cross-ref finding committed — iOS Ghidra exports show
  `PTR__NCIV_001fc1e0` referenced 286 times as a single global. If PS3
  mirrors that design the loop-bound patch catalog collapses to one
  initialization-site byte patch. Static instruction scan for `li rN,
  0x10; stw rN, *(rPtr)` yields 89 candidates — too many without a
  TOC-prefilter.
- **§5.2:** `LDR_*` leader internal tag array confirmed end-to-end at
  `0x0194b318` (5 parallel arrays now fully mapped).

**Verification:** `./korea_mod/verify.sh --tier=static` → PASS
(xmllint + M0b 9632 file content checks + eboot dry-run zero
mismatch).

**Open blockers:**
- `_NCIV` init-site not yet identified. Needed before the patch list
  in `eboot_patches.py` can become non-empty.
- No live-runtime access to the game — M1+ tiers still not wired.

**Next iteration should:**
- Either: decode PS3 TOC-relative `ld rN, offset(r2)` pointer loads
  (TOC base at `0x0193a288`) and filter the 89 `li 0x10; stw`
  candidates down to the ones where the target pointer came from the
  data-segment region where `_NCIV` would live, OR boot
  RPCS3 via `rpcs3_automation/docker_run.sh` and GDB-scan the live
  game's memory for an int-16 in the cluster near other civ globals.
- Wire M1/M2 harness entry points in `verify.sh --tier=fast` so we
  can prove the menu shows 17 civs (or, failingly, show precisely
  what goes wrong when the 17th entry is dropped).

**PRD changes made this iteration:** Progress Log entry; status
counters updated.

### 2026-04-13 — iter-1 (scaffold + §5.2 kickoff)

**Status:** investigating
**Working on:** §5.2 civ-record layout, §5.1 NCIV references, korea_mod scaffold

**Did this iteration:**
- Scaffolded `civrev_ps3/korea_mod/` (docs/, xml_overlays/, verification/,
  scripts/, addresses.py, build.sh, verify.sh, .gitignore).
- **§5.2:** confirmed the PS3 EBOOT uses PARALLEL POINTER ARRAYS, not a
  civ-record struct. Four 16 × 4-byte tables located and dumped end-to-end:
  leader display names `0x0194b434`, civ internal tags `0x0194b35c`, civ
  adjectives `0x0195fe28`, civ adjective/plural pairs `0x0194b3c8`. Full
  pointer→string mapping recorded in `korea_mod/docs/civ-record-layout.md`.
- **§5.1:** restated the investigation for the parallel-array reality and
  captured candidate patch-site classes in
  `korea_mod/docs/ncv-references.md`. Concrete call-site enumeration is
  still outstanding.
- **§6.3:** wrote `xml_overlays/leaderheads.xml` with a 17th `<LeaderHead
  Nationality="16" Text="Sejong" ...>` entry reusing China's `GLchi_Mao.*`
  asset prefix. CRLF preserved, xmllint clean.
- **§5.5:** wired `build.sh` (stages overlays, hooks for future patcher)
  and `verify.sh --tier=static` with M0 XML well-formedness check. M0
  passes on the current scaffold.
- Updated PRD §6.2 to reflect the parallel-array model and retire the
  "extend the civ table" single-struct assumption.

**Verification:** `./korea_mod/verify.sh --tier=static` → PASS (M0 only).

**Open blockers:**
- §5.1 call-site enumeration not yet started. Needed before any EBOOT
  patching can begin — if we miss one `cmpwi rN, 0x10` the 17th civ
  either reads out of bounds or aliases civ 0.
- `LDR_*` leader internal tag array head not yet scanned (only the tail
  `LDR_india..LDR_england` is visible in the current dump). Trivial to
  resolve next iteration.
- pediainfo / pregame XML overlays still TODO; they are not boot-blocking
  but should land before M0d (string-key inventory) can be meaningful.
- No EBOOT patcher yet (`eboot_patches.py` missing); M0a is skipped.

**Next iteration should:**
- Finish enumerating the `LDR_*` array head and any fifth parallel array
  (city-name list pointers, color table, etc.) using the same
  pointer-scan technique against `leaderheads.xml`-derived string needles.
- Begin §5.1 call-site catalog by grepping
  `civrev_ps3/decompiled_v130/` for references to the four confirmed
  array bases and recording every enclosing function in
  `ncv-references.md`.
- Draft `eboot_patches.py --dry-run` against the (still-short) patch
  site list so M0a starts producing real output.

**PRD changes made this iteration:** §6.2 intro rewritten; Progress Log
entry added.



