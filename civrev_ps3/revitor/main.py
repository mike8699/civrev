#!/usr/bin/env python3
"""Revitor — the CivRev map & scenario editor (civREV + edITOR).

Run with the repo venv:  ../../.venv/bin/python main.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import theme
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QApplication.setAttribute(Qt.AA_UseDesktopOpenGL, True)
    QApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    from gl_preview import default_surface_format
    from PyQt5.QtGui import QSurfaceFormat

    QSurfaceFormat.setDefaultFormat(default_surface_format())

    app = QApplication(sys.argv)
    app.setApplicationName("Revitor")
    app.setOrganizationName("civrev")
    app.setStyleSheet(theme.APP_STYLESHEET)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(theme.BG))
    palette.setColor(QPalette.WindowText, QColor(theme.TEXT))
    palette.setColor(QPalette.Base, QColor(theme.PANEL))
    palette.setColor(QPalette.AlternateBase, QColor(theme.CARD))
    palette.setColor(QPalette.ToolTipBase, QColor(theme.CARD))
    palette.setColor(QPalette.ToolTipText, QColor(theme.TEXT))
    palette.setColor(QPalette.Text, QColor(theme.TEXT))
    palette.setColor(QPalette.Button, QColor(theme.CARD))
    palette.setColor(QPalette.ButtonText, QColor(theme.TEXT))
    palette.setColor(QPalette.Highlight, QColor(theme.ACCENT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)

    from editor import EditorWindow

    window = EditorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
