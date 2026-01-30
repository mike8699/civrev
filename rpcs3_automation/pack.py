"""Pack Pak9/ directory into FPK and install to RPCS3."""
import shutil
import subprocess
import sys
from pathlib import Path

from config import PAK9_DIR, FPK_SCRIPT, VENV_PYTHON, EDAT_DEST, PROJECT_ROOT, IN_DOCKER

WORK_DIR = Path("/tmp/civrev_pack")


def pack_and_install() -> Path:
    """Repack Pak9/ into FPK and copy to RPCS3 game directory."""
    if IN_DOCKER:
        # Copy Pak9/ to a writable location since fpk.py writes
        # the .FPK next to the source directory
        work_pak9 = WORK_DIR / "Pak9"
        if work_pak9.exists():
            shutil.rmtree(work_pak9)
        WORK_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copytree(str(PAK9_DIR), str(work_pak9))
        pak9_dir = work_pak9
    else:
        pak9_dir = PAK9_DIR

    print("Repacking Pak9/ ...")
    result = subprocess.run(
        [str(VENV_PYTHON), str(FPK_SCRIPT), "repack", str(pak9_dir)],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"fpk.py repack failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    fpk_path = pak9_dir.parent / "Pak9.FPK"
    if not fpk_path.exists():
        print("Error: Pak9.FPK was not created", file=sys.stderr)
        sys.exit(1)

    EDAT_DEST.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(fpk_path), str(EDAT_DEST))
    print(f"Installed to {EDAT_DEST}")
    return EDAT_DEST


if __name__ == "__main__":
    pack_and_install()
