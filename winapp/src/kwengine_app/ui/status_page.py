"""Status dashboard — KPI cards, pipeline chart, pending work, verify, reindex."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ..l10n import tr
from ..theme import palette
from .widgets import Card, HBarChart, KPICard, clear_layout, section_label


class StatusPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        p = palette()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        content = QWidget()
        scroll.setWidget(content)
        lay = QVBoxLayout(content)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(16)

        title = QLabel(tr("知识库状态", "Knowledge Base"))
        title.setStyleSheet(f"color: {p.ink}; font-size: 20px; font-weight: 600; background: transparent;")
        sub = QLabel(tr("蒸馏 → 抽象 → 综合 → 按结构检索",
                        "distill → abstract → synthesize → search by structure"))
        sub.setStyleSheet(f"color: {p.ink_secondary}; font-size: 12px; background: transparent;")
        lay.addWidget(title)
        lay.addWidget(sub)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        self.kpi_papers = KPICard(tr("论文", "Papers"), p.accent)
        self.kpi_principles = KPICard(tr("原则", "Principles"), p.emerald)
        self.kpi_synthesis = KPICard(tr("上次综合", "Last synthesis"), p.ultra_violet)
        for k in (self.kpi_papers, self.kpi_principles, self.kpi_synthesis):
            kpi_row.addWidget(k)
        kpi_row.addStretch(1)
        lay.addLayout(kpi_row)

        self.chart_card = Card()
        self.chart_card.add(section_label(tr("论文流水线", "Paper pipeline")))
        self.chart = HBarChart()
        self.chart_card.add(self.chart)
        self.chart_card.setMaximumWidth(520)
        lay.addWidget(self.chart_card)

        self.work_box = QVBoxLayout()
        self.work_box.setSpacing(12)
        lay.addLayout(self.work_box)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.verify_btn = QPushButton(tr("校验完整性", "Verify invariants"))
        self.verify_btn.clicked.connect(self._run_verify)
        self.reindex_btn = QPushButton(tr("重建索引", "Rebuild index"))
        self.reindex_btn.setToolTip(tr("从 markdown 重建 index.json 与 .kw/index.db（markdown 为真相）",
                                       "Rebuild index.json and .kw/index.db from markdown (markdown is truth)"))
        self.reindex_btn.clicked.connect(self._run_reindex)
        self.maint_note = QLabel("")
        self.maint_note.setStyleSheet(f"color: {p.emerald}; font-size: 11px; background: transparent;")
        btn_row.addWidget(self.verify_btn)
        btn_row.addWidget(self.reindex_btn)
        btn_row.addWidget(self.maint_note)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        self.verdicts_box = QVBoxLayout()
        self.verdicts_box.setSpacing(6)
        lay.addLayout(self.verdicts_box)
        lay.addStretch(1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        p = palette()
        ws = self.app.workspace
        if ws is None:
            return
        busy = self.app.busy
        self.verify_btn.setEnabled(not busy)
        self.reindex_btn.setEnabled(not busy)
        try:
            s = ws.status_summary()
        except Exception as e:
            self.kpi_papers.set_value("—")
            self.kpi_principles.set_value("—")
            self.kpi_synthesis.set_value("—")
            self.maint_note.setText(str(e))
            return

        self.kpi_papers.set_value(str(s.papers_total))
        self.kpi_principles.set_value(str(s.principles))
        if s.principles == 0:
            self.kpi_synthesis.set_value(s.synthesis_last_run or tr("从未", "never"))
        elif s.synthesis_stale:
            self.kpi_synthesis.set_value(s.synthesis_last_run or tr("从未", "never"),
                                         tr(f"过期 +{s.new_since_synthesis}", f"stale +{s.new_since_synthesis}"),
                                         p.saffron)
        else:
            self.kpi_synthesis.set_value(s.synthesis_last_run or tr("从未", "never"),
                                         tr("最新", "fresh"), p.emerald)

        self.chart_card.setVisible(s.papers_total > 0)
        self.chart.set_rows([
            (tr("待读取", "Pending"), s.papers_by_status.get("pending", 0), p.ink_secondary),
            (tr("已读 L1", "Read · L1"),
             s.papers_by_status.get("L1", 0) + s.papers_by_status.get("L2", 0), p.accent),
            (tr("已蒸馏", "Distilled"), s.papers_by_status.get("complete", 0), p.emerald),
            (tr("不完整", "Incomplete"), s.papers_by_status.get("incomplete", 0), p.saffron),
        ])

        clear_layout(self.work_box)
        if s.pending_papers:
            self.work_box.addWidget(self._work_list(
                tr("待读取 — 运行 L1", "Pending read — run L1"), s.pending_papers))
        if s.l1_papers:
            self.work_box.addWidget(self._work_list(
                tr("已读取，待蒸馏 — 运行 L2", "Read, awaiting distillation — run L2"), s.l1_papers))
        if s.papers_total == 0:
            card = Card()
            card.add(section_label(tr("开始使用", "Get started")))
            hint = QLabel(tr(
                "从「论文」页导入一篇 PDF。流程：导入 → L1 忠实读取 → L2 蒸馏原则 → L3 综合 → 按结构检索。",
                "Import a PDF in Papers. Flow: import → L1 faithful read → L2 distill principles → "
                "L3 synthesize → search by structure."))
            hint.setWordWrap(True)
            hint.setStyleSheet(f"color: {palette().ink_secondary}; background: transparent;")
            card.add(hint)
            card.setMaximumWidth(520)
            self.work_box.addWidget(card)

    def _work_list(self, title: str, ids: list[str]) -> QWidget:
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(section_label(title))
        lst = QListWidget()
        lst.setObjectName("contentList")
        for pid in ids:
            item = QListWidgetItem(pid)
            item.setData(Qt.ItemDataRole.UserRole, pid)
            lst.addItem(item)
        lst.setFixedHeight(min(len(ids), 6) * 32 + 10)
        lst.setMaximumWidth(520)
        lst.itemClicked.connect(lambda it: self.app.show_paper(it.data(Qt.ItemDataRole.UserRole)))
        lay.addWidget(lst)
        return box

    # ------------------------------------------------------------------
    def _run_verify(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        p = palette()
        clear_layout(self.verdicts_box)
        self.verdicts_box.addWidget(section_label(tr("校验结果", "Verification results")))
        card = Card()
        for v in ws.verify():
            row = QLabel(
                f'{"✓" if v.passed else "✗"}  <b>{v.check_name}</b>  '
                f'<span style="color:{p.ink_secondary}">{v.message}</span>')
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setStyleSheet(
                f"color: {p.emerald if v.passed else p.fiery_red}; background: transparent; font-size: 12px;")
            row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.add(row)
        card.setMaximumWidth(640)
        self.verdicts_box.addWidget(card)

    def _run_reindex(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        try:
            papers, principles = ws.reindex()
            self.maint_note.setText(tr(f"已重建：{papers} 篇论文，{principles} 条原则",
                                       f"Rebuilt: {papers} papers, {principles} principles"))
            self.app.refresh_all()
        except Exception as e:
            self.app.show_error(str(e))
