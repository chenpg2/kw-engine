"""SQLite rebuildable index — derived from markdown source of truth."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from kw_engine.models import LinkEntry, PaperFull, Principle, paper_id_from_provenance

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    doi TEXT,
    title TEXT,
    bib_authors TEXT,
    bib_venue TEXT,
    bib_year INTEGER
);

CREATE TABLE IF NOT EXISTS principles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstraction_level TEXT,
    mechanism TEXT,
    rationale TEXT,
    falsifiable_prediction TEXT,
    boundaries TEXT,
    rubric_version TEXT
);

CREATE TABLE IF NOT EXISTS principle_signatures (
    principle_id TEXT NOT NULL,
    signature TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);

CREATE TABLE IF NOT EXISTS principle_math_basis (
    principle_id TEXT NOT NULL,
    basis TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);

CREATE TABLE IF NOT EXISTS principle_provenance (
    principle_id TEXT NOT NULL,
    paper_id TEXT NOT NULL,
    locator TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);

CREATE TABLE IF NOT EXISTS links (
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    link_type TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES principles(id)
);

CREATE TABLE IF NOT EXISTS paper_principles (
    paper_id TEXT NOT NULL,
    principle_id TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);
"""


def create_schema(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(_SCHEMA_SQL)
    return conn


def rebuild_index_db(
    db_path: Path,
    papers: list[PaperFull],
    principles: list[Principle],
) -> None:
    if db_path.exists():
        db_path.unlink()

    conn = create_schema(db_path)

    for p in papers:
        conn.execute(
            "INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)",
            (p.id, p.status, p.doi, p.bib.title, p.bib.authors, p.bib.venue, p.bib.year),
        )

    paper_to_principles: dict[str, list[str]] = {p.id: [] for p in papers}

    for pr in principles:
        conn.execute(
            "INSERT INTO principles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                pr.id,
                pr.title,
                pr.abstraction_level,
                pr.mechanism,
                pr.rationale,
                pr.falsifiable_prediction,
                pr.boundaries,
                pr.rubric_version,
            ),
        )
        for sig in pr.problem_signature:
            conn.execute(
                "INSERT INTO principle_signatures VALUES (?, ?)", (pr.id, sig)
            )
        for basis in pr.math_basis:
            conn.execute(
                "INSERT INTO principle_math_basis VALUES (?, ?)", (pr.id, basis)
            )
        for prov in pr.provenance:
            parts = prov.split(None, 1)
            paper_id = paper_id_from_provenance(prov)
            locator = parts[1] if len(parts) > 1 else ""
            conn.execute(
                "INSERT INTO principle_provenance VALUES (?, ?, ?)",
                (pr.id, paper_id, locator),
            )
            if paper_id in paper_to_principles and pr.id not in paper_to_principles[paper_id]:
                paper_to_principles[paper_id].append(pr.id)
        for link_str in pr.links:
            le = LinkEntry.from_str(link_str)
            conn.execute(
                "INSERT INTO links VALUES (?, ?, ?)", (pr.id, le.target, le.link_type)
            )

    for paper_id, pids in paper_to_principles.items():
        for pid in pids:
            conn.execute(
                "INSERT INTO paper_principles VALUES (?, ?)", (paper_id, pid)
            )

    conn.commit()
    conn.close()
