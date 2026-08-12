"""Single source of truth for colors, fonts, and Qt stylesheets."""

# ── Surface palette (dark, blue-ink) ─────────────────────────
BG = "#0d0f16"          # window ground / canvas surround
PANEL = "#141724"       # side rails
CARD = "#1b1f30"        # raised cards, inputs
CARD_HOVER = "#232840"
LINE = "#2a2f45"        # hairline borders
TEXT = "#d7dae8"
MUTED = "#8b90ab"
FAINT = "#565b74"

ACCENT = "#6c8aff"      # selection / focus
ACCENT_DIM = "rgba(108,138,255,0.16)"

GOOD = "#5cb87a"
WARN = "#e0a144"
BAD = "#e06767"

# ── Map palette ──────────────────────────────────────────────
# (base, light, dark) per terrain type 0-7.
# CORRECT mapping: 3=Hills (passable), 6=Mountains (impassable).
TERRAIN_COLORS = [
    ("#1a5c8a", "#2278b0", "#0e3e5e"),  # 0 Ocean
    ("#4a9040", "#5cac50", "#357030"),  # 1 Grassland
    ("#c4a844", "#d8bc58", "#a08830"),  # 2 Plains
    ("#8a7a4a", "#a09060", "#706038"),  # 3 Hills
    ("#2e7040", "#3c8850", "#1e5830"),  # 4 Forest
    ("#d8b050", "#e8c468", "#b89038"),  # 5 Desert
    ("#7a7068", "#908680", "#605650"),  # 6 Mountains
    ("#b8cce0", "#d0e0f0", "#90a8c0"),  # 7 Ice
]

RIVER = "#4aa8f0"
RIVER_GLOW = "#80d0ff"
SPAWN = "#ffcc00"

APP_STYLESHEET = f"""
QMainWindow, QDialog {{ background: {BG}; }}
QWidget {{
    font-family: -apple-system, 'Segoe UI', 'Inter', 'Ubuntu', sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
QToolTip {{
    background: {CARD}; color: {TEXT};
    border: 1px solid {LINE}; border-radius: 4px;
    padding: 4px 8px; font-size: 11px;
}}
QMenuBar {{
    background: {PANEL}; color: {TEXT};
    border-bottom: 1px solid {LINE}; padding: 1px 4px;
}}
QMenuBar::item {{ padding: 4px 9px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: {CARD_HOVER}; }}
QMenu {{
    background: {CARD}; color: {TEXT};
    border: 1px solid {LINE}; border-radius: 6px; padding: 4px;
}}
QMenu::item {{ padding: 5px 26px 5px 12px; border-radius: 4px; }}
QMenu::item:selected {{ background: {CARD_HOVER}; }}
QMenu::item:disabled {{ color: {FAINT}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 6px; }}
QStatusBar {{
    background: {PANEL}; border-top: 1px solid {LINE};
    color: {MUTED}; font-size: 11px;
}}
QStatusBar::item {{ border: none; }}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{ background: {BG}; width: 10px; }}
QScrollBar:horizontal {{ background: {BG}; height: 10px; }}
QScrollBar::handle {{ background: {LINE}; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: {FAINT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QComboBox {{
    background: {CARD}; border: 1px solid {LINE};
    border-radius: 5px; padding: 5px 10px; color: {TEXT}; font-size: 12px;
}}
QComboBox:hover {{ border-color: {FAINT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {CARD}; color: {TEXT}; border: 1px solid {LINE};
    selection-background-color: {CARD_HOVER}; outline: none;
}}
QLineEdit {{
    background: {CARD}; border: 1px solid {LINE};
    border-radius: 5px; padding: 5px 8px; color: {TEXT};
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border-color: {ACCENT}; }}
QCheckBox {{ color: {TEXT}; font-size: 12px; spacing: 7px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {LINE}; background: {CARD};
}}
QCheckBox::indicator:hover {{ border-color: {FAINT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}
QProgressBar {{
    background: {CARD}; border: none; border-radius: 3px;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 3px; }}
QTabWidget::pane {{ border: none; }}
QTabBar {{ background: {PANEL}; }}
QTabBar::tab {{
    background: transparent; color: {MUTED};
    padding: 7px 18px; border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom: 2px solid {ACCENT}; }}
QTabBar::tab:hover {{ color: {TEXT}; }}
QMessageBox {{ background: {PANEL}; }}
QMessageBox QLabel {{ color: {TEXT}; font-size: 13px; }}
QMessageBox QPushButton, QDialog QPushButton[dialogButton="true"] {{
    background: {CARD}; color: {TEXT}; border: 1px solid {LINE};
    border-radius: 5px; padding: 6px 18px; min-width: 70px;
}}
QMessageBox QPushButton:hover, QDialog QPushButton[dialogButton="true"]:hover {{
    background: {CARD_HOVER};
}}
"""


def section_label_style() -> str:
    return (
        f"font-size: 10px; font-weight: 700; letter-spacing: 1.2px;"
        f"color: {MUTED}; padding: 2px 0; background: transparent; border: none;"
    )


def tool_button_style() -> str:
    return (
        f"QToolButton {{ background: {CARD}; border: 1px solid transparent;"
        f" border-radius: 6px; }}"
        f"QToolButton:hover {{ background: {CARD_HOVER}; }}"
        f"QToolButton:checked {{ background: {ACCENT_DIM};"
        f" border: 1px solid {ACCENT}; }}"
    )


def terrain_button_style() -> str:
    return (
        f"QPushButton {{ background: transparent; color: {TEXT};"
        f" border: 1px solid transparent; border-radius: 5px;"
        f" text-align: left; padding: 3px 6px; font-size: 12px; }}"
        f"QPushButton:hover {{ background: {CARD_HOVER}; }}"
        f"QPushButton:checked {{ background: {ACCENT_DIM};"
        f" border: 1px solid {ACCENT}; }}"
    )


def primary_button_style() -> str:
    return (
        f"QPushButton {{ background: {ACCENT}; color: #ffffff; font-size: 13px;"
        f" font-weight: 600; border: none; border-radius: 6px; }}"
        f"QPushButton:hover {{ background: #7d98ff; }}"
        f"QPushButton:pressed {{ background: #5b78e8; }}"
        f"QPushButton:disabled {{ background: {CARD}; color: {FAINT}; }}"
    )


def quiet_button_style() -> str:
    return (
        f"QPushButton {{ background: {CARD}; color: {TEXT}; font-size: 12px;"
        f" border: 1px solid {LINE}; border-radius: 5px; padding: 5px 10px; }}"
        f"QPushButton:hover {{ background: {CARD_HOVER}; }}"
        f"QPushButton:disabled {{ color: {FAINT}; }}"
    )
