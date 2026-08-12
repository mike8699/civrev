# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — bundle Revitor into a single executable.

Build (from this directory, any platform):
    pyinstaller revitor.spec

Produces dist/revitor (dist/revitor.exe on Windows): a one-file binary with
PyQt5, numpy, Pillow, the blend-ref assets, and the FPK repacker bundled.
At runtime the app looks for Pak9/ and Pak9_original/ next to the executable
by default; all paths are configurable in File > Settings.
"""

from pathlib import Path

SPEC_DIR = Path(SPECPATH).resolve()          # civrev_ps3/revitor/
CIVREV = SPEC_DIR.parent                     # civrev_ps3/ (for fpk.py)

a = Analysis(
    [str(SPEC_DIR / "main.py")],
    pathex=[str(SPEC_DIR), str(CIVREV)],
    binaries=[],
    datas=[
        (str(SPEC_DIR / "assets"), "assets"),
    ],
    hiddenimports=[
        "fpk",                    # imported lazily inside build.py's worker
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "PyQt5.QtWebEngineWidgets",
        "PyQt5.QtMultimedia",
        "PyQt5.QtNetwork",
        "PyQt5.QtSql",
        "PyQt5.QtTest",
        "PyQt5.QtXml",
        "PyQt5.QtQml",
        "PyQt5.QtQuick",
        "PyQt5.QtBluetooth",
        "PyQt5.QtDBus",
        "PyQt5.QtDesigner",
        "PyQt5.QtHelp",
        "PyQt5.QtLocation",
        "PyQt5.QtNfc",
        "PyQt5.QtPositioning",
        "PyQt5.QtSensors",
        "PyQt5.QtSerialPort",
        "PyQt5.QtWebChannel",
        "PyQt5.QtWebSockets",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="revitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                    # avoid AV false-positives on Windows
    console=False,                # GUI app — no console window
    disable_windowed_traceback=False,
)
