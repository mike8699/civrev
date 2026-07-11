# Xenia harness → verification oracle: required improvements

*Written 2026-07-11. Companion to `../REXGLUE_PORT_PRD.md`. That PRD's milestones
(M3–M7) consume artifacts defined here; work items are labeled H1–H11 and referenced
from the PRD by those IDs.*

## Purpose

The porting agent needs the Xenia harness to answer one question repeatedly and
mechanically: **"is the port's behavior at milestone X correct?"** Today the harness can
boot the game and expose a VNC display — good for a human, insufficient for an
autonomous loop. The gap is: scripted scenarios, machine-readable outcomes, comparable
traces, and reference artifacts the port can be diffed against.

## Current state (inventory)

- `Dockerfile`: xenia-edge AppImage (latest at build time — **not pinned**), Xvfb/x11vnc
  + Weston/Xwayland display modes, lavapipe fallback, Ghidra 12.0.4 + XEXLoaderWV +
  Xenon extension + 360 SDK FIDBs.
- `entrypoint.sh`: display-mode selection (`VULKAN_DISPLAY=lavapipe|weston|xorg-dummy`),
  launches `xenia --apu=sdl --license_mask=-1 --protect_zero=false --log_file=/output/xenia.log`.
- `docker_run.sh`: mounts game file/dir read-only, `output/` read-write, VNC on :5900,
  `--device /dev/dri` for host GPU under Weston.
- `output/xenia.log`: one historical run (llvmpipe) — game initialized, loaded modules
  and shaders, then hit an access violation. The game is known to run under other
  conditions; the known-good configuration is not recorded anywhere. That's part of the
  problem this doc fixes.

## Work items

### H1 — Launch from the extracted game tree (asset parity with the port)
**What:** make reference runs load `xenon_recomp/work/extracted/` (`default.xex` +
`Resource/` + `shaders/`) instead of the ISO, so oracle and port consume byte-identical
assets from the same directory.
**How:** `docker_run.sh` already supports directory mounts and the entrypoint already
prefers `/game_data/default.xex`; add a documented `run_extracted.sh` (or flag) that
mounts the extracted tree, and verify boot behavior matches the ISO run (one-time
file-trace diff: ISO-mounted vs dir-mounted — expect only device-path differences).
**Accept:** boot from extracted tree reaches the same log landmarks as ISO boot.

### H2 — Pin versions and record the known-good configuration  ✅ DONE
**What:** the Dockerfile fetched `xenia-edge` "latest" — a moving oracle is not an
oracle. **Done:** pinned to tag `d158580` + sha256
`6b1b958a…ccd2d` (verified at build time via `sha256sum -c`), recorded in
`oracle/shlib/common.sh`. Moved the xenia layer AFTER Ghidra so future pin bumps
don't re-download the RE rig.
**Determinism fix found during rebuild:** the `GhidraXenon` extension step was
silently broken (`gradle buildExtension 2>/dev/null` — apt Gradle is 4.4.1 while
Ghidra 12.0.4 needs ≥8.5, and the upstream repo had switched to a `build_extension.sh`
prebuilt-SLEIGH flow). It never built — `latest` lacked the extension entirely, hidden
by `2>/dev/null`. Replaced with the correct `build_extension.sh <ghidra-version>` flow,
pinned to commit `3db42fe`, version-stamped to Ghidra's `application.version`, added the
required `zip` pkg, dropped the useless `gradle` pkg, and made it **fail the build hard**
(`test -f …/ppc_64_xenon.sla`) rather than mask failures.
**Known-good display:** lavapipe/Xvfb with host-GPU passthrough via `/dev/dri` boots the
game well past the historical llvmpipe crash (renders the title logo); it is the default
for reference capture. (The game then hits the profile crash — see INPUT_MAP.md / SAVES.md.)
**Still open (minor):** a pinned in-image `xenia.config.toml` (fixed 1280x720/backend +
verbose-kernel cvars) is not yet baked in; the config the container writes on first run is
used as-is. Not blocking — traces/screenshots are already reproducible run-to-run (H6
showed file-trace self-consistency).
**Accept:** ✅ two boots produce identical file traces (H6 `boot` run1==run2); the pinned
image builds deterministically and fails hard on any extension error.

### H3 — Screenshot capture command
**What:** `screenshot.sh [name]` executable via `docker exec`, writing
`/output/<name>.png`.
**How:** X11 modes: ImageMagick `import -window root` (already installed). Weston mode:
grab via VNC client capture (e.g. `vncsnapshot`/`gvnccapture` added to the image) or a
weston screenshooter; pick whichever proves reliable, hide it behind the one script.
**Accept:** non-black 1280x720 PNG captured at the title screen in the default mode.

### H4 — Input injection with a verified key map
**What:** `input.sh <action>` mapping logical pad actions (`A`, `B`, `START`, `DPAD_UP`,
`LSTICK_UP`, …) to host key events, plus `input.sh --script <file>` executing a timed
action list (`sleep`-annotated lines).
**How:** X11 modes: `xdotool key/keydown/keyup` (installed) against the Xenia window.
Xenia's SDL/keyboard→gamepad mapping must be *verified once empirically* (drive via VNC,
observe which keys navigate the CivRev menu) and written into `INPUT_MAP.md` — do not
trust documentation. Weston mode may need `wtype`/`ydotool` (add to image) — or simply
standardize reference capture on an X11-based mode if input there is more reliable.
**Accept:** a scripted sequence advances from title screen into the main menu
unattended, proven by H3 screenshots.

