"""Texture preview dialog — shows what Build will produce, without writing."""

import numpy as np
import theme
from build import PreviewWorker
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from settings import Settings


def _np_to_pixmap(arr: np.ndarray, display: int) -> QPixmap:
    h, w, _ = arr.shape
    img = QImage(arr.tobytes(), w, h, w * 3, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(img).scaled(
        display, display, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class TexturePreviewDialog(QDialog):
    PANEL = 300

    def __init__(self, map_snapshot: bytes, slot_index: int,
                 settings: Settings, smart_patch: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Texture Preview")
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        self.mode_lbl = QLabel("Generating textures…")
        self.mode_lbl.setStyleSheet(f"color: {theme.MUTED}; font-size: 12px;")
        root.addWidget(self.mode_lbl)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.panels = {}
        for i, (key, caption) in enumerate([
            ("heights", "Heights (shaded relief)"),
            ("lightmap", "Lightmap (in-game ground colors)"),
            ("blends", "Blends (R=forest, G=mountain masks)"),
        ]):
            img = QLabel("…")
            img.setFixedSize(self.PANEL, self.PANEL)
            img.setAlignment(Qt.AlignCenter)
            img.setStyleSheet(
                f"background: {theme.BG}; border: 1px solid {theme.LINE};"
                "border-radius: 6px;")
            cap = QLabel(caption)
            cap.setAlignment(Qt.AlignCenter)
            cap.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;")
            grid.addWidget(img, 0, i)
            grid.addWidget(cap, 1, i)
            self.panels[key] = img
        root.addLayout(grid)

        btns = QHBoxLayout()
        btns.addStretch()
        close = QPushButton("Close")
        close.setStyleSheet(theme.quiet_button_style())
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        root.addLayout(btns)

        self.worker = PreviewWorker(
            map_snapshot, slot_index, settings, smart_patch, parent=self)
        self.worker.ready.connect(self._on_ready)
        self.worker.failed.connect(self._on_failed)
        self.worker.start()

    def _on_ready(self, result: dict):
        for key in ("heights", "lightmap", "blends"):
            self.panels[key].setPixmap(
                _np_to_pixmap(result[key], self.PANEL))
        mode = ("smart patch — unchanged tiles keep original art"
                if result["mode"] == "smart-patch"
                else "full synthesis — no originals found for this slot")
        self.mode_lbl.setText(f"Mode: {mode}")

    def _on_failed(self, err: str):
        self.mode_lbl.setText(f"Preview failed: {err}")
        self.mode_lbl.setStyleSheet(f"color: {theme.BAD}; font-size: 12px;")

    def closeEvent(self, event):
        if self.worker.isRunning():
            self.worker.wait(2000)
        super().closeEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.settings = settings
        self.setMinimumWidth(560)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(10)

        self.edits = {}
        rows = [
            ("pak9_dir", "Pak9 working folder",
             "Unpacked Pak9 DLC — maps are saved and repacked here"),
            ("pak9_original_dir", "Pak9 originals folder",
             "Pristine DLC files — donor art for smart patch and restores"),
            ("rpcs3_usrdir", "RPCS3 USRDIR",
             "Where Pak9.edat is installed after a build"),
        ]
        for key, label, hint in rows:
            lbl = QLabel(label)
            lbl.setStyleSheet("font-size: 12px; font-weight: 600;")
            root.addWidget(lbl)
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(
                f"color: {theme.MUTED}; font-size: 11px;")
            root.addWidget(hint_lbl)
            row = QHBoxLayout()
            edit = QLineEdit(str(getattr(settings, key)))
            row.addWidget(edit, 1)
            browse = QPushButton("Browse…")
            browse.setStyleSheet(theme.quiet_button_style())
            browse.clicked.connect(
                lambda _, e=edit: self._browse(e))
            row.addWidget(browse)
            root.addLayout(row)
            self.edits[key] = edit

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(theme.quiet_button_style())
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setStyleSheet(theme.primary_button_style())
        save.setFixedHeight(30)
        save.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(save)
        root.addLayout(btns)

    def _browse(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(
            self, "Choose folder", edit.text())
        if path:
            edit.setText(path)

    def _save(self):
        from pathlib import Path

        for key, edit in self.edits.items():
            setattr(self.settings, key, Path(edit.text()))
        self.accept()
