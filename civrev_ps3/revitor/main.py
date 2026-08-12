#!/usr/bin/env python3
"""Revitor — the CivRev map & scenario editor (civREV + edITOR).

Run with the repo venv:  ../../.venv/bin/python main.py
"""

import os
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

    smoke = os.environ.get("REVITOR_SMOKE")
    if smoke:
        # CI smoke test: prove the (possibly frozen) app boots and its bundled
        # resources resolve, then exit without entering the event loop.
        # Run with QT_QPA_PLATFORM=offscreen on headless machines.
        # REVITOR_SMOKE=deep additionally performs a REAL build of the current
        # slot (requires Pak9/ + Pak9_original/; writes into them exactly like
        # pressing Build).
        #
        # Results also go to the file named by REVITOR_SMOKE_OUT, and exits
        # use os._exit: windowed (no-console) builds have no stdout and must
        # never reach the GUI unhandled-exception dialog, which would hang CI.
        def _report(msg: str, code: int):
            print(msg, flush=True)
            out = os.environ.get("REVITOR_SMOKE_OUT")
            if out:
                Path(out).write_text(msg + "\n")
            os._exit(code)

        try:
            app.processEvents()
            import texgen

            refs = texgen.load_blend_refs(window.settings.pak9_original_dir)
            assert len(refs) == 8, f"blend refs missing: {len(refs)}/8"
            assert texgen.REFS_MODE in ("derived", "fallback")
            import fpk  # noqa: F401  (FPK repacker importable when frozen)

            assert len(window.scenario_panel.rows) == 35, \
                "scenario schema short"
            built = ""
            if smoke == "deep":
                import build as build_mod

                oks, errs = [], []
                worker = build_mod.BuildWorker(
                    window.model.snapshot(), window.current_slot,
                    window.settings, install=False, smart_patch=True,
                    scenario_values=window.scenario_panel.get_values())
                worker.finished_ok.connect(oks.append)
                worker.failed.connect(errs.append)
                worker.run()
                assert oks and not errs, f"deep build failed: {errs}"
                built = f"\nREVITOR_SMOKE_BUILD_OK: {oks[0]}"
        except Exception as e:                    # -> file + nonzero exit
            _report(f"REVITOR_SMOKE_FAIL: {type(e).__name__}: {e}", 1)
        _report(f"REVITOR_SMOKE_OK{built}", 0)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
