"""Reusable UI pieces: icons, section labels, stat rows, toasts, minimap."""

import math

import theme
from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


def color_swatch(color: str, size: int = 16, radius: int = 3) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(0, 0, 0, 90), 1))
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), radius, radius)
    p.end()
    return pm


def tool_icon(name: str, size: int = 26, color: str = None) -> QIcon:
    """Simple vector icons drawn in the muted UI color."""
    col = QColor(color or theme.MUTED)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(col)
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    s = size

    if name == "brush":
        p.drawLine(QPointF(s * 0.7, s * 0.15), QPointF(s * 0.4, s * 0.52))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([
            QPointF(s * 0.44, s * 0.48), QPointF(s * 0.2, s * 0.85),
            QPointF(s * 0.34, s * 0.56),
        ]))
    elif name == "fill":
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(QPolygonF([
            QPointF(s * 0.25, s * 0.32), QPointF(s * 0.62, s * 0.2),
            QPointF(s * 0.72, s * 0.55), QPointF(s * 0.34, s * 0.66),
        ]))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(s * 0.72, s * 0.76), s * 0.07, s * 0.1)
    elif name == "line":
        p.drawLine(QPointF(s * 0.2, s * 0.8), QPointF(s * 0.8, s * 0.2))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawEllipse(QPointF(s * 0.2, s * 0.8), s * 0.07, s * 0.07)
        p.drawEllipse(QPointF(s * 0.8, s * 0.2), s * 0.07, s * 0.07)
    elif name == "rect":
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(s * 0.2, s * 0.27, s * 0.6, s * 0.46))
    elif name == "river":
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.5)
        path.cubicTo(s * 0.3, s * 0.22, s * 0.45, s * 0.78, s * 0.6, s * 0.42)
        path.cubicTo(s * 0.7, s * 0.22, s * 0.8, s * 0.62, s * 0.87, s * 0.5)
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
    elif name == "spawn":
        cx, cy, r = s * 0.5, s * 0.5, s * 0.32
        star = QPolygonF()
        for i in range(10):
            a = (i * math.pi / 5) - math.pi / 2
            rr = r if i % 2 == 0 else r * 0.42
            star.append(QPointF(cx + rr * math.cos(a), cy + rr * math.sin(a)))
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPolygon(star)
    elif name == "eraser":
        p.setBrush(QColor(col.red(), col.green(), col.blue(), 60))
        p.drawPolygon(QPolygonF([
            QPointF(s * 0.58, s * 0.16), QPointF(s * 0.82, s * 0.38),
            QPointF(s * 0.44, s * 0.8), QPointF(s * 0.2, s * 0.58),
        ]))
        p.drawLine(QPointF(s * 0.52, s * 0.46), QPointF(s * 0.32, s * 0.68))
    elif name == "picker":
        p.drawLine(QPointF(s * 0.66, s * 0.16), QPointF(s * 0.42, s * 0.48))
        p.setBrush(QColor(col.red(), col.green(), col.blue(), 80))
        p.drawEllipse(QPointF(s * 0.7, s * 0.16), s * 0.1, s * 0.1)
        p.setPen(Qt.NoPen)
        p.setBrush(col)
        p.drawPolygon(QPolygonF([
            QPointF(s * 0.42, s * 0.48), QPointF(s * 0.32, s * 0.52),
            QPointF(s * 0.24, s * 0.82), QPointF(s * 0.38, s * 0.54),
        ]))
    p.end()
    return QIcon(pm)


class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(theme.section_label_style())


class StatRow(QWidget):
    """Label + value + thin proportion bar."""

    def __init__(self, name: str, color: str, maximum: int, parent=None):
        super().__init__(parent)
        self._max = maximum
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)

        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(name)
        lbl.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 11px; background: transparent;")
        self.val = QLabel("0")
        self.val.setStyleSheet(
            f"color: {color}; font-family: monospace; font-size: 11px;"
            "background: transparent;")
        self.val.setAlignment(Qt.AlignRight)
        head.addWidget(lbl)
        head.addWidget(self.val)
        lay.addLayout(head)

        self.bar = QProgressBar()
        self.bar.setFixedHeight(4)
        self.bar.setTextVisible(False)
        self.bar.setRange(0, maximum)
        self.bar.setStyleSheet(
            f"QProgressBar {{ background: {theme.CARD}; border: none;"
            f" border-radius: 2px; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 2px; }}"
        )
        lay.addWidget(self.bar)

    def set_value(self, v: int):
        self.val.setText(str(v))
        self.bar.setValue(min(v, self._max))


class ValidationRow(QLabel):
    ICONS = {"pass": "✓", "warn": "⚠", "fail": "✗"}
    COLORS = {"pass": theme.GOOD, "warn": theme.WARN, "fail": theme.BAD}
    BGS = {
        "pass": "rgba(92,184,122,0.09)",
        "warn": "rgba(224,161,68,0.10)",
        "fail": "rgba(224,103,103,0.10)",
    }

    def __init__(self, status: str, msg: str, parent=None):
        super().__init__(f"{self.ICONS[status]}  {msg}", parent)
        self.setWordWrap(True)
        self.setStyleSheet(
            f"color: {self.COLORS[status]}; background: {self.BGS[status]};"
            "border-radius: 4px; padding: 5px 8px; font-size: 11px;"
        )


class Toast(QLabel):
    """Transient bottom-center notification."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(False)
        self.setStyleSheet(
            f"background: {theme.CARD}; border: 1px solid {theme.LINE};"
            f"border-radius: 6px; padding: 9px 18px; color: {theme.TEXT};"
            "font-size: 12px;"
        )
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, msg: str, msec: int = 3000):
        self.setText(msg)
        self.adjustSize()
        parent = self.parentWidget()
        if parent:
            self.move((parent.width() - self.width()) // 2,
                      parent.height() - self.height() - 46)
        self.show()
        self.raise_()
        self._timer.start(msec)


class MinimapWidget(QWidget):
    """Overlay minimap in the canvas corner."""

    SIZE = 128

    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setFixedSize(self.SIZE + 6, self.SIZE + 6)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(QPen(QColor(theme.LINE), 1))
        p.setBrush(QColor(theme.PANEL))
        p.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1,
                                 self.height() - 1), 5, 5)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.translate(3, 3)
        self.canvas.render_minimap(p, self.SIZE)
        p.end()
