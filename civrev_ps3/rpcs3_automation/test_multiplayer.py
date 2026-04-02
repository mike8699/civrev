"""Test multiplayer mode with the custom GameSpy replacement server.

Starts the custom server, launches RPCS3, navigates to multiplayer menu,
and captures screenshots showing what happens.
"""

import os
import subprocess
import sys
import time

import numpy as np
from config import RPCS3_BOOT_TIMEOUT
from launch import (
    _capture_display,
    _find_game_path,
    _navigate_startup_to_main_menu,
    _next_debug_prefix,
    _send_ps3_button,
    _wait_for_rsx,
)
from PIL import Image


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
            img.save(f"/output/debug_{_next_debug_prefix()}_{label}.png")
        except Exception:
            pass
    return frame


def _navigate_to_multiplayer():
    """From main menu, navigate to Multiplayer.

    Main menu layout (from top):
      Play Now
      Single Player
      Multiplayer        <- we want this (2x Down)
      Xbox LIVE / Online <- might be labeled differently
      Options
    """
    print("  Main menu → Multiplayer")

    # Down twice to reach Multiplayer
    _press("Down", delay=0.5)
    _press("Down", delay=0.5)
    _capture_state("menu_multiplayer_highlight")

    # Press X to enter Multiplayer
    _press("X", delay=5)
    _capture_state("after_multiplayer_select")

    # The game may show a "connecting to network" dialog or
    # "Powered by GameSpy" splash screen first
    # Wait and capture several frames to see what happens
    for i in range(10):
        time.sleep(3)
        frame = _capture_state(f"multiplayer_wait_{i}")
        if frame is None:
            print(f"    Frame {i}: no capture")
        else:
            brightness = np.mean(frame)
            print(f"    Frame {i}: brightness={brightness:.1f}")

    # Select "LAN Party" (3rd option — Down, Down)
    # LAN Party bypasses PSN sign-in and uses local network GameSpy
    print("  Selecting LAN Party (Down, Down, X)...")
    _press("Down", delay=0.5)
    _press("Down", delay=0.5)
    _capture_state("lan_party_highlight")
    _press("X", delay=5)
    _capture_state("after_lan_party_select")

    # Wait for the game browser to appear
    for i in range(10):
        time.sleep(3)
        frame = _capture_state(f"lan_wait_{i}")
        if frame is not None:
            brightness = np.mean(frame)
            print(f"    Frame {i}: brightness={brightness:.1f}")

    # Press Square (keyboard Z) to "Create Game"
    print("  Pressing Square (Z) to Create Game...")
    _send_ps3_button("Z")  # Square
    time.sleep(5)
    _capture_state("after_create_game")

    # Game Type menu: Head to Head / Teams / Free for All / Scenario
    # Select "Free for All" (Down, Down, X)
    print("  Selecting Free for All...")
    _press("Down", delay=0.5)
    _press("Down", delay=0.5)
    _capture_state("ffa_highlight")
    _press("X", delay=5)
    _capture_state("after_ffa_select")

    # Should now be on staging/lobby screen or game name entry
    for i in range(5):
        time.sleep(3)
        _capture_state(f"staging_wait_{i}")

    # If there's a name entry dialog, just press X to accept default
    print("  Pressing X to accept defaults...")
    _press("X", delay=3)
    _capture_state("after_accept_name")

    _press("X", delay=3)
    _capture_state("after_accept_2")

    # Capture the staging screen
    for i in range(10):
        time.sleep(3)
        _capture_state(f"lobby_{i}")


SERVER_LOG = "/output/server.log"


def start_custom_server():
    """Start the custom GameSpy server in the background."""
    print("Starting custom GameSpy server...")
    log_fh = open(SERVER_LOG, "w")
    # Use a wrapper script to enable DEBUG logging
    server_code = (
        "import logging; logging.basicConfig(level=logging.DEBUG, "
        "format='%(asctime)s %(name)s %(levelname)s %(message)s'); "
        "from civrev_server.__main__ import main; main()"
    )
    server_proc = subprocess.Popen(
        [sys.executable, "-c", server_code],
        cwd="/civrev/custom_server/src",
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": "/civrev/custom_server/src"},
    )
    # Give it time to bind ports
    time.sleep(2)
    if server_proc.poll() is not None:
        log_fh.close()
        with open(SERVER_LOG) as f:
            print(f"  Server FAILED to start! Exit code: {server_proc.returncode}")
            print(f"  Output: {f.read()[:1000]}")
        sys.exit(1)
    print(f"  Custom server started (PID: {server_proc.pid})")
    return server_proc, log_fh


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Test CivRev multiplayer with custom server"
    )
    parser.add_argument(
        "-w",
        "--wait",
        type=int,
        default=RPCS3_BOOT_TIMEOUT,
        help="Boot timeout in seconds",
    )
    args = parser.parse_args()

    # Start custom server
    server_proc, log_fh = start_custom_server()

    try:
        # Launch RPCS3
        game_path = _find_game_path()
        print(f"Launching RPCS3 with game at: {game_path}")

        rpcs3_proc = subprocess.Popen(
            ["rpcs3", "--no-gui", game_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Wait for boot
        time.sleep(2)
        if rpcs3_proc.poll() is not None:
            print("RPCS3 crashed on startup!")
            sys.exit(1)

        print("Waiting for RSX rendering...")
        if not _wait_for_rsx(rpcs3_proc, timeout=args.wait):
            print("RSX never started, aborting")
            rpcs3_proc.terminate()
            sys.exit(1)

        # Navigate through startup to main menu
        print("Navigating through startup screens...")
        _navigate_startup_to_main_menu(rpcs3_proc)

        # Now navigate to multiplayer
        print("Navigating to multiplayer...")
        _navigate_to_multiplayer()

        # Final state capture
        print("Capturing final state...")
        for i in range(5):
            time.sleep(3)
            _capture_state(f"final_{i}")

    finally:
        print("Cleaning up...")
        rpcs3_proc.terminate()
        try:
            rpcs3_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            rpcs3_proc.kill()

        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_proc.kill()
        log_fh.close()

    # Print server log
    print("\n" + "=" * 60)
    print("CUSTOM SERVER LOG")
    print("=" * 60)
    with open(SERVER_LOG) as f:
        print(f.read())
    print("=" * 60)

    # Print RPCS3 log (patch application and network info)
    rpcs3_log = "/root/.cache/rpcs3/RPCS3.log"
    if os.path.exists(rpcs3_log):
        print("\n" + "=" * 60)
        print("RPCS3 LOG (relevant lines)")
        print("=" * 60)
        with open(rpcs3_log) as f:
            for line in f:
                if any(
                    k in line
                    for k in [
                        "PAT:",
                        "Net:",
                        "sceNp",
                        "cellNet",
                        "NP ",
                        "PSN",
                        "network",
                        "Network",
                        "DNS",
                        "socket",
                        "connect",
                        "Available",
                    ]
                ):
                    print(line.rstrip())
        print("=" * 60)

    print("Done! Check /output/ for debug screenshots and server.log")


if __name__ == "__main__":
    main()
