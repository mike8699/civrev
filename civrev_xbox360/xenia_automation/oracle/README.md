# CivRev Xenia oracle harness

Tooling that turns the Xenia emulator (which boots CivRev 360) into a **machine-
checkable verification oracle** for the ReXGlue port: scripted scenarios,
comparable traces, screenshot diffing, and committed reference bundles the
porting agent diffs its build against — with no human in the loop. Built to the
plan in [`../ORACLE_IMPROVEMENTS.md`](../ORACLE_IMPROVEMENTS.md); consumed by the
port per [`../../REXGLUE_PORT_PRD.md`](../../REXGLUE_PORT_PRD.md) §7.

**Agent operating manual: [`AGENT_GUIDE.md`](AGENT_GUIDE.md)** — how to run
scenarios, interpret `result.json`, write OCR-verified navigation, and diff the
port against references. Read that first; this file is the component index.

## Layout

```
oracle/
  shlib/common.sh        shared paths, pinned config, logging
  shlib/gpu_lock.sh      H8  one-GPU-session lock (flock)
  shlib/container.sh     detached Xenia container lifecycle
  run_extracted.sh       H1  interactive launch from the extracted tree (VNC :5900)
  screenshot.sh          H3  capture a frame (import + docker cp)
  input.sh               H4  inject input via the virtual Xbox 360 gamepad
  virtpad.py             H4  uinput gamepad daemon (SDL-visible); input_map.conf, INPUT_MAP.md
  ocr.py                 OCR (tesseract) + --crop for selected-item verification
  run_scenario.sh        H5  scripted run + watchdog -> result.json
  capture_reference.sh   H6  run x2, self-consistency gate, promote references/<s>/
  compare_screens.py     H10 block-SSIM + RMSE + masks; test_compare_screens.py
  fixtures.sh            H9  profile/save snapshots; SAVES.md
  trace/                 H7  extract_file_trace / kernel_trace / crash, diff_trace, selftest.sh
  scenarios/             boot + golden_age (verified e2e), beta_centauri,
                         menu / newgame_20turns / save_load (pre-OCR style)
../references/<scenario>/  committed baselines (screenshots, traces, result.json)
../fixtures/               persistent Xenia content dir + committed save/profile snapshots
```

## Prerequisites

- The pinned Docker image: `docker build -t civrev-xbox360 xenia_automation/`
  (pins xenia-edge `7acf88d` + sha256 — newer `d158580` crashes CivRev on audio
  init; also carries the Ghidra RE rig, tesseract, PIL, evdev).
- The extracted game tree at `xenon_recomp/work/extracted/` (default.xex +
  Resource/ + shaders/) — the same bytes the port uses as `game_data_root`.
- Host: python3 + Pillow + numpy (for the comparator), flock, docker.

## Typical use (porting agent loop)

```bash
# 1. Capture / refresh the reference for a scenario (runs twice, self-consistency)
oracle/capture_reference.sh boot

# 2. ... build the ReXGlue port, produce its own run.log + screenshots ...

# 3. Diff the port's boot file-trace against the oracle
oracle/trace/extract_file_trace.py port_run.log --unique --out port_trace.txt
oracle/trace/diff_trace.py references/boot/file_trace.txt port_trace.txt

# 4. Compare a port screenshot against the oracle checkpoint
oracle/compare_screens.py references/boot/02_first_frame.png port_frame.png \
    --mask references/boot/02_first_frame.mask   # if animated regions exist
```

One-off interactive / manual driving:
```bash
oracle/run_extracted.sh            # VNC :5900
oracle/screenshot.sh myshot        # while a container is up
oracle/input.sh START
```

## Verified

All harness components are verified on real game runs (2026-07-11):

- **Full e2e navigation**: `golden_age` boots to the main menu and reaches
  in-game (Golden Age scenario / Deity / Russians, Settlers at 4000 BC) with
  every selection OCR-verified. `boot` reaches the main menu.
- **Boot is fast and deterministic**: intro movies are skipped by bind-mounting
  an empty file over the `.bik`s inside the container (never by button — that
  freezes Bink decode), and a fresh profile is seeded from
  `fixtures/saves/base_profile/` each run (the game crashes at boot without
  one; ephemeral seed = fully deterministic runs). Host game data is never
  touched.
- **Input works** via the virtual Xbox 360 gamepad (`virtpad.py`, uinput —
  Xenia's `hid="sdl"` never sees keyboard/xdotool events). D-pad presses drop
  intermittently, so selections must be OCR-verified (`find_text`), not fixed
  press counts — see [`AGENT_GUIDE.md`](AGENT_GUIDE.md).
- Plus the no-game-needed pieces: GPU lock (H8), trace extract/diff + self-test
  (H7), comparator + masks (H10), screenshots (H3), scenario watchdog +
  result.json (H5), reference promotion (H6), fixture snapshots (H9).

Remaining calibration: the comparator threshold (default 0.90) should be tuned
against two clean reference runs when the first port milestone needs it.

## Self-test

```bash
oracle/trace/selftest.sh          # trace extractors + diff invariants (no Docker)
python3 oracle/test_compare_screens.py   # comparator calibration (no Docker)
```
