"""Launch RPCS3, wait for loading, capture screenshot."""
import os
import subprocess
import threading
import time
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from config import (
    RPCS3_BIN,
    RPCS3_SCREENSHOT_DIR,
    GAME_DISC_DIR,
    RPCS3_BOOT_TIMEOUT,
    SCREENSHOT_DELAY,
)

DISPLAY = os.environ.get("DISPLAY", ":99")


def _existing_screenshots() -> set[str]:
    if not RPCS3_SCREENSHOT_DIR.exists():
        return set()
    return set(str(p) for p in RPCS3_SCREENSHOT_DIR.rglob("*.png"))


def _find_game_path() -> str:
    # Boot from disc game directory (PS3_GAME/USRDIR/EBOOT.BIN)
    boot = GAME_DISC_DIR / "PS3_GAME" / "USRDIR" / "EBOOT.BIN"
    if boot.exists():
        return str(GAME_DISC_DIR)
    raise FileNotFoundError(f"Could not find disc game at {GAME_DISC_DIR}")


def _find_rpcs3_window() -> str | None:
    """Find the RPCS3 game rendering window ID."""
    try:
        env = {**os.environ, "DISPLAY": DISPLAY}
        result = subprocess.run(
            ["xdotool", "search", "--name", "RPCS3"],
            capture_output=True, text=True, timeout=3, env=env,
        )
        window_ids = [w for w in result.stdout.strip().split("\n") if w]
        return window_ids[0] if window_ids else None
    except Exception:
        return None


def _capture_display() -> np.ndarray | None:
    """Capture the display as a numpy array using ImageMagick import."""
    try:
        result = subprocess.run(
            ["import", "-display", DISPLAY, "-window", "root", "png:-"],
            capture_output=True, timeout=5,
        )
        if result.returncode != 0 or not result.stdout:
            if result.stderr:
                print(f"  capture error: {result.stderr.decode().strip()}")
            return None
        img = Image.open(BytesIO(result.stdout)).convert("RGB")
        return np.array(img)
    except subprocess.TimeoutExpired:
        print("  capture timed out")
        return None
    except Exception as e:
        print(f"  capture failed: {e}")
        return None


def _frames_similar(a: np.ndarray, b: np.ndarray, threshold: float = 0.998) -> bool:
    if a.shape != b.shape:
        return False
    small_a = np.array(Image.fromarray(a).resize((160, 120), Image.Resampling.NEAREST))
    small_b = np.array(Image.fromarray(b).resize((160, 120), Image.Resampling.NEAREST))
    diff = np.mean(np.abs(small_a.astype(np.float32) - small_b.astype(np.float32))) / 255.0
    return (1.0 - diff) >= threshold


def _is_blank_or_black(frame: np.ndarray, threshold: int = 15) -> bool:
    return np.mean(frame) < threshold


def _is_rpcs3_alive(proc: subprocess.Popen) -> bool:
    """Check if RPCS3 process is still running."""
    return proc.poll() is None


def wait_for_stable_frame(
    proc: subprocess.Popen,
    timeout: int | None = None,
    poll_interval: float = 2.0,
    stable_count: int = 4,
) -> np.ndarray | None:
    """Poll the display until the image stabilizes.

    The loading screen has a progress bar and changing status text, so
    frames will differ between polls. Once the game reaches the main menu
    the screen becomes truly static and consecutive frames will match.
    Returns early if RPCS3 crashes or no frames are captured for too long.
    """
    if timeout is None:
        timeout = RPCS3_BOOT_TIMEOUT

    start = time.time()
    prev_frame = None
    consecutive = 0
    no_frame_count = 0

    # Brief initial wait for window to appear
    time.sleep(2)

    while time.time() - start < timeout:
        if not _is_rpcs3_alive(proc):
            print(f"  [{time.time() - start:.0f}s] RPCS3 exited (code {proc.returncode})")
            return None

        frame = _capture_display()
        if frame is None:
            no_frame_count += 1
            if no_frame_count >= 10:
                print(f"  [{time.time() - start:.0f}s] Failed to capture any frames after {no_frame_count} attempts, giving up")
                return None
            time.sleep(poll_interval)
            continue
        no_frame_count = 0

        if _is_blank_or_black(frame):
            print(f"  [{time.time() - start:.0f}s] Black screen (loading)...")
            prev_frame = None
            consecutive = 0
            time.sleep(poll_interval)
            continue

        elapsed = time.time() - start

        if prev_frame is not None and _frames_similar(prev_frame, frame):
            consecutive += 1
            print(f"  [{elapsed:.0f}s] Stable frame {consecutive}/{stable_count}")
            if consecutive >= stable_count:
                print("  Game appears loaded!")
                return frame
        else:
            consecutive = 1
            print(f"  [{elapsed:.0f}s] Frame changed, waiting for stability...")

        prev_frame = frame
        time.sleep(poll_interval)

    print(f"  Timed out after {timeout}s")
    # Return the last frame we captured so caller can save it for debugging
    return prev_frame


