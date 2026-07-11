# CivRev ReXGlue port — progress journal

Read `../REXGLUE_PORT_PRD.md` first; this file assumes it. Newest session at top.

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

### Next
- Rebuild port (stubs) → M2 launch check.
- Green boot run → `capture_reference.sh boot` for the real reference bundle.
- M3: file-trace diff (extract_file_trace.py already handles ReXGlue shapes).
- M4-goal: port renders copyright/ESRB screens; compare vs reference
  checkpoints 00_copyright/01_esrb.
