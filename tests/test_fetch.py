import json

from kw_engine.fetch import fetch_paper, validate_pdf


def test_validate_pdf_valid(tmp_path):
    pdf = tmp_path / "test.pdf"
    # Write fake PDF (valid magic, >10KB)
    pdf.write_bytes(b"%PDF-1.4" + b"\x00" * 20000)
    assert validate_pdf(pdf) is True


def test_validate_pdf_too_small(tmp_path):
    pdf = tmp_path / "small.pdf"
    pdf.write_bytes(b"%PDF-1.4" + b"\x00" * 100)
    assert validate_pdf(pdf) is False


def test_validate_pdf_html(tmp_path):
    pdf = tmp_path / "fake.pdf"
    pdf.write_bytes(b"<html>" + b"\x00" * 20000)
    assert validate_pdf(pdf) is False


def test_validate_pdf_missing(tmp_path):
    assert validate_pdf(tmp_path / "nope.pdf") is False


def test_fetch_paper_already_valid(tmp_path):
    """fetch_paper returns SKIP if PDF already valid."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    idx = {"version": 1, "counters": {"principle": 0}, "papers": [],
           "principles": [], "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    papers_dir = tmp_path / "paper"
    papers_dir.mkdir()
    pdf = papers_dir / "existing.pdf"
    pdf.write_bytes(b"%PDF-1.4" + b"\x00" * 20000)

    result = fetch_paper(mem, "existing", papers_dir=papers_dir)
    assert "SKIP" in result

    # Should still register in index
    new_idx = json.loads((mem / "index.json").read_text())
    assert any(p["id"] == "existing" for p in new_idx["papers"])


def test_fetch_paper_no_source_fails(tmp_path):
    """fetch_paper returns FAIL if no download source available."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    idx = {"version": 1, "counters": {"principle": 0}, "papers": [],
           "principles": [], "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    papers_dir = tmp_path / "paper"
    papers_dir.mkdir()

    result = fetch_paper(mem, "nonexistent-paper-xyz", papers_dir=papers_dir)
    assert "FAIL" in result
