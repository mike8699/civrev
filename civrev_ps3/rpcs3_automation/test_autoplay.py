#!/usr/bin/env python3
"""Test autoplay mode via RPCS3 binary patch.

The "Enable AutoPlay" patch hooks game-start to call FUN_0002dc2c(config, 1, 100),
which sets the 0x800 flag and initializes the AI engine. This test boots the game,
navigates to Play Now, and monitors whether the AI is playing autonomously.
"""

import ctypes
import struct
import subprocess
import sys
import time
from pathlib import Path

from config import RPCS3_BIN
from launch import (
    DISPLAY,
    _capture_display,
    _find_game_path,
    _is_rpcs3_alive,
    _navigate_startup_to_main_menu,
    _next_debug_prefix,
    _send_ps3_button,
    _wait_for_rsx,
)

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("Need PIL and numpy", file=sys.stderr)
    sys.exit(1)


PS3_BASE = 0x300000000


class iovec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]


def _find_rpcs3_pid():
    """Find RPCS3 PID that has PS3 memory mapped."""
    r = subprocess.run(["pgrep", "-f", "rpcs3"], capture_output=True, text=True)
    for p in r.stdout.strip().split("\n"):
        if not p:
            continue
        try:
            pid = int(p)
            buf = ctypes.create_string_buffer(4)
            local = iovec(ctypes.cast(buf, ctypes.c_void_p), 4)
            remote = iovec(ctypes.c_void_p(PS3_BASE + 0x0193A288), 4)
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            if (
                libc.process_vm_readv(
                    pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0
                )
                == 4
            ):
                return pid
        except Exception:
            pass
    return None


