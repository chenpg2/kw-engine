"""Read pydantic models from YAML-front-matter markdown files."""

from __future__ import annotations

from pathlib import Path

import yaml

from kw_engine.models import PaperFull, Principle


def _parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"No YAML front-matter in {path}")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Malformed front-matter in {path}")
    return yaml.safe_load(parts[1])


def read_paper_md(path: Path) -> PaperFull:
    data = _parse_frontmatter(path)
    return PaperFull.model_validate(data)


def read_principle_md(path: Path) -> Principle:
    data = _parse_frontmatter(path)
    return Principle.model_validate(data)


def scan_memory_dir(memory_dir: Path) -> tuple[list[PaperFull], list[Principle]]:
    papers_dir = memory_dir / "papers"
    principles_dir = memory_dir / "principles"

    papers: list[PaperFull] = []
    if papers_dir.exists():
        for f in sorted(papers_dir.glob("*.md")):
            papers.append(read_paper_md(f))

    principles: list[Principle] = []
    if principles_dir.exists():
        for f in sorted(principles_dir.glob("*.md")):
            principles.append(read_principle_md(f))

    return papers, principles
