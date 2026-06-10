"""Main window — welcome / (sidebar + pages), pipeline runner, log dock."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

from .. import settings as cfg
from ..l10n import tr
from ..llm import LLMClient, LLMError
from ..pipeline import Pipeline
from ..store import Workspace
from ..theme import palette
from .papers_page import PapersPage
from .principles_page import PrinciplesPage
from .search_page import SearchPage
from .settings_page import SettingsPage
from .status_page import StatusPage
from .synthesis_page import SynthesisPage
from .widgets import EngineGlyph
from .workers import Worker

from PySide6.QtWidgets import QMainWindow


SECTIONS = [
    ("status", lambda: tr("状态", "Status")),
    ("papers", lambda: tr("论文", "Papers")),
    ("principles", lambda: tr("原则", "Principles")),
    ("search", lambda: tr("检索 / 提问", "Search / Ask")),
    ("synthesis", lambda: tr("综合", "Synthesis")),
    ("settings", lambda: tr("设置", "Settings")),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.workspace: Workspace | None = None
        self.busy = False
        self._worker: Worker | None = None
        self._on_result = None

        self.setWindowTitle("KW Engine")
        self.resize(1180, 740)

        self.root_stack = QStackedWidget()
        self.setCentralWidget(self.root_stack)
        self.root_stack.addWidget(self._build_welcome())   # 0
        self.root_stack.addWidget(self._build_main())      # 1

        self._build_log_dock()
        self.statusBar().showMessage(tr("就绪", "Ready"))

        path = cfg.load_workspace_path()
        if path and Workspace.is_workspace(Path(path)):
            self._open(Path(path))

    # ------------------------------------------------------------ welcome
    def _build_welcome(self) -> QWidget:
        p = palette()
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch(3)
        glyph_row = QHBoxLayout()
        glyph_row.addStretch(1)
        glyph_row.addWidget(EngineGlyph(112))
        glyph_row.addStretch(1)
        lay.addLayout(glyph_row)
        title = QLabel("KW Engine")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {p.ink}; font-size: 28px; font-weight: 600; background: transparent;")
        lay.addWidget(title)
        sub = QLabel(tr("方法论进化引擎 — 蒸馏 · 抽象 · 综合 · 按结构检索",
                        "Methodology evolution engine — distill · abstract · synthesize · search by structure"))
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color: {p.ink_secondary}; font-size: 13px; background: transparent;")
        lay.addWidget(sub)
        lay.addSpacing(22)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        open_btn = QPushButton(tr("打开知识库…", "Open Workspace…"))
        open_btn.setObjectName("primary")
        open_btn.setMinimumWidth(170)
        open_btn.clicked.connect(self.open_workspace_dialog)
        create_btn = QPushButton(tr("新建知识库…", "Create Workspace…"))
        create_btn.setMinimumWidth(170)
        create_btn.clicked.connect(self.create_workspace_dialog)
        btn_row.addWidget(open_btn)
        btn_row.addSpacing(10)
        btn_row.addWidget(create_btn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)
        lay.addSpacing(18)
        note = QLabel(tr(
            "知识库与 kw CLI / Claude Code 插件完全互通 — markdown 为真相，索引为派生。\n首次使用请先在「设置」中配置 LLM API。",
            "Workspaces interoperate with the kw CLI / Claude Code plugin — markdown is truth.\n"
            "First time? Configure your LLM API in Settings."))
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color: {p.ink_secondary}; font-size: 11.5px; background: transparent;")
        lay.addWidget(note)
        lay.addStretch(4)
        return page

    # ------------------------------------------------------------ main split
    def _build_main(self) -> QWidget:
        p = palette()
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        side = QWidget()
        side.setFixedWidth(176)
        side.setStyleSheet(f"background: {p.sidebar};")
        slay = QVBoxLayout(side)
        slay.setContentsMargins(0, 8, 0, 8)
        slay.setSpacing(4)
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        for key, label_fn in SECTIONS:
            item = QListWidgetItem(label_fn())
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self._on_section)
        slay.addWidget(self.sidebar, 1)

        self.ws_label = QLabel("")
        self.ws_label.setStyleSheet(
            f"color: {p.ink_secondary}; font-size: 11px; padding: 0 10px; background: transparent;")
        self.ws_label.setWordWrap(True)
        slay.addWidget(self.ws_label)
        foot = QHBoxLayout()
        foot.setContentsMargins(8, 0, 8, 0)
        log_btn = QPushButton(tr("日志", "Log"))
        log_btn.clicked.connect(self._toggle_log)
        switch_btn = QPushButton(tr("切换", "Switch"))
        switch_btn.setToolTip(tr("切换知识库", "Switch knowledge base"))
        switch_btn.clicked.connect(self.close_workspace)
        foot.addWidget(log_btn)
        foot.addWidget(switch_btn)
        slay.addLayout(foot)
        lay.addWidget(side)

        self.pages = QStackedWidget()
        self.page_map: dict[str, QWidget] = {
            "status": StatusPage(self),
            "papers": PapersPage(self),
            "principles": PrinciplesPage(self),
            "search": SearchPage(self),
            "synthesis": SynthesisPage(self),
            "settings": SettingsPage(self),
        }
        for key, _ in SECTIONS:
            self.pages.addWidget(self.page_map[key])
        lay.addWidget(self.pages, 1)
        return page

    def _build_log_dock(self) -> None:
        self.log_dock = QDockWidget(tr("运行日志", "Pipeline log"), self)
        self.log_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(120)
        self.log_dock.setWidget(self.log_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        self.log_dock.hide()

    # ------------------------------------------------------------ workspace
    def open_workspace_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, tr("选择已有的 kw 知识库文件夹（包含 memory/）",
                     "Choose an existing kw workspace folder (containing memory/)"))
        if not path:
            return
        root = Path(path)
        if not Workspace.is_workspace(root):
            self.show_error(tr(
                "该文件夹不是 kw 知识库（缺少 memory/index.json）。请选择已有知识库，或使用「新建知识库」。",
                "That folder is not a kw workspace (no memory/index.json)."))
            return
        self._open(root)

    def create_workspace_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, tr("选择一个文件夹，将在其中创建知识库结构（memory/、paper/ 等）",
                     "Choose a folder; the workspace structure will be created inside it"))
        if not path:
            return
        root = Path(path)
        try:
            Workspace.scaffold(root)
        except Exception as e:
            self.show_error(str(e))
            return
        self._open(root)

    def _open(self, root: Path) -> None:
        self.workspace = Workspace(root)
        cfg.save_workspace_path(str(root))
        self.ws_label.setText(root.name)
        self.root_stack.setCurrentIndex(1)
        if self.sidebar.currentRow() < 0:
            self.sidebar.setCurrentRow(0)
        self.refresh_all()

    def close_workspace(self) -> None:
        self.workspace = None
        cfg.save_workspace_path("")
        self.root_stack.setCurrentIndex(0)

    # ------------------------------------------------------------ navigation
    def _on_section(self, row: int) -> None:
        if row < 0:
            return
        self.pages.setCurrentIndex(row)
        page = self.pages.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def _go(self, key: str) -> None:
        for i, (k, _) in enumerate(SECTIONS):
            if k == key:
                self.sidebar.setCurrentRow(i)
                return

    def show_paper(self, pid: str) -> None:
        self._go("papers")
        self.page_map["papers"].select_paper(pid)

    def show_principle(self, pid: str) -> None:
        self._go("principles")
        self.page_map["principles"].select_principle(pid)

    def refresh_all(self) -> None:
        for page in self.page_map.values():
            if hasattr(page, "refresh"):
                page.refresh()

    def show_error(self, message: str) -> None:
        QMessageBox.warning(self, tr("出错了", "Error"), message)

    # ------------------------------------------------------------ pipeline
    def run_pipeline(self, activity: str, step, on_result=None) -> None:
        """step: callable(pipeline) -> result. Runs in a worker thread."""
        if self.busy:
            self.show_error(tr("已有任务在运行", "A pipeline run is already in progress"))
            return
        ws = self.workspace
        if ws is None:
            return
        try:
            s = cfg.load_llm_settings()
            if not s.base_url:
                raise LLMError(tr("尚未配置 API 地址 — 请打开设置填写 Base URL",
                                  "API base URL not configured — open Settings"))
            if not s.strong_model:
                raise LLMError(tr("尚未配置模型 ID — 请打开设置",
                                  "Model id not configured — open Settings"))
            key = cfg.load_api_key()
            if not key:
                raise LLMError(tr("尚未配置 API Key — 请打开设置",
                                  "API key not configured — open Settings"))
        except LLMError as e:
            self.show_error(str(e))
            self._go("settings")
            return

        def fn(log):
            client = LLMClient(s, key)
            pipe = Pipeline(ws, client, log)
            return step(pipe)

        self.busy = True
        self._on_result = on_result
        self.statusBar().showMessage(tr(f"运行中：{activity} …", f"Running: {activity} …"))
        self.log_dock.show()
        self._append_log("info", f"——— {activity} ———")
        worker = Worker(fn)
        worker.log_line.connect(self._append_log)
        worker.done.connect(self._on_worker_done)
        worker.failed.connect(self._on_worker_failed)
        self._worker = worker
        self.refresh_all()
        worker.start()

    def _on_worker_done(self, result) -> None:
        self.busy = False
        self.statusBar().showMessage(tr("完成", "Done"), 5000)
        self.refresh_all()
        if self._on_result is not None:
            cb, self._on_result = self._on_result, None
            cb(result)

    def _on_worker_failed(self, message: str) -> None:
        self.busy = False
        self._on_result = None
        self._append_log("error", message)
        self.statusBar().showMessage(tr("失败", "Failed"), 5000)
        self.refresh_all()
        self.show_error(message)

    def _append_log(self, level: str, text: str) -> None:
        p = palette()
        color = {"info": p.ink_secondary, "warn": p.saffron,
                 "error": p.fiery_red, "success": p.emerald}.get(level, p.ink)
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(
            f'<span style="color:{p.ink_secondary}">[{stamp}]</span> '
            f'<span style="color:{color}">{html.escape(text)}</span>')

    def _toggle_log(self) -> None:
        self.log_dock.setVisible(not self.log_dock.isVisible())