RPCS3_LOG = Path("/root/.cache/rpcs3/RPCS3.log") if os.environ.get("IN_DOCKER") == "1" \
    else Path.home() / ".cache" / "rpcs3" / "RPCS3.log"


def _find_all_rpcs3_windows() -> list[str]:
    """Find all RPCS3-related window IDs (main window + game window)."""
    env = {**os.environ, "DISPLAY": DISPLAY}
    window_ids = []
    for search in ["RPCS3", "FPS:", "Civilization"]:
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", search],
                capture_output=True, text=True, timeout=3, env=env,
            )
            for wid in result.stdout.strip().split("\n"):
                if wid and wid not in window_ids:
                    window_ids.append(wid)
        except Exception:
            pass
    return window_ids


def _send_ps3_button(button: str):
    """Send a PS3 controller button press via keyboard mapping.

    RPCS3 keyboard mapping: X = Enter.
    Sends to the game window (FPS/Civilization title) specifically,
    since the keyboard pad handler only reads from that window.
    """
    key_map = {"X": "Return", "O": "BackSpace", "start": "1"}
    key = key_map.get(button, button)
    try:
        env = {**os.environ, "DISPLAY": DISPLAY}
        # Find the game rendering window (has "FPS:" in title)
        game_wid = None
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", "FPS:"],
                capture_output=True, text=True, timeout=3, env=env,
            )
            wids = [w for w in result.stdout.strip().split("\n") if w]
            if wids:
                game_wid = wids[0]
        except Exception:
            pass

        if game_wid is None:
            # Fallback: try any RPCS3 window
            try:
                result = subprocess.run(
                    ["xdotool", "search", "--name", "RPCS3"],
                    capture_output=True, text=True, timeout=3, env=env,
                )
                wids = [w for w in result.stdout.strip().split("\n") if w]
                if wids:
                    game_wid = wids[0]
            except Exception:
                pass

        if game_wid:
            subprocess.run(
                ["xdotool", "windowactivate", "--sync", game_wid],
                env=env, timeout=3, capture_output=True,
            )
            subprocess.run(
                ["xdotool", "key", "--delay", "100", key],
                env=env, timeout=3,
            )
        else:
            subprocess.run(["xdotool", "key", key], env=env, timeout=3)

        print(f"  Sent PS3 {button} (key: {key}) to window {game_wid}")
    except Exception as e:
        print(f"  Warning: Failed to send {button}: {e}")


def _wait_for_screen_text(keywords: list[str], timeout: int = 60, poll: float = 3.0) -> bool:
    """Wait until screen capture shows we've moved past a particular screen.

    This is a simple heuristic — we just wait for the screen to change
    significantly from a captured reference frame.
    """
    start = time.time()
    ref_frame = _capture_display()
    while time.time() - start < timeout:
        time.sleep(poll)
        frame = _capture_display()
        if frame is not None and ref_frame is not None:
            if not _frames_similar(ref_frame, frame, threshold=0.95):
                return True
        ref_frame = frame
    return False


