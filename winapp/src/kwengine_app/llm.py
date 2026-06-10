"""LLM client — OpenAI-compatible and Anthropic protocols, user-configured.
No silent fallback: HTTP errors and malformed model output raise with detail."""

from __future__ import annotations

import json
from dataclasses import dataclass

import requests


class LLMError(Exception):
    pass


PROTOCOL_OPENAI = "openai"
PROTOCOL_ANTHROPIC = "anthropic"


@dataclass
class LLMSettings:
    protocol: str = PROTOCOL_OPENAI
    base_url: str = ""
    strong_model: str = ""
    fast_model: str = ""
    max_tokens: int = 8192
    temperature: float = 0.2
    timeout: float = 600.0
    max_pdf_chars: int = 120_000

    @property
    def fast_model_effective(self) -> str:
        return self.fast_model or self.strong_model

    def endpoint(self) -> str:
        """Deterministic endpoint derivation — previewed live in Settings."""
        base = self.base_url.strip().rstrip("/")
        if not base:
            return ""
        if self.protocol == PROTOCOL_OPENAI:
            if base.endswith("/chat/completions"):
                return base
            return base + "/chat/completions"
        if base.endswith("/messages"):
            return base
        if base.endswith("/v1"):
            return base + "/messages"
        return base + "/v1/messages"


class LLMClient:
    def __init__(self, settings: LLMSettings, api_key: str):
        self.settings = settings
        self.api_key = api_key

    def complete(self, system: str, user: str, model: str) -> str:
        url = self.settings.endpoint()
        if not url:
            raise LLMError("API base URL is not set (open Settings)")
        if not model:
            raise LLMError("Model id is not set (open Settings)")

        if self.settings.protocol == PROTOCOL_OPENAI:
            headers = {"Authorization": f"Bearer {self.api_key}",
                       "Content-Type": "application/json"}
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": self.settings.temperature,
                "max_tokens": self.settings.max_tokens,
                "stream": False,
            }
        else:
            headers = {"x-api-key": self.api_key,
                       "anthropic-version": "2023-06-01",
                       "Content-Type": "application/json"}
            payload = {
                "model": model,
                "max_tokens": self.settings.max_tokens,
                "temperature": self.settings.temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }

        try:
            resp = requests.post(url, headers=headers, json=payload,
                                 timeout=self.settings.timeout)
        except requests.RequestException as e:
            raise LLMError(f"Network request failed: {e}") from e

        body_text = resp.text or ""
        if not (200 <= resp.status_code < 300):
            raise LLMError(f"API returned HTTP {resp.status_code}: {body_text[:600]}")
        try:
            data = resp.json()
        except ValueError:
            raise LLMError(f"API response is not JSON: {body_text[:300]}") from None

        if self.settings.protocol == PROTOCOL_OPENAI:
            try:
                content = data["choices"][0]["message"]["content"]
            except (KeyError, IndexError, TypeError):
                raise LLMError(f"Unexpected OpenAI-compatible response shape: {body_text[:400]}") from None
            if not content:
                raise LLMError(f"Empty completion content: {body_text[:400]}")
            return content
        blocks = data.get("content")
        if not isinstance(blocks, list):
            raise LLMError(f"Unexpected Anthropic response shape: {body_text[:400]}")
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text:
            raise LLMError(f"Anthropic response contained no text blocks: {body_text[:400]}")
        return text

    def complete_json(self, system: str, user: str, model: str):
        raw = self.complete(system, user, model)
        return extract_json(raw)

    def test_connection(self, model: str) -> str:
        import time
        started = time.time()
        reply = self.complete(
            system="You are a connectivity test. Reply with exactly: OK",
            user="ping", model=model)
        ms = int((time.time() - started) * 1000)
        return f"{ms} ms — {reply[:80]}"


def extract_json(text: str):
    """Pull the first JSON object/array out of a model reply (handles ``` fences)."""
    if "```" in text:
        parts = text.split("```")
        i = 1
        while i < len(parts):
            candidate = parts[i]
            nl = candidate.find("\n")
            if nl != -1:
                first_line = candidate[:nl].strip().lower()
                if first_line in ("json", ""):
                    candidate = candidate[nl + 1:]
            candidate = candidate.strip()
            if candidate.startswith("{") or candidate.startswith("["):
                try:
                    return json.loads(candidate)
                except ValueError:
                    pass
            i += 2
    snippet = _first_balanced_json(text)
    if snippet is not None:
        try:
            return json.loads(snippet)
        except ValueError:
            pass
    raise LLMError(f"No valid JSON found in model output. Output starts: {text[:400]}")


def _first_balanced_json(text: str) -> str | None:
    start = -1
    open_char = ""
    for i, ch in enumerate(text):
        if ch in "{[":
            start, open_char = i, ch
            break
    if start == -1:
        return None
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
        elif in_string:
            if ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == open_char:
                depth += 1
            elif ch == close_char:
                depth -= 1
                if depth == 0:
                    return text[start:i + 1]
    return None


# Lenient accessors for model-produced dicts (mirror the Swift flex helpers)

def flex_str(d: dict, key: str) -> str:
    v = d.get(key)
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def flex_list(d: dict, key: str) -> list[str]:
    v = d.get(key)
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x).strip() for x in v if x is not None and str(x).strip()]
    s = str(v).strip()
    return [s] if s else []


def flex_int(d: dict, key: str):
    v = d.get(key)
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            return None
    return None
