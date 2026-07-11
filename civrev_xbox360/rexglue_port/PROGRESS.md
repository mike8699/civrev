# CivRev ReXGlue port — progress journal

Read `../REXGLUE_PORT_PRD.md` first; this file assumes it. Newest session at top.

## Blocker investigation: guest main() returns 0 before first present (M2/M4)

**Symptom:** port boots, loads all assets (file trace PASSES vs Xenia reference:
49/49 paths, order ok), initializes D3D (full Vd sequence incl. ring buffer ×2,
EDRAM training), completes fxobj round 1 of 3, then guest main returns 0
("DbgPrint: [XAPI RETURN VALUE] 0" → TerminateTitle) ~0.76 s in. No crash, no
error. Xenia does 3 fxobj rounds then presents (Hardware scaler) and registers
audio. Port never presents, never calls XAudioRegisterRenderDriverClient.

**Hypotheses ELIMINATED (each verified, most against Xenia source):**
- XUsbcam/kernel export gaps (stubbed, Xenia semantics)
- data-referenced functions missing (843 gap-fill entries + 341 branch
  targets registered; zero unresolved fatals in generated code)
- switch tables (ReXGlue analyzed them; per-case targets registered)
- NtReadFile async/APC semantics (matches Xenia: sync read + APC + PENDING)
- 0xC0000002 conversions: red herring — game's OWN XAPI stub sub_82816398
  hardcodes li r3,0xC0000002; called once per fxobj on Xenia too
