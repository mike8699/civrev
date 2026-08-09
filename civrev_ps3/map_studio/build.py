"""Build pipeline: .map + DDS generation -> FPK repack -> RPCS3 install.

Runs in a background QThread so the UI stays responsive; reports step-level
progress. The model is snapshotted before the thread starts.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

import texgen
from model import DLC_SLOTS, MapModel
from PyQt5.QtCore import QThread, pyqtSignal
from settings import PROJECT_ROOT, Settings

# fpk.py lives in civrev_ps3/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

REQUIRED_PAK9_FILES = ["dlcscenariodata5.xml", "ordering.json"]


def slot_filenames(slot: dict) -> list:
    tag = slot["tag"].lower()
    return [
        slot["file"],
        f"map{tag}_heights.dds",
        f"map{tag}_lightmap.dds",
        f"map{tag}_mountainhill_blends.dds",
    ]


def pak9_ready(pak9_dir: Path) -> str | None:
    """Return an error message if the Pak9 working dir is unusable."""
    if not pak9_dir.is_dir():
        return f"Pak9 folder not found: {pak9_dir}"
    missing = [f for f in REQUIRED_PAK9_FILES if not (pak9_dir / f).exists()]
    for slot in DLC_SLOTS:
        missing += [f for f in slot_filenames(slot)
                    if not (pak9_dir / f).exists()]
    if missing:
        return "Pak9 folder is missing: " + ", ".join(missing[:6]) + (
            f" (+{len(missing) - 6} more)" if len(missing) > 6 else "")
    return None


def restore_slot(settings: Settings, slot_index: int) -> str:
    """Copy a slot's pristine files from Pak9_original back into Pak9."""
    slot = DLC_SLOTS[slot_index]
    src_dir = settings.pak9_original_dir
    dst_dir = settings.pak9_dir
    copied = []
    for name in slot_filenames(slot):
        src = src_dir / name
        if not src.exists():
            raise FileNotFoundError(f"Original file missing: {src}")
        shutil.copy2(src, dst_dir / name)
        copied.append(name)
    return f"Restored {len(copied)} original files for {slot['title']}"


class BuildWorker(QThread):
    """Full build: generate textures, write slot files, repack, install."""

    step_changed = pyqtSignal(str)
    progress = pyqtSignal(int)               # 0-100
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, map_snapshot: bytes, slot_index: int,
                 settings: Settings, install: bool, smart_patch: bool,
                 export_dir: Path | None = None, parent=None):
        super().__init__(parent)
        self.map_snapshot = map_snapshot
        self.slot_index = slot_index
        self.install = install
        self.smart_patch = smart_patch
        self.export_dir = export_dir
        # Copy settings values now — QSettings isn't thread-safe
        self.pak9_dir = settings.pak9_dir
        self.pak9_original_dir = settings.pak9_original_dir
        self.rpcs3_usrdir = settings.rpcs3_usrdir

    # ── Thread body ─────────────────────────────────────────

    def run(self):
        try:
            t0 = time.time()
            slot = DLC_SLOTS[self.slot_index]
            tag = slot["tag"].lower()

            model = MapModel()
            model.data[:] = self.map_snapshot

            out_dir = self.export_dir or self.pak9_dir
            if self.export_dir is None:
                err = pak9_ready(self.pak9_dir)
                if err:
                    self.failed.emit(err)
                    return
            else:
                out_dir.mkdir(parents=True, exist_ok=True)

            # 1. Texture generation ─ 0..70%
            self._step("Loading originals", 2)
            refs = texgen.load_blend_refs()
            target = None
            corpus = []
            if self.smart_patch:
                corpus = texgen.load_corpus(self.pak9_original_dir)
                target = next(
                    (s for s in corpus if s.tag == tag), None)
            if self.smart_patch and target is None:
                self.step_changed.emit(
                    "Originals unavailable — falling back to full synthesis")

            def on_progress(label, frac):
                self.step_changed.emit(label)
                self.progress.emit(5 + int(frac * 65))

            result = texgen.generate_textures(
                model, target, corpus, refs, progress=on_progress)

            # 2. Write slot files ─ 70..80%
            self._step("Writing map + textures", 72)
            model.save_file(out_dir / slot["file"])
            (out_dir / f"map{tag}_heights.dds").write_bytes(result["heights"])
            (out_dir / f"map{tag}_lightmap.dds").write_bytes(result["lightmap"])
            (out_dir / f"map{tag}_mountainhill_blends.dds").write_bytes(
                result["blends"])

            if self.export_dir is not None:
                self.progress.emit(100)
                self.finished_ok.emit(
                    f"Exported {slot['title']} ({result['mode']}) to "
                    f"{self.export_dir} in {time.time() - t0:.1f}s")
                return

            # 3. Repack FPK ─ 80..92%
            self._step("Repacking Pak9.FPK", 82)
            import fpk as fpk_module
            fpk_module.FPK.from_directory(self.pak9_dir)
            fpk_path = self.pak9_dir.parent / "Pak9.FPK"
            if not fpk_path.exists():
                self.failed.emit("fpk.py did not produce Pak9.FPK")
                return
            size = fpk_path.stat().st_size

            # 4. Install ─ 92..100%
            if self.install:
                self._step("Installing to RPCS3", 94)
                dest = self.rpcs3_usrdir / "Pak9.edat"
                self.rpcs3_usrdir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(fpk_path), str(dest))
                where = f"installed to {dest}"
            else:
                where = f"left at {fpk_path}"

            self.progress.emit(100)
            self.finished_ok.emit(
                f"Built {slot['title']} ({result['mode']}, "
                f"{size:,} byte FPK) — {where} in {time.time() - t0:.1f}s")
        except Exception as e:                      # surface to the UI
            self.failed.emit(f"{type(e).__name__}: {e}")

    def _step(self, label: str, pct: int):
        self.step_changed.emit(label)
        self.progress.emit(pct)


