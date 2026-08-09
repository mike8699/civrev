"""New Map wizard: blank, random continents, clone original, or import."""

from pathlib import Path

import numpy as np
import theme
from model import (
    DESERT,
    DLC_SLOTS,
    FOREST,
    GRASSLAND,
    GRID,
    HILLS,
    ICE,
    MAP_BYTES,
    MOUNTAINS,
    OCEAN,
    PLAINS,
    file_to_display,
)
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


def blank_map() -> bytearray:
    data = bytearray(MAP_BYTES)
    for c in range(GRID):
        for r in (0, 1, 30, 31):
            data[r * GRID + c] = ICE
    return data


def _smooth(a: np.ndarray, iters: int) -> np.ndarray:
    for _ in range(iters):
        p = np.pad(a, 1, mode="edge")
        a = sum(
            p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
            for dy in range(3) for dx in range(3)
        ) / 9.0
    return a


def _pick_terrain(e, m, v, lat_r, thresholds) -> int:
    peak, hi, wet, dry = thresholds
    if e >= peak:
        return MOUNTAINS
    if e >= hi:
        return HILLS
    if m >= wet:
        return FOREST
    if m <= dry and lat_r < 0.55:
        return DESERT
    return PLAINS if v > 0.55 else GRASSLAND


def _add_rivers(out: bytearray, data: np.ndarray, elev: np.ndarray, rng):
    """Short vertical river runs on elevated land (spawns require rivers)."""
    flags = (0x20, 0x40, 0x80)
    land_tiles = [(r, c) for r in range(2, 30) for c in range(GRID)
                  if data[r, c] not in (OCEAN, ICE)]
    if not land_tiles:
        return
    order = sorted(land_tiles, key=lambda rc: -elev[rc[0], rc[1]])
    starts = order[:len(order) // 3] or land_tiles
    used = set()
    runs = 0
    tries = 0
    while runs < 8 and tries < len(starts):
        r, c = starts[int(rng.integers(0, len(starts)))]
        tries += 1
        if (r, c) in used:
            continue
        flag = flags[int(rng.integers(0, 3))]
        for k in range(int(rng.integers(2, 5))):
            rr = r + k
            if rr >= 30 or data[rr, c] in (OCEAN, ICE):
                break
            out[rr * GRID + c] |= flag
            used.add((rr, c))
        runs += 1


def random_map(seed: int) -> bytearray:
    """Continents-style random map with correct terrain mapping and rivers."""
    rng = np.random.default_rng(seed)
    elev = _smooth(rng.random((GRID, GRID)), 3)
    moisture = _smooth(rng.random((GRID, GRID)), 2)
    variety = _smooth(rng.random((GRID, GRID)), 1)

    # Suppress land near the poles so continents sit in the playable band
    lat = np.abs(np.arange(GRID) - (GRID - 1) / 2) / (GRID / 2)
    elev = elev - (lat[:, None] ** 3) * 0.35

    land = elev > np.quantile(elev, 0.60)
    data = np.full((GRID, GRID), OCEAN, dtype=np.uint8)

    land_elev = np.where(land, elev, np.nan)
    thresholds = (
        np.nanquantile(land_elev, 0.93),   # peak
        np.nanquantile(land_elev, 0.80),   # hi
        np.quantile(moisture, 0.70),       # wet
        np.quantile(moisture, 0.25),       # dry
    )
    for r in range(GRID):
        for c in range(GRID):
            if land[r, c]:
                data[r, c] = _pick_terrain(
                    elev[r, c], moisture[r, c], variety[r, c],
                    lat[r], thresholds)

    for r in (0, 1, 30, 31):
        data[r, :] = ICE

    out = bytearray(data.tobytes())
    _add_rivers(out, data, elev, rng)
    return out


class GridPreview(QWidget):
    """Tiny read-only render of a candidate tile grid."""

    def __init__(self, parent=None, size: int = 192):
        super().__init__(parent)
        self._size = size
        self.data = blank_map()
        self.setFixedSize(size + 2, size + 2)

    def set_data(self, data: bytearray):
        self.data = data
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(QColor(theme.LINE), 1))
        p.setBrush(QColor(theme.BG))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        px = self._size / GRID
        p.translate(1, 1)
        for r in range(GRID):
            for c in range(GRID):
                t = self.data[r * GRID + c] & 0x07
                base, _, _ = theme.TERRAIN_COLORS[t]
                p.fillRect(QRectF(c * px, r * px, px + 0.5, px + 0.5),
                           QColor(base))
        rc = QColor(theme.RIVER)
        for r in range(GRID):
            for c in range(GRID):
                v = self.data[r * GRID + c]
                if v & 0x20:
                    p.fillRect(QRectF(c * px, r * px, 1, px), rc)
                if v & 0x40:
                    p.fillRect(QRectF((c + 1) * px - 1, r * px, 1, px), rc)
                if v & 0x80:
                    p.fillRect(QRectF(c * px, (r + 1) * px - 1, px, 1), rc)
        p.end()


