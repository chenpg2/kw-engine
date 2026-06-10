"""Synthesis — Layer-3 artifacts: design-space map, contradictions, gaps."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QVBoxLayout, QWidget,
)

from ..l10n import tr
from ..theme import palette


DOCS = [
    ("design-space.md", lambda: tr("设计空间", "Design space")),
    ("contradictions.md", lambda: tr("矛盾", "Contradictions")),
    ("gaps.md", lambda: tr("空白", "Gaps")),
]


class SynthesisPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.current_doc = "design-space.md"
        p = palette()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 14, 20, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.doc_group = QButtonGroup(self)
        for i, (filename, label_fn) in enumerate(DOCS):
            btn = QPushButton(label_fn())
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            self.doc_group.addButton(btn, i)
            top.addWidget(btn)
        self.doc_group.idClicked.connect(self._switch_doc)
        top.addStretch(1)
        self.last_run_lab = QLabel("")
        self.last_run_lab.setStyleSheet(
            f"color: {p.ink_secondary}; font-size: 11.5px; background: transparent;")
        top.addWidget(self.last_run_lab)
        self.run_btn = QPushButton(tr("运行综合 (L3)", "Synthesize (L3)"))
        self.run_btn.setObjectName("primary")
        self.run_btn.clicked.connect(self._run_l3)
        top.addWidget(self.run_btn)
        lay.addLayout(top)

        self.banner = QFrame()
        self.banner.setObjectName("banner")
        blay = QHBoxLayout(self.banner)
        blay.setContentsMargins(12, 7, 12, 7)
        self.banner_lab = QLabel("")
        self.banner_lab.setStyleSheet(f"color: {p.ink}; font-size: 12px; background: transparent;")
        blay.addWidget(self.banner_lab)
        blay.addStretch(1)
        self.banner.hide()
        lay.addWidget(self.banner)

        self.viewer = QTextBrowser()
        lay.addWidget(self.viewer, 1)

    def _switch_doc(self, idx: int) -> None:
        self.current_doc = DOCS[idx][0]
        self._load_doc()

    def refresh(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        self.run_btn.setEnabled(not self.app.busy)
        try:
            idx = ws.read_index()
            n = len(idx["principles"])
            syn = idx["synthesis"]
            last = syn.get("last_run")
            n_at_last = syn.get("n_principles_at_last_run", 0)
        except Exception:
            n, last, n_at_last = 0, None, 0
        self.run_btn.setEnabled(not self.app.busy and n > 0)
        if last:
            self.last_run_lab.setText(
                tr(f"上次综合：{last}（覆盖 {n_at_last} 条原则）",
                   f"Last run: {last} (over {n_at_last} principles)"))
        else:
            self.last_run_lab.setText(tr("尚未综合", "Never synthesized"))
        stale = n > n_at_last
        if stale and n > 0:
            self.banner_lab.setText(
                tr(f"⚠ 综合已过期：自上次综合以来新增了 {n - n_at_last} 条原则。",
                   f"⚠ Synthesis is stale: {n - n_at_last} principles added since the last run."))
            self.banner.show()
        else:
            self.banner.hide()
        self._load_doc()

    def _load_doc(self) -> None:
        ws = self.app.workspace
        if ws is None:
            return
        text = ws.read_synthesis_doc(self.current_doc)
        if text:
            self.viewer.setMarkdown(text)
        else:
            self.viewer.setMarkdown(
                tr("_还没有综合产物。积累若干原则后运行 L3。_",
                   "_No synthesis artifacts yet. Accumulate some principles, then run L3._"))

    def _run_l3(self) -> None:
        self.app.run_pipeline(tr("L3 · 综合", "L3 · synthesis"), lambda pipe: pipe.run_l3())
