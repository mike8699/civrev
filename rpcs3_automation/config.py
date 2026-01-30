"""Configuration for RPCS3 automation."""
import os
from pathlib import Path

# When running in Docker, paths are fixed. Otherwise use host defaults.
IN_DOCKER = os.environ.get("IN_DOCKER", "") == "1"

if IN_DOCKER:
    RPCS3_BIN = Path("/opt/rpcs3/usr/bin/rpcs3")
    RPCS3_CONFIG_DIR = Path("/root/.config/rpcs3")
    PROJECT_ROOT = Path("/civrev")
    VENV_PYTHON = Path("python3")
    GAME_DISC_DIR = Path("/game_disc")
else:
    RPCS3_BIN = Path.home() / "Desktop" / "rpcs3-v0.0.35-17645-7b212e0e_linux64.AppImage"
    RPCS3_CONFIG_DIR = Path.home() / ".config" / "rpcs3"
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
    GAME_DISC_DIR = PROJECT_ROOT / "modified"

RPCS3_SCREENSHOT_DIR = RPCS3_CONFIG_DIR / "screenshots"

# Game
GAME_ID = "BLUS30130"
GAME_USRDIR = RPCS3_CONFIG_DIR / "dev_hdd0" / "game" / GAME_ID / "USRDIR"
EDAT_DEST = GAME_USRDIR / "Pak9.edat"

# Project paths
PAK9_DIR = PROJECT_ROOT / "Pak9"
FPK_SCRIPT = PROJECT_ROOT / "fpk.py"

# Timing
RPCS3_BOOT_TIMEOUT = 300  # seconds to wait for game to reach menu
SCREENSHOT_DELAY = 2      # seconds to wait after F12 before grabbing screenshot
