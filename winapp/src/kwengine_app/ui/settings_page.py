"""Settings — user-configured LLM provider: protocol, base URL, API key, model ids."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from .. import settings as cfg
from ..l10n import tr
from ..llm import PROTOCOL_ANTHROPIC, PROTOCOL_OPENAI, LLMClient, LLMSettings
from ..theme import palette
from .widgets import Card, section_label
from .workers import Worker


class SettingsPage(QWidget):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self._loading = True
        self._test_worker: Worker | None = None
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
        lay.setSpacing(14)

        title = QLabel(tr("设置", "Settings"))
        title.setStyleSheet(f"color: {p.ink}; font-size: 20px; font-weight: 600; background: transparent;")
        lay.addWidget(title)

        # provider card -----------------------------------------------------
        provider = Card()
        provider.add(section_label(tr("LLM 提供方", "LLM provider")))
        form = QFormLayout()
        form.setSpacing(9)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItem("OpenAI-compatible (/chat/completions)", PROTOCOL_OPENAI)
        self.protocol_combo.addItem("Anthropic (/v1/messages)", PROTOCOL_ANTHROPIC)
        form.addRow(tr("协议", "Protocol"), self.protocol_combo)

        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.deepseek.com")
        form.addRow(tr("API 地址 (Base URL)", "API Base URL"), self.base_url_edit)

        self.endpoint_lab = QLabel("—")
        self.endpoint_lab.setStyleSheet(
            f"color: {p.ink_secondary}; font-size: 11px; font-family: Consolas, monospace; background: transparent;")
        self.endpoint_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(tr("实际请求端点", "Resolved endpoint"), self.endpoint_lab)

        key_row = QHBoxLayout()
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-…")
        self.key_save_btn = QPushButton(tr("保存", "Save"))
        self.key_save_btn.clicked.connect(self._save_key)
        key_row.addWidget(self.key_edit)
        key_row.addWidget(self.key_save_btn)
        form.addRow("API Key", key_row)
        self.key_note = QLabel("")
        self.key_note.setStyleSheet(f"color: {p.emerald}; font-size: 11px; background: transparent;")
        form.addRow("", self.key_note)
        provider.add_layout(form)

        examples = QLabel(tr(
            "示例 — DeepSeek: https://api.deepseek.com · Kimi: https://api.moonshot.cn/v1 · "
            "本地 Ollama: http://localhost:11434/v1 · Anthropic 协议: https://api.anthropic.com",
            "Examples — DeepSeek: https://api.deepseek.com · Kimi: https://api.moonshot.cn/v1 · "
            "local Ollama: http://localhost:11434/v1 · Anthropic protocol: https://api.anthropic.com"))
        examples.setWordWrap(True)
        examples.setStyleSheet(f"color: {p.ink_secondary}; font-size: 11px; background: transparent;")
        provider.add(examples)
        lay.addWidget(provider)

        # models card ---------------------------------------------------------
        models = Card()
        models.add(section_label(tr("模型", "Models")))
        mform = QFormLayout()
        mform.setSpacing(9)
        mform.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.strong_edit = QLineEdit()
        self.strong_edit.setPlaceholderText("deepseek-reasoner / claude-sonnet-4-6 / …")
        mform.addRow(tr("强模型（蒸馏/综合/回答）", "Strong model (distill/synthesize/answer)"),
                     self.strong_edit)
        self.fast_edit = QLineEdit()
        self.fast_edit.setPlaceholderText(tr("留空 = 用强模型", "empty = strong model"))
        mform.addRow(tr("快模型（读取/结构抽取）", "Fast model (read/extract)"), self.fast_edit)
        models.add_layout(mform)
        routing = QLabel(tr("沿用 kw-engine 的「读取用便宜模型、蒸馏用强模型」路由。",
                            "Mirrors kw-engine's read-cheap / distill-strong model routing."))
        routing.setStyleSheet(f"color: {p.ink_secondary}; font-size: 11px; background: transparent;")
        models.add(routing)
        lay.addWidget(models)

        # parameters card --------------------------------------------------------
        params = Card()
        params.add(section_label(tr("参数", "Parameters")))
        pform = QFormLayout()
        pform.setSpacing(9)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(256, 200_000)
        self.max_tokens_spin.setSingleStep(1024)
        pform.addRow("max_tokens", self.max_tokens_spin)
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        pform.addRow("temperature", self.temperature_spin)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 3600)
        self.timeout_spin.setSuffix(" s")
        pform.addRow(tr("请求超时", "Request timeout"), self.timeout_spin)
        self.max_pdf_spin = QSpinBox()
        self.max_pdf_spin.setRange(10_000, 2_000_000)
        self.max_pdf_spin.setSingleStep(10_000)
        pform.addRow(tr("PDF 文本上限（字符）", "Max PDF text (chars)"), self.max_pdf_spin)
        params.add_layout(pform)
        lay.addWidget(params)

        # test row -------------------------------------------------------------
        test_row = QHBoxLayout()
        self.test_btn = QPushButton(tr("测试连接", "Test connection"))
        self.test_btn.clicked.connect(self._test_connection)
        self.test_lab = QLabel("")
        self.test_lab.setWordWrap(True)
        self.test_lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        test_row.addWidget(self.test_btn)
        test_row.addWidget(self.test_lab, 1)
        lay.addLayout(test_row)
        lay.addStretch(1)

        self._load()
        for sig in (self.base_url_edit.textChanged, self.strong_edit.textChanged,
                    self.fast_edit.textChanged):
            sig.connect(self._on_change)
        self.protocol_combo.currentIndexChanged.connect(self._on_change)
        self.max_tokens_spin.valueChanged.connect(self._on_change)
        self.temperature_spin.valueChanged.connect(self._on_change)
        self.timeout_spin.valueChanged.connect(self._on_change)
        self.max_pdf_spin.valueChanged.connect(self._on_change)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        pass

    def _load(self) -> None:
        self._loading = True
        s = cfg.load_llm_settings()
        idx = self.protocol_combo.findData(s.protocol)
        self.protocol_combo.setCurrentIndex(max(0, idx))
        self.base_url_edit.setText(s.base_url)
        self.strong_edit.setText(s.strong_model)
        self.fast_edit.setText(s.fast_model)
        self.max_tokens_spin.setValue(s.max_tokens)
        self.temperature_spin.setValue(s.temperature)
        self.timeout_spin.setValue(int(s.timeout))
        self.max_pdf_spin.setValue(s.max_pdf_chars)
        self.key_edit.setText(cfg.load_api_key())
        self._loading = False
        self._update_endpoint()

    def _current_settings(self) -> LLMSettings:
        return LLMSettings(
            protocol=self.protocol_combo.currentData(),
            base_url=self.base_url_edit.text().strip(),
            strong_model=self.strong_edit.text().strip(),
            fast_model=self.fast_edit.text().strip(),
            max_tokens=self.max_tokens_spin.value(),
            temperature=self.temperature_spin.value(),
            timeout=float(self.timeout_spin.value()),
            max_pdf_chars=self.max_pdf_spin.value(),
        )

    def _on_change(self, *_args) -> None:
        if self._loading:
            return
        cfg.save_llm_settings(self._current_settings())
        self._update_endpoint()

    def _update_endpoint(self) -> None:
        ep = self._current_settings().endpoint()
        self.endpoint_lab.setText(ep or "—")

    def _save_key(self) -> None:
        p = palette()
        where = cfg.save_api_key(self.key_edit.text())
        if where == "keyring":
            self.key_note.setStyleSheet(f"color: {p.emerald}; font-size: 11px; background: transparent;")
            self.key_note.setText(tr("已存入系统凭据管理器", "Saved to the OS credential store"))
        else:
            self.key_note.setStyleSheet(f"color: {p.saffron}; font-size: 11px; background: transparent;")
            self.key_note.setText(tr("凭据管理器不可用 — 已明文存入设置（注意安全）",
                                     "Credential store unavailable — saved as plain text in settings"))

    def _test_connection(self) -> None:
        p = palette()
        s = self._current_settings()
        s.max_tokens = 64
        s.temperature = 0.0
        s.timeout = min(s.timeout, 60.0)
        key = self.key_edit.text() or cfg.load_api_key()
        if self.key_edit.text():
            self._save_key()
        client = LLMClient(s, key)
        model = s.strong_model
        self.test_btn.setEnabled(False)
        self.test_lab.setStyleSheet(f"color: {p.ink_secondary}; background: transparent;")
        self.test_lab.setText(tr("测试中…", "Testing…"))

        worker = Worker(lambda log: client.test_connection(model))

        def on_done(result):
            self.test_lab.setStyleSheet(f"color: {p.emerald}; background: transparent;")
            self.test_lab.setText(f"✓ {result}")
            self.test_btn.setEnabled(True)

        def on_failed(msg):
            self.test_lab.setStyleSheet(f"color: {p.fiery_red}; background: transparent;")
            self.test_lab.setText(msg)
            self.test_btn.setEnabled(True)

        worker.done.connect(on_done)
        worker.failed.connect(on_failed)
        self._test_worker = worker
        worker.start()
