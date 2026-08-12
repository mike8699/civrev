"""Paths and preferences, persisted via QSettings."""

from pathlib import Path

from PyQt5.QtCore import QSettings

STUDIO_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = STUDIO_DIR.parent          # civrev_ps3/
ASSETS_DIR = STUDIO_DIR / "assets"

GAME_ID = "BLUS30130"


def _default_pak9() -> Path:
    return PROJECT_ROOT / "Pak9"


def _default_pak9_original() -> Path:
    return PROJECT_ROOT / "Pak9_original"


def _default_rpcs3_usrdir() -> Path:
    return (Path.home() / ".config" / "rpcs3" / "dev_hdd0" / "game"
            / GAME_ID / "USRDIR")


class Settings:
    def __init__(self):
        self._qs = QSettings("civrev", "Revitor")

    def _path(self, key: str, default: Path) -> Path:
        v = self._qs.value(key, "")
        return Path(v) if v else default

    # ── Paths ───────────────────────────────────────────────

    @property
    def pak9_dir(self) -> Path:
        return self._path("paths/pak9", _default_pak9())

    @pak9_dir.setter
    def pak9_dir(self, p: Path):
        self._qs.setValue("paths/pak9", str(p))

    @property
    def pak9_original_dir(self) -> Path:
        return self._path("paths/pak9_original", _default_pak9_original())

    @pak9_original_dir.setter
    def pak9_original_dir(self, p: Path):
        self._qs.setValue("paths/pak9_original", str(p))

    @property
    def rpcs3_usrdir(self) -> Path:
        return self._path("paths/rpcs3_usrdir", _default_rpcs3_usrdir())

    @rpcs3_usrdir.setter
    def rpcs3_usrdir(self, p: Path):
        self._qs.setValue("paths/rpcs3_usrdir", str(p))

    # ── Preferences ─────────────────────────────────────────

    @property
    def install_after_build(self) -> bool:
        return self._qs.value("build/install_after", "true") == "true"

    @install_after_build.setter
    def install_after_build(self, on: bool):
        self._qs.setValue("build/install_after", "true" if on else "false")

    @property
    def smart_patch(self) -> bool:
        """Reuse original DDS art for unchanged tiles (recommended)."""
        return self._qs.value("build/smart_patch", "true") == "true"

    @smart_patch.setter
    def smart_patch(self, on: bool):
        self._qs.setValue("build/smart_patch", "true" if on else "false")
