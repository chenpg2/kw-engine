"""Principles — browse Layer-2 records: signature ↔ mechanism ↔ rationale."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from ..l10n import tr
from ..models import locator_from_provenance, paper_id_from_provenance
from ..theme import palette
from .widgets import (
    Card, ClickableChipButton, FieldRow, TagWrap, chip, clear_layout, section_label,
)


class PrinciplesPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.selected: str | None = None
        p = palette()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        split = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(split)

        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 8, 0)
        llay.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel(tr("原则", "Principles"))
        title.setStyleSheet(f"color: {p.ink}; font-size: 15px; font-weight: 600; background: transparent;")
        self.count_lab = QLabel("0")
        self.count_lab.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.count_lab)
        llay.addLayout(head)
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText(tr("过滤：id / 标题 / 签名 / 数学",
                                               "Filter: id / title / signature / math"))
        self.filter_edit.textChanged.connect(lambda _: self.refresh())
        llay.addWidget(self.filter_edit)
        self.listw = QListWidget()
        self.listw.setObjectName("contentList")
        self.listw.currentItemChanged.connect(self._on_select)
        llay.addWidget(self.listw)
        split.addWidget(left)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.detail = QWidget()
        self.detail_lay = QVBoxLayout(self.detail)
        self.detail_lay.setContentsMargins(12, 4, 8, 12)
        self.detail_lay.setSpacing(12)
        self.scroll.setWidget(self.detail)
        split.addWidget(self.scroll)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 640])

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        try:
            idx = ws.read_index()
        except Exception as e:
            self.app.show_error(str(e))
            return
        principles = idx["principles"]
        self.count_lab.setText(str(len(principles)))
        f = self.filter_edit.text().strip().lower()
        if f:
            principles = [
                pr for pr in principles
                if f in pr["id"].lower() or f in pr.get("title", "").lower()
                or f in " ".join(pr.get("problem_signature") or []).lower()
                or f in " ".join(pr.get("math_basis") or []).lower()
            ]
        current = self.selected
        self.listw.blockSignals(True)
        self.listw.clear()
        for pr in principles:
            item = QListWidgetItem(f'{pr["id"]}\n{pr.get("title", "")[:64]}')
            item.setData(Qt.ItemDataRole.UserRole, pr["id"])
            self.listw.addItem(item)
            if pr["id"] == current:
                self.listw.setCurrentItem(item)
        self.listw.blockSignals(False)
        self._build_detail()

    def select_principle(self, pid: str) -> None:
        self.filter_edit.clear()
        self.refresh()
        for i in range(self.listw.count()):
            item = self.listw.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == pid:
                self.listw.setCurrentItem(item)
                return

    def _on_select(self, current, _previous=None) -> None:
        self.selected = current.data(Qt.ItemDataRole.UserRole) if current else None
        self._build_detail()

    # ------------------------------------------------------------------
    def _build_detail(self) -> None:
        clear_layout(self.detail_lay)
        p = palette()
        ws = self.app.workspace
        pid = self.selected
        if ws is None or not pid or not ws.principle_path(pid).exists():
            hint = QLabel(tr("选择一条原则", "Select a principle")
                          if pid is None else tr("还没有原则 — 先对论文运行 L2 蒸馏",
                                                 "No principles yet — run L2 on a paper"))
            hint.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.detail_lay.addStretch(1)
            self.detail_lay.addWidget(hint)
            self.detail_lay.addStretch(1)
            return

        try:
            pr, body = ws.read_principle_file(pid)
        except Exception as e:
            err = QLabel(str(e))
            err.setWordWrap(True)
            err.setStyleSheet(f"color: {p.saffron}; background: transparent;")
            self.detail_lay.addWidget(err)
            return

        head = QHBoxLayout()
        id_lab = QLabel(pr.id)
        id_lab.setStyleSheet(
            f"color: {p.ink}; font-size: 18px; font-weight: 600; font-family: Consolas, monospace; background: transparent;")
        head.addWidget(id_lab)
        head.addStretch(1)
        ver = QLabel(pr.rubric_version)
        ver.setStyleSheet(f"color: {p.ink_secondary}; font-size: 11px; background: transparent;")
        head.addWidget(ver)
        self.detail_lay.addLayout(head)

        title = QLabel(pr.title)
        title.setWordWrap(True)
        title.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title.setStyleSheet(f"color: {p.ink}; font-size: 14px; font-weight: 600; background: transparent;")
        self.detail_lay.addWidget(title)

        mapping = Card()
        mapping.add(FieldRow("abstraction_level", pr.abstraction_level))
        mapping.add(TagWrap(tr("问题签名 — 何时适用 (problem_signature)",
                               "problem_signature — WHEN it applies"),
                            pr.problem_signature, p.accent))
        mapping.add(TagWrap("math_basis", pr.math_basis, p.ultra_violet))
        mapping.add(FieldRow(tr("机制 — 做什么 (mechanism)", "mechanism — WHAT to do"), pr.mechanism))
        mapping.add(FieldRow(tr("理由 — 为何成立 (rationale)", "rationale — WHY it holds"), pr.rationale))
        self.detail_lay.addWidget(mapping)

        limits = Card()
        limits.add(TagWrap("data_regime", pr.data_regime, p.teal))
        limits.add(FieldRow("falsifiable_prediction", pr.falsifiable_prediction))
        limits.add(FieldRow(tr("边界 — 何时失效 (boundaries)", "boundaries — when it breaks"), pr.boundaries))
        self.detail_lay.addWidget(limits)

        prov_box = QVBoxLayout()
        prov_box.setSpacing(4)
        prov_box.addWidget(section_label(tr("出处 (provenance)", "provenance")))
        for prov in pr.provenance:
            row = QHBoxLayout()
            row.setSpacing(6)
            ref = paper_id_from_provenance(prov)
            btn = ClickableChipButton(ref, p.accent)
            btn.clicked.connect(lambda _=False, x=ref: self.app.show_paper(x))
            row.addWidget(btn)
            loc = QLabel(locator_from_provenance(prov))
            loc.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
            row.addWidget(loc)
            row.addStretch(1)
            prov_box.addLayout(row)
        self.detail_lay.addLayout(prov_box)

        if pr.links:
            links_box = QVBoxLayout()
            links_box.setSpacing(4)
            links_box.addWidget(section_label("links"))
            for link in pr.links:
                if ":" not in link:
                    continue
                ltype, target = link.split(":", 1)
                row = QHBoxLayout()
                row.setSpacing(6)
                row.addWidget(chip(ltype, p.coral))
                btn = ClickableChipButton(target, p.accent)
                btn.clicked.connect(lambda _=False, x=target: self.app.show_principle(x))
                row.addWidget(btn)
                row.addStretch(1)
                links_box.addLayout(row)
            self.detail_lay.addLayout(links_box)

        cleaned = body.replace("<!-- Derivation, evidence quotes, transfer notes. -->", "").strip()
        if cleaned:
            self.detail_lay.addWidget(section_label(
                tr("推导与迁移笔记（正文）", "Derivation & transfer notes (body)")))
            well = QFrame()
            well.setObjectName("well")
            wlay = QVBoxLayout(well)
            wlay.setContentsMargins(12, 10, 12, 10)
            notes = QLabel(cleaned)
            notes.setWordWrap(True)
            notes.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            notes.setStyleSheet(f"color: {p.ink}; font-size: 12px; background: transparent;")
            wlay.addWidget(notes)
            self.detail_lay.addWidget(well)

        self.detail_lay.addStretch(1)
