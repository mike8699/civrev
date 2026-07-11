# Oracle harness — agent guide

How an autonomous agent drives the Xenia oracle harness while porting CivRev
(Xbox 360) to PC via ReXGlue. This is the operational manual; the port plan is
[`../../REXGLUE_PORT_PRD.md`](../../REXGLUE_PORT_PRD.md) (verification protocol
in §7), and the harness design rationale is
[`../ORACLE_IMPROVEMENTS.md`](../ORACLE_IMPROVEMENTS.md).

**Mental model.** Xenia running the real game IS the ground truth. The harness
turns a Xenia run into a scripted, machine-checkable artifact bundle
(screenshots, file/kernel traces, crash status, `result.json`). Your loop:

1. Capture a **reference bundle** from Xenia for a scenario (once per milestone).
2. Build/run the **port** under the same input timeline.
3. **Diff** the port's behavior against the reference (traces, screenshots, logs).
4. Fix divergences, repeat. No human interprets a run — `result.json` and the
   diff tools decide.

---

## Hard rules (non-negotiable)

- **Never modify the host game data.** The ISO and the extracted tree
  (`xenon_recomp/work/extracted/`) are read-only inputs. All mutations
  (movie-skip, profile seeding) happen INSIDE the container at start-up —
  ephemeral, rebuilt every run.
- **Never commit game assets** — no ISO, XEX, extracted resources, or code
  generated from the XEX — to any remote. The repo is public.
- **One emulator at a time.** Every run takes a GPU flock
  (`shlib/gpu_lock.sh`); two concurrent emulator containers starve the GPU and
  both fail. Don't bypass the lock, don't launch a second run while one is
  active (`docker ps | grep civrev-oracle` to check).
- **Builds fail loudly.** Never mask a failing step in the Dockerfile or
  scripts with `|| true` / `2>/dev/null` to "get past" it — diagnose the root
  cause. The image is pinned (xenia-edge `7acf88d` + sha256) and must stay
  deterministic.

---

## One-time setup

```bash
# Build the pinned image (xenia-edge 7acf88d; tesseract, PIL, evdev included)
docker build -t civrev-xbox360 xenia_automation/

# Verify the extracted game tree exists (default.xex + Resource/ + shaders/)
ls xenon_recomp/work/extracted/default.xex
```

Host needs: docker, python3 + Pillow + numpy (comparator), tesseract
(optional — OCR prefers the in-container binary), flock.

Path overrides (all optional, defaults in `shlib/common.sh`):
`CIVREV_EXTRACTED_TREE`, `CIVREV_OUTPUT_DIR`, `CIVREV_REFERENCES_DIR`,
`CIVREV_FIXTURES_DIR`, `CIVREV_PROFILE_SEED`, `CIVREV_DOCKER_IMAGE`,
`CIVREV_GPU_LOCK_FILE`, `VULKAN_DISPLAY` (default `lavapipe`).

What a run does automatically (supervisor inside the container): bind-mounts an
empty file over the intro `.bik` movies (fast, deterministic boot — never skip
mid-CG by button, it freezes Bink decode), seeds a fresh Xenia profile from
`fixtures/saves/base_profile/` (game crashes at boot without one; seed is
ephemeral so every run is identical), creates the virtual Xbox 360 gamepad,
then launches Xenia.

---

## Running a scenario

```bash
oracle/run_scenario.sh <scenario> [--out DIR] [--keep] [--game-dir DIR] [--display MODE]
```

Artifacts land in `--out` (default `output/<scenario>/`):

| File | What |
|---|---|
| `result.json` | machine verdict — parse this first |
| `run.log` | full Xenia log |
| `file_trace.txt` | unique guest file accesses (ResolvePath etc.) — the primary port-diff signal |
| `kernel_trace.txt` | kernel/export call trace |
| `crash.txt` | extracted crash context (only on crash) |
| `<checkpoint>.png` | screenshots taken by the script's `shot` commands |

`result.json.status` → what to do:

| status | Meaning | Action |
|---|---|---|
| `completed` | script ran to the end, no crash | inspect checkpoints/traces; success |
| `crash` | crash markers in the log | read `crash.txt`; `run.log` around it |
| `timeout` | a `wait` never matched | boot regression or wrong expectation |
| `hang` / `boot_fail` | no progress / no checkpoints | check container came up, GPU lock, image |
| `error` | harness fault | read the runner's own stderr |