class NewMapDialog(QDialog):
    """Returns .result_data (display-order bytearray) when accepted."""

    def __init__(self, pak9_original: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Map")
        self.setModal(True)
        self.pak9_original = pak9_original
        self.result_data = None
        self.result_label = ""

        root = QHBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(8)

        title = QLabel("Start from…")
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        left.addWidget(title)

        self.group = QButtonGroup(self)
        self.rb_blank = QRadioButton("Blank ocean")
        self.rb_random = QRadioButton("Random continents")
        self.rb_clone = QRadioButton("Copy of an original DLC map")
        self.rb_import = QRadioButton("Import a .map file…")
        for rb in (self.rb_blank, self.rb_random, self.rb_clone,
                   self.rb_import):
            rb.setStyleSheet("font-size: 13px; padding: 3px 0;")
            self.group.addButton(rb)
            left.addWidget(rb)

        # Random controls
        rand_row = QHBoxLayout()
        rand_row.setContentsMargins(24, 0, 0, 0)
        seed_lbl = QLabel("Seed")
        seed_lbl.setStyleSheet(f"color: {theme.MUTED}; font-size: 12px;")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(42)
        self.seed_spin.setStyleSheet(
            f"background: {theme.CARD}; border: 1px solid {theme.LINE};"
            "border-radius: 4px; padding: 3px 6px;")
        self.shuffle_btn = QPushButton("Shuffle")
        self.shuffle_btn.setStyleSheet(theme.quiet_button_style())
        rand_row.addWidget(seed_lbl)
        rand_row.addWidget(self.seed_spin)
        rand_row.addWidget(self.shuffle_btn)
        rand_row.addStretch()
        left.addLayout(rand_row)

        # Clone controls
        clone_row = QHBoxLayout()
        clone_row.setContentsMargins(24, 0, 0, 0)
        self.clone_combo = QComboBox()
        for s in DLC_SLOTS:
            self.clone_combo.addItem(s["title"])
        clone_row.addWidget(self.clone_combo)
        clone_row.addStretch()
        left.addLayout(clone_row)

        left.addStretch()

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setStyleSheet(theme.quiet_button_style())
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Create")
        ok.setStyleSheet(theme.primary_button_style())
        ok.setFixedHeight(30)
        ok.clicked.connect(self._accept)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        left.addLayout(btns)

        root.addLayout(left, 1)

        right = QVBoxLayout()
        pv_lbl = QLabel("Preview")
        pv_lbl.setStyleSheet(theme.section_label_style())
        right.addWidget(pv_lbl)
        self.preview = GridPreview()
        right.addWidget(self.preview)
        right.addStretch()
        root.addLayout(right)

        # Wiring
        self._import_path = None
        self._rand_widgets = (seed_lbl, self.seed_spin, self.shuffle_btn)
        self.rb_random.setChecked(True)
        for rb in (self.rb_blank, self.rb_random, self.rb_clone):
            rb.toggled.connect(self._refresh_preview)
        self.rb_import.toggled.connect(self._on_import_toggle)
        self.rb_random.toggled.connect(self._update_visibility)
        self.rb_clone.toggled.connect(self._update_visibility)
        self._update_visibility()
        self.seed_spin.valueChanged.connect(self._refresh_preview)
        self.shuffle_btn.clicked.connect(
            lambda: self.seed_spin.setValue(
                int.from_bytes(np.random.bytes(3), "little") % 1000000))
        self.clone_combo.currentIndexChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def _update_visibility(self, *args):
        for w in self._rand_widgets:
            w.setVisible(self.rb_random.isChecked())
        self.clone_combo.setVisible(self.rb_clone.isChecked())

    def _candidate(self):
        if self.rb_blank.isChecked():
            return blank_map(), "Blank ocean"
        if self.rb_random.isChecked():
            seed = self.seed_spin.value()
            return random_map(seed), f"Random continents (seed {seed})"
        if self.rb_clone.isChecked():
            slot = DLC_SLOTS[self.clone_combo.currentIndex()]
            path = self.pak9_original / slot["file"]
            if path.exists():
                return (file_to_display(path.read_bytes()),
                        f"Copy of {slot['title']}")
            return blank_map(), "Blank ocean (original missing)"
        if self.rb_import.isChecked() and self._import_path:
            try:
                return (file_to_display(Path(self._import_path).read_bytes()),
                        Path(self._import_path).name)
            except (OSError, ValueError):
                return blank_map(), "Blank ocean (import failed)"
        return None, ""

    def _on_import_toggle(self, checked):
        if checked:
            path, _ = QFileDialog.getOpenFileName(
                self, "Import .map File", str(self.pak9_original),
                "Map Files (*.map);;All Files (*)")
            if path:
                self._import_path = path
            else:
                self.rb_random.setChecked(True)
        self._refresh_preview()

    def _refresh_preview(self, *args):
        data, _ = self._candidate()
        if data is not None:
            self.preview.set_data(data)

    def _accept(self):
        data, label = self._candidate()
        if data is None:
            self.reject()
            return
        self.result_data = data
        self.result_label = label
        self.accept()
