"""Reusable Pantone-styled widgets: section labels, chips, badges, cards,
field rows, the pipeline bar chart, and the brand glyph."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ..theme import Palette, palette, status_color, status_label, with_alpha


def clear_layout(layout) -> None:
    """Remove and delete all child widgets/layouts.

    setParent(None) detaches the widget from the visual tree immediately —
    deleteLater() alone leaves ghosts on screen until the event loop spins.
    """
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())


def section_label(text: str) -> QLabel:
    p = palette()
    lab = QLabel(text.upper())
    f = lab.font()
    size = f.pointSizeF()
    if size > 0:
        f.setPointSizeF(max(7.0, size - 1.5))
    else:  # font specified in pixels (some platforms)
        f.setPixelSize(max(10, f.pixelSize() - 2))
    f.setBold(True)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
    lab.setFont(f)
    lab.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
    return lab


def chip(text: str, color: str | None = None) -> QLabel:
    p = palette()
    c = color or p.accent
    lab = QLabel(text)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    lab.setStyleSheet(
        f"color: {c}; background: {with_alpha(c, 0.10)};"
        f"border: 1px solid {with_alpha(c, 0.28)}; border-radius: 9px;"
        f"padding: 2px 9px; font-size: 12px;"
    )
    lab.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return lab


def status_badge(status: str) -> QLabel:
    p = palette()
    c = status_color(p, status)
    lab = QLabel(f"● {status_label(status)}")
    lab.setStyleSheet(
        f"color: {c}; background: {with_alpha(c, 0.10)};"
        f"border: 1px solid {with_alpha(c, 0.25)}; border-radius: 9px;"
        f"padding: 1px 8px; font-size: 11px; font-weight: 600;"
    )
    lab.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
    return lab


class Card(QFrame):
    def __init__(self, parent: QWidget | None = None, padding: int = 14):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(padding, padding, padding, padding)
        self._layout.setSpacing(12)

    def add(self, w: QWidget) -> None:
        self._layout.addWidget(w)

    def add_layout(self, lay) -> None:
        self._layout.addLayout(lay)


class FieldRow(QWidget):
    def __init__(self, label: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        p = palette()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        lay.addWidget(section_label(label))
        value = QLabel(text if text else "—")
        value.setWordWrap(True)
        value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        value.setStyleSheet(f"color: {p.ink}; font-size: 13px; background: transparent;")
        lay.addWidget(value)


class TagWrap(QWidget):
    def __init__(self, label: str, tags: list[str], color: str | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        p = palette()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(section_label(label))
        if not tags:
            dash = QLabel("—")
            dash.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
            lay.addWidget(dash)
        for tag in tags:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(chip(tag, color))
            row.addStretch(1)
            lay.addLayout(row)


class LinkButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None):
        super().__init__(text, parent)
        self.setObjectName("linkish")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        f = self.font()
        f.setFamily("Consolas" if f.family() != "Consolas" else f.family())
        self.setFont(f)


class HBarChart(QWidget):
    """Minimal horizontal bar chart — labels, Pantone-colored bars, counts."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._rows: list[tuple[str, int, str]] = []
        self.setMinimumHeight(20)

    def set_rows(self, rows: list[tuple[str, int, str]]) -> None:
        self._rows = rows
        self.setMinimumHeight(max(20, len(rows) * 30 + 8))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if not self._rows:
            return
        p = palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        label_w = 92
        count_w = 34
        bar_h = 14
        row_h = 30
        max_count = max(max(c for _, c, _ in self._rows), 1)
        avail = max(10, self.width() - label_w - count_w - 16)
        font = painter.font()
        size = font.pointSizeF()
        if size > 0:
            font.setPointSizeF(max(7.0, size - 1))
        else:
            font.setPixelSize(max(10, font.pixelSize() - 1))
        painter.setFont(font)
        for i, (label, count, color) in enumerate(self._rows):
            y = i * row_h + (row_h - bar_h) // 2
            painter.setPen(QPen(QColor(p.ink_secondary)))
            painter.drawText(QRectF(0, i * row_h, label_w - 8, row_h),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
            w = int(avail * (count / max_count)) if count > 0 else 3
            painter.setPen(Qt.PenStyle.NoPen)
            qc = QColor(color)
            qc.setAlphaF(0.88)
            painter.setBrush(qc)
            painter.drawRoundedRect(QRectF(label_w, y, max(w, 3), bar_h), 3, 3)
            painter.setPen(QPen(QColor(p.ink_secondary)))
            painter.drawText(QRectF(label_w + max(w, 3) + 8, i * row_h, count_w, row_h),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(count))
        painter.end()


class EngineGlyph(QWidget):
    """Brand mark: Classic-Blue squircle, three layers distilling to a dot."""

    def __init__(self, size: int = 112, parent: QWidget | None = None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt API)
        s = self._size
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, s)
        grad.setColorAt(0.0, QColor("#175894"))
        grad.setColorAt(1.0, QColor("#093A66"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawRoundedRect(QRectF(0, 0, s, s), s * 0.224, s * 0.224)

        glyph = QColor("#F4F5F0")
        cx = s / 2
        bar_h = s * 0.055
        gap = s * 0.062
        widths = [s * 0.37, s * 0.26, s * 0.15]
        alphas = [0.47, 0.71, 1.0]
        total = 3 * bar_h + 3 * gap + s * 0.064
        y = (s - total) / 2 + s * 0.01
        for w, a in zip(widths, alphas):
            c = QColor(glyph)
            c.setAlphaF(a)
            painter.setBrush(c)
            painter.drawRoundedRect(QRectF(cx - w / 2, y, w, bar_h), bar_h / 2, bar_h / 2)
            y += bar_h + gap
        dot = s * 0.064
        painter.setBrush(glyph)
        painter.drawEllipse(QRectF(cx - dot / 2, y, dot, dot))
        painter.end()


class KPICard(Card):
    def __init__(self, label: str, icon_color: str, parent: QWidget | None = None):
        super().__init__(parent, padding=12)
        p = palette()
        self._layout.setSpacing(5)
        self.add(section_label(label))
        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(
            f"color: {p.ink}; font-size: 22px; font-weight: 600; background: transparent;")
        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet(
            f"color: {p.ink_secondary}; font-size: 11px; font-weight: 600; background: transparent;")
        self.sub_label.hide()
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.value_label)
        row.addWidget(self.sub_label, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)
        self.add_layout(row)
        self.setMinimumWidth(130)

    def set_value(self, value: str, sub: str = "", sub_color: str | None = None) -> None:
        self.value_label.setText(value)
        if sub:
            self.sub_label.setText(sub)
            if sub_color:
                self.sub_label.setStyleSheet(
                    f"color: {sub_color}; font-size: 11px; font-weight: 600; background: transparent;")
            self.sub_label.show()
        else:
            self.sub_label.hide()


class ClickableChipButton(QPushButton):
    """Capsule chip that acts as a button (principle ids, paper refs)."""

    def __init__(self, text: str, color: str | None = None, parent: QWidget | None = None):
        super().__init__(text, parent)
        p = palette()
        c = color or p.accent
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            f"QPushButton {{ color: {c}; background: {with_alpha(c, 0.10)};"
            f"border: 1px solid {with_alpha(c, 0.28)}; border-radius: 9px;"
            f"padding: 2px 9px; font-size: 12px; }}"
            f"QPushButton:hover {{ background: {with_alpha(c, 0.18)}; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
