# Civilization Revolution (Xbox 360) → PC Port: Options & Recommendation

*Research document, 2026-07-11. Prepared as the decision basis for an agent-driven porting project (a Claude Fable/Opus agent will execute the port).*

---

## 1. Executive summary

Two serious toolchains exist for statically recompiling Xbox 360 games to native PC executables:

- **XenonRecomp** (hedge-dev) — a *recompiler only*. It translates PowerPC → C++ and deliberately provides **no runtime**. Every project must hand-build its own kernel shims, GPU layer, audio, and file I/O (the "UnleashedRecomp model"). Proven to produce fully-playable, shippable-quality ports — at the cost of an enormous, game-specific runtime engineering effort.
- **ReXGlue** (Tom Clay / rexglue-sdk) — a *complete recompilation SDK*: an AOT recompiler **plus a reusable batteries-included runtime** derived from Xenia (kernel emulation, Xenos GPU translation, VFS, audio, input). Games boot with mostly-TOML-level per-game work. Young (first release Feb 2026, v0.8.x) but very active, and multiple community ports already boot.

**Recommendation (detail in §9): use ReXGlue as the primary path**, keep the existing Xenia+VNC Docker harness as the verification oracle for the agent's feedback loop, and treat the already-generated XenonRecomp output as a fallback/second-phase asset. The project is **feasible**: this repo already contains a complete, cleanly-compiling XenonRecomp translation of the game (63,266 functions, 248 translation units, 0 compile errors), the game runs under Xenia for reference, and CivRev's technical profile (turn-based, 30 fps, modest GPU load, no complex physics/streaming) makes it a much friendlier target than the action games that pioneered these toolchains.

---

## 2. The game: technical profile

Facts established from the ISO in this repo (`Sid Meier's Civilization Revolution (USA)`), the extracted XEX, and the Xenia boot log:

| Property | Value |
|---|---|
| Title ID / Media ID | `545407E5` / `7DC1293B` |
| Binary | `default.xex`, built **2008-05-21**, XDK 2.0.6534/6690 |
| Image | 18.7 MB mapped at `0x82000000`, entry `0x8280AD78` |
| Imports | xboxkrnl.exe (350 imports / 181 unique), xam.xex (170 / 85 unique) |
| Static XDK libs | D3D9, D3DX9, XGRAPHC, XAUD, XMP, XNET, XONLINE, XHV, XCAM, XMEDIA, XAPILIB |
| TLS | 64 slots — the game is multithreaded but modestly so |

**Middleware fingerprint** (from binary strings + disc content — every one of these matters for porting):

- **Gamebryo** — scene graph / renderer framework (`CcGamebryoAnimationComponent`, `CivCon_LeaderheaderGamebryo.fxobj`)
- **Scaleform GFx 2.x** — the entire UI is Flash (`.gfx` files, `GFxLoader`, ActionScript bridges). Same SWF-based UI already reverse-engineered in the PS3 work.
- **Granny 3D** — animation (`granny` asset loading in resmgr)
- **Bink** — video (`.bik` files for all pedia movies)
- **Miles Sound System** — audio (`FAudioSystemMiles`), plus plain **MP3** music files on disc
- **zlib** (via GFx inflate wrappers)
- **GameSpy-era Live networking** — XNET/XONLINE/XHV static libs; multiplayer would be stubbed initially

**Graphics pipeline detail:** the disc ships 28 precompiled effect files (`shaders/fx/xenon/Release/*.fxobj`) — D3DX effect containers holding Xenos `vs_3_0`-era microcode compiled with XDK shader compiler 2.0.6534.1, **with all constant names intact** (`mtxViewProj`, `fCurveWorldRadius`, `g_fEnableDistFog`, …). Assert strings preserve full source paths (`c:\icbm\1\main\CivConsole\Src\...`). This is unusually good material both for automated shader recompilation and for an eventual native renderer.

**Sibling-platform knowledge multiplier (unique to this project):** the PS3 EBOOT has been deeply reverse-engineered in `../civrev_ps3` (gameplay effect layer located, debug flags documented, Korea-as-civ-16 mod shipped), and the **iOS build is symbolicated** — a Rosetta Stone for naming the 63k anonymous recompiled functions. The asset formats (FPK archives, DDS, GFx/SWF, Bink) are already fully understood and tooled from the map-editor work. No other 360 recompilation project has started with this much of the game already mapped.

