"""Keyword-based principle search over the kw-engine memory store.

Scores each principle by counting how many query tokens appear as substrings
in its ``problem_signature`` or ``math_basis`` fields (case-insensitive).
Returns principles sorted by score descending, filtered to score > 0.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens on whitespace and hyphens."""
    return [t for t in re.split(r"[\s\-]+", text.lower()) if t]


def search_principles(
    memory_dir: Path,
    query: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search principles by keyword overlap with problem_signature and math_basis.

    Args:
        memory_dir: Path to the ``memory/`` directory containing ``index.json``.
        query: Free-text query string; tokenised on whitespace and hyphens.
        top_k: Maximum number of results to return.

    Returns:
        List of principle dicts (from index.json) augmented with a ``score`` key,
        sorted by score descending, filtered to score > 0.
    """
    idx_path = memory_dir / "index.json"
    idx: dict[str, Any] = json.loads(idx_path.read_text(encoding="utf-8"))
    principles: list[dict[str, Any]] = idx.get("principles", [])

    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[dict[str, Any]] = []
    for principle in principles:
        # Build a single searchable text from the relevant fields
        sig_items: list[str] = principle.get("problem_signature") or []
        math_items: list[str] = principle.get("math_basis") or []
        haystack = " ".join(sig_items + math_items).lower()

        score = sum(1 for token in query_tokens if token in haystack)
        if score > 0:
            result = dict(principle)
            result["score"] = score
            scored.append(result)

    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:top_k]
