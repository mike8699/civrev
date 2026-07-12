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