def _navigate_startup(proc: subprocess.Popen):
    """Navigate from game boot through menus to Earth scenario.

    Sequence: wait 20s → X (skip cutscene) → START (title screen) →
    X (DLC dialog or title) → navigate menus to Earth scenario.
    """
    def _press(button: str, delay: float = 2.0):
        _send_ps3_button(button)
        time.sleep(delay)

    def _capture_state(label: str):
        frame = _capture_display()
        if frame is not None:
            brightness = np.mean(frame)
            print(f"    Screen state ({label}): brightness={brightness:.0f}")
            # Save debug frame
            try:
                img = Image.fromarray(frame)
                img.save(f"/output/debug_{label}.png")
            except Exception:
                pass

    # Wait 20s for cutscene to become skippable
    print("  Waiting 20s for cutscene...")
    time.sleep(20)
    _capture_state("after_20s_wait")

    # X skips cutscene → DLC dialog appears
    print("  Pressing X to skip cutscene...")
    _press("X", delay=8)
    _capture_state("after_cutscene_skip")

    # DLC dialog: dismiss with X (OK button is highlighted)
    print("  Pressing X to dismiss DLC dialog...")
    _press("X", delay=5)
    _capture_state("after_dlc_dismiss")

    # Now on title screen ("Press START to begin")
    print("  Pressing START for title screen...")
    _press("start", delay=8)
    _capture_state("after_start")

    # Now at main menu. Navigate to Earth scenario.
    _navigate_to_earth_scenario()


def _navigate_to_earth_scenario():
    """Navigate from main menu to Earth scenario difficulty screen.

    Main menu order: Play Now, Single Player, Multiplayer, Extras, Options
    Single Player menu: Play Scenario, ...
    Play Scenario list: includes Earth (need to scroll down)
    """
    def _press(button: str, delay: float = 2.0):
        _send_ps3_button(button)
        time.sleep(delay)

    def _capture_state(label: str):
        frame = _capture_display()
        if frame is not None:
            brightness = np.mean(frame)
            print(f"    Screen state ({label}): brightness={brightness:.0f}")
            try:
                img = Image.fromarray(frame)
                img.save(f"/output/debug_{label}.png")
            except Exception:
                pass

    # Main menu → Single Player (1 Down from Play Now)
    print("  Main menu → Single Player")
    _press("Down", delay=2)
    _press("X", delay=8)
    _capture_state("after_single_player")

    # Single Player menu: New Game, Load Game, Game of the Week, Play Scenario
    # Need 3 Down presses to reach Play Scenario
    print("  Single Player → Play Scenario")
    _press("Down", delay=1)
    _press("Down", delay=1)
    _press("Down", delay=1)
    _press("X", delay=8)
    _capture_state("after_play_scenario")

    # Scenario list → scroll to Earth
    # List: Attack of the Huns, Chariots of the Gods, Age of Imperialism,
    # Apocalypse!, Beta Centauri, Blitzkrieg!, Golden Age, Lightning Round, ...
    # Earth is further down (DLC scenario from Terrestrial Pack)
    print("  Scrolling to Earth scenario...")
    for i in range(10):
        _press("Down", delay=0.5)
    _capture_state("after_scroll_to_earth")

    print("  Selecting Earth scenario...")
    _press("X", delay=8)
    _capture_state("after_earth_select")

    print("  Should now be on difficulty selection screen.")