class PreviewWorker(QThread):
    """Generate preview imagery (decoded textures) without writing files."""

    ready = pyqtSignal(dict)     # {'heights': ndarray RGB, 'lightmap':..., 'blends':..., 'mode': str}
    failed = pyqtSignal(str)

    def __init__(self, map_snapshot: bytes, slot_index: int,
                 settings: Settings, smart_patch: bool, parent=None):
        super().__init__(parent)
        self.map_snapshot = map_snapshot
        self.slot_index = slot_index
        self.smart_patch = smart_patch
        self.pak9_original_dir = settings.pak9_original_dir

    def run(self):
        try:
            import numpy as np

            slot = DLC_SLOTS[self.slot_index]
            tag = slot["tag"].lower()
            model = MapModel()
            model.data[:] = self.map_snapshot

            refs = texgen.load_blend_refs()
            target = None
            corpus = []
            if self.smart_patch:
                corpus = texgen.load_corpus(self.pak9_original_dir)
                target = next((s for s in corpus if s.tag == tag), None)

            if target is not None:
                heights, light, blend = texgen.patch_textures(
                    model, target, corpus, refs)
                mode = "smart-patch"
                light_rgb = texgen.decode_dxt1(light)
            else:
                heights = texgen.synth_heights(model)
                light_rgb = texgen.synth_lightmap_rgb(model)
                blend = texgen.synth_blend_blocks(model, refs)
                mode = "full-synth"

            # Downscale lightmap for display
            light_small = light_rgb[::4, ::4]          # 1024x1024
            blend_rgb = texgen.decode_dxt1(blend)      # 2048
            blend_small = blend_rgb[::2, ::2]          # 1024
            shade = texgen.hillshade(heights)          # 512

            self.ready.emit({
                "heights": np.ascontiguousarray(shade),
                "lightmap": np.ascontiguousarray(light_small),
                "blends": np.ascontiguousarray(blend_small),
                "mode": mode,
            })
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")


class SceneWorker(QThread):
    """Compute raw texture payloads for the 3D in-game preview."""

    ready = pyqtSignal(object)          # gl_preview.SceneData
    failed = pyqtSignal(str)

    def __init__(self, map_snapshot: bytes, slot_index: int,
                 settings: Settings, smart_patch: bool, parent=None):
        super().__init__(parent)
        self.map_snapshot = map_snapshot
        self.slot_index = slot_index
        self.smart_patch = smart_patch
        self.pak9_original_dir = settings.pak9_original_dir

    def run(self):
        try:
            import numpy as np
            from gl_preview import SceneData

            slot = DLC_SLOTS[self.slot_index]
            tag = slot["tag"].lower()
            model = MapModel()
            model.data[:] = self.map_snapshot

            refs = texgen.load_blend_refs()
            target = None
            corpus = []
            if self.smart_patch:
                corpus = texgen.load_corpus(self.pak9_original_dir)
                target = next((s for s in corpus if s.tag == tag), None)

            from gl_preview import build_ground_albedo

            albedo = build_ground_albedo(bytes(model.data))
            if target is not None:
                heights, light, blend = texgen.patch_textures(
                    model, target, corpus, refs)
                scene = SceneData(
                    heights=heights,
                    light_dxt1=light.tobytes(),
                    light_rgb=None,
                    blend_dxt1=blend.tobytes(),
                    grid=bytes(model.data),
                    albedo=albedo,
                )
            else:
                heights = texgen.synth_heights(model)
                light_rgb = texgen.synth_lightmap_rgb(model)
                blend = texgen.synth_blend_blocks(model, refs)
                scene = SceneData(
                    heights=heights,
                    light_dxt1=None,
                    light_rgb=np.ascontiguousarray(light_rgb),
                    blend_dxt1=blend.tobytes(),
                    grid=bytes(model.data),
                    albedo=albedo,
                )
            self.ready.emit(scene)
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}")
