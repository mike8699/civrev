# SDK defects found / local patches carried

Pinned SDK: **nightly-20260628-8dadea63** (0.8.1.68-dev; bumped from v0.8.0 —
see PROGRESS.md "Blocker investigation": v0.8.0 ships known-broken VMX128
codegen — vpkd3d128 float16_4 mask feature later reverted upstream, unfixed
vaddsws — which made guest D3D init silently fail and main() exit 0).
Every entry lists symptom, root cause, our carry, and upstream status.

## 3. CP primary ring re-init races the worker thread (FIXED locally, 0002)

- **Symptom:** boot dies with `ExecutePacketType0 overflow (read count
  00000064, packet count 00002EB8)` + `PRIMARY RINGBUFFER: Failed to execute
  packet`. Ring dump shows a valid ME_INIT packet at ring offset 0 while the
  CP reads at stale index 0x1F.
- **Root cause:** `InitializeRingBuffer` writes `read_ptr_index_ = 0` from the
  guest thread; if the worker is inside `ExecutePrimaryBuffer`, its
  `read_ptr_index_ = ExecutePrimaryBuffer(...)` store lands after the reset
  and resurrects the stale index. CivRev's D3D re-initializes the ring during
  device creation and restarts its stream at offset 0. Xenia has the same
  code but its slower JIT never exposes the window; the native port does.
  (`pending_fns_`/CallInThread is a plain std::queue — itself not
  thread-safe — so it cannot carry the fix.)
- **Local patch:** `patches/0002-gpu-cp-ring-reinit-race.patch` — atomic
  ring-init epoch, applied by the worker at loop top (which owns
  read_ptr_index_); worker also re-loops after any stall wake-up. Also
  includes a diagnostic ring hexdump on packet failure and a temporary
  swap-path log.
- **Upstream status:** to file with the ring dump as reproducer evidence.

## 4. PWL gamma ramp upload swaps base/delta (found by inspection, NOT hit)

- `src/graphics/vulkan/command_processor.cpp` (~line 2556): the PWL upload
  loop assigns `upload.base = entry.delta; upload.delta = entry.base;`.
  Xenia uploads these unswapped. CivRev uses the 256-entry table path
  (8_8_8_8 front buffer) so this doesn't affect us, but any 2_10_10_10 title
  gets a corrupted PWL ramp. Report upstream.

## 5. OPEN: all game-rendered content ~1/255 brightness (llvmpipe, Vulkan)

- Port reaches the Loading splash; text renders crisp and correctly
  positioned but at exactly ~1/255 intensity (frame max pixel value = 1).
- Eliminated: gamma LUT machinery (byte-identical to Xenia), guest-computed
  ramp (verified healthy: ramp[255]=1023, proper sRGB curve), both present
  pipelines (plain and FXAA produce identical dimness), vertex-fetch
  normalization (translator identical to Xenia), vpkd3d128 D3DCOLOR pack
  (identical to XenonRecomp corpus).
- Remaining suspects: EDRAM render-target write path or resolve
  (draw output lands in the swap source already /255). Next step: RenderDoc
  capture / trace tooling, then upstream with reduced repro.

## 1. Conditional tail call loses CallTarget under overlapping coverage

- **Symptom:** generated code contains
  `if (...) REX_FATAL("Unresolved branch from 0x823E5948 to 0x823E5854")`
  (3 sites in CivRev) although the target address IS a registered function;
  codegen logs `Unresolved conditional branch ... (no CallTarget)`. At
  runtime the game dies at the first such site during boot.
- **Trigger:** a `[functions]` hint for a data-referenced entry (e.g.
  0x823E5880) that lies INSIDE another function's range (0x823E5840). Both
  functions translate the same bytes; `findCallTarget(site)` is keyed by site
  address and only carries the resolution for one copy.
- **Local patch:** `src/codegen/builders/context.cpp`,
  `emit_conditional_branch`: when `findCallTarget(base)` misses but
  `graph().getFunction(target)` exists, emit the conditional tail call
  directly (same shape as the CallTarget::isFunction branch). Patch is
  additive fallback only — no behavior change when CallTarget resolves.
- **Upstream status:** not filed yet (prepare reproducer once boot is green;
  minimal repro = two overlapping [functions] entries where the inner one
  conditionally branches below its own entry).

## 2. XUsbcam* exports missing (not a bug — gap)

- v0.8.0 has no XUsbcam* xboxkrnl exports; CivRev imports 6 of them and they
  are link-time-required by generated code. Carried as app-side stubs in
  `civrev/src/kernel_stubs.cpp` (Xenia semantics: Create MUST return success).
  Candidate for upstreaming as SDK stubs.

## 6. KTHREAD millisecond clock (unk_58 @ 0x58) never ticks (FIXED locally, 0009)

- **Symptom:** in-game, pressing End Turn deadlocks — the `CivConsole` thread
  busy-spins forever in guest `sub_8269D820`→`sub_8268E100` (a GPU ring-buffer
  wait); screen freezes, no log growth, every other thread idle.
- **Root cause:** the wait is CPU-waits-for-GPU: the game wrote ring commands
  (write cursor ahead) and polls for the GPU consumer to advance the read
  cursor. It has a built-in 5000ms stall-recovery (`sub_826A6300`, force-
  completes the wait), gated on `elapsed = *(X_KTHREAD+0x58) - saved`. That
  field (`unk_58`, a per-thread ms clock the real 360 kernel keeps ticking) is
  **frozen at 0** because the SDK never writes it → `elapsed ≡ 0 < 5000` forever
  → recovery never fires → infinite spin. The map renders fine, so the GPU
  normally drains the ring; this is a *transient* deadlock the recovery exists
  to break. Verified live via gdb (unk_58 unchanged across 300+ poll iters).
- **Local patch:** `patches/0009-kernel-kthread-ms-clock-unk58.patch` —
  `XboxkrnlModule` gains a 4ms repeating `HighResolutionTimer` (mirrors the
  existing `KeTimeStampBundle` 1ms pattern) that walks
  `object_table()->GetObjectsByType<XThread>()` and writes
  `QueryGuestUptimeMillis()` (big-endian) into every guest `KTHREAD::unk_58`.
- **Verified:** 8 end-turns, no hang, date 4000 BC→3500 BC, city founded, units
  simulate; gdb: unk_58 now ticks (delta ~948ms/120 polls, was 0).
- **Upstream status:** likely a real SDK gap (per-thread KTHREAD timing fields
  unmaintained). Report — repro = any title polling `KTHREAD+0x58` as a clock.
  Upstream may prefer maintaining it in the scheduler/quantum path rather than a
  standalone timer.
