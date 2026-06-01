"""Atomic mutation operations on the kw-engine memory store.

Each operation:
1. Reads index.json into memory.
2. Validates pre-conditions.
3. Writes the markdown file (new or modified).
4. Writes index.json back atomically via a temp-file rename.
5. If ``.kw/index.db`` exists, inserts the new record into SQLite so that
   search results stay fresh without requiring a manual ``kw reindex``.
"""

from __future__ import annotations

import fcntl
import json
import sqlite3
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import yaml

from kw_engine.models import paper_id_from_provenance

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_RUBRIC_VERSION = "distill-rubric@v1"


@contextmanager
def _locked_index(memory_dir: Path) -> Generator[None, None, None]:
    """Acquire an exclusive lock on index.json for atomic read-modify-write.

    Prevents pid collision when multiple processes call add_principle,
    add_paper, or add_link simultaneously.
    """
    lock_path = memory_dir / ".index.lock"
    lock_path.touch(exist_ok=True)
    fd = open(lock_path)  # noqa: WPS515 — intentional long-lived fd
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()


_EXTRACT_TEMPLATE_VERSION = "extract-template@v1"


def _read_index(memory_dir: Path) -> dict[str, Any]:
    idx_path = memory_dir / "index.json"
    result: dict[str, Any] = json.loads(idx_path.read_text(encoding="utf-8"))
    return result


def _write_index_atomic(memory_dir: Path, idx: dict[str, Any]) -> None:
    """Write index.json atomically via a temp file in the same directory."""
    idx_path = memory_dir / "index.json"
    content = json.dumps(idx, indent=2, ensure_ascii=False)
    # Write to a sibling temp file then rename (atomic on POSIX)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=memory_dir,
        prefix=".index_tmp_",
        suffix=".json",
        delete=False,
    ) as tf:
        tf.write(content)
        tmp_path = Path(tf.name)
    tmp_path.replace(idx_path)


def _write_md_atomic(dest: Path, content: str) -> None:
    """Write a markdown file atomically."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=dest.parent,
        prefix=".tmp_",
        suffix=".md",
        delete=False,
    ) as tf:
        tf.write(content)
        tmp_path = Path(tf.name)
    tmp_path.replace(dest)


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split ``---`` frontmatter from body text.

    Returns (frontmatter_dict, body_text).
    """
    if not text.startswith("---"):
        raise ValueError("No YAML front-matter found")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Malformed front-matter (missing closing ---)")
    fm: dict[str, Any] = yaml.safe_load(parts[1]) or {}
    body: str = parts[2]
    return fm, body


def _render_frontmatter(fm: dict[str, Any], body: str) -> str:
    """Re-serialize frontmatter dict + body back into a markdown string."""
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---\n{body}"


def _insert_link_in_text(text: str, link_str: str) -> str:
    """Insert a link entry into the raw markdown text without re-serializing YAML.

    Handles two cases:
    - `links: []` → replace with `links:\n  - "link_str"`
    - `links:\n  - "existing"` → append `  - "link_str"` after the last link entry
    """
    import re

    # Case 1: links: [] (empty inline list)
    empty_pattern = r"(links:\s*)\[\]"
    if re.search(empty_pattern, text):
        return re.sub(empty_pattern, f'\\1\n  - "{link_str}"', text)

    # Case 2: links already has items — find the last `  - "..."` after `links:`
    lines = text.split("\n")
    last_link_idx = -1
    in_links = False
    for i, line in enumerate(lines):
        if line.startswith("links:"):
            in_links = True
            continue
        if in_links:
            if line.startswith("  - "):
                last_link_idx = i
            elif line and not line.startswith(" "):
                break

    if last_link_idx >= 0:
        lines.insert(last_link_idx + 1, f'  - "{link_str}"')
        return "\n".join(lines)

    # Fallback: append before closing ---
    parts = text.split("---", 2)
    if len(parts) >= 3:
        parts[1] = parts[1].rstrip() + f'\nlinks:\n  - "{link_str}"\n'
        return "---".join(parts)

    return text


# ---------------------------------------------------------------------------
# SQLite incremental sync helpers
# ---------------------------------------------------------------------------


def _get_db_path(memory_dir: Path) -> Path | None:
    """Return the path to ``.kw/index.db`` if it exists, else ``None``."""
    db_path = memory_dir.parent / ".kw" / "index.db"
    return db_path if db_path.exists() else None


def _sync_paper_sqlite(memory_dir: Path, paper_id: str, doi: str | None, title: str) -> None:
    """Insert a paper row into SQLite if index.db is present."""
    db_path = _get_db_path(memory_dir)
    if db_path is None:
        return
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT OR IGNORE INTO papers"
            " (id, status, doi, title, bib_authors, bib_venue, bib_year)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (paper_id, "pending", doi, title, "", "", None),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass  # SQLite sync is best-effort; JSON is the source of truth