- FindFirstFile/NtQueryDirectoryFile enumeration (works; patterns match)
- movie blanking asymmetry (works; .bik query lines simply invisible in
  Xenia's ResolvePath-based trace)
- Vd* shims (VdInitializeEngines/RetrainEDRAM/IsHSIOTrainingSucceeded/
  SystemCommandBuffer/QueryVideoMode — byte-identical semantics to Xenia)
- vblank ISR delivery (instrumented: guest ISR 8269CDF8 invoked repeatedly)
- GPU MMIO register file (matches Xenia's ReadRegister/WriteRegister)
- audio backend (SDL, same as Xenia; game never got as far as audio init)

**Root-cause lead (STRONG):** v0.8.0 codegen has KNOWN-BROKEN VMX128
translations fixed after release:
- `vpkd3d128 float16_4 mask=2/3 zero-clear` (711d4d3) shipped in v0.8.0,
  REVERTED upstream 2026-06-03 (649a3b9) as wrong — 12 sites in our
  generated code; vpkd3d128 = D3D pack, exactly the D3D-init path
- `vaddsws` fixed 2026-06-03 (bd9b519) — 641 sites in our generated code
- `recover function tail after conditional bcctr` fixed in nightly 8dadea63
Guest D3D init computes with these → silently wrong values → device init
validation fails → clean exit. Consistent with "diverges between fxobj
rounds with nothing kernel-visible in between".

**Action:** bump SDK pin v0.8.0 → nightly-20260628-8dadea63 (0.8.1.68-dev),
per PRD §2.2 (bug-fix bump, recorded here). Debug instrumentation dropped on
bump; patches/0001 (CallTarget fallback) re-evaluated against the nightly.

## Session 1 — 2026-07-11 — M0 (toolchain) → M1 (codegen)

**Session goal:** boot the port far enough that the opening copyright/legal
screens render correctly (PRD M0→M4-partial).

### Done
- Branch `rexglue-port` created off `xenia-oracle-harness`.
- `.gitignore` written BEFORE anything else (excludes `civrev/generated/`,
  SDK checkout/install, zips, logs, all game-file extensions).
- ReXGlue SDK v0.8.0: cloned at tag `2bdb97f` (`rexglue-sdk/`, gitignored) AND
  prebuilt linux-amd64 release binary downloaded → `sdk_install/linux-amd64/`
  (gitignored). Prebuilt `rexglue --help` works on host. Rationale: prebuilt
  CLI unblocks codegen immediately; the source checkout is for local patches
  if needed (troubleshooting playbook) and is built via Docker.
- `docker/Dockerfile.toolchain` — replicates the SDK's own linux-amd64 CI env
  (ubuntu 24.04 + clang-20 + LunarG vulkan-sdk + GTK3 + audio deps + Xvfb/
  lavapipe/tesseract for headless port runs). Image `rexglue-toolchain`
  (build in progress).
- Scaffolded `civrev/` via
  `rexglue init --project-name civrev --xex-path ../xenon_recomp/work/extracted/default.xex --game-root ../xenon_recomp/work/extracted --project-root ./civrev`.
  NOTE: v0.8.0 CLI flags differ from PRD §5 sketch (`--app_name` → `--project-name`
  etc.); manifest file is `civrev_manifest.toml` (not `civrev_config.toml`),
  sections `[project]` + `[entrypoint]`. Config field names verified against
  `src/codegen/config.cpp` — match PRD §5 list (`[functions]`,
  `[[switch_tables]]` with address/register/labels, `[[invalid_instructions]]`,
  `[[midasm_hook]]`, `[rexcrt]`, `setjmp`/`longjmp`, `[analysis]`).
- Known harness fact: `references/boot/` bundle is STALE (checkpoint names from
  an older boot script, status=crash, screenshot shows profile dialog —
  predates profile seeding). Needs recapture before M3/M4 comparisons.

### M1 — PASSED
- Run 1: 3 unresolved tail-call targets (0x827F8840, 0x82324B48, 0x82841038;
  callers are 4-byte `b` thunks). Added `[entrypoint.functions]` sizes from the
  XenonRecomp corpus. Run 2: validation clean, emission 71 s, no `--force`.
- Function-count sanity: ReXGlue 40,067 vs XenonRecomp 62,939 — NOT a red flag:
  20,467+ of XR's are `.long 0x0` zero-padding stubs and XR splits switch cases
  into mini-functions (0x82D72318 verified as internal `loc_` label in ReXGlue,
  standalone stub-func in XR). Real counts agree within ~6%.

### Boot-reference work (goal: copyright screens)
- Discovered boot legal sequence via frame-grab run: copyright page
  (©2005-2008 Take-Two, ~4 s) → ESRB notice (~4 s) → "Loading..." splash →
  Press START title. OCR patterns validated on real frames.
- Stale `references/boot` bundle explained: pre-dated SDL_AUDIODRIVER=dummy and
  profile seeding fixes (audio-thread guest crash at 0x82A6DE1C + profile
  dialog on screen). Needs recapture — DO NOT diff against it.
- Harness: added `wait_text_shot` (checkpoint = the exact OCR-matched frame;
  short-lived screens can't be shot after the wait); OCR poll 2 s → 1 s;
  FIXED parser bug: aligned columns left a trailing space in wait_text
  patterns → `Loading\.\.\. ` can never match at end-of-text.
- boot_legal_v2 run: copyright + ESRB checkpoints captured ✓; game lingered on
  Loading splash >150 s (vs 43-48 s total in boot_fast3) — log identical to
  good runs (goes quiet after WSAStartup), so game alive; cause unclear
  (suspect CPU contention from 1 s OCR+tesseract polling under lavapipe).
  boot_legal_v3 rerunning with parser fix.

### M2 — in progress
- Build in rexglue-toolchain image: 117 recomp TUs compile clean (~19 min,
  all cores). Link failed: 6 undefined `__imp__XUsbcam*` (Xbox Live Vision
  camera XAM exports absent from SDK v0.8.0). Fix: `src/kernel_stubs.cpp`
  using REX_EXPORT_STUB_RETURN, semantics copied from Xenia
  (xboxkrnl_usbcam.cc): Create MUST return 0/success (error breaks some titles'
  init), GetState 0 = not connected. Rebuild pending (serialized after the
  Xenia run to avoid CPU starvation).
- `run_port.sh` written: container runner mirroring oracle semantics
  (movie-blank bind mounts, dummy audio, Xvfb+lavapipe 1280x720, RO game
  mount, frame grabs, GPU lock). Note: SDK hardcodes Vulkan backend on Linux —
  no --gpu_backend flag exists in v0.8.0.

### Boot reference — CAPTURED ✓
- `references/boot` re-promoted: 2×completed, file trace identical, legal-page
  shots pixel-identical across runs (combined=1.0000 for
  00_copyright/01_esrb/02_loading; title/menu differ = live 3D, use masks).
- boot scenario now: 00_copyright → 01_esrb → 02_loading → 03_title →
  04_main_menu. The v2 "stuck at Loading" was a flake/contention artifact; v3
  and both reference runs completed in ~147 s.

### M2 — runtime bring-up log
- Launch attempt 1: no run.log — `librexruntime.so` not found (SDK lib dir
  now mounted at /sdk + LD_LIBRARY_PATH; also fixed supervisor set -e/wait
  bug that swallowed exit_reason).
- Launch attempt 2: port initializes fully (logging, VFS mounts game:/d:,
  Vulkan/llvmpipe device, function table: 40,558 registered, XEX loads,
  imports patched, kernel threads spawn) then FATAL: "Call to invalid or
  unregistered function at guest address 0x82E80DA8" (SIGABRT) during
  KernelState module launch.
- Root cause class: ReXGlue reachability analysis misses functions referenced
  only through DATA (vtables/function-pointer tables). XenonRecomp's gap-fill
  found them. Mined the full set from the corpus:
  63,266 XR funcs − 20,467 zero-padding stubs − 1,545 present as internal
  labels in ReXGlue merges − present-as-functions ⇒ 872 truly absent.
  `tools/gen_missing_functions.py` emits `civrev/functions_xr_gapfill.toml`
  (address+size only — no game code committed), wired via manifest
  `includes`. 29 entries whose XR ranges overlap ReXGlue-merged functions
  produced "b <target> not in any function" (tail into another function's
  internal label) — dropped, validation-guided; kept 843. Codegen run 4
  clean, 81 s.
- Trace tooling proven on real port log; extractor regex fixed to terminate
  at quotes (`'game:\default.xex'` shape).

### Next
- Rebuild after codegen 4 (in flight, ~20 min) → rerun M2 smoke.
- M3: file-trace diff vs references/boot/file_trace.txt.
- M4-goal: port renders copyright/ESRB screens; compare vs reference
  checkpoints 00_copyright/01_esrb (these are pixel-deterministic in Xenia).