---

## 3. What already exists in this repo

- **`xenon_recomp/`** — Dockerized XenonRecomp pipeline (extract-xiso → XEX → codegen). Already run to completion:
  - `work/recomp_output/`: **63,266 functions across 248 C++ translation units (233 MB)** plus `ppc_context.h` / func-mapping tables.
  - `work/switch_tables.toml`: 765 KB of jump tables recovered by XenonAnalyse.
  - Register save/restore addresses located (`find_addresses.py`), XEX decompressor tool built (`tools/dump_xex_image`).
  - **Verified 2026-07-11: all 248 TUs compile with clang++ 18 with zero errors** (only benign vectorization warnings; needs only the `simde` headers on the include path).
- **`xenia_automation/`** — Docker image that runs the game in **xenia-edge** (Linux JIT/signal fixes) with the display exposed over **VNC (port 5900)**, three display modes (lavapipe/Weston/Xorg-dummy), logging to `output/xenia.log`. The game runs in Xenia. The same image bundles **Ghidra 12.0.4 + XEXLoaderWV + the Xenon VMX128 extension + Xbox 360 SDK FIDBs** — a complete headless reverse-engineering rig.
- **`examples_of_recompilations.md`** — pointers to community precedents (NocturneRecomp, reNut) analyzed in §6.

Together these mean: *step 1 of either toolchain path is already done, and the verification oracle for the porting agent's feedback loop already exists.*

---

## 4. Option A — XenonRecomp + hand-built runtime (the UnleashedRecomp model)

