"""Scenario Rules panel — typed controls for all 35 VARIATORs, grouped.

Each variator renders as a row whose control matches its kind:
  flag    → checkbox (checked = present, value 1)
  enum    → dropdown (the 0/"none" option means "not set")
  level   → enable checkbox + spinbox (0 is meaningful, so presence is explicit)
  value   → enable checkbox + spinbox (gold, year, …)
  bitmask → enable checkbox + spinbox (DISPLAYCARD)
  coord   → Place-on-map / Clear buttons + tile label (STARTLOC*)

The panel owns the in-memory value set for the current slot; the editor loads
it from the XML on slot change and writes it back at build time. STARTLOC rows
ask the editor (via signals) to arm the canvas placement tool.
"""

from __future__ import annotations

import scenario_schema as S
import theme
from canvas import STARTLOC_COLORS
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from widgets import SectionLabel, ValidationRow

_SPIN_QSS = f"""
QSpinBox {{
    background: {theme.CARD}; border: 1px solid {theme.LINE};
    border-radius: 5px; padding: 3px 6px; color: {theme.TEXT};
    min-width: 84px; font-family: monospace;
}}
QSpinBox:disabled {{ color: {theme.FAINT}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 16px; }}
"""


class Collapsible(QWidget):
    """A titled section whose body can be folded away."""

    def __init__(self, title: str, expanded: bool = True, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.header = QToolButton()
        # Escape '&' so Qt doesn't treat it as a mnemonic accelerator.
        self.header.setText("  " + title.replace("&", "&&"))
        self.header.setCheckable(True)
        self.header.setChecked(expanded)
        self.header.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.header.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.header.setStyleSheet(
            f"QToolButton {{ background: {theme.CARD}; color: {theme.TEXT};"
            f" border: 1px solid {theme.LINE}; border-radius: 6px;"
            f" padding: 7px 10px; font-weight: 600; font-size: 12px;"
            f" text-align: left; }}"
            f"QToolButton:hover {{ background: {theme.CARD_HOVER}; }}")
        self.header.clicked.connect(self._toggle)
        lay.addWidget(self.header)

        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(8, 6, 4, 4)
        self.body_lay.setSpacing(3)
        self.body.setVisible(expanded)
        lay.addWidget(self.body)

    def _toggle(self):
        on = self.header.isChecked()
        self.header.setArrowType(Qt.DownArrow if on else Qt.RightArrow)
        self.body.setVisible(on)

    def add(self, w: QWidget):
        self.body_lay.addWidget(w)


class VariatorRow(QWidget):
    """One variator's label + typed control. Reports (name → value|None)."""

    changed = pyqtSignal()
    place_requested = pyqtSignal(str)   # STARTLOC name
    clear_requested = pyqtSignal(str)

    def __init__(self, v: S.Variator, parent=None):
        super().__init__(parent)
        self.v = v
        self._value = None            # None = variator absent

        lay = QHBoxLayout(self)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(6)

        # Label (+ verified/inferred marker)
        name = QLabel(v.label)
        name.setToolTip(v.tooltip)
        name.setStyleSheet(f"color: {theme.TEXT}; font-size: 12px;"
                           " background: transparent;")
        name.setMinimumWidth(140)
        lay.addWidget(name)

        mark = QLabel("✓" if v.verified else "•")
        mark.setToolTip("Verified in-game" if v.verified
                        else "Effect inferred from shipped scenarios")
        mark.setStyleSheet(
            f"color: {theme.GOOD if v.verified else theme.FAINT};"
            " font-size: 11px; background: transparent;")
        mark.setFixedWidth(12)
        lay.addWidget(mark)

        lay.addStretch(1)
        self._build_control(lay)

    # ── control construction per kind ───────────────────────
    def _build_control(self, lay):
        v = self.v
        if v.kind == S.KIND_FLAG:
            self.chk = QCheckBox()
            self.chk.setToolTip(v.tooltip)
            self.chk.stateChanged.connect(self._flag_changed)
            lay.addWidget(self.chk)
        elif v.kind == S.KIND_ENUM:
            self.combo = QComboBox()
            self.combo.setToolTip(v.tooltip)
            for val, label in v.options:
                self.combo.addItem(label, val)
            self.combo.setMinimumWidth(150)
            self.combo.currentIndexChanged.connect(self._enum_changed)
            lay.addWidget(self.combo)
        elif v.kind == S.KIND_COORD:
            self.coord_lbl = QLabel("—")
            self.coord_lbl.setStyleSheet(
                f"color: {theme.MUTED}; font-family: monospace; font-size: 11px;"
                " background: transparent;")
            self.coord_lbl.setMinimumWidth(66)
            self.coord_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lay.addWidget(self.coord_lbl)
            place = QPushButton("Place")
            place.setStyleSheet(theme.quiet_button_style())
            place.setToolTip("Click a land tile on the Design map to set this "
                             "start location")
            place.clicked.connect(lambda: self.place_requested.emit(self.v.name))
            lay.addWidget(place)
            clr = QPushButton("✕")
            clr.setFixedWidth(26)
            clr.setStyleSheet(theme.quiet_button_style())
            clr.setToolTip("Clear this start location")
            clr.clicked.connect(self._clear_coord)
            lay.addWidget(clr)
        else:  # level / value / bitmask → enable checkbox + spinbox
            self.enable = QCheckBox()
            self.enable.setToolTip("Include this setting in the scenario")
            self.enable.stateChanged.connect(self._enable_changed)
            lay.addWidget(self.enable)
            self.spin = QSpinBox()
            self.spin.setRange(v.minimum, v.maximum)
            self.spin.setValue(v.default)
            self.spin.setEnabled(False)
            self.spin.setStyleSheet(_SPIN_QSS)
            self.spin.setToolTip(v.tooltip)
            self.spin.valueChanged.connect(self._spin_changed)
            lay.addWidget(self.spin)

    # ── change handlers ─────────────────────────────────────
    def _flag_changed(self, state):
        self._value = self.v.default if state else None
        self.changed.emit()

    def _enum_changed(self, idx):
        val = self.combo.itemData(idx)
        # value 0 (== "none/default") is treated as absent
        self._value = None if not val else int(val)
        self.changed.emit()

    def _enable_changed(self, state):
        self.spin.setEnabled(bool(state))
        self._value = int(self.spin.value()) if state else None
        self.changed.emit()

    def _spin_changed(self, val):
        if self.enable.isChecked():
            self._value = int(val)
            self.changed.emit()

    def _clear_coord(self):
        self._value = None
        self.coord_lbl.setText("—")
        self.clear_requested.emit(self.v.name)
        self.changed.emit()

    # ── external API ────────────────────────────────────────
    def value(self):
        return self._value

    def set_coord_tile(self, row: int, col: int):
        self._value = S.encode_startloc(row, col)
        self.coord_lbl.setText(f"({col}, {row})")
        self.changed.emit()

    def set_value(self, val):
        """Load a value (int) or None (absent) into the control silently."""
        v = self.v
        self._value = None if val is None else int(val)
        block = [w for w in (getattr(self, n, None)
                             for n in ("chk", "combo", "enable", "spin"))
                 if w is not None]
        for w in block:
            w.blockSignals(True)
        if v.kind == S.KIND_FLAG:
            self.chk.setChecked(bool(val))
        elif v.kind == S.KIND_ENUM:
            idx = self.combo.findData(int(val)) if val is not None else \
                self.combo.findData(0)
            if idx < 0 and val is not None:          # unknown value from file
                self.combo.addItem(f"(raw: {val})", int(val))
                idx = self.combo.count() - 1
            self.combo.setCurrentIndex(max(0, idx))
        elif v.kind == S.KIND_COORD:
            if val is None:
                self.coord_lbl.setText("—")
            else:
                row, col = S.decode_startloc(int(val))
                self.coord_lbl.setText(f"({col}, {row})")
        else:
            on = val is not None
            self.enable.setChecked(on)
            self.spin.setEnabled(on)
            if on:
                self.spin.setValue(int(val))
        for w in block:
            w.blockSignals(False)


class ScenarioPanel(QWidget):
    """Full scenario-rules editor for the current slot."""

    changed = pyqtSignal()
    place_startloc = pyqtSignal(str)          # arm canvas for this STARTLOC
    startlocs_changed = pyqtSignal(dict)      # {name: (row, col)} for canvas

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.rows: dict[str, VariatorRow] = {}
        self._meta = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header strip
        head = QWidget()
        head.setStyleSheet(f"background: {theme.PANEL};"
                           f" border-bottom: 1px solid {theme.LINE};")
        hl = QVBoxLayout(head)
        hl.setContentsMargins(16, 10, 16, 10)
        hl.setSpacing(3)
        self.title = QLabel("Scenario Rules")
        self.title.setStyleSheet(f"color: {theme.TEXT}; font-size: 15px;"
                                 " font-weight: 600; background: transparent;")
        hl.addWidget(self.title)
        self.subtitle = QLabel("")
        self.subtitle.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px;"
                                    " background: transparent;")
        self.subtitle.setWordWrap(True)
        hl.addWidget(self.subtitle)
        outer.addWidget(head)

        # Scrollable grouped body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background: {theme.BG}; border: none;")
        body = QWidget()
        self.body_lay = QVBoxLayout(body)
        self.body_lay.setContentsMargins(16, 12, 16, 12)
        self.body_lay.setSpacing(8)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._build_groups()

        # Validation strip
        self.validation_wrap = QVBoxLayout()
        self.validation_wrap.setSpacing(4)
        self.body_lay.addLayout(self.validation_wrap)
        self.body_lay.addStretch(1)

    def _build_groups(self):
        expanded = {"Starting conditions", "Victory"}
        for cat in S.CATEGORIES:
            vs = S.by_category(cat)
            if not vs:
                continue
            sec = Collapsible(cat, expanded=cat in expanded)
            for v in vs:
                row = VariatorRow(v)
                row.changed.connect(self._on_changed)
                row.place_requested.connect(self.place_startloc.emit)
                row.clear_requested.connect(lambda _n: self._emit_startlocs())
                self.rows[v.name] = row
                sec.add(row)
                sec.add(self._divider())
            self.body_lay.addWidget(sec)

    def _divider(self) -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        f.setFixedHeight(1)
        f.setStyleSheet(f"background: {theme.LINE}; border: none;")
        return f

    # ── data in/out ─────────────────────────────────────────
    def set_slot(self, title: str, meta: dict, values: dict):
        self._meta = meta
        et = meta.get("type", "?")
        self.title.setText(f"Scenario Rules — {title}")
        self.subtitle.setText(
            f"Entry {meta.get('id','?')} · {et} · "
            + ("multiplayer" if meta.get("mp") == "1" else "single-player")
            + ".  Advanced starts (STARTSIZE / STARTLOC) need a Start year set."
        )
        for name, row in self.rows.items():
            row.set_value(values.get(name))
        self._on_changed()

    def get_values(self) -> dict:
        out = {}
        for name, row in self.rows.items():
            val = row.value()
            if val is not None:
                out[name] = int(val)
        return out

    def startloc_markers(self) -> dict:
        out = {}
        for name in S.STARTLOC_NAMES:
            val = self.rows[name].value()
            if val is not None and S.startloc_is_valid(val):
                out[name] = S.decode_startloc(val)
        return out

    def apply_startloc(self, name: str, row: int, col: int):
        self.rows[name].set_coord_tile(row, col)
        self._emit_startlocs()

    # ── reactions ───────────────────────────────────────────
    def _on_changed(self):
        self._update_validation()
        self._emit_startlocs()
        self.changed.emit()

    def _emit_startlocs(self):
        self.startlocs_changed.emit(self.startloc_markers())

    def _update_validation(self):
        while self.validation_wrap.count():
            item = self.validation_wrap.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        issues = S.validate(self.get_values(), fixed_map=True, model=self.model)
        for status, msg in issues:
            self.validation_wrap.addWidget(ValidationRow(status, msg))
