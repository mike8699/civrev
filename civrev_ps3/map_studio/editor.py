"""Main window: layout, menus, panels, and build orchestration."""

from pathlib import Path

import build as build_mod
import theme
from canvas import TOOL_HINTS, MapCanvas
from model import DLC_SLOTS, GRID, TERRAIN_NAMES, MapModel
from newmap import NewMapDialog
from preview import SettingsDialog, TexturePreviewDialog
from PyQt5.QtCore import QSize, Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from settings import Settings
from widgets import (
    MinimapWidget,
    SectionLabel,
    StatRow,
    Toast,
    ValidationRow,
    color_swatch,
    tool_icon,
)

TOOL_DEFS = [
    ("brush", "Brush", "B"),
    ("fill", "Fill", "F"),
    ("line", "Line", "L"),
    ("rect", "Rectangle", "T"),
    ("river", "River", "R"),
    ("spawn", "Spawn", "S"),
    ("eraser", "Eraser", "E"),
    ("picker", "Eyedropper", "I"),
]


def _separator() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {theme.LINE}; border: none;")
    return f


class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.model = MapModel()
        self.current_slot = 0
        self.source_label = ""
        self.build_worker = None
        self.scene_worker = None
        self._scene_stale = True
        self._scene_pending = False
        self._scene_timer = QTimer(self)
        self._scene_timer.setSingleShot(True)
        self._scene_timer.setInterval(350)
        self._scene_timer.timeout.connect(self._refresh_scene)

        self.setWindowTitle("CivRev Map Studio")
        self.setMinimumSize(1150, 720)
        self.resize(1360, 860)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._load_slot(0, confirm=False)

    # ══════════════════════════ UI ══════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left_panel())

        self.canvas = MapCanvas(self.model)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        scroll.setAlignment(Qt.AlignCenter)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {theme.BG}; border: none; }}")
        self.canvas.scroll_area = scroll
        self.scroll_area = scroll

        self.center_tabs = QTabWidget()
        self.center_tabs.setDocumentMode(True)
        self.center_tabs.addTab(scroll, "Design")
        self.center_tabs.addTab(self._build_preview3d(), "In-Game Preview")
        self.center_tabs.currentChanged.connect(self._tab_changed)
        root.addWidget(self.center_tabs, 1)

        root.addWidget(self._build_right_panel())

        # Status bar
        self.status_coord = QLabel("(—, —)")
        self.status_coord.setFixedWidth(76)
        self.status_coord.setStyleSheet(
            f"font-family: monospace; color: {theme.TEXT};")
        self.status_info = QLabel("")
        self.status_info.setMinimumWidth(220)
        self.status_hint = QLabel(TOOL_HINTS["brush"])
        self.status_hint.setStyleSheet(f"color: {theme.FAINT};")
        self.status_zoom = QLabel("")
        self.status_zoom.setStyleSheet("font-family: monospace;")
        self.status_zoom.setMinimumWidth(84)
        self.status_zoom.setAlignment(Qt.AlignRight)

        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        sb.addWidget(self.status_coord)
        sb.addWidget(self.status_info)
        sb.addWidget(QLabel(" "), 1)
        sb.addWidget(self.status_hint)
        sb.addPermanentWidget(self.status_zoom)
        self.setStatusBar(sb)

        self.minimap = MinimapWidget(self.canvas, parent=scroll)
        self.minimap.move(12, 12)
        self.minimap.raise_()

        self.toast = Toast(self)

    # ── Left panel: tools + terrain ─────────────────────────

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(228)
        panel.setStyleSheet(
            f"background: {theme.PANEL}; border-right: 1px solid {theme.LINE};")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(7)

        lay.addWidget(SectionLabel("Tools"))
        grid = QGridLayout()
        grid.setSpacing(5)
        self.tool_buttons = {}
        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)
        for i, (name, label, key) in enumerate(TOOL_DEFS):
            btn = QToolButton()
            btn.setIcon(tool_icon(name))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(f"{label}  ({key})")
            btn.setCheckable(True)
            btn.setFixedSize(44, 40)
            btn.setStyleSheet(theme.tool_button_style())
            btn.clicked.connect(lambda _, n=name: self.set_tool(n))
            self.tool_group.addButton(btn)
            self.tool_buttons[name] = btn
            grid.addWidget(btn, i // 4, i % 4)
        self.tool_buttons["brush"].setChecked(True)
        lay.addLayout(grid)

        lay.addWidget(SectionLabel("Brush size"))
        size_row = QHBoxLayout()
        size_row.setSpacing(5)
        self.size_buttons = {}
        self.size_group = QButtonGroup(self)
        self.size_group.setExclusive(True)
        for sz in (1, 3, 5):
            btn = QToolButton()
            btn.setText(f"{sz}")
            btn.setToolTip(f"{sz}×{sz} brush  ([ and ] to change)")
            btn.setCheckable(True)
            btn.setFixedSize(44, 28)
            btn.setStyleSheet(theme.tool_button_style())
            btn.clicked.connect(lambda _, s=sz: self.set_brush_size(s))
            self.size_group.addButton(btn)
            self.size_buttons[sz] = btn
            size_row.addWidget(btn)
        size_row.addStretch()
        self.size_buttons[1].setChecked(True)
        lay.addLayout(size_row)

        lay.addWidget(_separator())
        lay.addWidget(SectionLabel("Terrain"))
        self.terrain_buttons = {}
        self.terrain_group = QButtonGroup(self)
        self.terrain_group.setExclusive(True)
        for i, name in enumerate(TERRAIN_NAMES):
            btn = QPushButton()
            _, light, _ = theme.TERRAIN_COLORS[i]
            btn.setIcon(QIcon(color_swatch(light)))
            btn.setIconSize(QSize(16, 16))
            btn.setText(f" {name}")
            btn.setCheckable(True)
            btn.setFixedHeight(27)
            btn.setStyleSheet(theme.terrain_button_style())
            btn.setToolTip(f"{name} — press {i}")
            btn.clicked.connect(lambda _, idx=i: self.set_terrain(idx))
            self.terrain_group.addButton(btn)
            self.terrain_buttons[i] = btn

            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(0)
            row.addWidget(btn, 1)
            count = QLabel("0")
            count.setFixedWidth(34)
            count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            count.setStyleSheet(
                f"color: {theme.FAINT}; font-family: monospace;"
                "font-size: 10px; background: transparent;")
            row.addWidget(count)
            btn.count_label = count
            w = QWidget()
            w.setLayout(row)
            w.setStyleSheet("background: transparent;")
            lay.addWidget(w)
        self.terrain_buttons[1].setChecked(True)

        lay.addStretch()
        return panel

    # ── 3D in-game preview tab ──────────────────────────────

    def _build_preview3d(self) -> QWidget:
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.preview3d = None
        try:
            from gl_preview import Preview3DWidget

            self.preview3d = Preview3DWidget()
            lay.addWidget(self.preview3d, 1)
        except Exception as e:                     # GL missing entirely
            err = QLabel(
                f"3D preview unavailable:\n{e}")
            err.setAlignment(Qt.AlignCenter)
            err.setStyleSheet(f"color: {theme.MUTED};")
            lay.addWidget(err, 1)
            return container

        hud = QLabel(
            "Drag orbit · Wheel zoom · Shift+drag pan · Double-click reset")
        hud.setParent(self.preview3d)
        hud.setStyleSheet(
            f"background: rgba(13,15,22,0.72); color: {theme.MUTED};"
            "border-radius: 5px; padding: 5px 10px; font-size: 11px;")
        hud.adjustSize()
        hud.move(12, 12)
        self._scene_status = QLabel("", self.preview3d)
        self._scene_status.setStyleSheet(
            f"background: rgba(13,15,22,0.72); color: {theme.ACCENT};"
            "border-radius: 5px; padding: 5px 10px; font-size: 11px;")
        self._scene_status.hide()
        return container

    def _tab_changed(self, idx):
        if idx == 1:
            self.status_hint.setText(
                "In-game preview — edits in Design update it live")
            if self._scene_stale:
                self._refresh_scene()
        else:
            self.status_hint.setText(TOOL_HINTS.get(self.canvas.tool, ""))

    def _mark_scene_stale(self):
        self._scene_stale = True
        if self.preview3d is not None and self.center_tabs.currentIndex() == 1:
            self._scene_timer.start()

    def _refresh_scene(self):
        if self.preview3d is None or self.preview3d.gl_error:
            return
        if self.scene_worker and self.scene_worker.isRunning():
            self._scene_pending = True
            return
        self._scene_status.setText("Rendering textures…")
        self._scene_status.adjustSize()
        self._scene_status.move(
            self.preview3d.width() - self._scene_status.width() - 12, 12)
        self._scene_status.show()
        self.scene_worker = build_mod.SceneWorker(
            self.model.snapshot(), self.current_slot, self.settings,
            self.smart_check.isChecked(), parent=self)
        self.scene_worker.ready.connect(self._scene_ready)
        self.scene_worker.failed.connect(self._scene_failed)
        self.scene_worker.start()

    def _scene_ready(self, scene):
        self._scene_stale = False
        self._scene_status.hide()
        if self.preview3d is not None:
            self.preview3d.set_scene(scene)
        if self._scene_pending:
            self._scene_pending = False
            self._refresh_scene()

    def _scene_failed(self, err):
        self._scene_status.hide()
        self.toast.show_message(f"Preview update failed: {err}")

    # ── Right panel: inspect / stats / validate / build ─────

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(272)
        panel.setStyleSheet(
            f"background: {theme.PANEL}; border-left: 1px solid {theme.LINE};")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(7)

        lay.addWidget(SectionLabel("Selected tile"))
        insp = QGridLayout()
        insp.setSpacing(3)
        insp.setColumnMinimumWidth(0, 66)
        self.insp_labels = {}
        for i, key in enumerate(
                ["Position", "Terrain", "Rivers", "Spawn", "Byte"]):
            k = QLabel(key)
            k.setStyleSheet(
                f"color: {theme.MUTED}; font-size: 11px; background: transparent;")
            v = QLabel("—")
            v.setStyleSheet(
                f"color: {theme.TEXT}; font-family: monospace; font-size: 11px;"
                "background: transparent;")
            insp.addWidget(k, i, 0)
            insp.addWidget(v, i, 1)
            self.insp_labels[key] = v
        lay.addLayout(insp)

        self.river_checks = {}
        river_row = QHBoxLayout()
        river_row.setSpacing(8)
        for flag, label in [("west", "W"), ("east", "E"), ("south", "S")]:
            cb = QCheckBox(label)
            cb.setToolTip(f"River on {flag} edge of the selected tile")
            cb.stateChanged.connect(
                lambda state, f=flag: self._toggle_river_flag(f, bool(state)))
            self.river_checks[flag] = cb
            river_row.addWidget(cb)
        river_row.addStretch()
        river_lbl = QLabel("River edges:")
        river_lbl.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 11px; background: transparent;")
        lay.addWidget(river_lbl)
        lay.addLayout(river_row)

        lay.addWidget(_separator())
        lay.addWidget(SectionLabel("Map"))
        self.stat_rows = {}
        for name, color, mx in [
            ("Land", theme.GOOD, GRID * GRID),
            ("Ocean", "#2278b0", GRID * GRID),
            ("Rivers (land)", theme.RIVER, 128),
            ("Spawns", theme.SPAWN, 16),
        ]:
            row = StatRow(name, color, mx)
            self.stat_rows[name] = row
            lay.addWidget(row)

        lay.addWidget(_separator())
        lay.addWidget(SectionLabel("Checks"))
        self.validation_box = QVBoxLayout()
        self.validation_box.setSpacing(4)
        lay.addLayout(self.validation_box)

        lay.addStretch()
        lay.addWidget(_separator())
        lay.addWidget(SectionLabel("Build target"))

        self.slot_combo = QComboBox()
        for s in DLC_SLOTS:
            self.slot_combo.addItem(f"{s['title']}  (DLC {s['id']})")
        self.slot_combo.currentIndexChanged.connect(self._slot_combo_changed)
        lay.addWidget(self.slot_combo)

        self.smart_check = QCheckBox("Smart patch (keep original art)")
        self.smart_check.setToolTip(
            "Unchanged tiles keep the original textures; edited tiles get\n"
            "matching art harvested from the four original DLC maps.")
        self.smart_check.setChecked(self.settings.smart_patch)
        self.smart_check.stateChanged.connect(self._smart_patch_toggled)
        lay.addWidget(self.smart_check)

        self.install_check = QCheckBox("Install to RPCS3 after build")
        self.install_check.setChecked(self.settings.install_after_build)
        self.install_check.stateChanged.connect(
            lambda s: setattr(self.settings, "install_after_build", bool(s)))
        lay.addWidget(self.install_check)

        self.build_btn = QPushButton("Build && Install")
        self.build_btn.setFixedHeight(38)
        self.build_btn.setStyleSheet(theme.primary_button_style())
        self.build_btn.clicked.connect(self.do_build)
        lay.addWidget(self.build_btn)

        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.setToolTip("Render the textures a build would produce")
        self.preview_btn.setStyleSheet(theme.quiet_button_style())
        self.preview_btn.clicked.connect(self.show_preview)
        row2.addWidget(self.preview_btn)
        self.restore_btn = QPushButton("Restore original")
        self.restore_btn.setToolTip(
            "Copy this slot's pristine files from Pak9_original back into Pak9")
        self.restore_btn.setStyleSheet(theme.quiet_button_style())
        self.restore_btn.clicked.connect(self.restore_original)
        row2.addWidget(self.restore_btn)
        lay.addLayout(row2)

        self.build_step = QLabel("")
        self.build_step.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 11px; background: transparent;")
        self.build_step.setWordWrap(True)
        self.build_step.hide()
        lay.addWidget(self.build_step)
        self.build_bar = QProgressBar()
        self.build_bar.setFixedHeight(5)
        self.build_bar.setTextVisible(False)
        self.build_bar.setRange(0, 100)
        self.build_bar.hide()
        lay.addWidget(self.build_bar)

        return panel

    # ── Menus ───────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        m_file = mb.addMenu("&File")
        self._add_action(m_file, "New Map…", "Ctrl+N", self.new_map)
        load_menu = m_file.addMenu("Load Slot")
        for i, s in enumerate(DLC_SLOTS):
            self._add_action(load_menu, s["title"], None,
                             lambda checked=False, idx=i: self._load_slot(idx))
        self._add_action(m_file, "Import .map…", "Ctrl+I", self.import_map)
        m_file.addSeparator()
        self._add_action(m_file, "Save to Slot", "Ctrl+S", self.save_map)
        self._add_action(m_file, "Export .map As…", "Ctrl+Shift+S",
                         self.export_map)
        self._add_action(m_file, "Export Map Image…", None, self.export_png)
        m_file.addSeparator()
        self._add_action(m_file, "Build && Install", "Ctrl+B", self.do_build)
        self._add_action(m_file, "Build to Folder…", None, self.build_to_folder)
        m_file.addSeparator()
        self._add_action(m_file, "Settings…", None, self.show_settings)
        m_file.addSeparator()
        self._add_action(m_file, "Quit", "Ctrl+Q", self.close)

        m_edit = mb.addMenu("&Edit")
        self._add_action(m_edit, "Undo", "Ctrl+Z",
                         lambda: self.canvas.undo() or self.toast.show_message(
                             "Nothing to undo"))
        self._add_action(m_edit, "Redo", "Ctrl+Y",
                         lambda: self.canvas.redo() or self.toast.show_message(
                             "Nothing to redo"))
        m_edit.addSeparator()
        self._add_action(m_edit, "Clear Map", None, self.clear_map)
        self._add_action(m_edit, "Mirror Left↔Right", None,
                         lambda: self._whole_map_op("mirror_horizontal"))
        self._add_action(m_edit, "Mirror Top↕Bottom", None,
                         lambda: self._whole_map_op("mirror_vertical"))
        shift_menu = m_edit.addMenu("Shift Map")
        for label, dr, dc in [("Up", -1, 0), ("Down", 1, 0),
                              ("Left", 0, -1), ("Right", 0, 1)]:
            self._add_action(
                shift_menu, label, None,
                lambda checked=False, a=dr, b=dc: self._whole_map_op(
                    "shift", a, b))

        m_view = mb.addMenu("&View")
        self._add_action(m_view, "Toggle Design / In-Game Preview", "P",
                         self.toggle_preview_tab)
        m_view.addSeparator()
        self._add_action(m_view, "Toggle Grid", "G", self.toggle_grid)
        self._add_action(m_view, "Toggle Polar Guides", None,
                         self.toggle_guides)
        m_view.addSeparator()
        self._add_action(m_view, "Zoom In", "Ctrl+=",
                         lambda: self.canvas.set_tile_size(
                             self.canvas.tile_size * 1.2))
        self._add_action(m_view, "Zoom Out", "Ctrl+-",
                         lambda: self.canvas.set_tile_size(
                             self.canvas.tile_size / 1.2))
        self._add_action(m_view, "Fit Map", "Ctrl+0", self.zoom_fit)

        m_help = mb.addMenu("&Help")
        self._add_action(m_help, "Quickstart", "F1", self.show_quickstart)
        self._add_action(m_help, "About", None, self.show_about)

    def _add_action(self, menu, text, shortcut, slot):
        act = QAction(text, self)
        if shortcut:
            act.setShortcut(QKeySequence(shortcut))
        act.triggered.connect(slot)
        menu.addAction(act)
        return act

    # ── Signals ─────────────────────────────────────────────

    def _connect_signals(self):
        self.canvas.tile_hovered.connect(self._on_hover)
        self.canvas.tile_unhovered.connect(self._on_unhover)
        self.canvas.tile_clicked.connect(self._on_tile_clicked)
        self.canvas.map_changed.connect(self._on_map_changed)
        self.canvas.terrain_picked.connect(self._on_terrain_picked)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)

    # ══════════════════════ Interaction ═════════════════════

    def _smart_patch_toggled(self, state):
        self.settings.smart_patch = bool(state)
        self._mark_scene_stale()

    def set_tool(self, name):
        self.canvas.tool = name
        self.tool_buttons[name].setChecked(True)
        self.status_hint.setText(TOOL_HINTS.get(name, ""))

    def set_terrain(self, idx):
        self.canvas.terrain = idx
        self.terrain_buttons[idx].setChecked(True)
        if self.canvas.tool not in ("brush", "fill", "line", "rect", "eraser"):
            self.set_tool("brush")

    def set_brush_size(self, size):
        self.canvas.brush_size = size
        self.size_buttons[size].setChecked(True)

    def _on_terrain_picked(self, idx):
        self.set_terrain(idx)
        self.set_tool("brush")
        self.toast.show_message(f"Picked {TERRAIN_NAMES[idx]}")

    def _on_hover(self, row, col):
        self.status_coord.setText(f"({col}, {row})")
        t = self.model.get_terrain(row, col)
        rivers = self.model.get_rivers(row, col)
        rstr = "+".join(k[0].upper() for k, v in rivers.items() if v)
        info = TERRAIN_NAMES[t]
        if rstr:
            info += f" · river {rstr}"
        if self.model.has_spawn(row, col):
            info += " · spawn"
        self.status_info.setText(info)

    def _on_unhover(self):
        self.status_coord.setText("(—, —)")
        self.status_info.setText("")

    def _on_tile_clicked(self, row, col):
        self._update_inspector(row, col)

    def _on_zoom_changed(self, ts):
        self.status_zoom.setText(f"{ts:.0f} px/tile")

    def _on_map_changed(self):
        self._update_stats()
        self._update_validation()
        self._update_title()
        self.minimap.update()
        self._mark_scene_stale()
        if self.canvas.selected:
            self._update_inspector(*self.canvas.selected)

    def keyPressEvent(self, event):
        text = event.text().lower()
        if not event.modifiers():
            tools = {key.lower(): name for name, _, key in TOOL_DEFS}
            if text in tools:
                self.set_tool(tools[text])
                return
            if text.isdigit() and int(text) <= 7:
                self.set_terrain(int(text))
                return
            if text == "[":
                sizes = [1, 3, 5]
                i = sizes.index(self.canvas.brush_size)
                self.set_brush_size(sizes[max(0, i - 1)])
                return
            if text == "]":
                sizes = [1, 3, 5]
                i = sizes.index(self.canvas.brush_size)
                self.set_brush_size(sizes[min(2, i + 1)])
                return
        super().keyPressEvent(event)

    # ── Inspector / stats / validation ──────────────────────

    def _update_inspector(self, row, col):
        byte = self.model.get_tile(row, col)
        t = byte & 0x07
        rivers = self.model.get_rivers(row, col)
        rstr = "+".join(k[0].upper() for k, v in rivers.items() if v) or "none"
        self.insp_labels["Position"].setText(
            f"({col}, {row})  file 0x{col * GRID + row:03x}")
        lbl = self.insp_labels["Terrain"]
        lbl.setText(TERRAIN_NAMES[t])
        _, light, _ = theme.TERRAIN_COLORS[t]
        lbl.setStyleSheet(
            f"color: {light}; font-family: monospace; font-size: 11px;"
            "background: transparent;")
        self.insp_labels["Rivers"].setText(rstr)
        self.insp_labels["Spawn"].setText(
            "yes" if byte & 0x10 else "no")
        self.insp_labels["Byte"].setText(f"0x{byte:02x}")
        for flag, cb in self.river_checks.items():
            cb.blockSignals(True)
            cb.setChecked(rivers[flag])
            cb.blockSignals(False)

    def _toggle_river_flag(self, flag, on):
        if not self.canvas.selected:
            self.toast.show_message("Click a tile first")
            return
        r, c = self.canvas.selected
        self.canvas.push_undo()
        self.model.set_river(r, c, flag, on)
        self.canvas.update()
        self.canvas.map_changed.emit()

    def _update_stats(self):
        s = self.model.stats()
        self.stat_rows["Land"].set_value(s["land"])
        self.stat_rows["Ocean"].set_value(s["ocean"])
        self.stat_rows["Rivers (land)"].set_value(s["land_rivers"])
        self.stat_rows["Spawns"].set_value(s["spawns"])
        for i in range(8):
            self.terrain_buttons[i].count_label.setText(
                str(s["terrain_counts"][i]))

    def _update_validation(self):
        while self.validation_box.count():
            item = self.validation_box.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        for status, msg in self.model.validate():
            self.validation_box.addWidget(ValidationRow(status, msg))

    def _update_title(self):
        slot = DLC_SLOTS[self.current_slot]
        star = " •" if self.model.dirty else ""
        src = f" — {self.source_label}" if self.source_label else ""
        self.setWindowTitle(
            f"CivRev Map Studio — {slot['title']}{src}{star}")

    # ══════════════════════ File actions ════════════════════

    def _confirm_discard(self, what="switching maps") -> bool:
        if not self.model.dirty:
            return True
        resp = QMessageBox.question(
            self, "Unsaved changes",
            f"The current map has unsaved edits. Discard them and continue "
            f"{what}?",
            QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Cancel)
        return resp == QMessageBox.Discard

    def _slot_combo_changed(self, idx):
        if idx == self.current_slot:
            return
        if not self._confirm_discard():
            self.slot_combo.blockSignals(True)
            self.slot_combo.setCurrentIndex(self.current_slot)
            self.slot_combo.blockSignals(False)
            return
        self._load_slot(idx, confirm=False)

    def _load_slot(self, idx, confirm=True):
        if confirm and not self._confirm_discard():
            return
        self.current_slot = idx
        self.slot_combo.blockSignals(True)
        self.slot_combo.setCurrentIndex(idx)
        self.slot_combo.blockSignals(False)
        slot = DLC_SLOTS[idx]
        path = self.settings.pak9_dir / slot["file"]
        if path.exists():
            self.canvas.undo_stack.clear()
            self.canvas.redo_stack.clear()
            self.model.load_file(path)
            self.source_label = ""
            self.canvas.selected = None
            self.canvas.update()
            self._on_map_changed()
            self.toast.show_message(f"Loaded {slot['title']} from Pak9")
        else:
            self.toast.show_message(f"Missing: {path}")

    def new_map(self):
        if not self._confirm_discard("creating a new map"):
            return
        dlg = NewMapDialog(self.settings.pak9_original_dir, parent=self)
        if dlg.exec_() and dlg.result_data is not None:
            self.canvas.push_undo()
            self.model.data[:] = dlg.result_data
            self.model.dirty = True
            self.source_label = dlg.result_label
            self.canvas.selected = None
            self.canvas.update()
            self._on_map_changed()
            self.toast.show_message(
                f"{dlg.result_label} — will build into "
                f"{DLC_SLOTS[self.current_slot]['title']}")

    def import_map(self):
        if not self._confirm_discard("importing"):
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Import .map", str(self.settings.pak9_dir),
            "Map Files (*.map);;All Files (*)")
        if path:
            try:
                self.model.load_file(Path(path))
            except (OSError, ValueError) as e:
                QMessageBox.critical(self, "Import failed", str(e))
                return
            self.model.dirty = True
            self.source_label = Path(path).name
            self.canvas.update()
            self._on_map_changed()

    def save_map(self):
        slot = DLC_SLOTS[self.current_slot]
        path = self.settings.pak9_dir / slot["file"]
        try:
            self.model.save_file(path)
        except OSError as e:
            QMessageBox.critical(self, "Save failed", str(e))
            return
        self._update_title()
        self.toast.show_message(
            f"Saved {path.name} — use Build && Install to update the game")

    def export_map(self):
        slot = DLC_SLOTS[self.current_slot]
        path, _ = QFileDialog.getSaveFileName(
            self, "Export .map", slot["file"],
            "Map Files (*.map);;All Files (*)")
        if path:
            was_dirty = self.model.dirty
            self.model.save_file(Path(path))
            self.model.dirty = was_dirty
            self.toast.show_message(f"Exported {Path(path).name}")

    def export_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Map Image", "map.png", "PNG Images (*.png)")
        if path:
            pm = QPixmap(self.canvas.size())
            self.canvas.render(pm)
            pm.save(path, "PNG")
            self.toast.show_message(f"Exported {Path(path).name}")

    def clear_map(self):
        self.canvas.push_undo()
        self.model.clear()
        self.canvas.update()
        self._on_map_changed()

    def _whole_map_op(self, name, *args):
        self.canvas.push_undo()
        getattr(self.model, name)(*args)
        self.canvas.update()
        self._on_map_changed()

    # ══════════════════════ Build actions ═══════════════════

    def do_build(self):
        self._start_build(export_dir=None)

    def build_to_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Export build to folder", str(Path.home()))
        if path:
            self._start_build(export_dir=Path(path))

    def _start_build(self, export_dir):
        if self.build_worker and self.build_worker.isRunning():
            self.toast.show_message("A build is already running")
            return
        fails = [m for s, m in self.model.validate() if s == "fail"]
        if fails:
            resp = QMessageBox.warning(
                self, "Map has problems",
                "This map will not play correctly:\n\n• "
                + "\n• ".join(fails) + "\n\nBuild anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if resp != QMessageBox.Yes:
                return

        self.save_map()
        self.build_btn.setEnabled(False)
        self.build_step.show()
        self.build_bar.show()
        self.build_bar.setValue(0)

        self.build_worker = build_mod.BuildWorker(
            self.model.snapshot(), self.current_slot, self.settings,
            install=self.install_check.isChecked() and export_dir is None,
            smart_patch=self.smart_check.isChecked(),
            export_dir=export_dir, parent=self)
        self.build_worker.step_changed.connect(self.build_step.setText)
        self.build_worker.progress.connect(self.build_bar.setValue)
        self.build_worker.finished_ok.connect(self._build_done)
        self.build_worker.failed.connect(self._build_failed)
        self.build_worker.start()

    def _build_done(self, msg):
        self.build_btn.setEnabled(True)
        self.build_step.setText("")
        self.build_step.hide()
        self.build_bar.hide()
        self.toast.show_message(msg, msec=6000)

    def _build_failed(self, err):
        self.build_btn.setEnabled(True)
        self.build_step.hide()
        self.build_bar.hide()
        QMessageBox.critical(self, "Build failed", err)

    def show_preview(self):
        dlg = TexturePreviewDialog(
            self.model.snapshot(), self.current_slot, self.settings,
            self.smart_check.isChecked(), parent=self)
        dlg.exec_()

    def restore_original(self):
        slot = DLC_SLOTS[self.current_slot]
        resp = QMessageBox.question(
            self, "Restore original",
            f"Copy the pristine {slot['title']} files from Pak9_original "
            "back into Pak9 and reload?\n\nYour edits to this slot will be "
            "lost.",
            QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Cancel)
        if resp != QMessageBox.Yes:
            return
        try:
            msg = build_mod.restore_slot(self.settings, self.current_slot)
        except (OSError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Restore failed", str(e))
            return
        self.model.dirty = False
        self._load_slot(self.current_slot, confirm=False)
        self.toast.show_message(msg)

    # ══════════════════════ View / misc ═════════════════════

    def toggle_preview_tab(self):
        self.center_tabs.setCurrentIndex(
            1 - self.center_tabs.currentIndex())

    def toggle_grid(self):
        self.canvas.show_grid = not self.canvas.show_grid
        self.canvas.update()

    def toggle_guides(self):
        self.canvas.show_guides = not self.canvas.show_guides
        self.canvas.update()

    def zoom_fit(self):
        vp = self.scroll_area.viewport()
        self.canvas.fit_to_area(vp.width(), vp.height())

    def show_settings(self):
        dlg = SettingsDialog(self.settings, parent=self)
        dlg.exec_()

    def show_quickstart(self):
        QMessageBox.information(
            self, "Quickstart",
            "<b>CivRev Map Studio</b> edits the four PS3 DLC map slots."
            "<ol>"
            "<li>Pick a <b>build target</b> slot (right panel) — your map "
            "replaces that DLC map in-game.</li>"
            "<li>Paint terrain with the <b>brush</b> (B). Right-click picks "
            "the terrain under the cursor. 1–7 select terrain, [ ] change "
            "brush size.</li>"
            "<li>Add <b>rivers</b> (R) by clicking tile edges — the game "
            "needs rivers on land or settlers spawn on ice.</li>"
            "<li><b>Preview</b> shows the textures a build will produce. "
            "<b>Smart patch</b> keeps original art wherever you didn't "
            "edit.</li>"
            "<li><b>Build &amp; Install</b> (Ctrl+B) regenerates textures, "
            "repacks Pak9, and installs to RPCS3.</li>"
            "</ol>"
            "<p>In-game: Single Player → Scenarios → your slot's name.</p>")

    def show_about(self):
        QMessageBox.about(
            self, "About",
            "<b>CivRev Map Studio</b><br>"
            "Map editor for Civilization Revolution (PS3) DLC maps.<br><br>"
            "Formats verified against the game binary — see "
            "MAP_EDITOR_APPROACH.md in the repo root.")

    # ── Window lifecycle ────────────────────────────────────

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.zoom_fit)

    def closeEvent(self, event):
        if self.build_worker and self.build_worker.isRunning():
            self.toast.show_message("Waiting for build to finish…")
            self.build_worker.wait(15000)
        if self.scene_worker and self.scene_worker.isRunning():
            self.scene_worker.wait(5000)
        if self.model.dirty:
            resp = QMessageBox.question(
                self, "Unsaved changes",
                "Save the current map to its slot before quitting?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save)
            if resp == QMessageBox.Cancel:
                event.ignore()
                return
            if resp == QMessageBox.Save:
                self.save_map()
        event.accept()