def _read_ps3_u32(pid, addr):
    """Read a 32-bit big-endian value from PS3 memory."""
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    buf = ctypes.create_string_buffer(4)
    local = iovec(ctypes.cast(buf, ctypes.c_void_p), 4)
    remote = iovec(ctypes.c_void_p(PS3_BASE + addr), 4)
    if (
        libc.process_vm_readv(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
        == 4
    ):
        return struct.unpack(">I", buf.raw)[0]
    return None


def _check_autoplay_flags(pid):
    """Read config flags and check autoplay state."""
    # Config pointer via TOC: *(*(TOC - 0xCEC))
    # TOC = 0x0193a288, so *(0x0193959C) -> config_ptr_ptr
    ptr_ptr = _read_ps3_u32(pid, 0x0193959C)
    if ptr_ptr is None:
        print("  Failed to read TOC[-0xCEC]")
        return
    config_ptr = _read_ps3_u32(pid, ptr_ptr)
    if config_ptr is None:
        print(f"  Failed to read *0x{ptr_ptr:08x}")
        return
    flags = _read_ps3_u32(pid, config_ptr + 4)
    if flags is None:
        print(f"  Failed to read flags at 0x{config_ptr + 4:08x}")
        return

    print(f"  Config ptr: 0x{config_ptr:08x}")
    print(f"  Config flags: 0x{flags:08x}")
    print(f"    0x800 (autoplay):    {'SET' if flags & 0x800 else 'NOT SET'}")
    print(f"    0x4000000 (in-game): {'SET' if flags & 0x4000000 else 'NOT SET'}")
    print(f"    0x200000 (debug):    {'SET' if flags & 0x200000 else 'NOT SET'}")

    # Also check the code cave is in memory
    cave_instr = _read_ps3_u32(pid, 0x001AF82C)
    hook_instr = _read_ps3_u32(pid, 0x00175A68)
    print(f"  Hook at 0x00175a68: 0x{hook_instr:08x} (expect 0x48039dc5)")
    print(f"  Cave at 0x001af82c: 0x{cave_instr:08x} (expect 0x7c0802a6)")

    # Check the byte flag that FUN_0002dc2c sets: **(r2-0x7c60) + 0x10
    byte_ptr_ptr = _read_ps3_u32(pid, 0x0193A288 - 0x7C60)  # TOC - 0x7c60
    if byte_ptr_ptr:
        byte_ptr = _read_ps3_u32(pid, byte_ptr_ptr)
        if byte_ptr:
            byte_val = _read_ps3_u32(pid, byte_ptr + 0x10)
            print(f"  Autoplay byte at **(TOC-0x7c60)+0x10: 0x{byte_val:08x}")

    return flags


def _press(button: str, delay: float = 2.0):
    _send_ps3_button(button)
    time.sleep(delay)


def _capture_state(label: str) -> np.ndarray | None:
    frame = _capture_display()
    if frame is not None:
        brightness = np.mean(frame)
        print(f"  Screen ({label}): brightness={brightness:.0f}")
        try:
            img = Image.fromarray(frame)
            img.save(f"/output/autoplay_{_next_debug_prefix()}_{label}.png")
        except Exception:
            pass
    return frame


def _navigate_to_play_now():
    """From main menu, select Play Now and start a game."""
    # Play Now is the first option in the main menu
    print("Pressing X for Play Now...")
    _press("X", delay=5)
    _capture_state("after_play_now")

    # Civ selection screen — accept default
    print("Accepting default civ...")
    _press("X", delay=10)
    _capture_state("after_civ_select")

    # Wait for game to load
    print("Waiting 30s for game to load...")
    time.sleep(30)
    _capture_state("game_loading")

    # Dismiss tutorial dialog: "I already know how to play" is the 2nd option
    print("Dismissing tutorial dialog...")
    _press("Down", delay=1)  # move to "I already know how to play"
    _press("X", delay=3)  # select it
    _capture_state("after_tutorial_dismiss")

    # Clear any remaining advisor/intro dialogs
    print("Clearing remaining dialogs...")
    for _ in range(5):
        _press("X", delay=2)
    _capture_state("game_loaded")


def _monitor_autoplay(proc: subprocess.Popen, duration: int = 300):
    """Monitor the game for signs of AI autoplay.

    Takes periodic screenshots and compares frames to detect whether
    the game is advancing autonomously (camera movement, turn changes).
    """
    print(f"\n=== MONITORING AUTOPLAY ({duration}s) ===")
    prev_frame = None
    interval = 10
    num_checks = duration // interval
    changes = 0

    for i in range(num_checks):
        if not _is_rpcs3_alive(proc):
            print("RPCS3 exited!")
            break

        frame = _capture_display()
        label = f"monitor_{i:02d}_{i * interval}s"

        if frame is not None:
            try:
                img = Image.fromarray(frame)
                img.save(f"/output/autoplay_{_next_debug_prefix()}_{label}.png")
            except Exception:
                pass

            if prev_frame is not None:
                small_a = np.array(
                    Image.fromarray(prev_frame).resize((160, 120))
                ).astype(np.float32)
                small_b = np.array(Image.fromarray(frame).resize((160, 120))).astype(
                    np.float32
                )
                diff = np.mean(np.abs(small_a - small_b)) / 255.0
                changed = diff > 0.01
                if changed:
                    changes += 1
                print(
                    f"  [{i * interval:3d}s] Frame diff: {diff:.4f} "
                    f"({'CHANGED' if changed else 'static'}) "
                    f"[{changes} changes so far]"
                )
            else:
                print(f"  [{i * interval:3d}s] First frame captured")

            prev_frame = frame

        time.sleep(interval)

    print(f"\n=== RESULT: {changes}/{num_checks - 1} frame changes detected ===")
    if changes > 3:
        print("AutoPlay appears to be WORKING — game is advancing autonomously")
    elif changes > 0:
        print(
            "Some changes detected but fewer than expected — may be partially working"
        )
    else:
        print("No changes detected — AutoPlay may not be active")

    return changes


def main():
    game_path = _find_game_path()
    launch_time = time.time()

    # Verify patch is installed
    patch_config = Path("/root/.config/rpcs3/patch_config.yml")
    if patch_config.exists():
        text = patch_config.read_text()
        if "Enable AutoPlay" in text:
            print("AutoPlay patch: ENABLED")
        else:
            print("WARNING: Enable AutoPlay patch not found in patch_config.yml!")
    else:
        print("WARNING: No patch_config.yml found — patches may not be enabled!")

    print(f"Launching RPCS3 with {game_path}...")
    print(f"DISPLAY={DISPLAY}")
    rpcs3 = subprocess.Popen(
        [str(RPCS3_BIN), str(game_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    try:
        time.sleep(2)
        if not _is_rpcs3_alive(rpcs3):
            stdout = (
                rpcs3.stdout.read().decode(errors="replace") if rpcs3.stdout else ""
            )
            print(f"RPCS3 failed to start (exit code {rpcs3.returncode})")
            for line in stdout.strip().split("\n")[-20:]:
                print(f"  rpcs3: {line}")
            return

        print("Waiting for RSX rendering (may take 5+ min for first boot)...")
        rsx_ok = _wait_for_rsx(rpcs3, timeout=600, launch_time=launch_time)
        if not rsx_ok:
            print("RSX never started. Aborting.")
            return

        _navigate_startup_to_main_menu(rpcs3)
        _navigate_to_play_now()

        # Check if autoplay flags are set in memory
        print("\n=== CHECKING AUTOPLAY FLAGS ===")
        pid = _find_rpcs3_pid()
        if pid:
            print(f"  RPCS3 PID: {pid}")
            _check_autoplay_flags(pid)
        else:
            print("  Could not find RPCS3 process for memory check")

        # Monitor for 5 minutes
        _monitor_autoplay(rpcs3, duration=300)

        # Final state
        _capture_state("final")

        # Check TTY log for game debug output
        tty_log = Path("/root/.cache/rpcs3/TTY.log")
        if tty_log.exists():
            tty = tty_log.read_text(errors="replace")
            if tty.strip():
                print(f"\n=== TTY LOG ({len(tty)} bytes) ===")
                for line in tty.strip().split("\n")[-50:]:
                    print(f"  TTY: {line}")

        # Check for fatal errors
        rpcs3_log = Path("/root/.cache/rpcs3/RPCS3.log")
        if rpcs3_log.exists():
            log = rpcs3_log.read_text(errors="replace")
            errors = [l for l in log.split("\n") if "·F " in l or "fatal" in l.lower()]
            if errors:
                print("\n=== RPCS3 ERRORS ===")
                for e in errors[-10:]:
                    print(f"  {e.strip()}")

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
    main()
