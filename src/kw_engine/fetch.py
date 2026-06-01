"""Paper PDF acquisition and validation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from kw_engine.store.ops import add_paper


def validate_pdf(path: Path) -> bool:
    """Check that a file is a valid PDF (magic bytes + size)."""
    if not path.exists():
        return False
    size = path.stat().st_size
    if size < 10240 or size > 52_428_800:
        return False
    with open(path, "rb") as f:
        magic = f.read(5)
    return magic == b"%PDF-"


def fetch_paper(
    memory_dir: Path,
    paper_id: str,
    *,
    papers_dir: Path | None = None,
    doi: str | None = None,
    title: str | None = None,
    paper_search_dir: str | None = None,
) -> str:
    """Fetch a paper PDF and register it.

    Returns a status string:
    - "OK: paper/<id>.pdf (NkB)" on success
    - "SKIP: already valid" if PDF exists and validates
    - "FAIL: <reason>" if acquisition failed
    """
    if papers_dir is None:
        papers_dir = memory_dir.parent / "paper"

    pdf_path = papers_dir / f"{paper_id}.pdf"

    # Idempotent: skip if already valid
    if validate_pdf(pdf_path):
        add_paper(memory_dir, paper_id, doi=doi, title=title)
        return f"SKIP: {pdf_path.name} already valid"

    # Attempt download via paper-search CLI
    downloaded = False
    if paper_search_dir:
        downloaded = _try_paper_search(paper_id, pdf_path, paper_search_dir, doi=doi)

    if not downloaded:
        # Try direct arxiv curl if paper_id looks like an arxiv id
        if _looks_like_arxiv(paper_id):
            downloaded = _try_arxiv_curl(paper_id, pdf_path)

    if downloaded and validate_pdf(pdf_path):
        add_paper(memory_dir, paper_id, doi=doi, title=title)
        size_kb = pdf_path.stat().st_size // 1024
        return f"OK: {pdf_path.name} ({size_kb}kB)"

    # Cleanup invalid download
    if pdf_path.exists() and not validate_pdf(pdf_path):
        pdf_path.unlink()

    return f"FAIL: {paper_id} (could not acquire valid PDF)"


def _looks_like_arxiv(paper_id: str) -> bool:
    """Check if paper_id looks like an arxiv id (e.g. 1706.08058 or 2304.04740)."""
    parts = paper_id.split(".")
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return True
    return False


def _try_arxiv_curl(paper_id: str, pdf_path: Path) -> bool:
    """Try to download from arxiv directly."""
    url = f"https://arxiv.org/pdf/{paper_id}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["curl", "-sL", "-o", str(pdf_path), url],
            timeout=60,
            capture_output=True,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _try_paper_search(
    paper_id: str,
    pdf_path: Path,
    paper_search_dir: str,
    *,
    doi: str | None = None,
) -> bool:
    """Try download via paper-search CLI."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    # Determine source and id for paper-search
    source = "arxiv" if _looks_like_arxiv(paper_id) else "crossref"
    identifier = doi if doi and source == "crossref" else paper_id

    try:
        result = subprocess.run(
            [
                "uv", "run", "--directory", paper_search_dir,
                "paper-search", "download", source, identifier,
                "-o", str(pdf_path.parent),
            ],
            timeout=120,
            capture_output=True,
            text=True,
        )
        # paper-search may save with a different filename; check if our target exists
        if pdf_path.exists():
            return True
        # Try to find any new PDF in the output dir
        return result.returncode == 0 and pdf_path.exists()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
