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

## Issue C (investigation ongoing): all game-rendered output at ~1/255
brightness (CivRev, Vulkan, llvmpipe AND Intel ANV)

Game renders structurally correct frames (text crisp, correct layout) but
every pixel is ~1/255 of expected intensity (frame max = 1/255).

Eliminated with evidence:
- gamma LUT machinery + guest-set ramp healthy (ramp[255]=1023, sRGB curve)
- both present pipelines (plain + FXAA) identical output
- pixel shader constants healthy at draw time (c2=(1,1,1,1), c3=(0,0,0,0))
- vertex fetch translator semantically identical to Xenia's
- vpkd3d128 D3DCOLOR codegen identical to XenonRecomp's translation
- render target path: same behavior on default and `fbo`

Open peculiarity: reading the bound vf0 vertex buffer via
`memory_->TranslatePhysical(fetch.address << 2)` at draw time shows the whole
buffer zero, while draws visibly produce (dim) geometry — suggests the probe
reads a different backing than SharedMemory uploads, or the visible content
comes from a pipeline other than the probed ones. Next step: RenderDoc
capture of a single dim draw.
