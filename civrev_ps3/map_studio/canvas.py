"""Interactive 32x32 map canvas: painting tools, pan/zoom, rendering."""

import math

import theme
from model import GRID, MapModel
from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget

TOOL_HINTS = {
    "brush": "Paint terrain — drag to stroke, right-click to pick a color",
    "fill": "Fill a connected region with the selected terrain",
    "line": "Drag to draw a straight line of terrain",
    "rect": "Drag to fill a rectangle of terrain",
    "river": "Click a tile edge to toggle a river — drag to paint along edges",
    "spawn": "Click to toggle a multiplayer spawn marker",
    "eraser": "Paint ocean — drag to stroke",
    "picker": "Click a tile to pick its terrain",
}


class MapCanvas(QWidget):
    tile_hovered = pyqtSignal(int, int)
    tile_unhovered = pyqtSignal()
    tile_clicked = pyqtSignal(int, int)
    map_changed = pyqtSignal()
    terrain_picked = pyqtSignal(int)
    zoom_changed = pyqtSignal(float)

    MIN_TILE = 10
    MAX_TILE = 72

    def __init__(self, model: MapModel, parent=None):
        super().__init__(parent)
        self.model = model
        self.tile_size = 24.0
        self.show_grid = True
        self.show_guides = True

        self.tool = "brush"
        self.terrain = 1
        self.brush_size = 1          # 1, 3, or 5 tiles across

        self.hovered = None          # (row, col)
        self.hover_edge = None       # (row, col, flag) for river tool
        self.selected = None
        self.painting = False
        self.shape_start = None
        self._last_edge = None
        self._panning = False
        self._pan_origin = None
        self._space_down = False

        self.scroll_area = None      # set by the editor window

        self.undo_stack = []
        self.redo_stack = []

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._update_size()

    # ── Geometry ────────────────────────────────────────────

    def _update_size(self):
        s = int(GRID * self.tile_size)
        self.setFixedSize(s, s)

    def set_tile_size(self, ts: float, anchor=None):
        """Set zoom; keep `anchor` (widget pos) stationary in the viewport."""
        ts = max(self.MIN_TILE, min(self.MAX_TILE, ts))
        if ts == self.tile_size:
            return
        ratio = ts / self.tile_size
        old_pos = anchor
        self.tile_size = ts
        self._update_size()
        if self.scroll_area and old_pos is not None:
            hbar = self.scroll_area.horizontalScrollBar()
            vbar = self.scroll_area.verticalScrollBar()
            hbar.setValue(int(old_pos.x() * ratio - (old_pos.x() - hbar.value())))
            vbar.setValue(int(old_pos.y() * ratio - (old_pos.y() - vbar.value())))
        self.update()
        self.zoom_changed.emit(self.tile_size)

    def fit_to_area(self, w: int, h: int):
        margin = 48
        ts = min(w - margin, h - margin) / GRID
        self.tile_size = max(self.MIN_TILE, min(self.MAX_TILE, ts))
        self._update_size()
        self.update()
        self.zoom_changed.emit(self.tile_size)

    def _tile_at(self, pos):
        ts = self.tile_size
        col = int(pos.x() // ts)
        row = int(pos.y() // ts)
        if 0 <= row < GRID and 0 <= col < GRID:
            return (row, col)
        return None

    def _edge_at(self, pos):
        """Nearest river edge to a mouse position.

        A tile stores west/east/south flags; its north edge is the south flag
        of the tile above.
        """
        tile = self._tile_at(pos)
        if not tile:
            return None
        r, c = tile
        ts = self.tile_size
        fx = (pos.x() - c * ts) / ts
        fy = (pos.y() - r * ts) / ts
        dists = {
            "west": fx, "east": 1 - fx,
            "north": fy, "south": 1 - fy,
        }
        side = min(dists, key=dists.get)
        if side == "north":
            if r == 0:
                return None
            return (r - 1, c, "south")
        return (r, c, side)

    # ── Undo / redo ─────────────────────────────────────────

    def push_undo(self):
        self.undo_stack.append(self.model.snapshot())
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(self.model.snapshot())
        self.model.restore(self.undo_stack.pop())
        self.update()
        self.map_changed.emit()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(self.model.snapshot())
        self.model.restore(self.redo_stack.pop())
        self.update()
        self.map_changed.emit()
        return True

    # ── Brush footprint ─────────────────────────────────────

    def _footprint(self, row, col):
        if self.tool not in ("brush", "eraser") or self.brush_size == 1:
            return [(row, col)]
        rad = self.brush_size // 2
        out = []
        for dr in range(-rad, rad + 1):
            for dc in range(-rad, rad + 1):
                if dr * dr + dc * dc <= rad * rad + rad * 0.5:
                    rr, cc = row + dr, col + dc
                    if 0 <= rr < GRID and 0 <= cc < GRID:
                        out.append((rr, cc))
        return out

    # ── Painting logic ──────────────────────────────────────

    def _apply_brush(self, row, col):
        t = 0 if self.tool == "eraser" else self.terrain
        for r, c in self._footprint(row, col):
            self.model.set_terrain(r, c, t)
        self.update()
        self.map_changed.emit()

    def _shape_tiles(self):
        if not self.shape_start or not self.hovered:
            return []
        r0, c0 = self.shape_start
        r1, c1 = self.hovered
        if self.tool == "line":
            return self.model.bresenham(r0, c0, r1, c1)
        tiles = []
        for r in range(min(r0, r1), max(r0, r1) + 1):
            for c in range(min(c0, c1), max(c0, c1) + 1):
                tiles.append((r, c))
        return tiles

    # ── Mouse events ────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (
            event.button() == Qt.LeftButton and self._space_down
        ):
            self._panning = True
            self._pan_origin = event.globalPos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        if event.button() == Qt.RightButton:
            tile = self._tile_at(event.pos())
            if tile:
                self.terrain_picked.emit(self.model.get_terrain(*tile))
            return

        if event.button() != Qt.LeftButton:
            return
        tile = self._tile_at(event.pos())
        if not tile:
            return

        if event.modifiers() & Qt.AltModifier or self.tool == "picker":
            self.terrain_picked.emit(self.model.get_terrain(*tile))
            return

        handler = {
            "line": self._press_shape, "rect": self._press_shape,
            "fill": self._press_fill, "river": self._press_river,
            "spawn": self._press_spawn,
        }.get(self.tool, self._press_brush)
        handler(tile, event)

    def _select_and_notify(self, tile):
        self.selected = tile
        self.update()
        self.tile_clicked.emit(*tile)
        self.map_changed.emit()

    def _press_shape(self, tile, event):
        self.push_undo()
        self.painting = True
        self.shape_start = tile
        self.update()

    def _press_fill(self, tile, event):
        self.push_undo()
        self.model.flood_fill(*tile, self.terrain)
        self._select_and_notify(tile)

    def _press_river(self, tile, event):
        edge = self._edge_at(event.pos())
        if edge:
            self.push_undo()
            self.painting = True
            self._last_edge = edge
            self.model.toggle_river(*edge)
            self._select_and_notify((edge[0], edge[1]))

    def _press_spawn(self, tile, event):
        self.push_undo()
        self.model.set_spawn(*tile, not self.model.has_spawn(*tile))
        self._select_and_notify(tile)

    def _press_brush(self, tile, event):
        self.push_undo()
        self.painting = True
        self._apply_brush(*tile)
        self.selected = tile
        self.tile_clicked.emit(*tile)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.globalPos() - self._pan_origin
            self._pan_origin = event.globalPos()
            if self.scroll_area:
                h = self.scroll_area.horizontalScrollBar()
                v = self.scroll_area.verticalScrollBar()
                h.setValue(h.value() - delta.x())
                v.setValue(v.value() - delta.y())
            return

        tile = self._tile_at(event.pos())
        edge = self._edge_at(event.pos()) if self.tool == "river" else None
        if tile != self.hovered or edge != self.hover_edge:
            self.hovered = tile
            self.hover_edge = edge
            if tile:
                self.tile_hovered.emit(*tile)
            else:
                self.tile_unhovered.emit()
            self.update()

        if self.painting and tile:
            if self.tool in ("line", "rect"):
                self.update()
            elif self.tool == "river":
                if edge and edge != self._last_edge:
                    self._last_edge = edge
                    self.model.toggle_river(*edge)
                    self.update()
                    self.map_changed.emit()
            else:
                self._apply_brush(*tile)

    def mouseReleaseEvent(self, event):
        if self._panning:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        if self.painting and self.shape_start and self.hovered:
            for r, c in self._shape_tiles():
                self.model.set_terrain(r, c, self.terrain)
            self.map_changed.emit()
        self.painting = False
        self.shape_start = None
        self._last_edge = None
        self.update()

    def leaveEvent(self, event):
        self.hovered = None
        self.hover_edge = None
        self.painting = False
        self.shape_start = None
        self.tile_unhovered.emit()
        self.update()

    def wheelEvent(self, event):
        step = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.set_tile_size(self.tile_size * step, anchor=event.pos())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = True
            self.setCursor(Qt.OpenHandCursor)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self._space_down = False
            if not self._panning:
                self.setCursor(Qt.ArrowCursor)
            return
        super().keyReleaseEvent(event)

    # ── Rendering ───────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        ts = self.tile_size

        for r in range(GRID):
            for c in range(GRID):
                self._draw_tile(p, r, c, c * ts, r * ts, ts)

        self._paint_grid_lines(p, ts)

        # Shape preview
        if self.painting and self.shape_start and self.hovered:
            p.setBrush(QColor(108, 138, 255, 70))
            p.setPen(Qt.NoPen)
            for rr, cc in self._shape_tiles():
                p.drawRect(QRectF(cc * ts, rr * ts, ts, ts))

        p.setRenderHint(QPainter.Antialiasing, True)
        self._paint_hover(p, ts)

        # Selection
        if self.selected:
            r, c = self.selected
            pen = QPen(QColor(255, 255, 255, 210))
            pen.setWidthF(1.6)
            pen.setDashPattern([3, 3])
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(c * ts + 1, r * ts + 1, ts - 2, ts - 2))
        p.end()

    def _paint_grid_lines(self, p, ts):
        total = GRID * ts
        if self.show_grid and ts >= 10:
            pen = QPen(QColor(255, 255, 255, 14))
            pen.setWidthF(1)
            p.setPen(pen)
            for i in range(GRID + 1):
                v = i * ts
                p.drawLine(QPointF(v, 0), QPointF(v, total))
                p.drawLine(QPointF(0, v), QPointF(total, v))
        if self.show_guides and ts >= 12:
            pen = QPen(QColor(180, 210, 240, 46))
            pen.setWidthF(1)
            pen.setDashPattern([4, 4])
            p.setPen(pen)
            for r in (2, 30):
                y = r * ts
                p.drawLine(QPointF(0, y), QPointF(total, y))

    def _paint_hover(self, p, ts):
        if self.tool == "river" and self.hover_edge:
            r, c, flag = self.hover_edge
            pen = QPen(QColor(theme.RIVER_GLOW))
            pen.setWidthF(max(3.0, ts * 0.22))
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setOpacity(0.75)
            x, y = c * ts, r * ts
            if flag == "west":
                p.drawLine(QPointF(x, y + ts * 0.12), QPointF(x, y + ts * 0.88))
            elif flag == "east":
                p.drawLine(QPointF(x + ts, y + ts * 0.12),
                           QPointF(x + ts, y + ts * 0.88))
            else:
                p.drawLine(QPointF(x + ts * 0.12, y + ts),
                           QPointF(x + ts * 0.88, y + ts))
            p.setOpacity(1.0)
            return
        if not self.hovered:
            return
        pen = QPen(QColor(108, 138, 255, 190))
        pen.setWidthF(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        tiles = (self._footprint(*self.hovered)
                 if self.tool in ("brush", "eraser") else [self.hovered])
        for rr, cc in tiles:
            p.drawRect(QRectF(cc * ts + 1, rr * ts + 1, ts - 2, ts - 2))

    def _draw_tile(self, p: QPainter, row, col, x, y, ts):
        byte = self.model.get_tile(row, col)
        terrain = byte & 0x07
        _, light, dark = theme.TERRAIN_COLORS[terrain]

        grad = QLinearGradient(x, y, x + ts, y + ts)
        grad.setColorAt(0, QColor(light))
        grad.setColorAt(1, QColor(dark))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(grad))
        p.drawRect(QRectF(x, y, ts, ts))

        if ts >= 14:
            p.setRenderHint(QPainter.Antialiasing, True)
            p.setOpacity(0.22)
            glyph = self._GLYPHS.get(terrain)
            if glyph:
                glyph(self, p, x, y, ts)
            p.setOpacity(1.0)
            p.setRenderHint(QPainter.Antialiasing, False)

        rivers = self.model.get_rivers(row, col)
        if any(rivers.values()):
            self._draw_rivers(p, rivers, x, y, ts)
        if byte & 0x10:
            self._draw_spawn(p, x, y, ts)

    # ── Terrain glyphs ──────────────────────────────────────

    def _glyph_ocean(self, p, x, y, ts):
        p.setPen(QPen(QColor("#80c0f0"), max(1.0, ts * 0.05)))
        p.setBrush(Qt.NoBrush)
        s = ts / 6
        p.drawLine(QPointF(x + s * 1.5, y + s * 2), QPointF(x + s * 4, y + s * 2))
        p.drawLine(QPointF(x + s * 0.5, y + s * 4), QPointF(x + s * 2.5, y + s * 4))

    def _glyph_hills(self, p, x, y, ts):
        p.setPen(QPen(QColor("#3b3320"), max(1.0, ts * 0.06)))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(x + ts * 0.15, y + ts * 0.42, ts * 0.4, ts * 0.36),
                  0, 180 * 16)
        p.drawArc(QRectF(x + ts * 0.45, y + ts * 0.5, ts * 0.4, ts * 0.36),
                  0, 180 * 16)

    def _glyph_forest(self, p, x, y, ts):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0a3018"))
        for cx, cy, r_ in ((0.36, 0.45, 0.2), (0.64, 0.6, 0.16)):
            p.drawPolygon(QPolygonF([
                QPointF(x + ts * (cx - r_), y + ts * (cy + r_)),
                QPointF(x + ts * cx, y + ts * (cy - r_ * 1.4)),
                QPointF(x + ts * (cx + r_), y + ts * (cy + r_)),
            ]))

    def _glyph_desert(self, p, x, y, ts):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#8a6a20"))
        for cx, cy in ((0.3, 0.35), (0.62, 0.55), (0.42, 0.72)):
            p.drawEllipse(QPointF(x + ts * cx, y + ts * cy),
                          ts * 0.05, ts * 0.05)

    def _glyph_mountains(self, p, x, y, ts):
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#3a3632"))
        p.drawPolygon(QPolygonF([
            QPointF(x + ts * 0.2, y + ts * 0.8),
            QPointF(x + ts * 0.5, y + ts * 0.18),
            QPointF(x + ts * 0.8, y + ts * 0.8),
        ]))
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(QPolygonF([
            QPointF(x + ts * 0.41, y + ts * 0.37),
            QPointF(x + ts * 0.5, y + ts * 0.18),
            QPointF(x + ts * 0.59, y + ts * 0.37),
        ]))

    def _glyph_ice(self, p, x, y, ts):
        p.setPen(QPen(QColor("#ffffff"), 0.6))
        step = max(4, int(ts / 4))
        for i in range(0, int(ts) + step, step):
            p.drawLine(QPointF(x + i, y), QPointF(x + i - ts * 0.3, y + ts))

    _GLYPHS = {
        0: _glyph_ocean, 3: _glyph_hills, 4: _glyph_forest,
        5: _glyph_desert, 6: _glyph_mountains, 7: _glyph_ice,
    }

    def _draw_rivers(self, p, rivers, x, y, ts):
        p.setRenderHint(QPainter.Antialiasing, True)
        rw = max(2.0, ts * 0.16)
        for width, color, opacity in (
            (rw + 2.5, theme.RIVER_GLOW, 0.28),
            (rw, theme.RIVER, 1.0),
        ):
            pen = QPen(QColor(color))
            pen.setWidthF(width)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setOpacity(opacity)
            if rivers["west"]:
                p.drawLine(QPointF(x, y + ts * 0.15), QPointF(x, y + ts * 0.85))
            if rivers["east"]:
                p.drawLine(QPointF(x + ts, y + ts * 0.15),
                           QPointF(x + ts, y + ts * 0.85))
            if rivers["south"]:
                p.drawLine(QPointF(x + ts * 0.15, y + ts),
                           QPointF(x + ts * 0.85, y + ts))
        p.setOpacity(1.0)
        p.setRenderHint(QPainter.Antialiasing, False)

    def _draw_spawn(self, p, x, y, ts):
        p.setRenderHint(QPainter.Antialiasing, True)
        cx, cy = x + ts / 2, y + ts / 2
        r_ = ts * 0.26
        p.setPen(QPen(QColor(0, 0, 0, 120), max(1.0, ts * 0.04)))
        p.setBrush(QColor(theme.SPAWN))
        star = QPolygonF()
        for i in range(10):
            a = (i * math.pi / 5) - math.pi / 2
            rr = r_ if i % 2 == 0 else r_ * 0.45
            star.append(QPointF(cx + rr * math.cos(a), cy + rr * math.sin(a)))
        p.drawPolygon(star)
        p.setRenderHint(QPainter.Antialiasing, False)

    # ── Minimap ─────────────────────────────────────────────

    def render_minimap(self, p: QPainter, size: int):
        px = size / GRID
        for r in range(GRID):
            for c in range(GRID):
                terrain = self.model.get_terrain(r, c)
                base, _, _ = theme.TERRAIN_COLORS[terrain]
                p.fillRect(QRectF(c * px, r * px, px + 0.5, px + 0.5),
                           QColor(base))
        rc = QColor(theme.RIVER)
        p.setOpacity(0.8)
        for r in range(GRID):
            for c in range(GRID):
                rivers = self.model.get_rivers(r, c)
                if rivers["west"]:
                    p.fillRect(QRectF(c * px, r * px, 1, px), rc)
                if rivers["east"]:
                    p.fillRect(QRectF((c + 1) * px - 1, r * px, 1, px), rc)
                if rivers["south"]:
                    p.fillRect(QRectF(c * px, (r + 1) * px - 1, px, 1), rc)
        p.setOpacity(1.0)
