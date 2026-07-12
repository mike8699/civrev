# CivRev ReXGlue port — progress journal

Read `../REXGLUE_PORT_PRD.md` first; this file assumes it. Newest session at top.

## M4 BRIGHTNESS — ROOT CAUSE LOCALIZED (not yet fixed)

**Proven:** the render pipeline works end-to-end. With a diagnostic gamma-table
remap (`--civrev_gamma_boost`, patches/0003: maps any nonzero source index to
full-bright), the **Loading screen renders crisp, correct WHITE text**
(`port_output/m4_gboost/frames/f0030.png`). So geometry, text, layout, blending
and present are all correct.

**Exact defect:** the swap-source front buffer stores **white as byte 1, not
255** — every rendered value is quantized to ~1/256 of correct. Without the
boost, the game's own gamma ramp (verified healthy: ramp[1]=1/1023≈0.001,
ramp[255]=1023) maps source-index-1 → ~0, so the whole frame presents at
max-byte 1 (looks near-black with barely-visible dim text). Secondary artifact:
the black background carries a green floor (G=1, R=B=0).

**Bisection (all via in-plugin log/readback probes; RenderDoc replay hangs
under both lavapipe and Intel in this containerized env):**
- Present/gamma EXONERATED (boost proves it; ramp healthy; plain==fxaa output).
- Render exp_bias = 0; resolve `copy_dest_exp_bias` = 0 → resolve takes the
  FAST raw-byte-copy path (k_8_8_8_8 fmt0 → fmt6, bitwise-equivalent), so the
  byte-1 value is already in EDRAM before the resolve.
- All GPU shaders (texture_load_32bpb, resolve_fast_32bpp, gamma apply) are
  Xenia's precompiled SPIR-V — byte-identical. Host-RT = R8G8B8A8_UNORM.
- Cross-GPU identical (lavapipe AND Intel ANV) ⇒ deterministic logic.

**Remaining fork (needs a working frame debugger):** either (a) the recompiled
guest computes 1/256-scaled vertex colors into the GFx composite (a VMX/float
recompilation bug — PRD §2.6 escalation class), or (b) the host-RT→EDRAM store
for format 0 truncates UNORM 1.0→1. Definitive next step: RenderDoc capture
REPLAY (capture WORKS — `port_output/m4_rdoc5/*.rdc` via layer-manifest fix +
in-app StartFrameCapture; replay hangs here) to read the host-RT texel right
after the text draw — dim ⇒ (a), bright ⇒ (b).

**Goal status:** copyright/ESRB screens do NOT yet render correctly/visibly.
NOT ACHIEVED. Upstream issue drafted (UPSTREAM_ISSUE_DRAFT.md §C); needs user
confirmation to file.

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

### RESULT of the bump — M2 PASSED, exit bug GONE
- Nightly SDK built from source in the toolchain image (needs libxss-dev —
  added to Dockerfile; SDL3 submodule newer). patches/0001 still needed,
  re-applied cleanly. Codegen clean on first run (73 s), zero unresolved
  fatals, port rebuilt against the nightly install.
- Nightly moved GPU emulation behind a plugin: `--gpu_plugin=xenos` +
  librexgpu-xenos.so staged next to the exe (CMakeLists inlines
  rexglue_configure_target(civrev GPU_PLUGINS xenos); run_port.sh passes the
  flag). Without it the game runs headless ("native rendering mode").
- **The guest no longer exits.** With GPU emulation on, boot proceeded to
  a NEW failure: CP `ExecutePacketType0 overflow` on the primary ring — a
  ring re-init race (see NOTES_UPSTREAM §3), fixed locally
  (patches/0002-gpu-cp-ring-reinit-race.patch, epoch handshake).
- **After the CP fix: the game BOOTS and RENDERS.** 3 fxobj rounds (matches
  Xenia), device init completes, background-loader thread resumes, resolves
  and swaps flow (1110+), and the **Loading splash renders with crisp,
  correctly-positioned text** — at ~1/255 brightness (see NOTES_UPSTREAM §5,
  open). First visible frame at ~32 s (llvmpipe pipeline warm-up); legal
  screens presumably pass during the black warm-up window — needs a
  faster-present run or host-GPU run to verify/capture.
- M2 acceptance: builds/links/launches, runtime init, VFS mounts, guest
  entry invoked, survives indefinitely with no host crash — **PASS**.
