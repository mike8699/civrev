# CivRev Xenia oracle harness

Tooling that turns the Xenia emulator (which boots CivRev 360) into a **machine-
checkable verification oracle** for the ReXGlue port: scripted scenarios,
comparable traces, screenshot diffing, and committed reference bundles the
porting agent diffs its build against — with no human in the loop. Built to the
plan in [`../ORACLE_IMPROVEMENTS.md`](../ORACLE_IMPROVEMENTS.md); consumed by the
port per [`../../REXGLUE_PORT_PRD.md`](../../REXGLUE_PORT_PRD.md) §7.

## Layout

```
oracle/
  shlib/common.sh        shared paths, pinned config, logging
  shlib/gpu_lock.sh      H8  one-GPU-session lock (flock)
  shlib/container.sh     detached Xenia container lifecycle
  run_extracted.sh       H1  interactive launch from the extracted tree (VNC :5900)
  screenshot.sh          H3  capture a frame (import + docker cp)
  input.sh               H4  inject input (xdotool XTEST); input_map.conf, INPUT_MAP.md
  run_scenario.sh        H5  scripted run + watchdog -> result.json
  capture_reference.sh   H6  run x2, self-consistency gate, promote references/<s>/
  compare_screens.py     H10 block-SSIM + RMSE + masks; test_compare_screens.py
  fixtures.sh            H9  profile/save snapshots; SAVES.md
  trace/                 H7  extract_file_trace / kernel_trace / crash, diff_trace, selftest.sh
  scenarios/             boot (usable), menu / newgame_20turns / save_load (gated)
../references/<scenario>/  committed baselines (screenshots, traces, result.json)
../fixtures/               persistent Xenia content dir + committed save/profile snapshots
```

## Prerequisites

- The pinned Docker image: `docker build -t civrev-xbox360 xenia_automation/`
  (pins xenia-edge `d158580` + sha256; also carries the Ghidra RE rig).
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

## Verified vs pending

**Verified** (no game changes needed): GPU lock serialization/timeout (H8);
trace extraction + diff against the historical log, with a self-test (H7);
comparator decision boundaries + masks (H10); screenshot capture of live frames
(H3); input injection mechanism, XTEST path (H4); extracted-tree boot (H1);
end-to-end scenario run with crash/hang/timeout watchdog + result.json (H5);
reference self-consistency + promotion (H6); fixture snapshot/restore roundtrip
(H9). Run `oracle/selftest.sh` for the no-Docker checks.

**Pending real-frame / game work** (documented, not blocking the tooling):
- **Xenia needs a user profile** or CivRev crashes at boot (`No Profiles Found`
  → guest crash). Only the `boot` scenario is clean today; `menu`/`newgame`/
  `save_load` are gated. Provision a profile once over VNC — see
  [`SAVES.md`](SAVES.md).
- **Input delivery to Xenia's GUI is unconfirmed** on the WM-less Xvfb display
  (SDL ignores synthetic `--window` events; XTEST+focus is wired but unverified
  on a real frame). Confirm over VNC and correct `input_map.conf` — see
  [`INPUT_MAP.md`](INPUT_MAP.md). May require the Weston display mode.
- **Comparator threshold** (default 0.90) needs calibration against two real
  clean boots once the profile lets the game reach a stable menu.

## Self-test

```bash
oracle/trace/selftest.sh          # trace extractors + diff invariants (no Docker)
python3 oracle/test_compare_screens.py   # comparator calibration (no Docker)
```
