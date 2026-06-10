"""Search / Ask — the payoff: new problem → structure match → mechanism + rationale."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton,
    QScrollArea, QTabWidget, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
)

from ..l10n import tr
from ..pipeline import AskResult
from ..theme import palette
from .widgets import TagWrap, clear_layout, section_label


class SearchPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        p = palette()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 14, 20, 14)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)

        # --- keyword tab (deterministic, port of `kw search`) -------------
        kw_tab = QWidget()
        kw_lay = QVBoxLayout(kw_tab)
        kw_lay.setSpacing(10)
        kw_hint = QLabel(tr(
            "按问题结构检索：词元会与每条原则的 problem_signature 与 math_basis 做子串匹配。",
            "Search by problem structure: tokens are substring-matched against each principle's "
            "problem_signature and math_basis."))
        kw_hint.setWordWrap(True)
        kw_hint.setStyleSheet(f"color: {p.ink_secondary}; font-size: 12px; background: transparent;")
        kw_lay.addWidget(kw_hint)
        row = QHBoxLayout()
        self.kw_edit = QLineEdit()
        self.kw_edit.setPlaceholderText(
            tr("例如：unpaired marginal snapshots optimal transport",
               "e.g. unpaired marginal snapshots optimal transport"))
        self.kw_edit.returnPressed.connect(self._run_keyword)
        kw_btn = QPushButton(tr("检索", "Search"))
        kw_btn.setObjectName("primary")
        kw_btn.clicked.connect(self._run_keyword)
        row.addWidget(self.kw_edit)
        row.addWidget(kw_btn)
        kw_lay.addLayout(row)
        self.kw_results = QListWidget()
        self.kw_results.setObjectName("contentList")
        self.kw_results.itemClicked.connect(
            lambda it: self.app.show_principle(it.data(Qt.ItemDataRole.UserRole)))
        kw_lay.addWidget(self.kw_results)
        self.kw_note = QLabel("")
        self.kw_note.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
        kw_lay.addWidget(self.kw_note)
        self.tabs.addTab(kw_tab, tr("结构关键词", "Structure keywords"))

        # --- ask tab (LLM) --------------------------------------------------
        ask_tab = QWidget()
        ask_outer = QVBoxLayout(ask_tab)
        ask_outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        ask_outer.addWidget(scroll)
        inner = QWidget()
        scroll.setWidget(inner)
        ask_lay = QVBoxLayout(inner)
        ask_lay.setSpacing(10)
        ask_hint = QLabel(tr(
            "用自然语言描述你的新问题。引擎先抽取问题的结构签名，再在库中检索，"
            "最后把命中的机制 + 理由 + 失效边界组织成答案。",
            "Describe your new problem in natural language. The engine extracts its structural "
            "signature, searches the library, then composes the matched mechanism + rationale + "
            "boundaries into an answer."))
        ask_hint.setWordWrap(True)
        ask_hint.setStyleSheet(f"color: {p.ink_secondary}; font-size: 12px; background: transparent;")
        ask_lay.addWidget(ask_hint)
        self.question_edit = QTextEdit()
        self.question_edit.setFixedHeight(100)
        ask_lay.addWidget(self.question_edit)
        ask_row = QHBoxLayout()
        self.ask_btn = QPushButton(tr("提问", "Ask"))
        self.ask_btn.setObjectName("primary")
        self.ask_btn.clicked.connect(self._run_ask)
        ask_row.addWidget(self.ask_btn)
        ask_row.addStretch(1)
        ask_lay.addLayout(ask_row)
        self.ask_result_box = QVBoxLayout()
        self.ask_result_box.setSpacing(10)
        ask_lay.addLayout(self.ask_result_box)
        ask_lay.addStretch(1)
        self.tabs.addTab(ask_tab, tr("描述问题（LLM）", "Describe a problem (LLM)"))

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.ask_btn.setEnabled(not self.app.busy)

    def _run_keyword(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        query = self.kw_edit.text().strip()
        if not query:
            return
        hits = ws.search_principles(query, top_k=20)
        self.kw_results.clear()
        for hit in hits:
            item = QListWidgetItem(
                f'{hit.id}   ·   {hit.title}   ·   '
                + tr(f"分数 {hit.score}", f"score {hit.score}"))
            item.setData(Qt.ItemDataRole.UserRole, hit.id)
            self.kw_results.addItem(item)
        self.kw_note.setText(
            "" if hits else tr("没有匹配 — 这可能是知识库的空白",
                               "No match — possibly a gap in the library"))

    def _run_ask(self) -> None:
        question = self.question_edit.toPlainText().strip()
        if not question:
            return
        self.app.run_pipeline(
            tr("提问", "Ask"),
            lambda pipe: pipe.ask(question),
            on_result=self._show_ask_result,
        )

    def _show_ask_result(self, result) -> None:
        if not isinstance(result, AskResult):
            return
        p = palette()
        clear_layout(self.ask_result_box)
        self.ask_result_box.addWidget(
            TagWrap(tr("抽取的问题签名", "Extracted problem signature"), result.signature, p.accent))
        if result.math_basis:
            self.ask_result_box.addWidget(
                TagWrap(tr("候选数学机制", "Candidate math machinery"), result.math_basis, p.ultra_violet))
        self.ask_result_box.addWidget(section_label(tr("回答", "Answer")))
        answer = QTextBrowser()
        answer.setMarkdown(result.answer)
        answer.setOpenExternalLinks(False)
        answer.setMinimumHeight(220)
        self.ask_result_box.addWidget(answer)
        if result.hits:
            self.ask_result_box.addWidget(section_label(tr("命中原则", "Matched principles")))
            lst = QListWidget()
            lst.setObjectName("contentList")
            for hit in result.hits:
                item = QListWidgetItem(
                    f'{hit.id}   ·   {hit.title}   ·   '
                    + tr(f"分数 {hit.score}", f"score {hit.score}"))
                item.setData(Qt.ItemDataRole.UserRole, hit.id)
                lst.addItem(item)
            lst.setFixedHeight(min(len(result.hits), 6) * 32 + 10)
            lst.itemClicked.connect(
                lambda it: self.app.show_principle(it.data(Qt.ItemDataRole.UserRole)))
            self.ask_result_box.addWidget(lst)
