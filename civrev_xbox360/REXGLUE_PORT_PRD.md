# PRD: Civilization Revolution (Xbox 360) native PC port via ReXGlue

*Handoff document for an autonomous AI agent. Written 2026-07-11. Companion docs:
`PORT_OPTIONS.md` (why ReXGlue was chosen) and `xenia_automation/ORACLE_IMPROVEMENTS.md`
(harness work that provides your verification oracle — read it; some milestones below
depend on artifacts it defines).*

---

## 1. Mission

Produce a **native Linux x86-64 build of Sid Meier's Civilization Revolution (Xbox 360)**
using the [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk): statically recompiled
game code linked against ReXGlue's runtime, loading the user's own extracted game assets,
verified milestone-by-milestone against the game running in Xenia.

**Definition of done (v1):** milestone M7 below — a single-player game can be started,
played for 20+ consecutive turns with rendering/input/audio working, saved, and reloaded,
launched by one script, with no crash across a 200-turn soak. Windows support, polish
items, and native-renderer work are explicitly out of scope for v1 (§10).

**Not the goal:** do not attempt to hand-write a runtime (XenonRecomp path), do not
reimplement game systems natively, do not fork Xenia. If ReXGlue is missing something,
prefer (a) config/TOML solutions, (b) mid-asm hooks, (c) minimal local patches to a
pinned SDK checkout, (d) upstream issue with reproducer — in that order.

## 2. Hard constraints & ground rules

1. **Legal hygiene:** never commit game assets, the ISO, XEX, or generated code derived
   from the XEX to any public remote. Work in this private repo. Add `.gitignore`
   entries before the first commit of the port project.
2. **Pin your toolchain.** Use ReXGlue **v0.8.0** (tag, 2026-05-16) unless blocked by a
   bug that a specific nightly fixes; record every version bump and why in `PROGRESS.md`.
   Breaking API changes between ReXGlue versions are known behavior.
3. **One GPU session at a time.** Two concurrent emulator/game processes starve the GPU
   on this host (verified previously with RPCS3). Take the lock defined in
   `ORACLE_IMPROVEMENTS.md` (H8) before any GPU-using run — both Xenia and your port.
   Exception: lavapipe/llvmpipe software-rendering runs are CPU-only and may run in
   parallel.
4. **Capture Xenia references first, then test the port** (never interleave two live
   sessions). Reference bundles live in `xenia_automation/references/`.
5. **Git discipline:** branch `rexglue-port`; commit at least at every milestone with the
   milestone ID in the message; keep `rexglue_port/PROGRESS.md` updated every session
   (what was tried, what worked, current blocker, next step). This file is your memory
   across context windows — write it for a successor who has read only this PRD.
6. **Escalate, don't thrash:** if a single blocker survives ~10 focused iterations or a
   full session, write it up in `PROGRESS.md` (symptom, hypotheses eliminated, exact
   repro), file an upstream issue if it's an SDK defect, and move to a parallelizable
   milestone (there is nearly always one — e.g. harness work, trace tooling, Ghidra
   symbol hunting).
7. Don't fall down any rabbit holes, and ensure things work before you build on them.

## 3. Environment

- Host: Linux x86-64 (kernel 6.17, Wayland session), Docker available and already used
  for all emulator work. Prefer Docker for toolchain isolation (Clang 20 may not be on
  the host); native host builds are fine if you install the toolchain cleanly.
- Working directory for the port project: create `civrev_xbox360/rexglue_port/`.
- All commands below assume repo root = `/home/mike/Desktop/civrev/civrev_xbox360`.

## 4. Asset & knowledge inventory (all paths verified 2026-07-11)