- M3 acceptance: file-trace diff vs references/boot PASS (49/49 paths,
  landmarks ordered, 2 benign misses <10% tolerance) — **PASS** (recorded
  from the pre-bump run; re-verify on the nightly build during M4 work).

### M4 brightness investigation — full elimination trail (this session)
All via cheap plugin-log probes (rebuild rexgpu-xenos only, ~1 min/cycle):
- Present side EXONERATED: plain and FXAA pipelines produce byte-identical
  dim output; gamma LUT machinery byte-identical to Xenia; guest-set 256-entry
  ramp verified healthy at swap time (ramp[1]=1, ramp[128]=462,
  ramp[255]=1023 — correct sRGB curve, so guest FLOAT math is fine too).
- Draw-side probes: for both boot pixel-shader pipelines (C3BE tfetch-alpha
  text shader; 3A92 `mad oC0, r0, c2, c3`), shader float constants at draw
  time are healthy (c2=(1,1,1,1) c3=(0,0,0,0)).
- Peculiarity: scanning the bound vf0 vertex heap (15 MB at phys 0x08000000)
  via TranslatePhysical at draw time shows ALL ZEROS across every record,
  while draws visibly emit (dim) geometry — either the probe reads a
  different backing than SharedMemory's upload path, or the visible content
  is drawn by an unprobed pipeline. RenderDoc single-draw capture is the
  right next instrument.
- Fade-stuck and vblank-starvation theories eliminated (game presents
  1110+ swaps at ~12 fps; loop runs).
- Xenia stubs VdRegisterGraphicsNotification identically — not the tick source.
- Host-GPU (Intel ANV) run also dark ⇒ not llvmpipe-specific.
- Audio never registers (XAudioRegisterRenderDriverClient never called) —
  in Xenia it fires ~1 s after first present. Likely downstream of whatever
  gates the game's boot progression; revisit after brightness.

### M4 continued (same session, later)
- Eliminated additionally: async-shader-compilation placeholder pipelines
  (--no-async_shader_compilation → identical 1/255 output); pipeline-cache
  warm-up (persisted cache; presents still gated by game pace under llvmpipe,
  legal text at 1/255 quantizes to 0 in 8-bit capture, so copyright screens
  cannot be verified until brightness is fixed).
- RenderDoc 1.33 binary tarball staged at tools_bin/renderdoc_1.33 (gitignored);
  auto-TriggerCapture at swap 10 wired into the plugin's IssueSwap (debug-only,
  in the gitignored SDK tree — re-add after any SDK re-checkout). Injection
  verified ("RenderDoc API initialized", trigger fired once) but no .rdc
  written before timeout — llvmpipe under the capture layer is extremely slow.
  Host-GPU capture attempts: injection works (hooks registered, API init,
  in-app TriggerCapture fires — logged), but no .rdc is written; first attempt
  with -c template hit "Stream created with invalid file handle", second with
  default paths produced nothing. Suspect capture/window association with the
  runtime-dlopen'd librexgpu-xenos Vulkan usage. NEXT SESSION: (a) try
  StartFrameCapture/EndFrameCapture with explicit device/window handles via
  the in-app API instead of TriggerCapture, or (b) set RENDERDOC_CAPTUREOPTS /
  use qrenderdoc UI on the host interactively, or (c) fall back to the SDK's
  own trace_gpu_stream + a minimal trace parser for the resolve-destination
  bytes. Then analyze the dim draw (pipeline, VS input values, blend state).
  Also fix stale-process kill in capture helpers (pkill pattern must match
  full cmdline; a leftover instance contended the second attempt).

### Next (M4)
1. RenderDoc capture of one dim draw (or minimal trace tool from the SDK's
   trace_writer output) → upstream Issue C with capture attached.
2. File UPSTREAM_ISSUE_DRAFT.md issues A (CP race, patch ready) and B (PWL
   swap) — CONFIRM WITH USER before filing (public, outward-facing).
3. Once brightness is fixed: host-GPU or weston-mode container run (fast
   pipeline warm-up) so the copyright/ESRB screens are visible during their
   ~4 s window; then compare vs references/boot 00_copyright/01_esrb.
4. Re-verify M3 file trace on the nightly build (was recorded pre-bump).

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
