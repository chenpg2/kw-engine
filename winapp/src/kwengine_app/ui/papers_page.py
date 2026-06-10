"""Papers — list of L1 records + per-paper pipeline actions."""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from ..l10n import tr
from ..theme import palette, status_label
from .widgets import (
    Card, ClickableChipButton, FieldRow, clear_layout, section_label, status_badge,
)


def open_in_file_manager(path) -> None:
    if sys.platform == "win32":
        if path.exists():
            subprocess.Popen(["explorer", "/select,", str(path)])
        else:
            subprocess.Popen(["explorer", str(path.parent)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])


def open_file(path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class PapersPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.selected: str | None = None
        p = palette()

        outer = QHBoxLayout(self)
        outer.setContentsMargins(14, 12, 14, 12)
        split = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(split)

        # left: list -----------------------------------------------------
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 8, 0)
        llay.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel(tr("论文", "Papers"))
        title.setStyleSheet(f"color: {p.ink}; font-size: 15px; font-weight: 600; background: transparent;")
        self.import_btn = QPushButton(tr("导入 PDF…", "Import PDF…"))
        self.import_btn.setObjectName("primary")
        self.import_btn.clicked.connect(self._import_pdfs)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self.import_btn)
        llay.addLayout(head)
        self.listw = QListWidget()
        self.listw.setObjectName("contentList")
        self.listw.currentItemChanged.connect(self._on_select)
        llay.addWidget(self.listw)
        split.addWidget(left)

        # right: detail ----------------------------------------------------
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
        self.import_btn.setEnabled(not self.app.busy)
        try:
            idx = ws.read_index()
        except Exception as e:
            self.app.show_error(str(e))
            return
        current = self.selected
        self.listw.blockSignals(True)
        self.listw.clear()
        for paper in idx["papers"]:
            label = f'{paper["id"]}   ·   {status_label(paper["status"])}'
            if paper.get("title"):
                label += f'\n{paper["title"][:60]}'
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, paper["id"])
            self.listw.addItem(item)
            if paper["id"] == current:
                self.listw.setCurrentItem(item)
        self.listw.blockSignals(False)
        self._build_detail()

    def select_paper(self, pid: str) -> None:
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
        if ws is None or not pid:
            hint = QLabel(tr("选择一篇论文", "Select a paper"))
            hint.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.detail_lay.addStretch(1)
            self.detail_lay.addWidget(hint)
            self.detail_lay.addStretch(1)
            return

        try:
            idx = ws.read_index()
        except Exception:
            idx = {"papers": []}
        entry = next((x for x in idx["papers"] if x["id"] == pid), None)

        head = QHBoxLayout()
        id_lab = QLabel(pid)
        id_lab.setStyleSheet(
            f"color: {p.ink}; font-size: 18px; font-weight: 600; font-family: Consolas, monospace; background: transparent;")
        id_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        head.addWidget(id_lab)
        if entry:
            head.addWidget(status_badge(entry["status"]))
        head.addStretch(1)
        self.detail_lay.addLayout(head)

        paper = None
        body = ""
        if ws.paper_path(pid).exists():
            try:
                paper, body = ws.read_paper_file(pid)
            except Exception as e:
                err = QLabel(str(e))
                err.setWordWrap(True)
                err.setStyleSheet(f"color: {p.saffron}; background: transparent;")
                self.detail_lay.addWidget(err)

        if paper and paper.bib.title:
            t = QLabel(paper.bib.title)
            t.setWordWrap(True)
            t.setStyleSheet(f"color: {p.ink}; font-size: 14px; font-weight: 600; background: transparent;")
            t.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.detail_lay.addWidget(t)
        if paper:
            meta_parts = [x for x in [
                paper.bib.authors, paper.bib.venue,
                str(paper.bib.year) if paper.bib.year else "",
                f"doi:{paper.doi}" if paper.doi else "",
            ] if x]
            if meta_parts:
                meta = QLabel("   ·   ".join(meta_parts))
                meta.setWordWrap(True)
                meta.setStyleSheet(f"color: {p.ink_secondary}; font-size: 11.5px; background: transparent;")
                meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                self.detail_lay.addWidget(meta)

        # actions ----------------------------------------------------------
        actions = QHBoxLayout()
        actions.setSpacing(8)
        busy = self.app.busy
        pdf_exists = ws.pdf_path(pid).exists()

        l1_btn = QPushButton(tr("读取 L1", "Read (L1)"))
        l1_btn.setToolTip(tr("忠实抽取：PDF → memory/papers/", "Faithful extraction: PDF → memory/papers/"))
        l1_btn.setEnabled(not busy and pdf_exists)
        l1_btn.clicked.connect(lambda: self.app.run_pipeline(
            tr(f"L1 · {pid}", f"L1 · {pid}"), lambda pipe: pipe.run_l1(pid)))

        l2_btn = QPushButton(tr("蒸馏 L2", "Distill (L2)"))
        l2_btn.setToolTip(tr("抽象出可迁移原则 → memory/principles/",
                             "Abstract transferable principles → memory/principles/"))
        l2_btn.setEnabled(not busy and entry is not None and entry["status"] != "pending")
        l2_btn.clicked.connect(lambda: self.app.run_pipeline(
            tr(f"L2 · {pid}", f"L2 · {pid}"), lambda pipe: pipe.run_l2(pid)))

        both_btn = QPushButton(tr("一键处理 (L1+L2)", "Process (L1+L2)"))
        both_btn.setObjectName("primary")
        both_btn.setEnabled(not busy and pdf_exists)

        def run_both(pipe):
            pipe.run_l1(pid)
            return pipe.run_l2(pid)

        both_btn.clicked.connect(lambda: self.app.run_pipeline(
            tr(f"L1+L2 · {pid}", f"L1+L2 · {pid}"), run_both))

        pdf_btn = QPushButton("PDF")
        pdf_btn.setEnabled(pdf_exists)
        pdf_btn.clicked.connect(lambda: open_file(ws.pdf_path(pid)))
        reveal_btn = QPushButton(tr("打开所在文件夹", "Show in folder"))
        reveal_btn.clicked.connect(lambda: open_in_file_manager(ws.paper_path(pid)))

        for b in (l1_btn, l2_btn, both_btn):
            actions.addWidget(b)
        actions.addStretch(1)
        actions.addWidget(pdf_btn)
        actions.addWidget(reveal_btn)
        self.detail_lay.addLayout(actions)

        if paper is None:
            note = QLabel(tr("尚未读取（L1）。运行 L1 生成忠实记录。",
                             "Not read yet (L1). Run L1 to produce the faithful record."))
            note.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
            self.detail_lay.addWidget(note)
            self.detail_lay.addStretch(1)
            return

        card = Card()
        for label, text in [
            ("problem_addressed", paper.problem_addressed),
            ("method_summary", paper.method_summary),
            ("math_used", paper.math_used),
            ("claimed_mechanism", paper.claimed_mechanism),
            ("key_evidence", paper.key_evidence),
        ]:
            card.add(FieldRow(label, text))
        self.detail_lay.addWidget(card)

        if entry and entry.get("principles"):
            box = QVBoxLayout()
            box.setSpacing(5)
            box.addWidget(section_label(tr("蒸馏出的原则", "Distilled principles")))
            row = QHBoxLayout()
            row.setSpacing(6)
            for ppid in entry["principles"]:
                btn = ClickableChipButton(ppid, p.emerald)
                btn.clicked.connect(lambda _=False, x=ppid: self.app.show_principle(x))
                row.addWidget(btn)
            row.addStretch(1)
            box.addLayout(row)
            self.detail_lay.addLayout(box)

        cleaned = body.replace("<!-- Fill in faithful notes below. No abstraction. -->", "").strip()
        if cleaned:
            self.detail_lay.addWidget(section_label(tr("忠实笔记（正文）", "Faithful notes (body)")))
            from PySide6.QtWidgets import QFrame
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

    # ------------------------------------------------------------------
    def _import_pdfs(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("选择论文 PDF（文件名将作为 paper id）",
                     "Choose paper PDFs (the filename stem becomes the paper id)"),
            "", "PDF (*.pdf)")
        if not paths:
            return
        from pathlib import Path
        first = None
        for path in paths:
            try:
                pid = ws.import_pdf(Path(path))
                first = first or pid
            except Exception as e:
                self.app.show_error(str(e))
        self.app.refresh_all()
        if first:
            self.select_paper(first)