### H5 — Scenario runner with watchdog and machine-readable results
**What:** `run_scenario.sh <scenario>` = boot (H1/H2) → execute the scenario's input
script (H4) → capture screenshots at named checkpoints (H3) → tear down → emit
`/output/<scenario>/result.json`: `{status: booted|title|completed|crash|hang|timeout,
checkpoints: {...}, timings, log_path}`.
**How:** bash driving `docker run` + `docker exec`; watchdog = per-phase timeouts +
log-progress monitoring (log file byte-count stalls ⇒ hang) + crash detection (grep
`==== CRASH DUMP ====`). Scenario definitions live in `scenarios/<name>/script.txt`.
Initial scenarios, matching PRD milestones: `boot` (to title screen), `menu`
(title → main menu → SP setup), `newgame_20turns` (start game, 20 scripted end-turns),
`save_load` (save, quit, relaunch, load).
**Accept:** `run_scenario.sh boot` returns `status=title` on a healthy build and
`status=hang|crash` (not a false `title`) when given a deliberately broken input.

### H6 — Reference bundles
**What:** `capture_reference.sh <scenario>` = H5 run + copy artifacts into
`references/<scenario>/` (screenshots, `result.json`, full log, extracted traces per
H7). Commit these bundles to git (they are small: PNGs + text; logs gzipped) — they are
the milestone acceptance baselines for PRD M3–M7.
**Accept:** `references/boot/` and `references/menu/` exist, regenerated twice with
passing self-consistency (H2 criterion).

### H7 — Trace extractors (the cheapest cross-implementation signals)
**What:** small scripts (python3 is in the image) that normalize a Xenia log — and the
port's ReXGlue trace log — into comparable text files:
- `extract_file_trace.py`: ordered list of guest file opens/resolves
  (Xenia: `ResolvePath(...)` / NtCreateFile lines; ReXGlue: its VFS trace lines —
  normalize both to bare guest paths, dedup consecutive repeats). Output:
  `file_trace.txt`.
- `extract_kernel_trace.py`: sequence/histogram of kernel calls where log level allows;
  at minimum thread-creation order and wait-object patterns.
- `extract_crash.py`: on crash, pull the dump block + preceding 100 lines into
  `crash.txt`.
Plus `diff_trace.py` implementing the PRD's comparison semantics (set equality +
landmark ordering, tolerant of thread interleaving).
**Accept:** `extract_file_trace.py` over the existing `output/xenia.log` yields the
known boot sequence (xex → ini/config → FPKs → `.fxobj` shaders → movie probes).

### H8 — GPU session lock
**What:** all GPU-consuming runs (Xenia reference capture AND the port under test) take
an exclusive host-side lock; lavapipe/software runs are exempt.
**How:** `flock /tmp/civrev_gpu.lock` wrapper sourced by `docker_run.sh`,
`run_scenario.sh`, and documented in the PRD for the port's run script. Include a
timeout + stale-lock breaker (lock holder PID recorded).
**Accept:** two simultaneous `run_scenario.sh` invocations serialize (second waits),
verified once.

### H9 — Save-game fixtures (shared with the port)
**What:** a persistent Xenia content/profile directory so saves survive runs; a
`save_load` scenario producing a known mid-game save; fixtures exported to
`fixtures/saves/<name>/` (Xenia content dir layout for title 545407E5).
**Why:** PRD M7 uses "save produced in Xenia loads in the port" as a strong
cross-implementation correctness check (both map XamContent to a host directory).
**How:** mount a host dir over Xenia's content root (currently ephemeral inside the
container at `/root/.local/share/Xenia/content`); document the layout mapping to
ReXGlue's `user_data_root`.
**Accept:** a save created in one Xenia run is visible and loadable in the next.

### H10 — Screenshot comparator
**What:** `compare_screens.py <a.png> <b.png> [--mask <region-file>]` → similarity
score + pass/fail at a tuned threshold; masks for known-animated regions (menu
shimmer, blinking prompts, turn-timer text).
**How:** ImageMagick `compare -metric RMSE` or python-PIL SSIM; calibrate the threshold
empirically: two independent Xenia boots must pass; Xenia-vs-black must fail; keep
calibration images in `references/_calibration/`.
**Accept:** calibration suite passes; thresholds recorded in the script defaults.

### H11 — Stretch (only if a concrete debugging need arises)
- Investigate xenia-edge GPU trace dump / trace-viewer support for frame-level GPU
  diffing against RenderDoc captures of the port (PRD M4/M6 rendering triage).
- Triage the recorded llvmpipe access-violation crash (useful headless CI mode if
  fixable via newer xenia-edge or config; not a blocker while Weston+GPU works).
- OCR checkpoint extraction (tesseract) for reading turn counters/menu labels from
  screenshots — upgrade from "images look similar" to semantic assertions.

## Suggested order

H2 → H1 → H3 → H4 (needs one interactive VNC session to verify the key map) → H7 →
H5 → H6 → H10 → H8 → H9. H1–H7 unblock PRD M3/M4; H8 is required before the first
port GPU run; H9/H10 before M5–M7 acceptance.

## Acceptance for the harness as a whole

The harness is "oracle-ready" when: `capture_reference.sh boot|menu|newgame_20turns`
each produce committed reference bundles from the pinned configuration, self-consistent
across two runs, and `run_scenario.sh` returns correct machine-readable statuses for
healthy and deliberately-broken runs. At that point the porting agent (PRD §7) never
needs a human in its verification loop.
