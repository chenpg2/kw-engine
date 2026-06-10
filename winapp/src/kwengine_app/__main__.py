"""Entry point: python -m kwengine_app"""

from __future__ import annotations

import sys
from pathlib import Path


def asset_path(name: str) -> Path:
    """Resolve bundled assets both in dev and inside a PyInstaller onefile exe."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "assets" / name  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent / "assets" / name


def main() -> int:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setApplicationName("KW Engine")
    app.setOrganizationName("kw-engine")

    from . import theme
    p = theme.detect_palette()
    app.setStyleSheet(theme.build_qss(p))

    icon_file = asset_path("icon.png")
    if icon_file.exists():
        app.setWindowIcon(QIcon(str(icon_file)))

    from .ui.main_window import MainWindow
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