def _sync_principle_sqlite(
    memory_dir: Path,
    pid: str,
    title: str,
    abstraction_level: str,
    mechanism: str,
    rationale: str,
    falsifiable_prediction: str,
    boundaries: str,
    rubric_version: str,
    problem_signature: list[str],
    math_basis: list[str],
    provenance: list[str],
    links: list[str],
) -> None:
    """Insert a principle and its child rows into SQLite if index.db is present."""
    db_path = _get_db_path(memory_dir)
    if db_path is None:
        return
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT OR IGNORE INTO principles"
            " (id, title, abstraction_level, mechanism, rationale,"
            "  falsifiable_prediction, boundaries, rubric_version)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pid, title, abstraction_level, mechanism, rationale,
             falsifiable_prediction, boundaries, rubric_version),
        )
        for sig in problem_signature:
            conn.execute(
                "INSERT INTO principle_signatures (principle_id, signature) VALUES (?, ?)",
                (pid, sig),
            )
        for basis in math_basis:
            conn.execute(
                "INSERT INTO principle_math_basis (principle_id, basis) VALUES (?, ?)",
                (pid, basis),
            )
        for prov in provenance:
            parts = prov.split(None, 1)
            paper_id = paper_id_from_provenance(prov)
            locator = parts[1] if len(parts) > 1 else ""
            conn.execute(
                "INSERT INTO principle_provenance (principle_id, paper_id, locator)"
                " VALUES (?, ?, ?)",
                (pid, paper_id, locator),
            )
            conn.execute(
                "INSERT OR IGNORE INTO paper_principles (paper_id, principle_id) VALUES (?, ?)",
                (paper_id, pid),
            )
        for link_str in links:
            if ":" in link_str:
                link_type, target = link_str.split(":", 1)
                conn.execute(
                    "INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                    (pid, target, link_type),
                )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass  # SQLite sync is best-effort; JSON is the source of truth


def _sync_link_sqlite(
    memory_dir: Path,
    from_pid: str,
    to_pid: str,
    link_type: str,
) -> None:
    """Insert a link row into SQLite if index.db is present."""
    db_path = _get_db_path(memory_dir)
    if db_path is None:
        return
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
            (from_pid, to_pid, link_type),
        )
        conn.commit()
        conn.close()
    except sqlite3.Error:
        pass  # SQLite sync is best-effort; JSON is the source of truth


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def add_paper(
    memory_dir: Path,
    paper_id: str,
    *,
    doi: str | None = None,
    title: str | None = None,
) -> Path:
    """Create ``memory/papers/<paper_id>.md`` and register it in ``index.json``.

    Idempotent: if the paper already exists in the index, returns the path
    without modifying anything.

    Args:
        memory_dir: Path to the ``memory/`` directory.
        paper_id: Unique paper identifier (filename stem, e.g. ``gkaf1205``).
        doi: Optional DOI string.
        title: Optional title string.

    Returns:
        Path to the paper markdown file.
    """
    with _locked_index(memory_dir):
        idx = _read_index(memory_dir)

        # Idempotency check
        if any(p["id"] == paper_id for p in idx["papers"]):
            return memory_dir / "papers" / f"{paper_id}.md"

        md_path = memory_dir / "papers" / f"{paper_id}.md"

        # Build minimal paper scaffold YAML frontmatter
        fm: dict[str, Any] = {
            "id": paper_id,
            "doi": doi,
            "bib": {
                "title": title or "",
                "authors": "",
                "venue": "",
                "year": None,
            },
            "problem_addressed": "",
            "method_summary": "",
            "math_used": "",
            "claimed_mechanism": "",
            "key_evidence": "",
            "status": "pending",
            "extract_template_version": _EXTRACT_TEMPLATE_VERSION,
        }
        body = "\n<!-- Fill in faithful notes below. No abstraction. -->\n"
        content = _render_frontmatter(fm, body)

        # Write markdown (inside the lock so idempotency is truly atomic)
        _write_md_atomic(md_path, content)

        # Update index
        idx["papers"].append({
            "id": paper_id,
            "status": "pending",
            "doi": doi,
            "title": title or "",
            "principles": [],
        })
        _write_index_atomic(memory_dir, idx)

    # Sync to SQLite (outside the lock — best-effort, non-blocking)
    _sync_paper_sqlite(memory_dir, paper_id, doi, title or "")

    return md_path