Exit code is 0 only for healthy terminal states — safe to gate CI/loops on it.

**Beware transient black frames**: a `shot` can catch a frame mid
shader-compile and save a black PNG even though the game is fine (observed on a
verified-good run). A black checkpoint alone is not failure — cross-check
`run.log` (active shader/asset traffic = alive) or take a fresh shot with
`oracle/screenshot.sh` while the container is up (`--keep`).

### Scenario catalog

| Scenario | State | What it proves |
|---|---|---|
| `boot` | verified | launch → title ("Press START") → decline sign-in → main menu |
| `golden_age` | **verified e2e 2026-07-11** | main menu → Single Player → Play Scenario → **Golden Age** → **Deity** → **Russians** → in-game (Settlers @ 4000 BC). ~5 min. The template for menu-navigation scenarios. |
| `beta_centauri` | works | like golden_age but the scenario opens with a Modern-Era popup (extra dismiss) |
| `menu`, `newgame_20turns`, `save_load` | older | predate the OCR-verified navigation style; modernize before trusting |

---

## Input: what actually works (hard-won)

Input goes through a **virtual Xbox 360 gamepad** (`virtpad.py`, uinput) — the
only path Xenia's `hid="sdl"` reads. Keyboard/xdotool events never reach the
game. `input.sh <ACTION>` (mappings in `input_map.conf`) writes to the pad's
FIFO in the container.

Facts your scripts must respect:

- **Button presses hold 0.4 s** (`input_map.conf`); shorter drops intermittently
  — the game samples the pad slowly.
- **D-pad steps hold 0.2 s** — the compromise: 0.35 s auto-repeats (over-moves),
  0.15 s drops (under-moves). Even at 0.2 s, **presses still drop ~1-in-2/3 on
  carousels**. Therefore:
- **Never trust fixed press counts for selection.** Any "press N times to reach
  item X" script is flaky by construction. Use `find_text` (OCR-verified
  stepping, below) for every list/carousel selection. Fixed counts are
  acceptable only for short hops that a following `wait_text` verifies.
- A=confirm, B=back/dismiss, START=advance title. Accept screens can need a
  second A press (harmless to double-press).

## OCR-verified navigation (the core technique)

`find_text <ACTION> <max> [crop=L,T,R,B] <pattern>` — OCR the screen; if the
pattern isn't there, press ACTION and re-OCR, up to `max` times. It checks the
frame **before each press and once after the last press** (a dropped-press
target can land on the final press), settling 1.3 s between presses so slide
animations finish.

**The crop is what makes "selected" ≠ "visible".** Menus show the SELECTED
item's name in a fixed description panel; OCR only that panel and a match means
the item is actually selected, not merely on screen. Fractions of
width/height, L,T,R,B. Known-good crops (1280×720):

| Screen | Crop | Panel reads e.g. |
|---|---|---|
| Scenario list description | `0.54,0.21,0.82,0.33` | `~ Golden Age ~` |
| Difficulty description | `0.56,0.34,0.82,0.46` | `a Deity r the hravect of the hrave.` |
| Civ-select description | `0.38,0.49,0.64,0.63` | `t Catherine Russians NS wl` |

**Patterns must tolerate garble.** The game's stylized font garbles short
words ("bravest" → "hravect"; "Deity" sometimes → "Dety"/"De1ty"). Derive
patterns empirically — never guess:

1. Get a frame with the target selected (run with `--keep`, drive manually via
   `oracle/input.sh`, capture with `oracle/screenshot.sh check`).
2. OCR the crop: `python3 oracle/ocr.py check.png 'ZZZ' --crop L,T,R,B` prints
   nothing on no-match; to see raw text, crop+tesseract by hand or grep the
   matched-text line `ocr.py` prints on success.
3. Set the pattern to what tesseract actually produced (regex, case-insensitive
   — e.g. `De[il1]t|eity`, `Cath|ussia`).

**Carousels that wrap or start randomly need a reset.** The civ carousel opens
on a random civ and wraps; the difficulty list wraps too. Pattern (from
`golden_age`, mirrors the PS3 `launch.py` approach): scroll LEFT to the edge
item (Romans — left stops there, so over-pressing is harmless), OCR-confirm
arrival, then scroll RIGHT to the target, OCR-confirmed, with `max` sized ~3×
the logical distance to absorb drops:

```
find_text  DPAD_LEFT   30  crop=0.38,0.49,0.64,0.63  Caesar|Roman
find_text  DPAD_RIGHT  20  crop=0.38,0.49,0.64,0.63  Cath|ussia
```

## Scenario script reference

One command per line, `#` comments. Executed by `run_scenario.sh`:

| Command | Semantics |
|---|---|
| `wait <regex> <timeout>` | wait for a Xenia **log** line (pattern may contain spaces; last token is the timeout). Sets crash/timeout status on failure. |
| `wait_text <regex> <timeout>` | wait until **screen OCR** matches (full frame). Use for UI states with no log signature (e.g. `Press START`). Non-fatal on timeout. |
| `find_text <ACTION> <max> [crop=..] <regex>` | OCR-verified stepping (above). Warns (rc 1 internally) if not found. |
| `wait_stable <idle> [max]` | wait until the screen stops changing. **Unusable on screens with live 3D backgrounds** (title, menus) — they never settle; prefer `wait_text`. |
| `wait_idle <idle> [max]` | wait until the log stops growing. |
| `sleep <secs>` | fixed wait (menu transitions ~1–3 s; scenario load ~15–20 s). |
| `shot <name>` | screenshot checkpoint → `result.json.checkpoints`. |
| `input <ACTION>` | mapped action (`A B X Y START BACK DPAD_* LB RB LT RT`). |
| `raw <virtpad cmd>` | raw pad command, e.g. `raw press A 0.3`, `raw dpad down`. |
| `hold <ACTION> <secs>` | hold a button. |
| `expect_no_crash` | assert no crash markers so far. |

New-scenario checklist: start from `golden_age/script.txt`; boot with
`wait Hardware scaler|Shader .* translated successfully 90` +
`wait_text Press START 90`; verify every screen transition with a `wait_text`;
every selection with a `find_text` crop; end with `expect_no_crash`; validate
patterns against real captured frames before trusting a green run.

---

## Using it as the port's oracle

Per PRD §7. Once a scenario is trustworthy in Xenia:

```bash
# 1. Promote a reference bundle (runs twice, gates on run-to-run self-consistency
#    of the file trace; screenshots reported, gated only with --strict-shots)
oracle/capture_reference.sh golden_age            # → references/golden_age/

# 2. Run the PORT under the same input timeline, capturing its log + frames.

# 3. Diff file access order/set (primary M3+ signal)
oracle/trace/extract_file_trace.py port_run.log --unique --out port_trace.txt
oracle/trace/diff_trace.py references/golden_age/file_trace.txt port_trace.txt

# 4. Compare frames at checkpoints (M4+). Masks exclude animated regions.
oracle/compare_screens.py references/golden_age/07_russians.png port_civselect.png \
    --threshold 0.90 [--mask ref.mask]     # exit 0 = match, 3 = differ
```

Interpretation rules: the file trace is authoritative (deterministic
run-to-run); screenshots tolerate animated overlays via masks; some
file-not-founds are NORMAL (the game probes optional paths — diff against the
Xenia reference before "fixing" the port). Record accepted divergences with
reasoning in `PROGRESS.md`.

## Debugging a run

```bash
oracle/run_scenario.sh golden_age --out output/dbg --keep   # container stays up
# watch live:            VNC to localhost:5900
oracle/screenshot.sh now --dir output/dbg                   # live frame
oracle/input.sh DPAD_DOWN ; oracle/input.sh A               # drive manually
oracle/input.sh --raw "press A 0.3"                         # raw pad command
docker exec civrev-oracle tail -f /output/run.log           # live log
oracle/trace/extract_crash.py output/dbg/run.log --context 30
docker rm -f civrev-oracle                                  # ALWAYS clean up (frees the GPU lock path)
```

The scenario runner prints `[oracle] OK find_text matched '<pat>' after N
<ACTION>` / `WARN ... not found after <max>` lines — the fastest way to see
which navigation step diverged. On a WARN, the run continues; the *next*
`wait_text`/checkpoint tells you where it actually ended up.

Verified navigation ground truth (for sanity-checking logs, not for hardcoding):
main menu → Single Player = 1 down; → Play Scenario = 3 downs; Golden Age =
index 6 in the list; Deity = 4 downs from Chieftain; Russians = 5 civs right of
Romans. `find_text` press counts will exceed these (drops) — that's normal.