**What it is.** [hedge-dev/XenonRecomp](https://github.com/hedge-dev/XenonRecomp) (MIT, 6.4k★, inspired by N64Recomp) converts a XEX into C++: each PPC function becomes a C++ function taking a CPU-context struct and a guest-memory base pointer, with automatic big↔little endian swaps and indirect calls resolved through a perfect-hash function table. Companion [XenosRecomp](https://github.com/hedge-dev/XenosRecomp) translates compiled Xenos shader binaries → HLSL → DXIL/SPIR-V.

**What it deliberately does not do** (from its own README): *"This project does not provide a runtime implementation... Making the game work is your responsibility."* Specifically:

- **No runtime at all** — no kernel/XAM implementation, no GPU, no audio, no file I/O, no input.
- **No MMIO** — which is exactly where XMA audio decoding lives (the 360 decoded XMA in silicon; Xenia handles this with an FFmpeg-based software decoder you'd have to replicate).
- **No exception support**; incomplete VMX128 coverage (e.g. reNut hit an unimplemented `vsldoi128` crash); jump-table detection is per-compiler-version pattern matching with "no fully generic solution"; function boundary analysis needs hand-fixing where jump tables masquerade as tail calls.
- **Project health:** effectively dormant — last push 2025-08-04, 88 open issues.

**What the runtime actually took in practice.** UnleashedRecomp (4.9k★, v1.0.3) is the only polished 1.0 in this lineage: ~6 months of focused work (Sept 2024 → Mar 2025) by a veteran Sonic-modding team that *already knew the engine deeply* — while writing XenonRecomp, XenosRecomp, and the [plume](https://github.com/renderbag/plume) D3D12/Vulkan graphics HAL along the way, and hand-implementing **343 PPC instructions**. Their runtime tree (`kernel/`, `cpu/`, `gpu/`, `apu/`, `hid/`, `patches/`, `install/`, `ui/`…) is the de-facto template, but **hedge-dev never extracted a reusable runtime library** — reuse means forking the tree. The cautionary datapoint: MarathonRecomp (Sonic '06) copied that tree nearly folder-for-folder, credits the Unleashed team for "significantly accelerating development," and after 15+ months still has **no public release** ("NOT suitable for public use").

Applied to CivRev, Option A additionally means dealing with the D3DX9 effect framework: the game drives rendering through `.fxobj` effect containers and 360-D3D9 calls, so a hand-built HLE renderer must reimplement that layer, and XenosRecomp — which is openly Unleashed-tailored (`UNLEASHED_RECOMP` ifdefs) and hard-requires reflection data in shader binaries — would need game-specific extension to consume shaders extracted from effect containers.

**Pros**
- Proven ceiling: the only recompilation lineage that has shipped a genuinely polished, native-renderer, 1.0-quality port (Unleashed: no shader stutter, MSAA, ultrawide, mod loader).
- Leanest possible result — no emulator layers at runtime; full control over every subsystem; ideal endpoint for the project's modding ambitions.
- The codegen half is *already done and verified compiling* in this repo.

**Cons**
- The runtime is a from-scratch, game-specific engineering project measured in **person-months to person-years** (6 months for experts who wrote the tools; 15+ months and counting for the team that merely forked it).
- Recompiler unmaintained since Aug 2025; VMX128/jump-table gaps become *your* problem.
- GPU path is the hard 20% that's 80% of the work: reimplementing the game's D3D9+effects usage on a modern API, plus per-game shader-toolchain surgery.
- Long "nothing renders yet" valley — weak intermediate feedback for an agent-driven loop.

## 5. Option B — ReXGlue SDK

**What it is.** [rexglue/rexglue-sdk](https://github.com/rexglue/rexglue-sdk) — "Xbox 360 Recompilation Runtime and Toolkit," BSD-3-Clause, by Tom Clay (tomcl7 — the same author as the Xbox 360 SDK FIDBs already used in this repo's Ghidra image). Best understood as **Xenia converted from a JIT emulator into an AOT static-recompilation runtime and packaged as an SDK**. It credits XenonRecomp for analysis/instruction-translation logic and reuses Xenia's kernel and GPU layers (license-clean: Xenia is BSD-3, XenonRecomp is MIT).

**Pipeline:** `rexglue init` (scaffolds CMake project + TOML config) → `rexglue codegen config.toml` (XEX → C++) → `cmake --build` (Clang — 18+ for v0.8.0, 20+ on current nightlies; C++23; x64) → native executable linked against the SDK runtime. The user supplies only `default.xex` and the assets folder. The wiki is explicit that this is "not a push-button process": expect iterative rounds of fixing unresolved functions and kernel imports.

**What the runtime provides out of the box:**
- **Kernel/XAM:** Xenia's `KernelState` — threads, events/semaphores/mutants, handle tables, module loading with export resolution, achievements.
- **GPU:** low-level **Xenos emulation inherited from Xenia** — guest command-list translation + shader translation (D3D12/HLSL on Windows, Vulkan/SPIR-V on Linux). No renderer rewrite needed to boot. Since v0.8.0 the Xenos layer is a swappable runtime plugin (`rexgpu-xenos`), explicitly designed so a native renderer can replace it later.
- **Memory:** 512 MB guest space at fixed host base `0x100000000` preserving 360 pointer semantics; automatic endian conversion; MMIO handler registration.
- **Audio:** Xenia-derived XMA path (XAudio2 on Windows, PulseAudio/ALSA on Linux) — least-mature subsystem.
- **VFS, input (SDL3), windowing.**

**Per-game work:** a TOML file — `[[functions]]` boundary overrides, `[[switch_tables]]` hints, `[[mid_asm_hooks]]` to inject C++ at guest addresses — plus a small app class (`OnInitialize()`/`OnUpdate()`). Real-world data point: WistfulHopes' DBZ Budokai HD port repo is essentially CMake + TOML + a small `src/`.

**Maturity (July 2026):** 688★, 502 commits, first release ~Feb 2026, latest stable v0.8.0 (2026-05-16), nightlies ongoing (repo updated 2026-07-10). Explicit early-development warning; breaking API changes happen. Games booting on it: Blue Dragon (pilot title), Lost Odyssey, Ninja Gaiden 2, Halo 3 beta, Crackdown 1/2, Banjo-Kazooie: Nuts & Bolts (reNut), Viva Piñata TiP, DBZ Budokai HD, Raging Blast 2 — all classed "experimental" on the community catalog; none has shipped a polished 1.0.

**Docs / agent-friendliness:** Mintlify docs site + wiki + CLI reference; **indexed on Context7**, i.e. directly consumable by LLM tooling. Fully CLI-driven and declarative — an unusually good fit for an autonomous agent loop (`codegen → build → run with --log_level=trace → read log → adjust TOML → repeat`).

**Pros**
- Fastest credible path to a **booting native build** — the entire runtime problem (kernel, GPU, audio, VFS) is somebody else's actively-maintained code.
- Cross-platform (Windows D3D12, Linux Vulkan — matches this project's Linux-first workflow) with prebuilt releases and CI.
- Declarative TOML iteration loop is ideal for an AI agent; docs are LLM-indexed.
- Pluggable GPU: start on emulated Xenos, graduate to a native renderer later without redoing the CPU side — an incremental path the XenonRecomp model doesn't offer.
- BSD-3, standard "user supplies the game files" legal model.

**Cons**
- Early-stage churn: 0.8.x, breaking changes between versions; must pin a version/nightly.
- Out-of-the-box rendering is **emulator-class** (it *is* Xenia's GPU code compiled AOT) — the community's "isn't this just Xenia?" criticism. Accuracy/perf quirks of Xenia's Xenos translation are inherited. For a 30 fps turn-based strategy game this matters far less than for the action titles that criticism targets.
- No ReXGlue port has yet demonstrated "shippable 1.0" quality; the proven-polish precedents are all on the XenonRecomp side.
- Smaller community than hedge-dev's (688★ vs 6.4k★).

## 6. Community precedents (including the `examples_of_recompilations.md` repos)

Both repos collected in `examples_of_recompilations.md` turn out to be **ReXGlue** projects — and both went from zero to playable in weeks:

- **[NocturneRecomp](https://github.com/birabittoh/NocturneRecomp)** — *Castlevania: Symphony of the Night* (XBLA, "Nocturne in the Moonlight"). ReXGlue SDK; Windows + Linux x64 + Linux ARM64. Created 2026-06-06; v1.0 within weeks; v1.2.6 on 2026-07-10 with a mod system (symbol maps, graphics settings, music player). 200★. Solo human developer; no evidence of AI assistance.
- **[reNut](https://github.com/masterspike52/reNut)** — *Banjo-Kazooie: Nuts & Bolts*, a full disc-based 3D title. ReXGlue SDK (`rexglue codegen renut_config.toml`), mid-asm hooks. Created 2026-02-28, **playable ~6–8 weeks later**; latest release May 2026 with achievements; residual animation glitches don't block gameplay. Along the way they surfaced and got fixed an unimplemented VMX128 opcode in ReXGlue. Linux/Steam Deck via community fork.

The most directly relevant precedent for *this* project, found during research:

- **[DownpourRecomp](https://github.com/LittleBitUA/DownpourRecomp)** — *Silent Hill: Downpour* on ReXGlue, **v1.0 in roughly two weeks**, now v1.1.6 (June 2026) with a 60 FPS unlock and ~1,370 prewarmed shaders — and the README **explicitly discloses "AI assistance (Claude Code) alongside hands-on reverse-engineering."** An AI-agent-driven ReXGlue port is not hypothetical; it has already shipped.

Broader field (curated at [awesome-x360-recomps](https://github.com/abduznik/awesome-x360-recomps) and the [Recompendium](https://nio03.github.io/unricopie/en/)): playable — UnleashedRecomp (XenonRecomp lineage), Skate 3, WWE SvR07, Naughty Bear, Lollipop Chainsaw; in progress — Ace Combat 6, Deadly Premonition, Kameo, Destroy All Humans PotF, Forza Horizon, Guitar Hero II, GoldenEye XBLA, Blue Dragon, Lost Odyssey, Ninja Gaiden 2, Halo 3 beta, Crackdown 1/2, Viva Piñata TiP, and more. **Nearly everything started in 2026 uses ReXGlue; the hedge-dev-lineage projects are forks of the Unleashed tree.**

## 7. Other options considered

**Option C — Ship it in an emulator (Xenia bundling).** Zero porting work; the game already runs in the local xenia-edge harness. But it is not a port: per-frame JIT overhead, no moddability hooks, awkward distribution (Xenia is BSD but bundling a game image is not distributable), and the Windows-centric Xenia mainline vs the niche xenia-edge Linux fork. **Verdict: not the goal, but the harness is the indispensable *reference oracle* for whichever real port path is chosen.**

**Option D — Source-level reimplementation.** Ghidra-driven rewrite of the game in portable C++, leaning on the symbolicated iOS build and the PS3 effect-layer work as a Rosetta Stone. This yields the *best possible* end state (true native code, full moddability — the project's long-term interest given the map-editor/Korea-mod history) but is a multi-month-to-year effort even for an agent fleet, with a long "nothing runs" valley. **Verdict: wrong first step; becomes attractive *after* a recompiled port exists as an executable specification.** A hybrid is possible: start from a working recomp and incrementally replace subsystems with native reimplementations (function-by-function, validated against the recomp behavior).

**Option E — Port a different SKU.** The 2012 Windows Phone version (2K China's port of the iOS build) sits in `../Civilization Revolution v1.0.0.0 [Winphone Iz].xap`, and inspection confirms it is **pure managed C#/XNA**: `WMAppManifest.xml` declares `RuntimeType="XNA"`, and the whole game is one 3.9 MB .NET assembly (`Civ_WP7.dll`) plus XNA `.xnb` content (asset names like `Credits_iphone_*` confirm the iOS lineage). A .NET assembly decompiles to near-complete C# with ILSpy, and XNA titles have a well-trodden PC path via MonoGame/FNA. Two implications:
- As a *port base*: the fastest route to "CivRev running natively on PC" of any option here — but it is the cut-down mobile edition (touch UI, reduced presentation), so it does not satisfy the goal of porting the 360 version.
- As *reference material*: decompiled C# of the complete rules engine, cross-referenced with the symbolicated iOS build, gives the porting agent readable ground truth for what the anonymous recompiled 360 functions do. This is a uniquely strong asset for verification and for any later native-rewrite phase.

## 8. Feasibility assessment for an agent-driven port

**Overall: feasible, with high confidence for a playable build and moderate confidence for a polished one.** The reasoning:

**Why CivRev is an easier-than-average target.**
- Turn-based, 30 fps, small maps, no physics middleware, no streaming open world — the failure modes that plague action-game recomps (frame pacing, animation jitter, audio sync) are far less punishing here.
- Deterministic rules engine → cheap correctness testing (same inputs should produce the same game states in Xenia and in the port).
- The UI is Scaleform GFx running entirely inside the recompiled guest code — it needs only working rendering + input, not a UI reimplementation.
- Audio is Miles + MP3/Bink — conventional formats with known host-side paths; XMA (the classic recomp pain point) is handled by ReXGlue's Xenia-derived decoder if present at all.

**Why the agent workflow is unusually well-supported here.**
1. **A working oracle already exists**: `xenia_automation/` runs the real game with VNC output and full logging. The agent can boot Xenia and the port side-by-side, compare screenshots/logs at each milestone, and diff guest-visible behavior. (Two emulator instances shouldn't run concurrently on this host — GPU starvation — so the loop should capture references first, then test the port.)
2. **A reverse-engineering rig already exists in the same image**: Ghidra 12 + XEX loader + Xenon VMX128 extension + 360 SDK FIDBs for symbol identification when a specific function misbehaves.
3. **Cross-SKU ground truth**: symbolicated iOS binary, deeply-mapped PS3 EBOOT, and now decompilable C# from the WP7 XAP — three independent references for naming and verifying logic.
4. **Precedent**: DownpourRecomp shipped a v1.0 ReXGlue port in ~2 weeks with Claude Code assistance; reNut (a bigger 3D title) reached playable in 6–8 weeks solo. Both are consistent with an agent iterating TOML/config/log loops.

**Milestone ladder for the port** (each step has a crisp, machine-checkable success signal):
1. `rexglue codegen` completes on `default.xex` (reuse `switch_tables.toml` + save/restore addresses already found).
2. Build links and the executable starts; guest entry point runs (trace log).
3. Boot reaches the Firaxis/2K logos → Bink playback works.
4. Main menu renders → Scaleform + GPU path works; input works.
5. New game starts, map renders, turns advance → core loop works.
6. Full game completable; save/load (XAM content shims); audio correct.
7. Polish: 60 fps unlock, resolution/ultrawide, keyboard+mouse mapping, stub Live networking cleanly.

**Main risks and mitigations.**
- *ReXGlue API churn* → pin one release/nightly; upgrade deliberately.
- *Unimplemented PPC/VMX instructions* → precedent shows these get fixed upstream quickly (reNut's `vsldoi128`); the agent can also implement locally since codegen output is plain C++.
- *Xenia-inherited GPU quirks* → acceptable for a strategy game; long-term escape hatch is ReXGlue's pluggable GPU (`rexgpu-xenos` → native renderer later, aided by the named-constant `.fxobj` shaders).
- *An emulated-Xenos "port" is judged not native enough* → phase 2 exists (see below); the CPU-side work transfers.

**Effort estimate** (agent-driven, human-reviewed): reaching milestone 5 in days-to-weeks of iteration; milestone 6–7 in weeks. Option A by contrast fronts a person-month-scale runtime build before milestone 3 is even reachable.

## 9. Recommendation

**Primary path: ReXGlue.** Every line of evidence points the same way:

1. **It solves the actual hard problem.** The recompilation half was never the bottleneck — this repo proved that in April (63k functions compiled clean). The bottleneck is the runtime, and ReXGlue ships one that is maintained by someone else, derived from the emulator this game already demonstrably runs on.
2. **The precedents match.** Both examples in `examples_of_recompilations.md` are ReXGlue projects that reached playable in weeks; the one known AI-assisted (Claude Code) 360 port is a ReXGlue project; essentially all new 2026 ports chose ReXGlue. Meanwhile XenonRecomp is dormant and its only polished port took a veteran team six months of hand-building a runtime — and the team that forked that runtime is 15+ months in without a release.
3. **It fits an agent loop.** CLI-driven, declarative TOML, trace logging, LLM-indexed docs, and this repo's existing Xenia/VNC oracle for verification.
4. **It preserves the better endgame instead of foreclosing it.** The pluggable GPU plugin boundary means "native renderer" (the thing Option A buys) remains reachable incrementally — and CivRev's named-constant effect files make that unusually tractable when the time comes.

**Keep as supporting assets:** the Xenia harness (verification oracle), the existing XenonRecomp output (reference corpus — useful for diffing codegen and for local instruction fixes), the Ghidra rig and cross-SKU symbol sources (debugging), and the WP7 C# decompilation (rules-engine ground truth).

**Fallback / phase 2:** if ReXGlue's runtime proves too immature for this title, fall back to Option A using the already-generated XenonRecomp output with a runtime forked from UnleashedRecomp's tree — expensive but proven. If the ReXGlue port succeeds and native-quality rendering is desired later, replace the Xenos GPU plugin with a native renderer as a phase-2 project rather than restarting.

**Concrete first steps for the porting agent:**
1. Pin the latest ReXGlue stable (v0.8.0) or a chosen nightly; build its toolchain in Docker (Clang 20, CMake 3.25+, Ninja) alongside the existing images.
2. `rexglue init` a project; feed it `xenon_recomp/work/extracted/default.xex`; port over the known-good save/restore addresses and `switch_tables.toml` hints.
3. Iterate codegen → build → run `--log_level=trace` against the extracted `Resource/` tree, climbing the milestone ladder above, using `xenia_automation/` captures as the reference at each rung.

---

## Appendix: key sources

- ReXGlue: [repo](https://github.com/rexglue/rexglue-sdk) · [docs](https://rexglue-rexglue-sdk.mintlify.app/introduction) · [Getting Started wiki](https://github.com/rexglue/rexglue-sdk/wiki/Getting-Started) · [maintainer interview (Read Only Memo)](https://readonlymemo.com/rexglue-xbox-360-recompilation-interview/) · [Time Extension interview](https://www.timeextension.com/news/2026/03/i-hold-my-work-to-a-strict-standard-the-driving-force-behind-xbox-360-recomp-tool-rexglue-speaks-out) · [Habr workflow walkthrough](https://habr.com/en/articles/1003322/)
- hedge-dev: [XenonRecomp](https://github.com/hedge-dev/XenonRecomp) · [XenosRecomp](https://github.com/hedge-dev/XenosRecomp) · [UnleashedRecomp](https://github.com/hedge-dev/UnleashedRecomp) · [plume](https://github.com/renderbag/plume) · [Game Developer interview on Unleashed Recompiled](https://www.gamedeveloper.com/programming/how-a-sonic-unleashed-preservation-project-hopes-to-protect-obscure-ports) · [MarathonRecomp](https://github.com/sonicnext-dev/MarathonRecomp)
- Precedents: [NocturneRecomp](https://github.com/birabittoh/NocturneRecomp) · [reNut](https://github.com/masterspike52/reNut) · [DownpourRecomp (Claude Code-assisted)](https://github.com/LittleBitUA/DownpourRecomp) · [awesome-x360-recomps](https://github.com/abduznik/awesome-x360-recomps) · [Recompendium catalog](https://nio03.github.io/unricopie/en/)
- Xenia internals referenced: [XMA decoder](https://github.com/xenia-project/xenia/blob/master/src/xenia/apu/xma_decoder.cc) · [CivRev compat issue (stale, 2020)](https://github.com/xenia-project/game-compatibility/issues/1571)
