# CivRev ReXGlue port — progress journal

Read `../REXGLUE_PORT_PRD.md` first; this file assumes it. Newest session at top.

## M4 BRIGHTNESS — CONFIRMED an SDK GPU-render bug (fixable), not recompilation

**Definitive (staging readback of the device-local shared-memory buffer via a
host-visible copy — the measurement that finally cracked the confusion):**
- Every draw's bound **vertex-color data in GPU memory is BRIGHT (max byte 255,
  0xFFFFFFFF)** — pixel shaders 2E37/C3BE/3A92 all carry 0xFF colors. The guest
  is NOT writing dim colors, so this is NOT a recompilation bug.
- The FMT_8_8_8_8 vertex fetch normalization is correct (packed width 8 →
  1/255 scale, 0xFF → 1.0; matches Xenia). The 3A92/11213E38 composite VS/PS
  are identity (VS `max o0,r0,r0`; PS `mad oC0,r0,c2,c3` with c2=1,c3=0).
- Yet the presented **display front buffer is ~1/256** (`chmax=[1,2,1,255]`
  whole-frame), while other intermediate render targets resolve BRIGHT (255).
  Two resolves with IDENTICAL params (1D818000 bright vs 1F6F8000 dim; both
  src_fmt=0 dst_fmt=6 exp_bias=0 2xMSAA sample_sel=k01 edram_base=0) prove the
  resolve isn't the cause — the EDRAM content already differs.

**Conclusion:** bright vertex input → ~1/256 output. The SDK's render pipeline
(interpolation or, more likely, the host-RT→EDRAM store for the specific
2x-MSAA display-composite draws) dims it. This is a **fixable SDK GPU bug**.
The exact render state that triggers it (vs the identical-param bright draws)
needs frame-debugger draw inspection — RenderDoc capture works but replay
hangs headless here. Xenia's scaler is a NOP (matches ReXGlue), so the
composite is done by guest draws, not the scaler.

Diagnostics for continuation live in patches/0003 (default-off cvars:
--civrev_gamma_boost, --civrev_swap_reload, --civrev_force_color_mask).

## M4 BRIGHTNESS — earlier localization trail (superseded by the above)

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

**FURTHER LOCALIZED via per-channel readback of resolve outputs (guest RAM,
`--vulkan_readback_resolve`):**
- The **scene/UI render targets are FULLY BRIGHT** in guest RAM: e.g. 1D0F0000
  chmax=[255,255,255,254] with varied real content; a clear buffer 1E3B0000 =
  all 0xFFFFFFFF.
- The **presented display front buffer is near-zero RGB** across the WHOLE
  1280×720 frame: 1F6F8000/1F360000/1F70C000/1F374000 all chmax=[1,2,1,255]
  (R≤1, G≤2, B≤1, A=255) — no RGB byte anywhere exceeds 8, including where the
  bright UI/text should be.
- So the game renders the UI correctly to intermediate targets, but the **final
  composite into the display front buffer produces ~1/128–1/256 RGB** (white →
  byte 1–2) with full alpha. That composite draw is the culprit.

**Eliminated at the composite:** color write mask (`--civrev_force_color_mask`
= RGBA → no change), swap-texture staleness (`--civrev_swap_reload` → no
change), resolve `copy_dest_exp_bias` (=0, fast raw copy). So not masked, not
stale, not resolve-scaled.

**Remaining fork (needs a working frame debugger):** the composite draw either
(a) is issued by the recompiled guest with a wrong ~1/256 color constant/scale
(VMX/float recompilation bug — PRD §2.6 escalation class), or (b) samples its
source UI texture and the sample returns 1/256 (a resolve-target-sampled-as-
texture GPU bug). Definitive next step: RenderDoc REPLAY of the saved capture
(`port_output/m4_rdoc5/*.rdc`; replay hangs headless here on both lavapipe and
Intel) to inspect that draw's shader, constants, and sampled-texture values.

