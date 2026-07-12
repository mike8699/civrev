# DRAFT upstream issues for rexglue-sdk (prepared; NOT filed — confirm first)

## Issue A: CP primary ring re-initialization races the worker thread

**Title:** Primary ring buffer re-init from guest thread races worker's
read-index store → "ExecutePacketType0 overflow" / CP death at boot

**Version:** nightly-20260628-8dadea63 (also present in v0.8.0)

**Description:**
`CommandProcessor::InitializeRingBuffer` writes `read_ptr_index_ = 0` from the
guest thread. If the CP worker is inside `ExecutePrimaryBuffer` at that
moment, `WorkerThreadMain`'s `read_ptr_index_ = ExecutePrimaryBuffer(...)`
lands after the reset and the stale index survives.

Repro: Civilization Revolution (545407E5) boot. Its D3D device init calls
VdInitializeRingBuffer twice (D3D re-inits the ring during CreateDevice) and
restarts its command stream at ring offset 0. The CP keeps reading at the old
index and dies on garbage:

```
ExecutePacketType0 overflow (read count 00000064, packet count 00002EB8)
**** PRIMARY RINGBUFFER: Failed to execute packet.
ring: ptr=1FC50000 size=00040000 read_index=0000001F write_index=00000019 remaining=00000064
  ring[000000]> C0114800 000003FF 00000000 00000000   <- valid ME_INIT at offset 0
```

Xenia has the same code but its JIT never exposes the window; a natively
recompiled title hits it reliably. Note `CallInThread`/`pending_fns_` is a
plain `std::queue` and is not thread-safe either, so it can't carry the fix.

**Fix carried locally** (attached patch): an atomic ring-init epoch bumped by
`InitializeRingBuffer`, applied by the worker at loop top (the worker owns
`read_ptr_index_`); the worker also restarts its loop after any stall wake-up
so a pending re-init is applied before executing.

## Issue B: PWL gamma ramp upload swaps base/delta

**Title:** Vulkan: PWL gamma ramp upload writes base into delta and delta
into base

`src/graphics/vulkan/command_processor.cpp` (UpdateGammaRamp PWL path):

```cpp
gamma_ramp_pwl_upload_entry.base = gamma_ramp_pwl_entry.delta;
gamma_ramp_pwl_upload_entry.delta = gamma_ramp_pwl_entry.base;
```

Xenia uploads these unswapped. Affects 2_10_10_10 front-buffer titles.
(Found by inspection while chasing Issue C; not the cause of C.)

## Issue C: texture fetch result exponent bias read from fetch constant word 4 (lod_bias) instead of word 3 (exp_adjust)

**Title:** SPIR-V translator: texture fetch exp_adjust taken from bits 13:18 of
fetch constant word **4** — that's inside `lod_bias`; it lives in word **3**

**Version:** nightly-20260628-8dadea63

`SpirvShaderTranslator::ProcessTextureFetchInstruction` (spirv_translator_fetch.cpp,
"Apply the exponent bias from the bits 13:18 of the fetch constant word 4"):
the bias is extracted from `fetch_constant_word_4_signed`. Per
`xe_gpu_texture_fetch_t` in the SDK's own xenos.h, `exp_adjust : 6` is at bit 13 of
**dword_3**; dword_4 bits 12:21 are `lod_bias : 10`.

Repro: Civilization Revolution (545407E5). Its UI texture fetch constants carry a
lod_bias whose bits 13:18 decode as −8, so every texture sample is scaled by 2^-8 =
1/256. All Scaleform UI (font-atlas-alpha modulated) renders at ~1/256 brightness —
near-black boot screens. Fix: read word 3 (patch attached). Verified: legal screens
match the Xenia reference at SSIM-combined 0.994+ after the fix.

## Issue D: `execute_unclipped_draw_vs_on_cpu` default diverges from Xenia (false vs true) — EDRAM ownership stolen via wrapped whole-EDRAM claims

**Title:** draw_extent_estimator: default `execute_unclipped_draw_vs_on_cpu=false`
lets clip-disabled stencil-mask draws claim the entire EDRAM (wrapped), breaking
render target ownership

**Version:** nightly-20260628-8dadea63

Xenia defaults this cvar to `true`. With the ReXGlue default of `false`,
`DrawExtentEstimator::EstimateMaxY` falls back to the scissor for clip-disabled
draws. Scaleform stencil-mask rectangles (clip disabled, 8192 scissor) in CivRev's
legal screens then get `length_used_tiles` = full EDRAM: a depth/stencil-only draw
at base 1328 claims 2048 tiles, wrapping around and taking ownership of the display
color buffer's tiles 0-720. The next display resolve dumps from the depth render
target and presents black. Ownership timeline captured with instrumentation:
claim [2x color @0 len 720] → claim [4x depth @1328 len 2048, wraps] → resolve dump
owner = 4x depth. Restoring the Xenia default fixes it (patch attached);
recommending either the default flip or clamping single-RT claims to avoid wrapping
through other RTs' bases.
