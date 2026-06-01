"""Keyword-based principle search over the kw-engine memory store.

Scores each principle by counting how many query tokens appear as substrings
in its ``problem_signature`` or ``math_basis`` fields (case-insensitive).

Search strategy (in priority order):
1. SQLite: query ``.kw/index.db`` using LIKE on ``principle_signatures`` and
   ``principle_math_basis`` tables — fast and always in sync after mutations.
2. JSON fallback: read ``index.json`` if ``.kw/index.db`` doesn't exist (e.g.
   before the user has run ``kw reindex``).

Returns principles sorted by score descending, filtered to score > 0.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens on whitespace and hyphens."""
    return [t for t in re.split(r"[\s\-]+", text.lower()) if t]


def _search_via_sqlite(
    db_path: Path,
    query_tokens: list[str],
    top_k: int,
) -> list[dict[str, Any]] | None:
    """Query index.db via SQLite LIKE.

    Returns a list of scored principle dicts on success, or ``None`` if the db
    is absent or the query fails (caller should fall back to JSON).
    """
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Count token hits per principle_id across both signature and basis tables
        hit_counts: dict[str, int] = {}
        for token in query_tokens:
            pattern = f"%{token}%"
            rows = conn.execute(
                """
                SELECT DISTINCT principle_id FROM principle_signatures
                WHERE signature LIKE ?
                UNION
                SELECT DISTINCT principle_id FROM principle_math_basis
                WHERE basis LIKE ?
                """,
                (pattern, pattern),
            ).fetchall()
            for row in rows:
                pid = row[0]
                hit_counts[pid] = hit_counts.get(pid, 0) + 1

        if not hit_counts:
            conn.close()
            return []

        # Fetch titles for matched principle ids
        placeholders = ",".join("?" * len(hit_counts))
        title_rows = conn.execute(
            f"SELECT id, title FROM principles WHERE id IN ({placeholders})",
            list(hit_counts.keys()),
        ).fetchall()
        conn.close()

        id_to_title: dict[str, str] = {r[0]: r[1] for r in title_rows}

        scored: list[dict[str, Any]] = []
        for pid, count in hit_counts.items():
            scored.append({
                "id": pid,
                "title": id_to_title.get(pid, ""),
                "score": count,
            })

        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    except sqlite3.Error:
        return None


def _search_via_json(
    memory_dir: Path,
    query_tokens: list[str],
    top_k: int,
) -> list[dict[str, Any]]:
    """Fallback: scan index.json (original behaviour)."""
    idx_path = memory_dir / "index.json"
    idx: dict[str, Any] = json.loads(idx_path.read_text(encoding="utf-8"))
    principles: list[dict[str, Any]] = idx.get("principles", [])

    scored: list[dict[str, Any]] = []
    for principle in principles:
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


def search_principles(
    memory_dir: Path,
    query: str,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search principles by keyword overlap with problem_signature and math_basis.

    First tries the SQLite index at ``.kw/index.db`` (sibling of ``memory/``).
    Falls back to reading ``index.json`` if the database doesn't exist yet.

    Args:
        memory_dir: Path to the ``memory/`` directory containing ``index.json``.
        query: Free-text query string; tokenised on whitespace and hyphens.
        top_k: Maximum number of results to return.

    Returns:
        List of principle dicts augmented with a ``score`` key,
        sorted by score descending, filtered to score > 0.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    # Try SQLite first (.kw/ is a sibling of memory/)
    kw_dir = memory_dir.parent / ".kw"
    db_path = kw_dir / "index.db"
    sqlite_results = _search_via_sqlite(db_path, query_tokens, top_k)
    if sqlite_results is not None:
        return sqlite_results

    # Fallback: read index.json
    return _search_via_json(memory_dir, query_tokens, top_k)