def _wait_for_rsx(proc: subprocess.Popen, timeout: int, launch_time: float = 0) -> bool:
    """Wait for RPCS3's RSX rendering to start by monitoring the log file.

    Returns True if RSX was detected, False on timeout/crash.
    """
    start = time.time()
    log_size = 0
    log_found = False

    while time.time() - start < timeout:
        if not _is_rpcs3_alive(proc):
            print(f"  RPCS3 exited (code {proc.returncode})")
            return False

        if RPCS3_LOG.exists():
            # Wait for RPCS3 to create a fresh log (mtime after launch)
            if not log_found:
                if RPCS3_LOG.stat().st_mtime >= launch_time:
                    log_found = True
                    log_size = 0
                else:
                    time.sleep(1)
                    continue

            current_size = RPCS3_LOG.stat().st_size
            if current_size > log_size:
                with open(RPCS3_LOG, "r", errors="replace") as f:
                    f.seek(log_size)
                    new_text = f.read()
                log_size = current_size

                for line in new_text.splitlines():
                    if "sys_rsx_context_attribute" in line:
                        elapsed = time.time() - start
                        print(f"  [{elapsed:.0f}s] RSX rendering started")
                        return True
                    if "Title:" in line:
                        print(f"  Log: {line.strip()}")

        elapsed = time.time() - start
        if int(elapsed) % 15 == 0 and int(elapsed) > 0:
            print(f"  [{elapsed:.0f}s] Waiting for RSX init...")
        time.sleep(1)

    print(f"  Timed out waiting for RSX after {timeout}s")
    return False


def _send_f12():
    """Send F12 keystroke to RPCS3."""
    try:
        env = {**os.environ, "DISPLAY": DISPLAY}
        windows = _find_all_rpcs3_windows()
        for wid in windows:
            subprocess.run(
                ["xdotool", "key", "--window", wid, "F12"],
                env=env, timeout=3,
            )
        if windows:
            print(f"Sent F12 screenshot key to {len(windows)} window(s)")
        else:
            subprocess.run(["xdotool", "key", "F12"], env=env, timeout=3)
            print("Sent F12 screenshot key to focused window")
    except FileNotFoundError:
        print("Warning: xdotool not installed")
    except Exception as e:
        print(f"Warning: Failed to send F12: {e}")


def launch_and_screenshot(max_wait: int | None = None) -> Path | None:
    """Launch RPCS3, wait for load, capture screenshot, terminate."""
    game_path = _find_game_path()
    before = _existing_screenshots()

    launch_time = time.time()

    print(f"Launching RPCS3 with {game_path} ...")
    print(f"DISPLAY={DISPLAY}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        # Check it actually started
        time.sleep(2)
        if not _is_rpcs3_alive(rpcs3):
            stdout = rpcs3.stdout.read().decode(errors="replace") if rpcs3.stdout else ""
            print(f"RPCS3 failed to start (exit code {rpcs3.returncode})")
            if stdout:
                # Print last 20 lines
                lines = stdout.strip().split("\n")
                for line in lines[-20:]:
                    print(f"  rpcs3: {line}")
            return None

        print("Waiting for RSX rendering to start...")
        timeout = max_wait or RPCS3_BOOT_TIMEOUT
        rsx_ok = _wait_for_rsx(rpcs3, timeout=timeout, launch_time=launch_time)

        stable = None
        if rsx_ok:
            # Navigate through startup screens to main menu.
            # Use screen capture to verify state at each step.
            _navigate_startup(rpcs3)

            # Try frame capture (works in headless/Xvfb, fails in GUI mode)
            test_frame = _capture_display()
            if test_frame is not None:
                print("  Screen capture available, waiting for stable frame...")
                stable = wait_for_stable_frame(rpcs3, timeout=30)
            else:
                print("  Screen capture unavailable (GUI mode), using fixed delay")

        _send_f12()
        time.sleep(SCREENSHOT_DELAY)

        after = _existing_screenshots()
        new = after - before
        if new:
            newest = max(new, key=os.path.getmtime)
            print(f"Screenshot captured: {newest}")
            return Path(newest)

        if stable is not None:
            fallback = Path("/tmp/rpcs3_capture.png")
            Image.fromarray(stable).save(str(fallback))
            print(f"Saved window capture to {fallback}")
            return fallback

        print("No screenshot captured (try RPCS3's F12 screenshot in ~/.config/rpcs3/screenshots/)")
        return None
    finally:
        print("Terminating RPCS3...")
        rpcs3.terminate()
        try:
            rpcs3.wait(timeout=5)
        except subprocess.TimeoutExpired:
            rpcs3.kill()
            rpcs3.wait()
        print("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--wait", type=int, default=None,
                        help="Max seconds to wait for game to load")
    args = parser.parse_args()
    launch_and_screenshot(args.wait)
