"""Pantone design system — same palette as the macOS app, in Qt clothing.
Color is semantic, never decorative. Light/dark follow the OS."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    accent: str          # PANTONE 19-4052 Classic Blue
    navy: str            # PANTONE 533 C
    ink: str             # PANTONE Black 6 C / Bright White
    ink_secondary: str   # PANTONE Cool Gray 11 C / 4 C
    emerald: str         # PANTONE 17-5641
    saffron: str         # PANTONE 1235 C
    fiery_red: str       # PANTONE 485 C
    coral: str           # PANTONE 16-1546 Living Coral
    ultra_violet: str    # PANTONE 18-3838
    teal: str            # PANTONE 3262 C
    canvas: str          # PANTONE 11-0601 Bright White / slate
    card: str
    hairline: str
    well: str
    sidebar: str
    is_dark: bool = False


LIGHT = Palette(
    accent="#0F4C81", navy="#1F2A44", ink="#101820", ink_secondary="#53565A",
    emerald="#009473", saffron="#E8A317", fiery_red="#DA291C", coral="#E85D4E",
    ultra_violet="#5F4B8B", teal="#00897F",
    canvas="#F4F5F0", card="#FFFFFF", hairline="#D9D9D6", well="#EDEEE9",
    sidebar="#ECEDE8", is_dark=False,
)

DARK = Palette(
    accent="#7AA5CC", navy="#27344F", ink="#F4F5F0", ink_secondary="#A8AAAD",
    emerald="#2FBF96", saffron="#FFC64A", fiery_red="#F0564A", coral="#FF8A7E",
    ultra_violet="#9786BE", teal="#34D6C9",
    canvas="#17191D", card="#212429", hairline="#3A3D42", well="#1B1E22",
    sidebar="#1D2024", is_dark=True,
)

_current = LIGHT


def detect_palette() -> Palette:
    global _current
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        scheme = QGuiApplication.styleHints().colorScheme()
        _current = DARK if scheme == Qt.ColorScheme.Dark else LIGHT
    except Exception:
        _current = LIGHT
    return _current


def palette() -> Palette:
    return _current


def status_color(p: Palette, status: str) -> str:
    return {
        "pending": p.ink_secondary,
        "L1": p.accent,
        "L2": p.teal,
        "complete": p.emerald,
        "incomplete": p.saffron,
    }.get(status, p.ink_secondary)


def status_label(status: str) -> str:
    from .l10n import tr
    return {
        "pending": tr("待读", "Pending"),
        "L1": tr("已读 L1", "Read · L1"),
        "L2": "L2",
        "complete": tr("已蒸馏", "Distilled"),
        "incomplete": tr("不完整", "Incomplete"),
    }.get(status, status)


def with_alpha(hex_color: str, alpha: float) -> str:
    """#RRGGBB + alpha → rgba() string for QSS."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{int(alpha * 255)})"


def build_qss(p: Palette) -> str:
    return f"""
QMainWindow, QDialog {{ background: {p.canvas}; }}
QWidget {{ color: {p.ink}; font-size: 13px; }}
QLabel {{ background: transparent; }}

QListWidget#sidebar {{
    background: {p.sidebar}; border: none; outline: none; padding: 6px 4px;
}}
QListWidget#sidebar::item {{
    color: {p.ink_secondary}; border-radius: 6px; padding: 7px 10px; margin: 1px 4px;
}}
QListWidget#sidebar::item:hover {{ background: {with_alpha(p.ink, 0.05)}; }}
QListWidget#sidebar::item:selected {{ background: {p.accent}; color: {"#F4F5F0" if not p.is_dark else "#101820"}; }}

QListWidget#contentList {{
    background: {p.card}; border: 1px solid {p.hairline}; border-radius: 8px; outline: none; padding: 3px;
}}
QListWidget#contentList::item {{ border-radius: 5px; padding: 7px 8px; color: {p.ink}; }}
QListWidget#contentList::item:hover {{ background: {with_alpha(p.accent, 0.06)}; }}
QListWidget#contentList::item:selected {{ background: {with_alpha(p.accent, 0.14)}; color: {p.ink}; }}

QFrame#card {{
    background: {p.card}; border: 1px solid {p.hairline}; border-radius: 10px;
}}
QFrame#well {{
    background: {p.well}; border: 1px solid {p.hairline}; border-radius: 8px;
}}
QFrame#banner {{
    background: {with_alpha(p.saffron, 0.10)}; border: 1px solid {with_alpha(p.saffron, 0.45)};
    border-radius: 8px;
}}

QPushButton {{
    background: {p.card}; color: {p.ink}; border: 1px solid {p.hairline};
    border-radius: 6px; padding: 5px 14px;
}}
QPushButton:hover {{ border-color: {p.accent}; color: {p.accent}; }}
QPushButton:pressed {{ background: {with_alpha(p.accent, 0.10)}; }}
QPushButton:disabled {{ color: {with_alpha(p.ink_secondary, 0.55)}; border-color: {with_alpha(p.hairline, 0.6)}; }}
QPushButton#primary {{
    background: {p.accent}; color: {"#F4F5F0" if not p.is_dark else "#101820"}; border: none; font-weight: 600;
}}
QPushButton#primary:hover {{ background: {p.navy if not p.is_dark else "#8FB5D8"}; color: {"#F4F5F0" if not p.is_dark else "#101820"}; }}
QPushButton#primary:disabled {{ background: {with_alpha(p.accent, 0.4)}; }}
QPushButton#linkish {{ background: transparent; border: none; color: {p.accent}; padding: 1px 4px; text-align: left; }}
QPushButton#linkish:hover {{ text-decoration: underline; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background: {p.card}; color: {p.ink}; border: 1px solid {p.hairline};
    border-radius: 6px; padding: 5px 8px; selection-background-color: {with_alpha(p.accent, 0.35)};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border-color: {p.accent};
}}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {p.card}; color: {p.ink}; border: 1px solid {p.hairline};
    selection-background-color: {with_alpha(p.accent, 0.16)}; selection-color: {p.ink};
}}

QTextBrowser {{
    background: {p.card}; color: {p.ink}; border: 1px solid {p.hairline};
    border-radius: 8px; padding: 10px;
}}

QSplitter::handle {{ background: transparent; width: 6px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {with_alpha(p.ink_secondary, 0.35)}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {with_alpha(p.ink_secondary, 0.35)}; border-radius: 4px; min-width: 30px; }}

QTabWidget::pane {{ border: none; top: 6px; }}
QTabBar::tab {{
    background: transparent; color: {p.ink_secondary}; padding: 6px 14px;
    border: 1px solid {p.hairline}; border-radius: 6px; margin-right: 6px;
}}
QTabBar::tab:selected {{ background: {p.accent}; color: {"#F4F5F0" if not p.is_dark else "#101820"}; border-color: {p.accent}; }}

QStatusBar {{ background: {p.sidebar}; color: {p.ink_secondary}; }}
QDockWidget {{ color: {p.ink}; titlebar-close-icon: none; }}
QToolTip {{ background: {p.card}; color: {p.ink}; border: 1px solid {p.hairline}; padding: 4px 6px; }}
"""