def add_principle(
    memory_dir: Path,
    *,
    title: str,
    abstraction_level: str,
    problem_signature: list[str],
    math_basis: list[str],
    mechanism: str,
    rationale: str,
    data_regime: list[str],
    falsifiable_prediction: str,
    boundaries: str,
    provenance: list[str],
    links: list[str] | None = None,
) -> str:
    """Allocate the next ``P-XXXX`` id, write its markdown, and update ``index.json``.

    Args:
        memory_dir: Path to the ``memory/`` directory.
        title: One-line principle title.
        abstraction_level: Domain-stripped statement of the principle.
        problem_signature: List of problem-structure tags (WHEN it applies).
        math_basis: List of math-machinery tags.
        mechanism: How the math attacks the structure.
        rationale: WHY structure↔mechanism connects (first principles).
        data_regime: Required data scale / conditions.
        falsifiable_prediction: A testable prediction implied by the principle.
        boundaries: When the principle breaks / its assumptions.
        provenance: List of paper-section refs, e.g. ``["gkaf1205 §3.2"]``.
        links: Optional list of link strings, e.g. ``["generalizes:P-0003"]``.

    Returns:
        The allocated principle id, e.g. ``"P-0001"``.
    """
    if links is None:
        links = []

    with _locked_index(memory_dir):
        idx = _read_index(memory_dir)

        # Allocate next pid
        current_counter: int = idx["counters"]["principle"]
        new_counter = current_counter + 1
        pid = f"P-{new_counter:04d}"

        md_path = memory_dir / "principles" / f"{pid}.md"

        # Build YAML frontmatter
        fm: dict[str, Any] = {
            "id": pid,
            "title": title,
            "abstraction_level": abstraction_level,
            "problem_signature": problem_signature,
            "math_basis": math_basis,
            "mechanism": mechanism,
            "rationale": rationale,
            "data_regime": data_regime,
            "falsifiable_prediction": falsifiable_prediction,
            "boundaries": boundaries,
            "provenance": provenance,
            "rubric_version": _RUBRIC_VERSION,
            "links": links,
        }
        body = "\n<!-- Derivation, evidence quotes, transfer notes. -->\n"
        content = _render_frontmatter(fm, body)

        # Write markdown (inside the lock so pid allocation + file write are atomic)
        _write_md_atomic(md_path, content)

        # Update index
        idx["counters"]["principle"] = new_counter
        idx["principles"].append({
            "id": pid,
            "title": title,
            "problem_signature": problem_signature,
            "math_basis": math_basis,
            "provenance": provenance,
            "rubric_version": _RUBRIC_VERSION,
            "links": links,
        })
        _write_index_atomic(memory_dir, idx)

    # Sync to SQLite (outside the lock — best-effort, non-blocking)
    _sync_principle_sqlite(
        memory_dir,
        pid=pid,
        title=title,
        abstraction_level=abstraction_level,
        mechanism=mechanism,
        rationale=rationale,
        falsifiable_prediction=falsifiable_prediction,
        boundaries=boundaries,
        rubric_version=_RUBRIC_VERSION,
        problem_signature=problem_signature,
        math_basis=math_basis,
        provenance=provenance,
        links=links,
    )

    return pid


def add_link(
    memory_dir: Path,
    from_pid: str,
    to_pid: str,
    link_type: str,
) -> None:
    """Append ``<link_type>:<to_pid>`` to ``from_pid``'s links.

    Updates both the markdown frontmatter and the ``index.json`` projection.
    Idempotent: does nothing if the link already exists.

    Args:
        memory_dir: Path to the ``memory/`` directory.
        from_pid: Source principle id, e.g. ``"P-0001"``.
        to_pid: Target principle id, e.g. ``"P-0002"``.
        link_type: One of the allowed link types (e.g. ``"generalizes"``).
    """
    link_str = f"{link_type}:{to_pid}"

    # --- Update markdown frontmatter (targeted edit, preserves formatting) ---
    md_path = memory_dir / "principles" / f"{from_pid}.md"
    text = md_path.read_text(encoding="utf-8")
    fm, _body = _parse_frontmatter(text)

    existing_links: list[str] = fm.get("links") or []
    if link_str not in existing_links:
        # Insert the new link into the raw text to preserve block scalar styles
        new_text = _insert_link_in_text(text, link_str)
        _write_md_atomic(md_path, new_text)

    # --- Update index.json (locked to prevent concurrent corruption) ---
    with _locked_index(memory_dir):
        idx = _read_index(memory_dir)
        changed = False
        for entry in idx["principles"]:
            if entry["id"] == from_pid:
                idx_links: list[str] = entry.get("links") or []
                if link_str not in idx_links:
                    idx_links.append(link_str)
                    entry["links"] = idx_links
                    changed = True
                break

        if changed:
            _write_index_atomic(memory_dir, idx)

    # Sync to SQLite (outside the lock — best-effort, non-blocking)
    _sync_link_sqlite(memory_dir, from_pid, to_pid, link_type)
