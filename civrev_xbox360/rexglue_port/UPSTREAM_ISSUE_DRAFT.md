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

## Issue C: all game-rendered output quantized to ~1/256 (CivRev, Vulkan,
llvmpipe AND Intel ANV)

**Symptom:** structurally-correct frames (text crisp, layout right) but the
swap-source front buffer stores **white as byte 1, not 255** — every value is
~1/256 of correct. The game's healthy gamma ramp then maps source-index-1 → ~0,
so present max byte = 1 (near-black).

**Proof the render is otherwise correct:** remapping the gamma table so any
nonzero source index → full-bright makes the Loading screen render crisp,
correct WHITE text (screenshot available). Secondary artifact: black
background carries a green floor (G=1, R=B=0).

**Eliminated with evidence:**
- present/gamma (boost proves it; ramp[1]=1/1023, ramp[255]=1023; plain==fxaa)
- render `color_exp_bias` = 0 (system constants)
- resolve `copy_dest_exp_bias` = 0 → resolve uses the fast raw-byte-copy path
  (fmt0→fmt6 bitwise-equivalent), so byte-1 is already in EDRAM pre-resolve
- all chain shaders (texture_load_32bpb, resolve_fast_32bpp, gamma) are the
  stock precompiled SPIR-V
- host RT format R8G8B8A8_UNORM; cross-GPU identical ⇒ deterministic logic

**Localized (per-channel readback of resolve outputs in guest RAM):** the
game's intermediate UI render targets are FULLY BRIGHT (chmax=[255,255,255,x]),
but the presented display front buffer is near-zero RGB across the whole frame
(chmax=[1,2,1,255]). So the final composite into the display buffer produces
~1/128–1/256 RGB with full alpha. Not the color write mask (forcing RGBA: no
change), not swap-texture staleness (forcing reload: no change), not resolve
exp_bias (=0, fast raw copy).

**Open fork:** the composite draw either (a) is issued by guest code with a
wrong ~1/256 color scale (recompilation), or (b) samples its source UI texture
and the sample returns 1/256 (resolve-target-sampled-as-texture). A RenderDoc
capture reproduces it (attach .rdc), but the replay hangs headless here (both
lavapipe and Intel). Ask whether maintainers can inspect that draw's shader +
sampled-texture values. Repro title: CivRev 545407E5, boot to Loading screen.
