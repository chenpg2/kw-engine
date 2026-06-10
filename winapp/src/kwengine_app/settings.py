"""Settings persistence: QSettings for parameters, OS credential store for the API key
(Windows Credential Manager via keyring; falls back to QSettings with a warning flag)."""

from __future__ import annotations

from PySide6.QtCore import QSettings

from .llm import PROTOCOL_OPENAI, LLMSettings

ORG = "kw-engine"
APP = "KWEngine"
KEYRING_SERVICE = "kw-engine-app"
KEYRING_USER = "llm-api-key"


def _qs() -> QSettings:
    return QSettings(ORG, APP)


def load_llm_settings() -> LLMSettings:
    q = _qs()
    return LLMSettings(
        protocol=str(q.value("llm/protocol", PROTOCOL_OPENAI)),
        base_url=str(q.value("llm/baseURL", "")),
        strong_model=str(q.value("llm/strongModel", "")),
        fast_model=str(q.value("llm/fastModel", "")),
        max_tokens=int(q.value("llm/maxTokens", 8192)),
        temperature=float(q.value("llm/temperature", 0.2)),
        timeout=float(q.value("llm/timeout", 600.0)),
        max_pdf_chars=int(q.value("llm/maxPDFChars", 120_000)),
    )


def save_llm_settings(s: LLMSettings) -> None:
    q = _qs()
    q.setValue("llm/protocol", s.protocol)
    q.setValue("llm/baseURL", s.base_url)
    q.setValue("llm/strongModel", s.strong_model)
    q.setValue("llm/fastModel", s.fast_model)
    q.setValue("llm/maxTokens", s.max_tokens)
    q.setValue("llm/temperature", s.temperature)
    q.setValue("llm/timeout", s.timeout)
    q.setValue("llm/maxPDFChars", s.max_pdf_chars)


def save_api_key(key: str) -> str:
    """Returns where the key was stored: 'keyring' or 'qsettings'."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)
        _qs().remove("llm/apiKeyPlain")
        return "keyring"
    except Exception:
        _qs().setValue("llm/apiKeyPlain", key)
        return "qsettings"


def load_api_key() -> str:
    try:
        import keyring
        v = keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
        if v:
            return v
    except Exception:
        pass
    return str(_qs().value("llm/apiKeyPlain", ""))


def load_workspace_path() -> str:
    return str(_qs().value("workspace/path", ""))


def save_workspace_path(path: str) -> None:
    if path:
        _qs().setValue("workspace/path", path)
    else:
        _qs().remove("workspace/path")