**Goal status:** copyright/ESRB screens do NOT render correctly/visibly.
NOT ACHIEVED. The diagnostic `--civrev_gamma_boost` recovers visibility (white
text) but with a wrong green background (the bg's G=2 floor amplified), so it
is not a correct fix. Escalated per PRD §2.6: upstream issue drafted
(UPSTREAM_ISSUE_DRAFT.md §C, updated with the composite localization); needs
user confirmation to file, and a machine where the RenderDoc replay runs.

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

---

## M4 — opening screens render (in progress; blocked on a GPU-side vertex-color defect)

**Status:** The port boots and reaches the copyright → ESRB → "Loading…" screens.
Every screen is **structurally perfect** — correct geometry, glyph shapes,
anti-aliasing, layout, and position all match the Xenia reference — but renders
at **~1/256 brightness (near-black)**. Under the lavapipe (Mesa software Vulkan)
rasterizer used by the headless harness, the "Loading…" text amplifies to a
crisp but **near-zero green** string, and the logo region is a correctly-placed
but near-black block.

### Root cause, localized with high confidence
The near-black output is caused entirely by **UI vertex COLORS decoding to a
near-zero constant** (`0x00000100`, i.e. green byte = 1) while the geometry
(position/UV) decodes correctly. Everything that consumes those colors —
Scaleform text (pixel shader `C3BE`) and the logo (`2E37`/`3A92`) — reads the
color from the packed `FMT_8_8_8_8` vertex attribute, so all UI is affected.

The vertex layout (VS `2BA2`) is stride-7 dwords:
`[0..3]=position k_32_32_32_32_FLOAT`, `[4..5]=UV k_32_32_FLOAT`,
`[6]=color k_8_8_8_8` (a `vfetch_mini`).

### What is PROVEN correct (so the bug is NOT here)
1. **Render pipeline** — forcing the `k_8_8_8_8` fetch result to white in the
   translator makes the whole screen render bright white (264k px, max=255). So
   rasterization, atlas sampling, blend, resolve, present, and gamma are correct.
2. **Guest data** — the CPU mirror (`memory().TranslatePhysical`) holds the
   correct bright cream color `0xD5EFEFFF` at the color dword for every drawn
   vertex (fetch constant 95 @ e.g. 0x1EC97920, offset 6).
3. **GPU upload** — `VulkanSharedMemory::UploadRanges` copies from the same
   `TranslatePhysical` source; instrumenting it showed `colorSrc=D5EFEFFF
   colorDst=D5EFEFFF` — the correct cream reaches the device staging buffer.
4. **Generated SPIR-V** — disassembled the translated VS. The color mini-fetch
   computes `address = (base_fc95 + floor(r0.x)*7) + 6`, splits it into the
   multi-binding shared-memory descriptor (`>>25` binding, `&0x1FFFFFF` offset),
   loads via the same binding `OpSwitch` structure as the (working) position
   fetch, endian-swaps, and byte-extracts. Byte-for-byte correct; identical
   structure to the position/UV fetches that work.
5. **The pixel shader constants** — `c2=(1,1,1,1)`, `c3=(0,0,0,0)` (identity).

### What was ruled out (with the test that ruled it out)
- Alpha blending / gamma / present / exp_bias / resolve — earlier M4 work.
- The font-atlas sample — atlas raw bytes are bright (bmax=255); the atlas-only
  shader test still rendered near-zero-colored (green) glyphs.
- The mini-fetch **address** — forcing the mini to recompute its address fresh
  (bypassing `xe_var_vfetch_address`) gave the identical wrong result.
- **Out-of-bounds** address — a shader marker confirmed the computed address is
  in `[0x1000000, 0x8000000)` (in the vertex buffer's binding).
- The **byte-extract decode** — replacing `OpBitFieldUExtract` with manual
  shift+mask gave the identical wrong result.
- **`r0` (index register) clobbering** — SPIR-V shows `registers[0]` is written
  once (index setup) and only read by the fetches until after the color result.
- **Primitive conversion** — `host_vertex_shader_type = kVertex`, `guest/host
  prim = TriangleList`; no repack, vertices come straight from shared memory.
- **Cross-GPU env** — tried the real Intel Iris Xe GPU (`--device /dev/dri`,
  intel_icd). It renders (3535 present/resolve ops) but the headless Xvfb has
  **no DRI3**, so nothing can be captured; frontbuffer/vertex readbacks return 0
  on both GPUs (GPU-produced data is not CPU-mirror-visible — a consistent
  measurement limitation of this environment).

### The remaining suspect
With the shader, guest data, upload, and address all verified correct, the color
`vfetch_mini` load returns a **constant** `0x00000100` for all vertices while the
`vfetch_full` position load at the same base address returns correct per-vertex
data. The constant-ness points to a **lavapipe (software rasterizer)
miscompilation** of the packed-color fetch path (or a device-buffer-content issue
that cannot be measured here — every GPU-buffer / frontbuffer readback in this
Docker+Xvfb environment reads zero for GPU-produced data).

### Decisive next step (needs a real display, which the headless harness lacks)
Run the port on **real hardware with a working DRI3 display** (e.g. the host's
Intel Iris Xe on the actual Wayland/X session, not headless Xvfb). If the
colors are correct there, the port is functionally correct and the near-black
output is purely a lavapipe test-environment artifact. If still near-black, it is
a genuine SDK/GPU bug to escalate upstream (the shader translation itself is
verified correct, so the escalation target would be the shared-memory SSBO load
path or Mesa/lavapipe).

**All diagnostics used during this investigation have been reverted; the SDK
working tree is back to the M0–M3 patches + inert cvar-gated blend diagnostics.**

### M4 update — DECISIVE evidence the defect is lavapipe-specific (multi-binding SSBO load)

`maxStorageBufferRange`: **lavapipe = 128 MB**, **Intel Iris Xe = 4 GB**. The
shared-memory SSBO is split into `512MB / maxStorageBufferRange` bindings:
- lavapipe → **4 bindings**, loads go through `LoadUint32FromSharedMemory`'s
  multi-binding path (`address>>25` binding index + `OpSwitch`/`OpPhi`).
- Intel → **1 binding**, a **direct** `shared_memory[0][address]` load with no
  multi-binding path at all.

The UI vertex-color load fails **only** on the multi-binding path: position/UV
(also binding 3, same buffer, adjacent dwords) read correctly, but the color
dword returns a constant `0x00000100`. Since Intel never takes the multi-binding
path, the port almost certainly renders correctly on Intel/real hardware.

Additional eliminations this round:
- Replaced the `OpSwitch`/`OpPhi` binding load with a branch-free
  unconditional-load + `OpSelect` chain (constant descriptor indices) → **no
  change** (rules out the switch/phi form AND dynamic descriptor indexing).
- Forced single-binding (`GetSharedMemoryStorageBufferCountLog2 → 0`) on lavapipe
  → the whole frame goes black: lavapipe **clamps** the 512 MB SSBO binding to
  128 MB, so the vertex buffer at ~483 MB becomes unreadable (position breaks
  too). Confirms multi-binding is *required* on lavapipe and mostly works.
- `GALLIVM_PERF=nopt` (disable LLVMpipe optimizer) → no change.
- No memexport draws target the vertex buffer (it is CPU-written; mirror = cream).

**Bottom line:** the bug lives in the lavapipe execution of the 4-binding SSBO
load for this specific fetch; it is not reproducible on a single-binding device.
This cannot be fixed in the port/shader (both verified correct) or worked around
on lavapipe without breaking the >128 MB addressing it needs. **The remaining
action is a real-hardware visual (Intel, with a DRI3 display) — expected to be
correct.** run_port.sh now passes `GALLIVM_PERF`/`LP_NUM_THREADS` env through and
supports `CIVREV_ICD/CIVREV_DRI/CIVREV_SOFTGL` for a real-GPU run.

---

## M4 — ✅ PASS (2026-07-12): copyright/ESRB screens render correctly; boot reaches the title screen

**Formal verification (compare_screens.py vs pixel-deterministic Xenia references,
threshold 0.90):**
- `00_copyright` (Take-Two legal text): **combined = 0.9942 → PASS**
- `01_esrb` ("ESRB Notice: Online Interactions Not Rated by the ESRB"): **combined = 0.9983 → PASS**
- `02_loading` ("Loading..." text): renders at full brightness, correct position/color
- Title screen: full 3D world panorama + "Press START to begin", animating at 4-frame
  cycle (vs 03_title: 0.69 — expected; the reference titled scene is live/never settles
  per the oracle's own notes). Artifacts: run `port_output/m4_final` (fb dumps +
  extracted `screens/*.png`).

### Root causes found and FIXED (both were ReXGlue SDK bugs, not recompilation)

**Fix 1 — texture fetch exponent bias read from the wrong fetch-constant word
(`patches/0004-gpu-texture-fetch-exp-adjust-word3.patch`).**
`SpirvShaderTranslator::ProcessTextureFetchInstruction` applied the result exponent
bias from bits 13:18 of fetch constant **word 4** — which is inside the `lod_bias`
field. Per `xe_gpu_texture_fetch_t` (the SDK's own xenos.h), `exp_adjust` is bits
13:18 of **word 3**. CivRev's UI texture fetch constants have lod_bias bits that
decode as −8 → every texture sample was multiplied by 2⁻⁸ = **1/256** — the
session-long "~1/256 quantization" bug. All UI is texture-alpha modulated
(Scaleform font atlas), so every screen rendered near-black. Proof chain: guest
vertex colors verified bright end-to-end (CPU mirror → UploadRanges staging →
device SSBO via draw-time readback → shader-loaded word via SSBO debug store →
decoded value → PS r1 interpolator = cream 0xFFEFEFD5), PS constants c2/c3 verified
identity in the bound uniform, final oC0 alpha measured ≤ 1/255 via atomic-max
debug store → the tfetch sample was the only dim factor; ×255 experiment confirmed;
word-3 fix renders identically to the experiment. (The lavapipe-vs-Intel
`maxStorageBufferRange` theory from earlier today was a red herring — the readbacks
that "proved" it were unreliable; the working memexport-style readback disproved it.)

**Fix 2 — `execute_unclipped_draw_vs_on_cpu` default restored to Xenia's `true`
(`patches/0005-gpu-execute-unclipped-draw-vs-on-cpu-default-true.patch`).**
ReXGlue changed this Xenia cvar default to `false`. With it off, clip-disabled
draws (Scaleform stencil-mask rectangles in GFX_LegalScreen.gfx) get their EDRAM
extent estimated from the scissor alone (8192 high), so a depth/stencil-only draw
claimed `len=2048` tiles from base 1328 — **wrapping around EDRAM and stealing tile
ownership of the display color buffer (tiles 0-720)**. The next display resolve
then dumped from the depth render target → black frames for the whole legal-screen
phase (`ChangeOwnership` timeline: claim [2x color 0..720] → claim [4x depth
1328 +2048 wraps] → resolve dump owner = 4x depth). The loading screen survived
because its frames have no mask draws. With the Xenia default restored, the CPU
vertex-shader extent estimation bounds the mask draw and ownership stays correct.

### Also fixed in the runner
- **Audio**: the runtime SDL3 build has no "dummy" audio target (alsa/pipewire/pulse
  only) — `SDL_AUDIODRIVER=dummy` made `XAudioRegisterRenderDriverClient` fail and
  the render-driver callback never fired. run_port.sh now writes an ALSA null-device
  `/etc/asound.conf` and sets `SDL_AUDIODRIVER=alsa` (callbacks verified firing).
- run_port.sh: `CIVREV_ICD`/`CIVREV_DRI`/`CIVREV_SOFTGL` (real-GPU runs),
  `EXTRA_ARGS` passthrough, `CIVREV_FB_DUMP[_START|_STEP]` — an SDK-side guest
  front-buffer PPM dump (`patches/0006-diag-civrev-frontbuffer-ppm-dump.patch`,
  env-gated) that captures presented frames below the X11 layer (needed because
  llvmpipe present warm-up hides the short legal screens from X11 grabs; frames are
  Xenos-tiled — untile with XGAddress2DTiledOffset, see port_output/m4_final).

### Upstream
- Issue A (CP ring re-init race) and B (PWL gamma swap) unchanged.
- Old draft "Issue C" (brightness) superseded: the real cause is the exp_adjust
  word-3/word-4 bug (Fix 1) — rewrite before filing. Fix 2 is Xenia-default
  restoration and should also go upstream. NOT filed — needs user confirmation.

---

## Input — TOML-configurable keyboard/mouse controls (2026-07-12): ✅ DONE, verified

Goal: remappable keyboard+mouse controls via a TOML config.

**What was added** (`patches/0007-input-toml-configurable-mnk-keymap.patch`):
- `rex/input/mnk/mnk_keymap.{h,cpp}` — TOML mapping loader (toml++). Schema:
  `[options]` enabled/user_index; `[mouse]` stick=right|left|none, sensitivity,
  invert_y, wheel_up/wheel_down→any controller control (pulsed per notch);
  `[buttons]` a/b/x/y/start/back/shoulders/thumbs/dpad_* (single key name or
  array); `[triggers]` left/right; `[sticks.left|right]` up/down/left/right
  digital emulation. Key names = rex::ui::ParseVirtualKey names (letters,
  digits, F-keys, nav, modifiers, numpad, LMB/RMB/MMB + new Mouse4/Mouse5).
  Unknown keys/controls fail loudly; a failed load keeps previous bindings and
  falls back to the legacy keybind_* cvars.
- MnK driver: `--mnk_config` cvar (default `controls.toml` in CWD); TOML
  `[options].enabled` can switch the emulation on without `--mnk_mode`; mouse
  wheel listener; X1/X2 mouse buttons; mouse motion can drive either stick with
  inversion; bindings table replaces the per-cvar chain.
- Sample config: `rexglue_port/controls.toml` (fully commented).
- Unit tests: `tests/unit/input/mnk_keymap_test.cpp` — 7 cases / 60 assertions,
  ALL PASS (parse, defaults, unknown-key/control rejection, bad mouse.stick,
  failed-load keeps old bindings, control-name round-trip).

**End-to-end verification** (`test_controls.sh` — boots the port, waits for the
title screen, injects real X11 input via xdotool in-container, checks whether
the game advances):
| test | config | injected | expect | result |
|---|---|---|---|---|
| A  | controls.toml (Return→a/start) | hold Return | advance | ✅ PASS |
| B  | remap: Return unbound          | hold Return | ignore  | ✅ PASS |
| C  | remap: start="J"               | hold J      | advance | ✅ PASS (reached MAIN MENU) |
| D  | controls.toml (a=["Return","LMB"]) | hold left mouse btn | advance | ✅ PASS (buttons=0x1000) |
| A' | final production build re-run  | hold Return | advance | ✅ PASS |

Notes: xdotool `key` taps are too short for the slow llvmpipe poll loop — hold
via `keydown`/`keyup` with `sleep 3` between. One boot hang observed once after
a rebuild (log stops during .fxobj load, pre-render) — not reproducible; watch.

---

## Host builds, windowed mode + the stale-plugin incident (2026-07-12 pm)

**build.sh** — one script for both environments (separate build dirs; CMake
caches bake absolute paths): native host `civrev/out/build/host-release`
(any C++23 clang/gcc; picks clang++-20 > clang++ > g++), `--docker` / in-container
`civrev/out/build/linux-amd64-release` (what run_port.sh consumes). Stages
librexruntime/librexgpu-xenos/libTracyClient next to the binary (RUNPATH=$ORIGIN),
reclaims root-owned dirs, `--clean` wipes.

**Windowed mode** — `--fullscreen=false` (SDK cvar, default true). SDK-level
`--window_width/--window_height` size the window AND (by the SDK's design,
GetConfiguredVideoModeWidth fallback) become the guest render resolution — the
game handles non-720p fine (verified 960x540: full title screen renders; first
boot at a new resolution retranslates all shaders, slow on llvmpipe, fast on a
real GPU). Note: passing --video_mode_width equal to its default does NOT pin
the mode (HasNonDefaultValue is value-based). F11 toggles fullscreen at runtime
(patches/0008; needs a real WM — inert under bare Xvfb).

**⚠ Stale-plugin incident (root cause of the "UI stopped rendering" regression):**
the exe loads librexgpu-xenos.so from NEXT TO ITSELF. build.sh originally staged
it from the SDK *install tree*, which still held a Jul-11 pre-M4-fix plugin (all
M4-era runs had staged the fresh plugin via direct docker cp from
out/linux-amd64/Release/, never refreshing the install tree). Result: every
binary "rebuilt" by build.sh silently ran yesterday's GPU plugin -> deterministic
boot failure (`ExecutePacketType0 overflow (count 2EB8)` / `PRIMARY RINGBUFFER:
Failed to execute packet`, no presents). Fixed by refreshing the install tree
and staging with plain `cp` (no `-u`). RULE: after rebuilding any SDK lib,
refresh out/install/linux-amd64/lib AND restage the civrev build dirs — or just
rerun build.sh, which now always copies.
- Also ruled out along the way: clang-18 host builds are FINE (the "miscompile"
  was the stale plugin); duplicate cvar definitions in the exe DO break flag
  routing via symbol interposition (window_width/height dup killed sizing) —
  never REXCVAR_DEFINE a name the SDK already defines; use the SDK's.

Verified after fix: baseline title at t=17s ring_errors=0; windowed 960x540
title at t=19s ring_errors=0 (port_output/baseline4, win_f11).

---

## Input follow-up (2026-07-12): keystroke synthesis — intro skip + menu verified

Symptom: MnK controls didn't skip the intro movies. Root cause: the game skips
Bink intros via **XamInputGetKeystroke** (event-style VK_PAD_* input), not by
polling XamInputGetState. The MnK driver had a keystroke queue but never fed it
(EnqueueKeystroke was unused), so the SDL gamepad driver was the only source of
keystrokes — absent for keyboard/mouse.

Fix (folded into patches/0007): MnkInputDriver::GetKeystroke now synthesizes
KEYDOWN/KEYUP VK_PAD_* keystrokes from mapped-button state transitions (A/B/X/Y,
Start/Back, shoulders, thumb-presses, dpad, triggers — same 16-control table the
SDL driver uses), tracked via last_keystroke_buttons_.

Verified end-to-end (scratchpad final_input.sh / menu_nav.sh, movies KEPT):
- INTRO SKIP: with the full ~2-minute IntroMovie playing, a Return (START/A)
  press brings up the title screen ~18s later -> the movie was skipped, not
  waited out. Reproduced 3×.
- MENU NAVIGATE: left-stick down (mapped to S) moves the highlight
  (Play Now -> Extras, screenshot-confirmed).
- MENU SELECT: Return (A) on "Single Player" enters its submenu (New Game /
  Load Game / Game of the Week / Play Scenario, 278k-px screen change,
  OCR-confirmed).
Note: dpad does NOT drive this menu (game uses the left stick) — expected. The
menu uses the LEFT STICK for navigation; the dpad is inert here by design.
Harness caveat: llvmpipe renders ~1 fps, so short xdotool taps sometimes miss a
poll window (intermittent 0-diff frames); hold keys or use discrete taps. On a
real GPU host (60 fps) input is smooth.

---

## Input fix #2 (2026-07-12): keystroke dispatch short-circuit hid MnK behind a gamepad

Reported: on the host, no keyboard key skips the intro (worked in the headless
harness). Root cause: `InputSystem::GetKeystroke` returned on the FIRST driver
that yielded SUCCESS **or EMPTY**. Drivers are ordered SDL(gamepad) → MnK → NOP.
With a controller connected, the SDL driver is "connected but idle" and returns
X_ERROR_EMPTY, which short-circuited the loop -> the MnK (keyboard/mouse) driver
was never polled for keystrokes, so no key could skip the Bink intros. The
headless harness has NO gamepad (SDL returns DEVICE_NOT_CONNECTED, loop falls
through to MnK), which is why it passed there but failed on a host with a pad.

Fix: GetKeystroke now polls every driver and returns the first actual SUCCESS;
an EMPTY no longer short-circuits later drivers (mirrors GetState's merge).

Controlled A/B repro with a virtual Xbox pad (uinput/virtpad, SDL enumerates it
as controller 0 - matches "controller plugged in"):
- buggy runtime + pad present + keyboard Return -> NO skip (stuck on movie ~60s)
- fixed runtime + pad present + keyboard Return -> title in 11s (SKIP WORKS)
- fixed runtime, no pad -> unchanged (still skips; the fix is a no-op on the
  DEVICE_NOT_CONNECTED path).
Both input fixes are in patches/0007. Host binaries need the refreshed
librexruntime.so (build.sh restages it; the exe loads it from $ORIGIN).

---

## Session — 2026-07-12 (evening) — M5 nav harness + THE M6 LOADING-SCREEN HANG

**Goal:** in-game with terrain rendering (first part of M6), via the shortest
path: title → main menu ("Play Now" preselected) → A → civ card → Accept → load.

### Port scenario driver (new)
- `port_nav_lib.sh` — host-side primitives against the `civrev-port` container:
  `phold` (xdotool keydown/hold/keyup — one MnK keystroke per hold; taps are
  lost at llvmpipe poll rates), `pshot`, `pocr`/`pwait_text`/`pfind_text`
  (docker-cp frame + host tesseract via oracle/ocr.py), `pwait_log`,
  `nav_ocr_dump`. `nav_controls.toml` — scripted-run mapping (A=Return,
  START=j — SEPARATED, unlike interactive controls.toml; mouse detached).
- `m6_playnow.sh` — title→in-game driver with an adaptive OCR probe loop.
- **OCR lesson:** busy 3D scenes behind bright UI text (main menu, in-game HUD)
  OCR as garbage with plain autocontrast; binarizing at L>200 first fixes it.
  ocr.py grew `--thresh N`; pocr tries plain then thresh=200.
  **False-positive lesson:** Loading-screen hints mention Diplomacy/units —
  the only safe in-game anchor is the date plaque (`4000 BC`).
- Nav facts: port shows NO sign-in prompt after START (ReXGlue auto sign-in;
  B at main menu is harmless). Play Now → civ-select carousel with a random
  civ (Accept = A, sometimes needs a second press), then Loading screen.

### M6 BLOCKER FOUND + FIXED: under-populated switch tables → silent ud2 spin
- Symptom (also seen by user in manual testing): map load hangs forever on the
  animated Loading screen. Log goes quiet except [gpu] presents; last non-GPU
  lines are XGIUserSetContextEx/SetPropertyEx + an APC delivery burst.
- gdb ground truth: `CivConsole` thread ON-CPU (not blocked) at a single PC
  inside `sub_82DAD720`; `x/i $pc` = **ud2** — the
  `default: __builtin_trap()  // Switch case out of range` of a message
  dispatcher whose generated switch knew **1 of 221 cases**. The runtime
  exception handler returns without advancing → infinite silent spin.
  (Stack: sub_821CAB38 → sub_82DAD720, id range 2300..2520.)
- The jump table lives at bctr+4 (0x82DAD744) and was misdecoded as a
  "function" (wall of `lwz r22,...` = the table words as instructions).
  XenonRecomp ALSO failed here (`// ERROR 82DAD720`), and XenonAnalyse's
  switch_tables.toml has no entry — static analyzers all missed it.
- Fix at scale: decoded ALL trap-default dispatchers from the generated code
  (884 sites, lis/addi+lwzx+mtctr+bctr shape), dumped every table from live
  guest memory (host 0x100000000+guest) in one gdb batch during a short boot,
  validated (877 unique bctr sites, 0 bad labels), emitted
  `civrev/switch_tables_manual.toml`, included from the manifest. Procedure:
  `tools/dump_switch_tables_live.md`. Codegen clean (65 s);
  sub_82DAD720 now has 221 cases. Rebuild + restage + rerun in flight.
- The 221-entry table has only TWO distinct targets: id 2300 → 0x82DAE52C
  (return 1), all other ids → 0x82DAD564 (same handler as out-of-range) —
  classic sparse middleware dispatcher; the game legitimately sends ids other
  than 2300 during game-start.

### RESOLVED — M6 first part: TERRAIN MAP RENDERS IN-GAME ✅
The Loading hang had TWO layered causes, both fixed:
1. **Under-populated 221-entry dispatchers** (the ud2 spin above) — fixed with
   `switch_tables_manual.toml`: 12 hand-verified tables (4 template copies x 3
   chained dispatchers, guard cmplwi rIDX,220, inline table at bctr+4) for the
   middleware message-dispatcher family. Labels dumped from LIVE guest memory.
   ⚠ A first attempt bulk-added 877 tables decoded from generated-code comments;
   that CORRUPTED boot — table data misdecoded as functions yields phantom
   dispatch shapes at WRONG bctr addresses, and overriding those repartitioned
   unrelated functions → new fatal `Jump target 0x8250377C unresolved at bctr
   0x825033AC`. Lesson baked into the manifest comment: only override REAL bctr
   sites (verify table == bctr+4 for the inline family; dump from live rdata).
2. **Codegen non-reproducibility** — the earlier switch-tables session left
   `switch_tables_xr.toml` (54 XR-corpus jump tables from
   tools/gen_switch_tables.py) and a `functions_jt_targets.toml` UNCOMMITTED and
   OUT of the manifest includes. Regenerating without them reintroduced 92
   `unresolved at bctr` REX_FATAL sites (boot died at 0x825033AC). Fixed by
   (a) regenerating switch_tables_xr.toml, (b) a jump-target fixpoint loop
   (declare every `Jump target ... unresolved` addr as a sizeless `[functions]`
   entry → codegen → repeat; converged in 1 pass to 90 targets → 0 unresolved),
   both now in the manifest `includes`. Generated tree: sub_82DAD720 = 221
   cases, ZERO unresolved-bctr sites.

**Verified end-to-end (port_output/m6_playnow_v2/, converged build):**
title → START → main menu → A (Play Now) → random-civ card (Zulu) → Accept →
Loading → **MAP RENDERS** → tutorial advisor chain → **Impi Warrior selected
with full action panel** (2 Moves / Defend City / Wait One Turn / Civilopedia),
**Zimbabwe city pop 2**, City Screen + Diplomacy HUD buttons, full terrain
(grass/plains/desert/forest/coast, workable-tile outlines). Loader thread stayed
live through the load (no ud2 spin). The probe loop's own in-game anchor
("Wait One Turn") fired independently → `IN-GAME detected`.
Artifacts: `M6_terrain_with_city.png`, `M6_terrain_map.png`, `M6_ingame_hud.png`.
- Play Now enables the TUTORIAL (advisor dialogs + unit-move prompt); the
  deterministic golden_age path is tutorial-free but needs the full carousel
  navigation. m6_playnow.sh's probe loop now auto-walks the tutorial chain
  (A on advisor dialogs; stick+A on "awaiting orders") for unattended reruns.
- Pixel compare vs golden_v6/10_live.png = 0.51 (NOT meaningful — different
  scenario/civ/map/advisor). Structural match is the real check and passes:
  terrain + selected unit + action panel + city + HUD chrome all present, at
  Xenia's own render quality (the stated bar).

---

## Session — 2026-07-12 (evening) — TEXT/UI RENDERING BUG (in progress, root-caused)

**Symptom (user report):** "some words or characters not rendering." Actually
UI *bitmap images*, not text: the controller **button-prompt glyphs** ((A) on
Play Now, (Y)/(X)/(B)/(Ls) in the unit panel, (RB)/(RT)), unit **portraits**,
civ leader **thumbnails**, and the tutorial dialog **button fills** are all
invisible/black. Plain text, vector button-gradient fills, HUD panels, and the
3D scene all render correctly.

**Root cause (narrowed, not yet fixed):** small **tiled `k_8_8_8_8` (RGBA8)**
textures **load as black** (sample to zero), while `k_8` (font atlas) and
`k_DXT1`/`k_DXT2_3` (scene backgrounds) load fine.

Evidence chain:
- The failing draws EXIST (not culled): `--civrev_no_blend=true` renders the
  (A)-glyph region as an opaque BLACK box next to "Play Now" -> the draw runs
  but its texture samples RGB=0, alpha~0 (invisible under normal alpha blend).
- Fetch constants for all 5 menu textures are NORMAL (identity/expected
  swizzle, unsigned, exp_adjust=0) -> NOT another misread field like the M4
  exp_adjust(word3) bug. No "Unsupported texture format" errors.
- The 5 menu textures: `1FB17000 k_8 1024x1024` (font, WORKS), `1AEC2000
  k_DXT2_3 2048x512` (city panorama - kill-test removed it, DXT DECODES FINE),
  `1AEA2000 k_DXT1 1024x256` (sky - kill-test removed it), and TWO `64x64
  k_8_8_8_8 tiled` (`1BC9E000`,`1BCAA000`). By elimination the button glyph is a
  64x64 k_8_8_8_8.
- Trace log: the 64x64 k_8_8_8_8 are **"Created"+"Loaded"** (from guest via the
  load shader), **NOT resolve targets** -> it's the tiled-k_8_8_8_8 LOAD path,
  not EDRAM resolve.
- Host-format mapping for k_8_8_8_8 is standard (kLoadShaderIndex32bpb ->
  R8G8B8A8_UNORM, RGBA swizzle) - matches upstream Xenia, no obvious divergence.

**Two remaining candidate mechanisms (next experiment disambiguates):**
1. The generic **32bpb tiled untile load shader** produces zero for these
   (small 64x64, endian=2/8in32) — a decode/untile bug.
2. **Shared-memory dirty-tracking staleness**: the game CPU-writes these UI
   textures to guest RAM but the memory watch misses it, so the load shader
   reads stale zeros. (The M4 session hit an analogous swap-texture staleness —
   see the `civrev_swap_reload` diagnostic / `ForceBaseOutdated`.) DXT scene
   textures are uploaded once at load (watch catches them); UI glyphs may be
   written later.
   Test: force-reload all textures (ForceBaseOutdated) each frame -> if glyphs
   appear, it's texture-cache staleness; if not, untile or shared-mem upload.

**Diagnostic tooling added to the SDK working tree (env-gated, inert normally;
in `src/graphics/vulkan/command_processor.cpp` after SetScissor in
UpdateDynamicState):**
- `CIVREV_TEXDIAG=1` — logs each draw's scissor + its pixel-shader texture
  descriptors (base/dims/format/tiled/endian/swizzle/sign/exp_adjust).
- `CIVREV_TEXKILL=<hexbase>` — suppresses draws sampling that texture (empty
  scissor) to identify which on-screen element uses which texture.
- Host scripts: `debug_textures.sh`, `id_kill.sh` (OCR-nav + kill + diff);
  `run_port.sh` gained `CIVREV_LOG_LEVEL` and forwards the two env vars.
- Guest-memory dump is USELESS here: `0x100000000 + fetch_base` reads zero even
  for the working font atlas -> these are GPU-resident; that host mapping is
  wrong for GPU-physical texture addresses. Need GPU readback, not gdb.

### CORRECTION (same session, later): format hypothesis DISPROVEN — reframed
The "tiled k_8_8_8_8 loads black" root cause above is WRONG. Follow-up work:
- Dumped the menu textures at the CORRECT physical host address
  (physical_membase = mapping_base(0x100000000) + 0x100000000 = 0x200000000;
  TranslatePhysical(g) = 0x200000000 + (g & 0x1FFFFFFF); earlier 0x100000000+g
  read the VIRTUAL heap = zero for everyone, incl. the working font atlas).
  The 64x64 k_8_8_8_8 textures have VALID data (71-88% nonzero); untiled offline
  via GetTiledOffset2D they are a brown and an orange rounded square.
- One-shot experiment (SDK IssueSwap, env CIVREV_FORCE_REUPLOAD + touch
  /output/reupload): InvalidateAllPages() + texture_cache_->ClearCache() forces
  every texture to re-upload from guest RAM and reload. The (A) glyph stayed
  black -> NOT shared-memory staleness.
- TEXKILL at the menu: killing 1BC9E000 (a 64x64 tiled k_8_8_8_8) removed the
  BLUE BUTTON BACKGROUNDS -> that texture is the button-fill skin and it RENDERS
  FINE (blue, cxform-tinted from the brown source). So **tiled k_8_8_8_8 works**;
  the format is not the bug.

**Reframed understanding:** the menu's 5 pixel textures are font(k_8, text OK),
2 DXT atlases (city+sky backgrounds, OK), and 2 small k_8_8_8_8 (button skins,
OK). The green (A) button-prompt glyph is NOT among them and its draw samples
black. Combined with: the Xenia reference (golden_v6) was captured with a
VIRTUAL XBOX GAMEPAD (uinput virtpad), while the port runs KEYBOARD/MOUSE.
STRONG hypothesis: the game only draws controller **button-prompt glyphs**
(A/Y/X/B/LB/RB/RT/Ls) when a gamepad is detected -> with MnK they are
intentionally not drawn -> the "missing button prompts" may NOT be a rendering
bug. TEST: run the port with a virtpad (like the oracle) and see if the prompts
appear.
- SEPARATE, still-open genuine texture gaps (NOT controller prompts): unit
  PORTRAIT in the HUD panel, civ leader THUMBNAILS (gold placeholder boxes), and
  the tutorial dialog button FILLS (empty outlines while the MAIN-menu button
  fills render). These need in-game GPU-capture-level analysis; NOT yet
  root-caused. The 1BCAA000 (orange) 64x64 may be one of the gold placeholders.

Diagnostics still in the SDK working tree (env-gated, inert normally):
CIVREV_TEXDIAG, CIVREV_TEXKILL, CIVREV_FORCE_REUPLOAD (one-shot via
/output/reupload). Offline tools in scratch: decode_tex.py, untile.py.

---

## Session — 2026-07-12 (late): M6 gameplay / turn-loop — reached, input harness-limited

**Goal:** get the in-game turn loop working (end-turn advances the date).

**Confirmed working:**
- Play Now reaches full interactive gameplay: terrain renders, city (Rome, pop 2),
  Warrior unit selected with action panel (Move to Location / Defend City / Wait
  One Turn / Civilopedia), date plaque **4000 BC**, City Screen + Diplomacy.
- **End-turn input identified: RT (right trigger)** — the Xenia reference date
  plaque reads "4000 BC RT". In nav_controls.toml RT = PageUp.
- Input DOES reach and control the game in-game: the dpad moves the destination
  cursor (yellow "?"), pans the camera, and switches the panel to "Move to
  Location" with green movement arrows; buttons trigger pipeline creation. Menu
  input (reach_ingame probe) navigates reliably.

**Blocker (harness, not a port bug):** precise in-game unit control is
unreliable at the headless llvmpipe **~1 fps**. `xdotool key` TAPS get dropped
(the ~1fps poll misses them); only long HOLDS register, and the MnK driver emits
ONE keystroke per key transition (no auto-repeat), so per-tile cursor
positioning needs many separate hold/release cycles that mis-time. Net: I could
not reliably give the Warrior orders, so the turn never became end-able (the RT
prompt only appears once all units are done). Also: Play Now runs the TUTORIAL,
which hard-gates input to "move the Warrior" until it's done.
- Window FOCUS under bare Xvfb is lost between spaced commands; must
  `xdotool windowfocus <win>` before every input batch (getactivewindow returns
  nothing otherwise). This bit the manual driving until re-focus was added.

**Recommended next steps (unblock the turn-loop verification):**
1. golden_age scenario (TUTORIAL-FREE): menu-nav to in-game (reliable), then a
   single held RT skips remaining units and ends the turn — no per-tile unit
   movement needed. This sidesteps both the tutorial gate and the imprecise
   cursor.
2. Real-GPU host at 60fps where input timing is reliable (the harness runs
   ~1fps under llvmpipe; a real GPU makes taps/holds land).

---

## Session — 2026-07-12 (very late): golden_age turn-loop — REACHED, input-delivery blocked

Per user choice, built the tutorial-free **golden_age** headless path
(golden_reach.sh + golden_resume.sh, using port_nav_lib). Result:

**Achieved:**
- Full menu nav works on the port with the LEFT STICK (W/A/S/D): main menu ->
  Single Player -> Play Scenario -> **Choose Scenario list** (OCR-verified
  "Golden Age" selected) -> Deity difficulty -> civ carousel (scrolled 28x LEFT
  to Romans, confirmed by OCR) -> accept -> load. All OCR-verified via find_text
  crops. The whole carousel nav is reliable.
- **Reached golden_age gameplay (tutorial-free):** terrain renders, a **Settlers**
  unit is active, and the on-screen **"End Turn" button** is shown (top-center) —
  the turn loop is literally one input away. Date plaque reads **4000 BC**.
- **End-turn input = RT** (on-screen End Turn button + the Xenia reference date
  plaque "4000 BC RT"); RT = PageUp in nav_controls.toml.

**Blocker (harness, not a port bug):** could not drive the turn advance. In-game
the game is **event-driven and idle-waits** for input (gdb: ALL threads in
`futex_abstimed_wait`, run.log growth = 0, screen frozen with no animation). The
injected keyboard input (xdotool XTEST, `key --window` XSendEvent, and mouse
click) does NOT wake its SDL event loop in this state — so RT/A/START/dpad all
produce zero change. Menu navigation works because there the game actively POLLS
input every frame (animated menus), so injected input is seen on the next poll.
- Possible contributing cause: golden_resume's end-turn loop fired RT/Return/
  BackSpace 5x while the map was still LOADING (the 22s wait was too short for
  golden_age's map-gen); those queued events may have wedged the post-load state.
  A clean run that waits for the real HUD (not just absence of "Loading") before
  any input is the next thing to try.

**Recommended:**
1. Clean golden_age re-run: wait for the real in-game HUD (e.g. "End Turn" /
   "Diplomacy" + unit panel, NOT a Loading tip) before ANY input, then a single
   held RT. Rules out the loading-spam wedge.
2. If still blocked: the in-game input path needs the SDL event loop to be woken
   by injected events under Xvfb — investigate whether the game blocks on
   SDL_WaitEvent in-game (vs SDL_PollEvent in menus); a harness fix would inject
   via uinput (virtpad) rather than X events. OR verify on a real-GPU host at
   60fps with real input, where this doesn't arise.

---

## Session — 2026-07-13: virtpad in-game input BREAKTHROUGH + turn-advance HANG found

Per user choice, implemented the uinput VIRTPAD path (SDL gamepad) — the fix for
the earlier "in-game input doesn't wake the event loop" blocker.

**BREAKTHROUGH — virtpad drives the port:**
- `run_port.sh` gained `CIVREV_VIRTPAD=1`: starts the oracle's `virtpad.py`
  (uinput Xbox 360 pad, evdev auto-installed) on FIFO `/tmp/virtpad.cmd` BEFORE
  the game so SDL enumerates it at init. Drive from host via
  `docker exec ... printf '<cmd>' > /tmp/virtpad.cmd`. `port_pad_lib.sh` wraps it.
- **KEY: at ~1fps the game coalesces quick presses — buttons need a HELD press**
  (`down A; sleep >=2; up A`); a 0.4s tap is dropped. dpad/triggers likewise.
- Validated: virtpad START -> main menu (PAD_VALIDATE_PASS). Full golden_age nav
  automated via the pad (dpad + held A + OCR-verified carousel finds):
  main menu -> SP -> Play Scenario -> Golden Age -> (Deity) -> civ -> load ->
  gameplay. `golden_pad_full.sh` = self-contained boot->gameplay->turn-test.
  Menu/nav input is now RELIABLE via the pad.

**TURN-ADVANCE BLOCKER (root-caused, unfixed):** in-game, pressing End Turn (RT)
hangs the game — screen freezes (0 render, 0 log growth). gdb: the **CivConsole
thread is ON-CPU in a guest-code INFINITE LOOP**, PC advancing through
`sub_8269D820` / `sub_8268E100` (call chain sub_82C6DCF8 -> sub_821CC8D0 ->
sub_8250D4A8 -> sub_82518198 -> sub_826A4EB0 -> sub_8268E100 -> sub_8269D820)
for 2+ minutes at native recompiled speed = never exits. This is the SAME CLASS
as the loading hang (CivConsole stuck) but NOT a switch-table ud2 trap (PC
advances; no 'Switch case out of range' / REX_FATAL in these funcs) — a real
loop whose exit condition is never met. Date stays 4000 BC across 8 end-turns.
- Also unresolved: `Y` (Found City) via pad didn't found the Settlers' city
  (the Settlers persists) — may be related (the hang triggered by ending the
  turn with an unhandled unit, or Found City itself doesn't register).
- Next: instrument the loop (log the register/memory values `sub_8268E100`
  compares each iteration) to find what it waits for — likely a value another
  subsystem should set (GPU/kernel/another thread) or a miscompiled loop
  condition. Deep recompilation-debug, akin to the switch-table effort.

Scripts: validate_pad.sh, golden_pad.sh, golden_pad_full.sh, port_pad_lib.sh.

---

## Session — 2026-07-13 (cont.): turn-hang ROOT-CAUSED + FIXED (KTHREAD ms clock)

Instrumented the CivConsole infinite loop with gdb (installed in-container) and
found the never-met exit condition, then fixed it in the SDK.

**Diagnosis (live gdb on the hung process):**
- CivConsole is spinning in `sub_8268E100` (poll step) called from `sub_8269D820`
  (ring-buffer wait). Every OTHER thread is idle (futex/nanosleep) — including the
  "GPU Commands" thread. Classic producer/consumer stall: the CPU wrote ring
  commands (write cursor **9559**) and waits for the consumer to advance the read
  cursor (frozen at **9543**, gap 16). Since the map *renders* fine, the GPU
  normally advances this read pointer — so this is a **transient deadlock**, not a
  dead GPU.
- `sub_8268E100` disassembly: exit only when `elapsed = *(KTHREAD+0x58) - wctx+12`
  reaches **5000** (ms) → calls stall handler `sub_826A6300` which force-completes
  the wait (sets abort flag, fakes read cursor). This is the game's OWN designed
  deadlock-recovery path.
- The clock it uses, **`*(KTHREAD+0x58)` (X_KTHREAD::unk_58)**, is **frozen at 0** —
  the real 360 kernel ticks this field but the SDK never wrote it. gdb sampling:
  `timer[+0x58]=0` across 300+ poll iterations → `elapsed ≡ 0 < 5000` forever →
  stall handler NEVER fires → infinite loop.
  - Pointer chain verified live: guest `r13`=KPCR, `*(r13+256)`=`KPRCB.current_thread`
    =KTHREAD, `+0x58`=unk_58. Also `sub_82809E98` returns `*(KTHREAD+0x14C)`=thread_id
    (a self-wait owner check vs `ring+10888`), consistent with the struct.

**FIX (SDK, librexruntime.so):** maintain `X_KTHREAD::unk_58` as a monotonic ms
clock, mirroring the existing `KeTimeStampBundle` 1ms `HighResolutionTimer`. Added a
companion repeating timer (`kthread_clock_timer_`, 4ms) in `XboxkrnlModule` ctor
(`xboxkrnl_module.cpp`) that walks `object_table()->GetObjectsByType<XThread>()` and
writes `QueryGuestUptimeMillis()` (big-endian) to each guest KTHREAD's `unk_58`.
Header member added in `include/rex/kernel/xboxkrnl/module.h`. Rebuilt+installed the
lib to `rexglue-sdk/out/install/linux-amd64/lib` (mounted at `/sdk`).
Now the game's own 5000ms stall-recovery can fire and break the transient deadlock.
- Diagnostic gdb scripts: `inspect_hang.py`, plus `/tmp/{ring3,timer}.py` probes.
- Verification: fresh `golden_pad_full.sh` run (soft in-game gate now) → turn loop.

**VERIFIED (2026-07-13):** fresh `golden_pad_full.sh` run on the fixed lib →
founded Athens (Greeks) and ran **8 end-turns with NO hang**. Date advanced
**4000 BC → 3800 BC** (turn_6 shot), city grew, worker units appeared and
simulated. gdb on the live process: `KTHREAD.unk_58` now **1,160,682 → 1,161,630
(delta 948ms) = TICKING** (was frozen at 0). Game stayed alive through the probes,
log kept growing. Turn-advance blocker RESOLVED — interactive gameplay works.
Bonus: in-game HUD text renders CRISPLY here ("City Screen"/"Diplomacy"/"Athens"/
"Warrior"/"3800 BC") — the parked glyph-soup issue is absent on these screens.
Next (optional M6 hardening): 20-turn soak (task #12); investigate whether the
transient GPU-ring stall itself is avoidable (would remove the ~per-turn 5s
recovery latency), but not required for playability.

---

## Session — 2026-07-13 (cont.): 20-turn soak + intermittent boot GPU-hang finding

Committed the turn-hang fix (898414c, patch 0009 + NOTES #6). Then ran the soak.

**20-turn soak (golden_soak.sh + golden_soak_retry.sh): PASS on stability.**
- `SOAK_PASS: 20 turns, no crash, 19 screen-changes` — the game process stayed
  ALIVE across all 20 End-Turn (RT) presses, run.log grew (2452->2732), screen
  responded (19/20 CHANGED, one isolated SAME — NOT a hang cluster).
- Caveat: in THIS run the initial Found-City didn't register (settler kept
  cycling; year stayed 4000 BC), so the 20 turns exercised the end-turn path
  without advancing the year. Real turn advancement is proven separately
  (golden_pad_full: 8 turns, 4000 BC->3500 BC, Athens founded). Founding a city
  / unit-action-menu nav via the virtpad is UNRELIABLE at ~1fps (RT registers;
  dpad+A on the unit menu often gets dropped) — a harness limit, not a port bug.

**INTERMITTENT boot-time GPU-hang (new finding, mostly a headless artifact):**
- On boot the guest D3D fires `ERR[D3D]: The GPU is hung!` + a `tw/td trap
  (type 22)` — a guest software watchdog that decides the GPU stalled. Under
  llvmpipe (~1fps software raster) this trips ROUTINELY: the successful
  golden_pad_full run hit it **19 times and recovered every time** (reached
  in-game + 8 turns). Occasionally the recovery loses the race and boot
  deadlocks (first soak attempt froze at 543 log lines right after the first
  trap). `golden_soak_retry.sh` detects a boot deadlock (run.log frozen after a
  trap) and retries; attempt 1 booted clean here.
- Relationship to the fix: the KTHREAD unk_58 timer is what makes these
  watchdogs/recovery FUNCTION (before, frozen timer => neither fired => the
  end-turn silent hang). It's a net win (turns work). The residual boot
  flakiness is llvmpipe being so slow the guest thinks the GPU hung — on a
  REAL GPU (actual play) the GPU is fast and these watchdogs never fire. So the
  boot-hang is largely a software-rendering test artifact, not a HW-play bug.
- Optional future hardening: reduce transient GPU-ring stalls (CP ring re-init
  race, NOTES #2/#3) or test on a real Vulkan GPU to eliminate the watchdog
  trips entirely. Not required for playability.

Scripts: golden_soak.sh, golden_soak_retry.sh.

---

## Session — 2026-07-13 (cont.): title-logo investigation (diagnosed, NOT fixed) + boot-instability

**Goal:** fix the title logo ("SID MEIER'S CIVILIZATION REVOLUTION" banner) not
rendering on the title screen.

**Diagnosis (confirmed, not yet fixed):**
- Port title = correct 3D landscape + "Press START to begin", but the dark-blue
  banner + logo are ABSENT (Xenia reference shows them). Not a color/alpha bug:
  the logo is simply **never drawn**.
- TEXDIAG at the title (definitive multi-frame capture): the port samples ONLY 5
  textures — font `1FB17000` (k_8), 2 DXT backgrounds `1AEC2000`/`1AEA2000`, and
  2 button-skin `1BC9E000`/`1BCAA000` (64x64 k_8_8_8_8). **NO logo texture is
  sampled at all** — same 5 as the menu. So the logo draw is not issued / its
  texture never bound.
- NOT a file-load issue: assets load from FPKs (no per-`.dds`/`.gfx` file opens;
  the failing opens are `GAME:\Assets\Xenon\`,`\Resource\Xenon\`,`ObjectIcons\`
  optional-override dir probes that Xenia ALSO probes-and-ignores).
- **Asset IS present**: ran Xenia (`run_scenario.sh boot`) on the SAME extracted
  tree the port uses (`xenon_recomp/work/extracted`, `run_extracted.sh` = "same
  bytes") — Xenia renders the full logo banner. So it's a PORT draw bug, not an
  asset/extraction gap. `output/logo_ref/03_title.png` = Xenia proof.
- Class matches the parked "UI bitmaps render black" issue (portraits, leader
  thumbnails, tutorial fills) — needs a GPU-capture-level differential (what draw
  /texture Xenia issues for the logo that the port doesn't).

**Diagnostic added (uncommitted, inert, env-gated):** `CIVREV_DRAWDIAG=1` in
`command_processor.cpp` IssueDraw logs EVERY draw (prim, index count, VS/PS ucode
hash) incl. texture-less/culled draws. `run_port.sh` forwards it. NOTE: per-draw
REXGPU_ERROR logging is heavy under llvmpipe and can trip the GPU-hang watchdog
once rendering starts — needs in-code dedup/throttle to be usable.

**BLOCKER — boot-instability (worsened this session):** the port boot hangs with
`CivConsole` busy-spinning (~8 cores, 790% CPU, which itself drives host load to
~16 — the load/hang correlation is BACKWARDS: the spin causes the load). Same
GPU-ring-wait spin class as the end-turn hang; at boot under llvmpipe the recovery
sometimes never wins the race and boot never reaches the title. Booted fine this
morning (golden_pad_full) with identical code (verified: restoring the original
Jul-12 `librexgpu-xenos.so` did NOT help — my DRAWDIAG rebuild was NOT the cause),
so it's environmental/timing degradation (heavy session use, 6-day uptime). This
blocks iterative port-side title captures. Likely aggravated by the KTHREAD-timer
fix enabling the guest GPU-hang watchdog under slow software rendering.

**Next steps to actually fix (both are larger efforts):**
1. Xenia GPU-trace differential (Xenia boots reliably): dump Xenia's title-frame
   draw/texture list, find the logo's texture base+format+shader, then trace why
   the port doesn't load/bind/draw it.
2. A real-GPU (non-llvmpipe) headless env would remove the boot-hang + watchdog
   trips, making port-side iteration reliable.

---

## Session — 2026-07-13 (cont. 2): LOGO ROOT CAUSE NARROWED — Scaleform atlas never sampled

Xenia-differential + live-gdb investigation. The missing title logo, button-prompt
glyphs, portraits, and tutorial button fills are ONE bug.

**The unified mechanism (proven):**
- Xenia (same extracted tree) title uses 11 textures; the port uses 5. The key
  missing pair: two tiled 1024x256 k_8_8_8_8 pages at **1BBBC000/1BB92000** —
  the **Scaleform glyph/image ATLAS**. Decoded it from PORT memory (gdb dump +
  offline untile): it contains the LOGO lettering + globe, the tutorial button
  fills, AND the controller glyphs (Ls/LT...) — every missing UI bitmap, one atlas.
- **The port's guest CPU fully rasterizes this atlas EVERY FRAME** (hardware
  watchpoint on the atlas bytes: writer = guest chain sub_826A20A0 <- sub_826A2390
  <- sub_826A25F0 <- sub_826A2B80 <- sub_826A3210 <- sub_826A3338 <- sub_8250CCF0
  <- sub_82511510 <- sub_821D6E38 <- sub_821D6D78 <- sub_82C6DCF8 (CivConsole)).
  In XENIA the atlas is invalidated only ~6 times total (rasterize-once, then reuse).
- **The port NEVER issues any draw sampling the atlas** (TEXDIAG with new ps= hash
  across whole boots: zero fetch constants ever reference 1BBBC000/1BB92000).
  In Xenia the atlas is sampled with VS 5F6EB3BC96CE8FC0 + PS 6831098A8316F932 —
  the SAME pipeline the port uses for the (working) 64x64 button-skin quads.
- So: the guest's glyph-cache "valid/latched" state never sticks -> re-rasterize
  every frame -> never emit atlas quads. The gating input differs from Xenia.

**Ruled out this session (each with evidence):**
- Asset/extraction gap (Xenia renders logo from the SAME tree) - file I/O (all
  reads succeed; 1064 APC-style reads, APCs queue+deliver; log_noisy=true trace)
- XMemDecompress (not imported) - fences via EVENT_WRITE-with-address (all
  EVENT_WRITE packets have count=1) - EVENT_WRITE_SHD (implemented, Xenia-identical)
- CP interrupts (source=1 dispatches flow, 20 PM4_INTERRUPT/s) - COHER (matches
  Xenia base impl) - pipeline-cache poisoning (fresh cache: identical behavior)
- shader translation failures (none) - texture-format bugs (atlas never referenced
  at all) - GPU-hang recovery aborting atlas (a zero-hang boot still lacked draws).

**Diagnostics added (SDK working tree, env-gated):** TEXDIAG now logs ps= ucode
hash + ntex=0 draws; new CIVREV_DRAWDIAG logs EVERY IssueDraw (prim/idx/vs/ps).
run_port.sh forwards CIVREV_DRAWDIAG. **GOTCHA: the GPU plugin is dlopen'd from
/port (staged next to the binary, $ORIGIN), NOT /sdk/lib — stage rebuilt
librexgpu-xenos.so into civrev/out/build/linux-amd64-release/ or it won't load**
(librexruntime.so DOES come from /sdk/lib via LD_LIBRARY_PATH).

**Next step:** guest-logic dive into the glyph-cache manager (sub_821D6E38 /
sub_82511510): find the branch that chooses re-rasterize vs reuse+draw, and which
guest-visible input (a flag/counter someone must set) differs under the port.
ACCELERATOR: the iOS build is symbolicated ("Rosetta Stone", see Korea-mod memory)
— map these 360 functions to named iOS/Scaleform equivalents (GFxFontCacheManager /
glyph-cache family) to read the logic with names. Also worth checking guest reads
of the VdGlobalDevice/VdGlobalXamDevice variables and D3D caps the glyph cache
might branch on.

### Guest glyph-cache gate analysis (logo bug, static recomp reading)

Call chain into the atlas rasterizer (from HW watchpoint):
`sub_821D6D78 -> sub_821D6E38 -> vtable[348] -> sub_82511510 -> (vtable call) ->
sub_8250CCF0 -> sub_826A3338 ... -> sub_826A20A0` (writes atlas bytes).

- `sub_821D6D78` calls `vtable[116](this)` (=GetRenderer) then `sub_821D6E38(this,
  renderer, r5=**hardcoded 7**)` — flag bits 1|2 (0x6) = "use HW glyph-cache atlas"
  are ALWAYS requested. Bit 0 = base render.
- `sub_821D6E38`: mode gate (*(this+160) in {1,2,4}) + failure latch (*(this+156),
  set when vtable[348] returns nonzero; fail-fast on later calls unless mode==4).
  Flags pass through unchanged to vtable[348] -> sub_82511510(this, renderer, flags).
- `sub_82511510` entry: r18 = sub_82521DC0(this) (syncs 4 cache-texture slots
  this+256.. vs globals @82F6FC14, via sub_82691E18(halGlobal+188, i)); if r18==0
  -> WHOLE function exits (no rasterize — but rasterize DOES happen, so passes).
  Then **sub_823ABF58(renderer) = (*(renderer+28) != 0)**; if FALSE -> `flags &=
  ~6` (kill HW-atlas bits!) and skip vtable[112]+sub_82510638 (bind cache texture).
  Later: `if ((flags&4) XOR (flags&2)) vtable[332](this,0,flags&6)` then main
  `vtable[332](this,0,flags)`. With flags=7 both bits set -> XOR false -> single
  main call WITH bits 6 -> HW path inside vtable[332]. With +28==0 -> flags=1 ->
  vector/CPU path (no atlas quads) = EXACTLY the port's behavior.
- HAL singleton [0x82F6E1E0] (=0x400C5740 in a probed boot): hal+188 =
  **0x400DFA00** — the SAME object as the graphics-interrupt callback context and
  the end-turn ring-wait object. hal+28 nonzero (but hal may not be the checked
  renderer object; renderer comes from vtable[116] — class ctor sub_823ABFD0
  vtable 0x8200FA68 zeroes +28; setter unknown).
- Probe in flight: at sub_82511510 entry read (flags, renderer, *(renderer+28)).
  If +28==0 -> find who fails to set it (Xenia comparison). Boot-hang mitigation:
  fresh per-attempt CIVREV_PORT_CACHE (the grown persistent cache lengthens the
  boot pipeline-preload stall; the guest GPU-watchdog then deadlocks boot).

### Logo bug: setter identified + time_scalar mitigation (cont. 3)

- `sub_82521DC0` always returns 1 (read to end) — non-factor. Everything gates on
  `*(renderer+28)`.
- **+28 setter found**: `sub_823AC2B8` (vtable slot **+104** of class vt 0x8200FA68)
  assigns its r4 arg into this+28 via `sub_82567D30(&this[28], tex)` (ref-ptr assign).
  The wrapper object (36 bytes) is built by factory `sub_823AC478`: gates on
  `vtable[144](renderer) >= 1` (caps/texture-count query), constructs
  (`sub_823ABFD0`, +28 zeroed), sets +24=1, then calls `vtable[100]`=`sub_823AC250`
  (slot-array init via sub_82567D30 into this[(slot+2)*4], NOT +28). So +28 is
  assigned LATER via vfunc+104 — caller unknown (too many generic +104 sites);
  runtime probe pending. Init chain: `sub_82510E38` (glyph-cache-mgr init, recomp.28)
  -> sub_823AC3E8/sub_823AC478 factories.
- **BOOT-HANG mitigation added (SDK)**: new `--time_scalar=<f>` cvar
  (`runtime.cpp`, wired to the existing-but-hardcoded
  `Clock::set_guest_time_scalar`) — <1 slows guest-perceived time so the guest
  D3D "GPU hung" panic (2.5s guest) tolerates llvmpipe pipeline-compile stalls.
  0.25 delayed the panic 4x (still tripped); 0.05 boot survives past the usual
  trap point but boots VERY slowly (guest-timed boot steps also 20x). Boot-hang
  became ~100% this evening regardless of pipeline cache (fresh-cache theory
  disproven) — host slowdown tipped a race; morning boots at 1.0 worked.