| Asset | Path | Notes |
|---|---|---|
| Game ISO | `./Sid Meier's Civilization Revolution (USA) (En,Fr,De,Es,It).iso` | Title ID 545407E5 |
| Extracted game tree | `xenon_recomp/work/extracted/` | `default.xex` + `Resource/` + `shaders/` — **this is your `game_data_root`** and the oracle's mount (H1) |
| Decompressed XEX image | `xenon_recomp/work/extracted/default_decompressed.bin` | mapped image @ 0x82000000, for Ghidra/byte-level work |
| XenonRecomp output (reference corpus) | `xenon_recomp/work/recomp_output/` | 63,266 functions / 248 TUs, compiles clean. Use to cross-check ReXGlue codegen (function counts, boundaries, a given function's translation) |
| XenonAnalyse switch tables | `xenon_recomp/work/switch_tables.toml` | format: `[[switch]] base/r/default/labels`; ReXGlue wants `[[switch_tables]] address/register/labels`. ReXGlue runs its own analysis — treat this file as a cross-check/fallback, converting entries only for tables ReXGlue misses |
| Old XenonRecomp config | `xenon_recomp/work/civrev.toml` | register save/restore addresses (savegprlr_14=0x827F3F50, restgprlr_14=0x827F3FA0, savefpr_14=0x827F5470, restfpr_14=0x827F54BC; no VMX save/restore present). ReXGlue's schema has no such fields (auto-detected) — historical reference only |
| Xenia oracle harness | `xenia_automation/` | see `ORACLE_IMPROVEMENTS.md`; game boots in xenia-edge here |
| Ghidra rig | inside `xenia_automation` Docker image | Ghidra 12.0.4 + XEXLoaderWV + Xenon VMX128 extension + 360 SDK FIDBs; `analyzeHeadless` on PATH |
| Reference Xenia log | `xenia_automation/output/xenia.log` | full module map, import lists, a crash under llvmpipe (display-mode issue, not a game blocker) |
| WP7 C# build | `../Civilization Revolution v1.0.0.0 [Winphone Iz].xap` | `Civ_WP7.dll` is managed C#/XNA → decompile with ILSpy for readable rules-engine logic |
| Cross-SKU RE knowledge | `../civrev_ps3/` (+ memory files) | PS3 effect layer, FPK/DDS/GFx asset tooling, debug-mode analysis (PS3 addresses do NOT transfer; concepts do) |
| Decision doc | `PORT_OPTIONS.md` | game middleware profile: Gamebryo, Scaleform GFx 2.x UI, Granny, Bink, Miles audio (+MP3), 28 `.fxobj` effect files |

Key binary facts: base `0x82000000`, entry `0x8280AD78`, image 18.7 MB, TLS 64 slots,
imports = xboxkrnl (181 unique) + xam (85 unique), built May 2008, XDK 2.0.6534/6690.

## 5. ReXGlue essentials (verified against SDK docs/wiki, July 2026)

- **Toolchain:** CMake ≥ 3.25, Ninja, **Clang 20+**, GTK3 dev headers on Linux
  (`libgtk-3-dev`); SDK is C++23, x64.
- **Build the SDK:**
  `git clone --recursive https://github.com/rexglue/rexglue-sdk && cd rexglue-sdk &&
  git checkout v0.8.0 && cmake --preset linux-amd64 && cmake --build out/build/linux-amd64 --target install`
- **Scaffold:** `rexglue init --app_name civrev --app_root ./civrev` → generates
  `CMakeLists.txt`, `CMakePresets.json`, `civrev_config.toml`, `src/main.cpp` (ReXApp
  subclass), `generated/rexglue.cmake`.
- **Codegen:** `rexglue codegen civrev_config.toml` (flags: `--force`,
  `--log_level=trace`, `--log_file=...`). Also exposed as a CMake target
  (`--target civrev_codegen`). Output: `generated/` with per-function `.cpp`,
  `sources.cmake`, init files. *"Unresolved functions are expected"* — iterate.
- **Config TOML surface** (full reference: wiki page "rexglue CLI Configuration File"):
  - required: `project_name`, `file_path` (the XEX), `out_directory_path`
  - `setjmp_address` / `longjmp_address` — find in Ghidra if the game uses them
    (search for the classic setjmp prologue; the XDK CRT is statically linked and the
    FIDBs will likely name them)
  - `[analysis]`: `max_jump_extension`, `data_region_threshold`,
    `large_function_threshold`, `exception_handler_funcs`
  - `[functions]` — `0xADDR = { name/size/end/parent }` manual boundaries
  - `[[switch_tables]]` — `address` (of the `bctr`), `register`, `labels`
  - `[[invalid_instructions]]` — `data`, `size` (mark embedded data)
  - `[[midasm_hook]]` — `address`, `name`, `registers`, `after_instruction`,
    `return`/`jump_address`/`*_on_true`/`*_on_false`
  - `[rexcrt]` — map CRT functions (`memcpy`, `RtlAllocateHeap` group…) to guest
    addresses so the runtime substitutes host implementations. The FIDBs identify these
    in Ghidra. Heap group is all-or-nothing. Likely a meaningful perf/stability lever.
  - codegen options (`skip_lr`, `ctr_as_local`, …): **leave all `false`** until the game
    is fully working; they are optimizations with correctness risk.
- **VFS:** `game:` and `d:` → `\Device\Harddisk0\Partition1` → host dir
  (**`game_data_root`**); `update:` → `update_data_root` if present; cache partitions are
  NullDevice no-ops. Configure via `ReXApp::OnConfigurePaths()` (`PathConfig`) or the
  `user_data_root`/`update_data_root` CVars. Point `game_data_root` at
  `xenon_recomp/work/extracted/` (or a copy).
- **Run:** `./out/linux-amd64/Debug/civrev --log_level=trace --log_file=run.log
  --gpu_backend=vulkan`.
- **Docs for deeper questions:** wiki pages *Codegen Pipeline Overview, Generated Code
  Structure, Function Overrides, Mid-ASM Hooks, Runtime Architecture Overview, ReXApp,
  Kernel State & Objects, Memory, Virtual File System, CVar System, Logging*; docs site
  `rexglue-rexglue-sdk.mintlify.app`; the SDK is indexed on Context7. Study one working
  port for idioms: [WistfulHopes/DBZ1](https://github.com/WistfulHopes/DBZ1) (minimal),
  [masterspike52/reNut](https://github.com/masterspike52/reNut) (disc game, hooks),
  [birabittoh/NocturneRecomp](https://github.com/birabittoh/NocturneRecomp) (Linux CI,
  mod system). Community: ReXGlue Discord, GitHub issues.

## 6. Milestones

Each milestone lists **acceptance criteria** (machine-checkable where possible) and the
**oracle artifact** it is verified against (defined in `ORACLE_IMPROVEMENTS.md`).
Do them in order; report progress against these IDs.

**M0 — Toolchain ready.**
SDK v0.8.0 builds; `rexglue --help` works; project scaffolded under
`rexglue_port/civrev/`; `.gitignore` excludes `generated/`, `assets/`, game files.
*Optional sanity check:* build and run the SDK's `demo-iruka` example first.

**M1 — Codegen completes.**
`rexglue codegen` exits 0 **without `--force`** (all unresolved-function/boundary
validation errors fixed via `[functions]` / `[[switch_tables]]` / `[[invalid_instructions]]`).
Sanity: generated function count within ~10% of 63,266 (XenonRecomp found that many);
spot-check 3 functions' boundaries against `recomp_output/` and/or Ghidra.

**M2 — Builds, links, starts.**
`cmake --build` succeeds; executable launches; trace log shows runtime init, VFS mounts,
guest entry `0x8280AD78` invoked; process survives ≥ 5 s or exits with a *diagnosable*
guest-side error (not a host crash in the SDK).

**M3 — Asset-loading parity.**
The port's file-access sequence (from its trace log) matches the Xenia reference trace
(oracle artifact `references/boot/file_trace.txt`): same file *set* for the boot phase;
landmark ordering preserved (xex → config/ini → early FPKs → shaders → movies). Threading
may reorder neighbors; compare sets + landmarks, not strict order.

**M4 — Boot flow reaches title screen.**
Firaxis/2K/Bink intro movies play (or are cleanly skipped — acceptable fallback: a
midasm hook or asset swap to bypass Bink, *documented*), then the title/press-start
screen renders. Verify: screenshot vs `references/boot/title.png` via the compare
tooling (H10) above its threshold; log shows GFx UI stream loads (`GFX_*.gfx`).

**M5 — Main menu interactive.**
Scripted input (SDL keyboard/gamepad) navigates: title → main menu → single-player
setup. Screenshot at each step matches the corresponding reference. Input path proven
end-to-end.

**M6 — In-game.**
A new single-player game starts: terrain map renders, a unit can be selected and moved,
end-turn advances (turn counter changes on screen and/or in log markers). Scripted
20-turn run completes without crash. Screenshot checkpoints vs `references/ingame/*`.
(Rendering need not be pixel-perfect — Xenia's own output is the bar; structural match.)

**M7 — Persistence, audio, soak. (v1 done)**
Save → quit → relaunch → load restores the game (XamContent* → VFS-backed content dir;
cross-check: a save produced in Xenia loads in the port, fixture H9). Music and SFX
audible (MP3 music via Miles is the likely first win; if XMA SFX are problematic,
document and stub — audio must not crash). 200-turn scripted soak without crash or
>100 MB/hr memory growth.

**M8 — Polish (stretch, unordered).**
Resolution options/ultrawide; 60 fps investigation; keyboard+mouse mapping; clean
stubbing of Xbox Live/multiplayer menu paths; achievements metadata; a `play.sh`
one-command launcher (mirroring the PS3 project's convention); Windows build via CI.

## 7. Verification protocol (per milestone)

Operational manual for the oracle harness (commands, result.json semantics,
OCR-verified navigation, debugging): `xenia_automation/oracle/AGENT_GUIDE.md`.

1. Ensure the reference bundle for the scenario exists (else generate per
   `ORACLE_IMPROVEMENTS.md` §H5–H6, taking the GPU lock).
2. Run the port under the same scenario script (same input timeline, same assets).
3. Compare: `file_trace` diff (M3+), screenshot compare (M4+), log-marker checklist
   (every milestone), exit status/watchdog result.
4. Record in `PROGRESS.md`: milestone, pass/fail, artifact paths, divergences accepted
   (with reasoning). A milestone "passes" only from a clean run started fresh, not from
   a lucky interactive session.

## 8. Troubleshooting playbook

| Symptom | Likely cause | Play |
|---|---|---|
| Codegen validation error: unresolved function / overlapping boundaries | analysis mis-split a function (jump table read as tail call) | Find the function in Ghidra (the rig auto-IDs SDK funcs via FIDB); add `[functions]` entry with `size`/`end`; cross-check against the XenonRecomp output for the same address |
| Runtime crash at a `bctr` (log/PC near a computed jump) | missed switch table | Locate table in Ghidra; add `[[switch_tables]]` (address = the `bctr`, `register`, `labels`); check `switch_tables.toml` from XenonAnalyse for a ready-made entry to convert |
| Codegen or runtime hits "unimplemented instruction" (likely VMX128 variants) | SDK gap | Implement locally in the pinned SDK checkout (instruction semantics: PowerPC ISA + VMX128 docs; XenonRecomp's translation of the same opcode in `recomp_output/` is a working reference); upstream a PR/issue — precedent: reNut's `vsldoi128` fix |
| Log: "undefined extern call" / missing kernel export | unimplemented xboxkrnl/xam shim | Check the SDK's kernel sources for near-neighbors; implement or stub (return success + log). CivRev's Xenia run needed only 4+19 unimplemented imports total — expect few gaps; likely candidates: `XeKeysConsolePrivateKeySign`, `IoDismountVolumeByFileHandle` (Xenia stubs these too and the game boots) |
| Boot stalls: repeated file-not-found in log | VFS layout mismatch | Diff requested path vs `extracted/` tree; the game probes optional paths (e.g. `\Data\Shaders\...DefaultCache.psc`, `$SystemUpdate`) that fail on Xenia too — compare against the Xenia reference trace before "fixing" anything |
| Hang, log silent, threads alive | wait-object deadlock or vblank starvation | Raise log level; inspect KeWaitForSingleObject/KeSetEvent traffic; check the SDK's vblank/VdSwap pump; compare thread creation sequence vs Xenia log |
| Renders garbage / black screen at M4 | shader translation or vertex-fetch issue in rexgpu-xenos | Try `--gpu_backend=vulkan` vs `d3d12` (on Windows CI), capture with RenderDoc, reduce to a single draw; report upstream with capture — do NOT start writing a renderer |
| Crash inside a specific guest function, cause opaque | logic-level question | Identify the function: Ghidra + FIDB; map to iOS symbol names / WP7 C# (ILSpy) via string xrefs (`c:\source\main\civconsole\src\...` asserts are gold); the PS3 project's function-naming techniques transfer |
| Divergent behavior vs Xenia (same inputs, different game state) | recompilation correctness bug | Bisect via file/kernel trace to the divergence point; instrument with `[[midasm_hook]]` logging registers at suspect functions; compare against XenonRecomp's translation of the same function |

## 9. Reporting & deliverables

- `rexglue_port/PROGRESS.md` — running journal (per session: date, milestone focus,
  attempts, outcome, next).
- `rexglue_port/civrev/` — the ReXGlue project (config TOML is the crown jewel — keep it
  heavily commented: every manual entry gets a one-line "why").
- `rexglue_port/NOTES_UPSTREAM.md` — every SDK bug found, local patch carried, and issue
  filed (with links), so version bumps are auditable.
- On v1 completion: update `PORT_OPTIONS.md` with an outcome addendum and write a
  `README.md` in `rexglue_port/` covering build-from-scratch instructions.

## 10. Out of scope for v1

Native renderer (phase 2 — via the `rexgpu-xenos` plugin boundary), Windows/macOS
builds, multiplayer/Xbox Live, DLC map packs (the PS3 project's Pak9 knowledge suggests
later fun), achievements UI, mod loader, performance tuning beyond "plays smoothly",
and any XenonRecomp-path work.
