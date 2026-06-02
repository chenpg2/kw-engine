from pathlib import Path

from kw_engine.rubric import add_candidate, assemble_review_bundle, count_candidates, promote


def _setup_process(tmp_path: Path) -> Path:
    process_dir = tmp_path / "process"
    process_dir.mkdir()
    (process_dir / "distill-rubric.md").write_text(
        "# distill-rubric@v1\n\nRule 1: strip the biology.\n"
    )
    return process_dir


def test_add_candidate(tmp_path: Path) -> None:
    process_dir = _setup_process(tmp_path)
    add_candidate(
        process_dir,
        rule="Never use organism names in abstraction_level; use 'entity'.",
        trigger="P-0047 abstraction_level contained 'Lactobacillus'",
    )
    candidates = (process_dir / "distill-rubric.candidates.md").read_text()
    assert "organism names" in candidates
    assert "P-0047" in candidates


def test_count_candidates(tmp_path: Path) -> None:
    process_dir = _setup_process(tmp_path)
    assert count_candidates(process_dir) == 0
    add_candidate(process_dir, rule="rule A", trigger="trigger A")
    add_candidate(process_dir, rule="rule B", trigger="trigger B")
    assert count_candidates(process_dir) == 2


def test_assemble_review_bundle(tmp_path: Path) -> None:
    process_dir = _setup_process(tmp_path)
    add_candidate(process_dir, rule="rule A", trigger="trigger A")
    bundle = assemble_review_bundle(process_dir)
    # Bundle must contain the live rubric AND the candidates for Codex to audit
    assert "strip the biology" in bundle
    assert "rule A" in bundle
    assert "CURRENT RUBRIC" in bundle
    assert "CANDIDATE RULES" in bundle


def test_promote(tmp_path: Path) -> None:
    process_dir = _setup_process(tmp_path)
    add_candidate(process_dir, rule="rule A", trigger="trigger A")
    # Simulate Codex having written a proposed rubric
    (process_dir / "distill-rubric.proposed.md").write_text(
        "# distill-rubric@v2\n\nRule 1: strip the biology.\nRule 2: rule A integrated.\n"
    )
    promote(process_dir)
    # Live rubric is now the proposed content
    live = (process_dir / "distill-rubric.md").read_text()
    assert "rule A integrated" in live
    assert "v2" in live
    # Old live archived
    archive = list((process_dir / ".rubric-archive").glob("*.md"))
    assert len(archive) == 1
    assert "strip the biology" in archive[0].read_text()
    # Candidates cleared
    assert count_candidates(process_dir) == 0
    # Proposed consumed (removed)
    assert not (process_dir / "distill-rubric.proposed.md").exists()


def test_promote_without_proposed_raises(tmp_path: Path) -> None:
    process_dir = _setup_process(tmp_path)
    import pytest
    with pytest.raises(FileNotFoundError):
        promote(process_dir)


def test_promote_archive_numbering_no_reuse(tmp_path: Path) -> None:
    """Archive numbers must not be reused even if an older archive is deleted."""
    process_dir = _setup_process(tmp_path)

    def _do_promote(version: str) -> None:
        (process_dir / "distill-rubric.proposed.md").write_text(
            f"# distill-rubric@{version}\n\ncontent {version}\n"
        )
        promote(process_dir)

    _do_promote("v2")  # archives 001
    _do_promote("v3")  # archives 002
    archive_dir = process_dir / ".rubric-archive"
    assert {f.name for f in archive_dir.glob("*.md")} == {
        "distill-rubric-001.md",
        "distill-rubric-002.md",
    }
    # Delete the first archive, then promote again — must NOT reuse 001
    (archive_dir / "distill-rubric-001.md").unlink()
    _do_promote("v4")  # archives live (v3) as 003 (max+1), not 001
    assert (archive_dir / "distill-rubric-003.md").exists()
    assert "content v3" in (archive_dir / "distill-rubric-003.md").read_text()
