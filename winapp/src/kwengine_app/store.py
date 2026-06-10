"""Portable storage substrate — consolidation of kw_engine's init/ops/markdown/
json_proj/sqlite/search/verify, with fcntl replaced by a cross-platform lock so it
runs on Windows.

Conventions identical to the kw CLI:
- Markdown is truth; index.json + .kw/index.db are derived.
- YAML rendered with the same PyYAML call → byte-compatible records.
- Paper id = PDF filename stem; principle id = P-#### (zero-padded).
- No silent fallback: validation errors raise, never coerce.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .models import (
    EXTRACT_TEMPLATE_VERSION, RUBRIC_VERSION, PaperFull, Principle, SearchHit,
    StatusSummary, Verdict, locator_from_provenance, paper_id_from_provenance,
)
from . import templates


class StoreError(Exception):
    pass


# ---------------------------------------------------------------------------
# Cross-platform best-effort lock (replaces fcntl.flock)
# ---------------------------------------------------------------------------

@contextmanager
def _locked_index(memory_dir: Path):
    lock_path = memory_dir / ".index.lock"
    lock_path.touch(exist_ok=True)
    f = open(lock_path, "r+")
    locked = False
    try:
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(f, fcntl.LOCK_EX)
            locked = True
        except OSError:
            pass  # single-process GUI: lock is belt-and-braces only
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f, fcntl.LOCK_UN)
            except OSError:
                pass
        f.close()


# ---------------------------------------------------------------------------
# Frontmatter (identical serialization to kw_engine/store/ops.py)
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        raise StoreError("No YAML front-matter found")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise StoreError("Malformed front-matter (missing closing ---)")
    fm = yaml.safe_load(parts[1]) or {}
    if not isinstance(fm, dict):
        raise StoreError("Front-matter is not a mapping")
    return fm, parts[2]


def render_frontmatter(fm: dict[str, Any], body: str) -> str:
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---\n{body}"


def _insert_link_in_text(text: str, link_str: str) -> str:
    """Raw-text link insertion preserving formatting (port of ops.py)."""
    empty_pattern = r"(links:\s*)\[\]"
    if re.search(empty_pattern, text):
        return re.sub(empty_pattern, f'\\1\n  - "{link_str}"', text)

    lines = text.split("\n")
    last_link_idx = -1
    in_links = False
    for i, line in enumerate(lines):
        if line.startswith("links:"):
            in_links = True
            continue
        if in_links:
            if line.startswith("  - ") or line.startswith("- "):
                last_link_idx = i
            elif line and not line.startswith(" "):
                break
    if last_link_idx >= 0:
        indent = "  " if lines[last_link_idx].startswith("  - ") else ""
        lines.insert(last_link_idx + 1, f'{indent}- "{link_str}"')
        return "\n".join(lines)

    parts = text.split("---", 2)
    if len(parts) >= 3:
        parts[1] = parts[1].rstrip() + f'\nlinks:\n  - "{link_str}"\n'
        return "---".join(parts)
    return text


# ---------------------------------------------------------------------------
# SQLite schema (identical to kw_engine/store/sqlite.py)
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id TEXT PRIMARY KEY, status TEXT NOT NULL, doi TEXT, title TEXT,
    bib_authors TEXT, bib_venue TEXT, bib_year INTEGER
);
CREATE TABLE IF NOT EXISTS principles (
    id TEXT PRIMARY KEY, title TEXT NOT NULL, abstraction_level TEXT,
    mechanism TEXT, rationale TEXT, falsifiable_prediction TEXT,
    boundaries TEXT, rubric_version TEXT
);
CREATE TABLE IF NOT EXISTS principle_signatures (
    principle_id TEXT NOT NULL, signature TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);
CREATE TABLE IF NOT EXISTS principle_math_basis (
    principle_id TEXT NOT NULL, basis TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);
CREATE TABLE IF NOT EXISTS principle_provenance (
    principle_id TEXT NOT NULL, paper_id TEXT NOT NULL, locator TEXT NOT NULL,
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);
CREATE TABLE IF NOT EXISTS links (
    source_id TEXT NOT NULL, target_id TEXT NOT NULL, link_type TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES principles(id)
);
CREATE TABLE IF NOT EXISTS paper_principles (
    paper_id TEXT NOT NULL, principle_id TEXT NOT NULL,
    FOREIGN KEY (paper_id) REFERENCES papers(id),
    FOREIGN KEY (principle_id) REFERENCES principles(id)
);
"""


# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

@dataclass
class Workspace:
    root: Path

    # paths ------------------------------------------------------------
    @property
    def memory_dir(self) -> Path: return self.root / "memory"
    @property
    def papers_dir(self) -> Path: return self.memory_dir / "papers"
    @property
    def principles_dir(self) -> Path: return self.memory_dir / "principles"
    @property
    def synthesis_dir(self) -> Path: return self.memory_dir / "synthesis"
    @property
    def pdf_dir(self) -> Path: return self.root / "paper"
    @property
    def index_path(self) -> Path: return self.memory_dir / "index.json"
    @property
    def db_path(self) -> Path: return self.root / ".kw" / "index.db"

    def paper_path(self, pid: str) -> Path: return self.papers_dir / f"{pid}.md"
    def principle_path(self, pid: str) -> Path: return self.principles_dir / f"{pid}.md"
    def pdf_path(self, pid: str) -> Path: return self.pdf_dir / f"{pid}.pdf"

    # detection / scaffold ----------------------------------------------
    @staticmethod
    def is_workspace(root: Path) -> bool:
        return (root / "memory" / "index.json").exists() or (root / "memory" / "SCHEMA.md").exists()

    @staticmethod
    def scaffold(root: Path) -> None:
        """Port of init_workspace — idempotent, never overwrites."""
        for d in [".kw/logs", "memory/papers", "memory/principles", "memory/synthesis",
                  "memory/golden", "paper", "process", "problems"]:
            (root / d).mkdir(parents=True, exist_ok=True)
        writes = {
            ".kw/config.yaml": templates.CONFIG_YAML,
            "memory/index.json": templates.INITIAL_INDEX_JSON,
            "memory/SCHEMA.md": templates.SCHEMA_MD,
            "process/extract-template.md": templates.EXTRACT_TEMPLATE_MD,
            "process/distill-rubric.md": templates.DISTILL_RUBRIC_MD,
        }
        for rel, content in writes.items():
            p = root / rel
            if not p.exists():
                p.write_text(content, encoding="utf-8")

    # index.json ----------------------------------------------------------
    def read_index(self) -> dict[str, Any]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise StoreError(f"index.json is invalid: {e}") from e

    def _write_index_atomic(self, idx: dict[str, Any]) -> None:
        content = json.dumps(idx, indent=2, ensure_ascii=False)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.memory_dir,
            prefix=".index_tmp_", suffix=".json", delete=False,
        ) as tf:
            tf.write(content)
            tmp = Path(tf.name)
        tmp.replace(self.index_path)

    def _write_md_atomic(self, dest: Path, content: str) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=dest.parent,
            prefix=".tmp_", suffix=".md", delete=False,
        ) as tf:
            tf.write(content)
            tmp = Path(tf.name)
        tmp.replace(dest)

    # record I/O ----------------------------------------------------------
    def read_paper_file(self, pid: str) -> tuple[PaperFull, str]:
        text = self.paper_path(pid).read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        return PaperFull.from_frontmatter(fm, f"{pid}.md"), body

    def read_principle_file(self, pid: str) -> tuple[Principle, str]:
        text = self.principle_path(pid).read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        return Principle.from_frontmatter(fm, f"{pid}.md"), body

    def scan_markdown(self) -> tuple[list[PaperFull], list[Principle]]:
        papers: list[PaperFull] = []
        if self.papers_dir.exists():
            for f in sorted(self.papers_dir.glob("*.md")):
                fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
                papers.append(PaperFull.from_frontmatter(fm, f.name))
        principles: list[Principle] = []
        if self.principles_dir.exists():
            for f in sorted(self.principles_dir.glob("*.md")):
                fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
                principles.append(Principle.from_frontmatter(fm, f.name))
        return papers, principles

    # add_paper (port of ops.add_paper) ------------------------------------
    def add_paper(self, paper_id: str, *, doi: str | None = None, title: str | None = None) -> Path:
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            if any(p["id"] == paper_id for p in idx["papers"]):
                return self.paper_path(paper_id)
            fm: dict[str, Any] = {
                "id": paper_id,
                "doi": doi,
                "bib": {"title": title or "", "authors": "", "venue": "", "year": None},
                "problem_addressed": "",
                "method_summary": "",
                "math_used": "",
                "claimed_mechanism": "",
                "key_evidence": "",
                "status": "pending",
                "extract_template_version": EXTRACT_TEMPLATE_VERSION,
            }
            body = "\n<!-- Fill in faithful notes below. No abstraction. -->\n"
            self._write_md_atomic(self.paper_path(paper_id), render_frontmatter(fm, body))
            idx["papers"].append({
                "id": paper_id, "status": "pending", "doi": doi,
                "title": title or "", "principles": [],
            })
            self._write_index_atomic(idx)
        self._sync_paper_sqlite(paper_id, doi, title or "")
        return self.paper_path(paper_id)

    @staticmethod
    def sanitize_paper_id(stem: str) -> str:
        cleaned = "".join(ch if (ch.isalnum() or ch in "._-") else "-" for ch in stem.strip())
        return cleaned.strip("-")

    def import_pdf(self, source: Path) -> str:
        pid = self.sanitize_paper_id(source.stem)
        if not pid:
            raise StoreError(f"Cannot derive a paper id from {source.name}")
        data = source.read_bytes()
        if not data.startswith(b"%PDF-"):
            raise StoreError(f"{source.name} is not a valid PDF (missing %PDF- magic bytes)")
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        dest = self.pdf_path(pid)
        if not dest.exists():
            shutil.copyfile(source, dest)
        self.add_paper(pid)
        return pid

    # L1 write --------------------------------------------------------------
    def write_paper_record(self, paper: PaperFull, body_notes: str,
                           index_status: str | None = None) -> None:
        fm: dict[str, Any] = {"id": paper.id, "doi": paper.doi}
        if paper.arxiv:
            fm["arxiv"] = paper.arxiv
        fm.update({
            "bib": {"title": paper.bib.title, "authors": paper.bib.authors,
                    "venue": paper.bib.venue, "year": paper.bib.year},
            "problem_addressed": paper.problem_addressed,
            "method_summary": paper.method_summary,
            "math_used": paper.math_used,
            "claimed_mechanism": paper.claimed_mechanism,
            "key_evidence": paper.key_evidence,
            "status": paper.status,
            "extract_template_version": paper.extract_template_version,
        })
        body = body_notes if body_notes.startswith("\n") else "\n" + body_notes
        self._write_md_atomic(self.paper_path(paper.id), render_frontmatter(fm, body))

        proj_status = index_status or paper.status
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            for entry in idx["papers"]:
                if entry["id"] == paper.id:
                    entry["status"] = proj_status
                    entry["title"] = paper.bib.title
                    entry["doi"] = paper.doi
                    break
            else:
                idx["papers"].append({"id": paper.id, "status": proj_status, "doi": paper.doi,
                                      "title": paper.bib.title, "principles": []})
            self._write_index_atomic(idx)

    def update_index_paper(self, paper_id: str, *, status: str | None = None,
                           add_principles: list[str] | None = None) -> None:
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            for entry in idx["papers"]:
                if entry["id"] == paper_id:
                    if status:
                        entry["status"] = status
                    for pid in add_principles or []:
                        if pid not in entry["principles"]:
                            entry["principles"].append(pid)
                    entry["principles"] = sorted(entry["principles"])
                    break
            self._write_index_atomic(idx)

    # add_principle (port of ops.add_principle) -------------------------------
    def add_principle(self, *, title: str, abstraction_level: str,
                      problem_signature: list[str], math_basis: list[str],
                      mechanism: str, rationale: str, data_regime: list[str],
                      falsifiable_prediction: str, boundaries: str,
                      provenance: list[str], links: list[str] | None = None,
                      body_notes: str | None = None) -> str:
        links = links or []
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            new_counter = idx["counters"]["principle"] + 1
            pid = f"P-{new_counter:04d}"
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
                "rubric_version": RUBRIC_VERSION,
                "links": links,
            }
            body = "\n<!-- Derivation, evidence quotes, transfer notes. -->\n"
            if body_notes:
                body = "\n" + body_notes + "\n"
            self._write_md_atomic(self.principle_path(pid), render_frontmatter(fm, body))
            idx["counters"]["principle"] = new_counter
            idx["principles"].append({
                "id": pid, "title": title, "problem_signature": problem_signature,
                "math_basis": math_basis, "provenance": provenance,
                "rubric_version": RUBRIC_VERSION, "links": links,
            })
            self._write_index_atomic(idx)
        self._sync_principle_sqlite(pid, title, abstraction_level, mechanism, rationale,
                                    falsifiable_prediction, boundaries, problem_signature,
                                    math_basis, provenance, links)
        return pid

    # add_link (port of ops.add_link) ------------------------------------------
    def add_link(self, from_pid: str, to_pid: str, link_type: str) -> None:
        link_str = f"{link_type}:{to_pid}"
        path = self.principle_path(from_pid)
        text = path.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        existing = fm.get("links") or []
        if link_str not in existing:
            self._write_md_atomic(path, _insert_link_in_text(text, link_str))
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            for entry in idx["principles"]:
                if entry["id"] == from_pid:
                    idx_links = entry.get("links") or []
                    if link_str not in idx_links:
                        idx_links.append(link_str)
                        entry["links"] = idx_links
                        self._write_index_atomic(idx)
                    break
        self._sync_link_sqlite(from_pid, to_pid, link_type)

    def append_provenance(self, pid: str, entries: list[str]) -> list[str]:
        principle, body = self.read_principle_file(pid)
        added = [e for e in entries if e not in principle.provenance]
        if not added:
            return []
        principle.provenance.extend(added)
        fm: dict[str, Any] = {
            "id": principle.id, "title": principle.title,
            "abstraction_level": principle.abstraction_level,
            "problem_signature": principle.problem_signature,
            "math_basis": principle.math_basis,
            "mechanism": principle.mechanism, "rationale": principle.rationale,
            "data_regime": principle.data_regime,
            "falsifiable_prediction": principle.falsifiable_prediction,
            "boundaries": principle.boundaries, "provenance": principle.provenance,
            "rubric_version": principle.rubric_version, "links": principle.links,
        }
        self._write_md_atomic(self.principle_path(pid), render_frontmatter(fm, body))
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            for entry in idx["principles"]:
                if entry["id"] == pid:
                    entry["provenance"] = principle.provenance
                    break
            self._write_index_atomic(idx)
        self._sync_provenance_sqlite(pid, added)
        return added

    # reindex (port of cli.reindex + json_proj.build_index_json) ----------------
    def reindex(self) -> tuple[int, int]:
        papers, principles = self.scan_markdown()
        paper_to_principles: dict[str, list[str]] = {p.id: [] for p in papers}
        for pr in principles:
            for prov in pr.provenance:
                ref = paper_id_from_provenance(prov)
                if ref in paper_to_principles and pr.id not in paper_to_principles[ref]:
                    paper_to_principles[ref].append(pr.id)
        try:
            old_synthesis = self.read_index().get("synthesis") or {}
        except StoreError:
            old_synthesis = {}
        idx = {
            "version": 1,
            "counters": {"principle": len(principles)},
            "papers": [
                {"id": p.id, "status": p.status, "doi": p.doi, "title": p.bib.title,
                 "principles": sorted(paper_to_principles.get(p.id, []))}
                for p in papers
            ],
            "principles": [
                {"id": pr.id, "title": pr.title, "problem_signature": pr.problem_signature,
                 "math_basis": pr.math_basis, "provenance": pr.provenance,
                 "rubric_version": pr.rubric_version, "links": pr.links}
                for pr in principles
            ],
            "synthesis": {
                "last_run": old_synthesis.get("last_run"),
                "n_principles_at_last_run": old_synthesis.get("n_principles_at_last_run", 0),
            },
        }
        self._write_index_atomic(idx)
        self._rebuild_index_db(papers, principles)
        return len(papers), len(principles)

    # synthesis -----------------------------------------------------------------
    def read_synthesis_doc(self, name: str) -> str | None:
        p = self.synthesis_dir / name
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            return None

    def write_synthesis_docs(self, design_space: str, contradictions: str,
                             gaps: str, date: str) -> None:
        self.synthesis_dir.mkdir(parents=True, exist_ok=True)
        (self.synthesis_dir / "design-space.md").write_text(design_space, encoding="utf-8")
        (self.synthesis_dir / "contradictions.md").write_text(contradictions, encoding="utf-8")
        (self.synthesis_dir / "gaps.md").write_text(gaps, encoding="utf-8")
        with _locked_index(self.memory_dir):
            idx = self.read_index()
            idx["synthesis"]["last_run"] = date
            idx["synthesis"]["n_principles_at_last_run"] = len(idx["principles"])
            self._write_index_atomic(idx)

    # status (mirror of `kw status`) ----------------------------------------------
    def status_summary(self) -> StatusSummary:
        idx = self.read_index()
        by_status: dict[str, int] = {}
        for p in idx["papers"]:
            by_status[p["status"]] = by_status.get(p["status"], 0) + 1
        n = len(idx["principles"])
        n_at_last = idx["synthesis"].get("n_principles_at_last_run", 0)
        return StatusSummary(
            papers_total=len(idx["papers"]),
            papers_by_status=by_status,
            principles=n,
            pending_papers=[p["id"] for p in idx["papers"] if p["status"] == "pending"],
            l1_papers=[p["id"] for p in idx["papers"] if p["status"] == "L1"],
            synthesis_last_run=idx["synthesis"].get("last_run"),
            synthesis_stale=n > n_at_last,
            new_since_synthesis=max(0, n - n_at_last),
        )

    # verify (port of verify.py + counter check) -----------------------------------
    def verify(self) -> list[Verdict]:
        verdicts: list[Verdict] = []
        try:
            papers, principles = self.scan_markdown()
        except (StoreError, ValueError, OSError) as e:
            return [Verdict("parse", False, str(e))]
        paper_ids = {p.id for p in papers}
        principle_ids = {p.id for p in principles}

        try:
            idx = self.read_index()
            counter = idx["counters"]["principle"]
            if counter == len(principles):
                verdicts.append(Verdict("counter_invariant", True,
                                        f"counters.principle == {len(principles)}"))
            else:
                verdicts.append(Verdict("counter_invariant", False,
                                        f"counters.principle = {counter}, but {len(principles)} records exist"))
        except (StoreError, KeyError):
            verdicts.append(Verdict("counter_invariant", False, "index.json missing or unreadable"))

        prov_ok = True
        for pr in principles:
            for prov in pr.provenance:
                ref = paper_id_from_provenance(prov)
                if ref not in paper_ids:
                    prov_ok = False
                    verdicts.append(Verdict("provenance_resolves", False,
                                            f"{pr.id} cites '{ref}' which is not in papers"))
        if prov_ok:
            verdicts.append(Verdict("provenance_resolves", True, "all provenance resolves"))

        link_ok = True
        for pr in principles:
            for link_str in pr.links:
                if ":" not in link_str:
                    link_ok = False
                    verdicts.append(Verdict("link_integrity", False,
                                            f"{pr.id} has malformed link '{link_str}'"))
                    continue
                target = link_str.split(":", 1)[1]
                if target not in principle_ids:
                    link_ok = False
                    verdicts.append(Verdict("link_integrity", False,
                                            f"{pr.id} links to {target} which does not exist"))
        if link_ok:
            verdicts.append(Verdict("link_integrity", True, "all link targets exist"))

        l2_ok = True
        for pr in principles:
            for name, empty in [
                ("problem_signature", not pr.problem_signature),
                ("mechanism", not pr.mechanism),
                ("rationale", not pr.rationale),
                ("falsifiable_prediction", not pr.falsifiable_prediction),
            ]:
                if empty:
                    l2_ok = False
                    verdicts.append(Verdict("l2_fields_nonempty", False, f"{pr.id}.{name} is empty"))
        if l2_ok:
            verdicts.append(Verdict("l2_fields_nonempty", True, "all L2 load-bearing fields filled"))
        return verdicts

    # search (port of search.py: sqlite first, index.json fallback) -----------------
    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [t for t in re.split(r"[\s\-]+", text.lower()) if t]

    def search_principles(self, query: str, top_k: int = 10) -> list[SearchHit]:
        tokens = self._tokenize(query)
        if not tokens:
            return []
        hits = self._search_sqlite(tokens, top_k)
        if hits is not None:
            return hits
        return self._search_index(tokens, top_k)

    def _search_sqlite(self, tokens: list[str], top_k: int) -> list[SearchHit] | None:
        if not self.db_path.exists():
            return None
        try:
            conn = sqlite3.connect(self.db_path)
            hit_counts: dict[str, int] = {}
            for token in tokens:
                pattern = f"%{token}%"
                rows = conn.execute(
                    """
                    SELECT DISTINCT principle_id FROM principle_signatures WHERE signature LIKE ?
                    UNION
                    SELECT DISTINCT principle_id FROM principle_math_basis WHERE basis LIKE ?
                    """,
                    (pattern, pattern),
                ).fetchall()
                for row in rows:
                    hit_counts[row[0]] = hit_counts.get(row[0], 0) + 1
            if not hit_counts:
                conn.close()
                return []
            placeholders = ",".join("?" * len(hit_counts))
            title_rows = conn.execute(
                f"SELECT id, title FROM principles WHERE id IN ({placeholders})",
                list(hit_counts.keys()),
            ).fetchall()
            conn.close()
            titles = {r[0]: r[1] for r in title_rows}
            scored = [SearchHit(pid, titles.get(pid, ""), c) for pid, c in hit_counts.items()]
            scored.sort(key=lambda h: (-h.score, h.id))
            return scored[:top_k]
        except sqlite3.Error:
            return None

    def _search_index(self, tokens: list[str], top_k: int) -> list[SearchHit]:
        try:
            idx = self.read_index()
        except StoreError:
            return []
        scored: list[SearchHit] = []
        for p in idx.get("principles", []):
            hay = " ".join((p.get("problem_signature") or []) + (p.get("math_basis") or [])).lower()
            score = sum(1 for t in tokens if t in hay)
            if score > 0:
                scored.append(SearchHit(p["id"], p.get("title", ""), score))
        scored.sort(key=lambda h: (-h.score, h.id))
        return scored[:top_k]

    # SQLite derived index ------------------------------------------------------
    def _rebuild_index_db(self, papers: list[PaperFull], principles: list[Principle]) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.db_path.exists():
            self.db_path.unlink()
        conn = sqlite3.connect(self.db_path)
        conn.executescript(_SCHEMA_SQL)
        for p in papers:
            conn.execute("INSERT INTO papers VALUES (?, ?, ?, ?, ?, ?, ?)",
                         (p.id, p.status, p.doi, p.bib.title, p.bib.authors, p.bib.venue, p.bib.year))
        paper_to_principles: dict[str, list[str]] = {p.id: [] for p in papers}
        for pr in principles:
            conn.execute("INSERT INTO principles VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (pr.id, pr.title, pr.abstraction_level, pr.mechanism, pr.rationale,
                          pr.falsifiable_prediction, pr.boundaries, pr.rubric_version))
            for sig in pr.problem_signature:
                conn.execute("INSERT INTO principle_signatures VALUES (?, ?)", (pr.id, sig))
            for basis in pr.math_basis:
                conn.execute("INSERT INTO principle_math_basis VALUES (?, ?)", (pr.id, basis))
            for prov in pr.provenance:
                ref = paper_id_from_provenance(prov)
                conn.execute("INSERT INTO principle_provenance VALUES (?, ?, ?)",
                             (pr.id, ref, locator_from_provenance(prov)))
                if ref in paper_to_principles and pr.id not in paper_to_principles[ref]:
                    paper_to_principles[ref].append(pr.id)
            for link_str in pr.links:
                if ":" in link_str:
                    t, target = link_str.split(":", 1)
                    conn.execute("INSERT INTO links VALUES (?, ?, ?)", (pr.id, target, t))
        for paper_id, pids in paper_to_principles.items():
            for pid in pids:
                conn.execute("INSERT INTO paper_principles VALUES (?, ?)", (paper_id, pid))
        conn.commit()
        conn.close()

    # best-effort incremental syncs (mirror ops.py: silent if db absent) ---------
    def _sync_paper_sqlite(self, paper_id: str, doi: str | None, title: str) -> None:
        if not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO papers (id, status, doi, title, bib_authors, bib_venue, bib_year)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (paper_id, "pending", doi, title, "", "", None))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def _sync_principle_sqlite(self, pid: str, title: str, abstraction_level: str,
                               mechanism: str, rationale: str, falsifiable_prediction: str,
                               boundaries: str, problem_signature: list[str],
                               math_basis: list[str], provenance: list[str],
                               links: list[str]) -> None:
        if not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO principles (id, title, abstraction_level, mechanism,"
                " rationale, falsifiable_prediction, boundaries, rubric_version)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, title, abstraction_level, mechanism, rationale,
                 falsifiable_prediction, boundaries, RUBRIC_VERSION))
            for sig in problem_signature:
                conn.execute("INSERT INTO principle_signatures (principle_id, signature) VALUES (?, ?)",
                             (pid, sig))
            for basis in math_basis:
                conn.execute("INSERT INTO principle_math_basis (principle_id, basis) VALUES (?, ?)",
                             (pid, basis))
            for prov in provenance:
                ref = paper_id_from_provenance(prov)
                conn.execute(
                    "INSERT INTO principle_provenance (principle_id, paper_id, locator) VALUES (?, ?, ?)",
                    (pid, ref, locator_from_provenance(prov)))
                conn.execute(
                    "INSERT OR IGNORE INTO paper_principles (paper_id, principle_id) VALUES (?, ?)",
                    (ref, pid))
            for link_str in links:
                if ":" in link_str:
                    t, target = link_str.split(":", 1)
                    conn.execute("INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                                 (pid, target, t))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def _sync_link_sqlite(self, from_pid: str, to_pid: str, link_type: str) -> None:
        if not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("INSERT INTO links (source_id, target_id, link_type) VALUES (?, ?, ?)",
                         (from_pid, to_pid, link_type))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass

    def _sync_provenance_sqlite(self, pid: str, entries: list[str]) -> None:
        if not self.db_path.exists():
            return
        try:
            conn = sqlite3.connect(self.db_path)
            for prov in entries:
                ref = paper_id_from_provenance(prov)
                conn.execute(
                    "INSERT INTO principle_provenance (principle_id, paper_id, locator) VALUES (?, ?, ?)",
                    (pid, ref, locator_from_provenance(prov)))
                conn.execute(
                    "INSERT OR IGNORE INTO paper_principles (paper_id, principle_id) VALUES (?, ?)",
                    (ref, pid))
            conn.commit()
            conn.close()
        except sqlite3.Error:
            pass
