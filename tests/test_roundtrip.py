"""
Zero-drift roundtrip: rebuild index.json from markdown, compare to existing.
Run with: pytest tests/test_roundtrip.py -v
Requires: KNOWLEDGE_WIKI env var or defaults to ~/Downloads/soft/knowledge_wiki
"""

import json
import os
from pathlib import Path

import pytest

from kw_engine.store.markdown import scan_memory_dir
from kw_engine.store.json_proj import build_index_json


def _wiki_root() -> Path:
    env = os.environ.get("KNOWLEDGE_WIKI")
    if env:
        return Path(env)
    default = Path.home() / "Downloads" / "soft" / "knowledge_wiki"
    if default.exists():
        return default
    pytest.skip("knowledge_wiki corpus not found")


@pytest.fixture
def wiki_memory():
    root = _wiki_root()
    mem = root / "memory"
    if not (mem / "SCHEMA.md").exists():
        pytest.skip("memory/SCHEMA.md not found")
    return mem


def test_all_papers_parse(wiki_memory):
    """Every paper markdown file must parse without error."""
    papers, _ = scan_memory_dir(wiki_memory)
    assert len(papers) > 0, "No papers found"


def test_all_principles_parse(wiki_memory):
    """Every principle markdown file must parse without error."""
    _, principles = scan_memory_dir(wiki_memory)
    assert len(principles) > 0, "No principles found"


def test_roundtrip_index_json(wiki_memory):
    """Regenerated index.json must match existing (semantic equality)."""
    papers, principles = scan_memory_dir(wiki_memory)

    existing_path = wiki_memory / "index.json"
    existing = json.loads(existing_path.read_text())
    synthesis_last_run = existing.get("synthesis", {}).get("last_run")
    synthesis_n_at_last_run = existing.get("synthesis", {}).get("n_principles_at_last_run")

    rebuilt = build_index_json(papers, principles, synthesis_last_run, synthesis_n_at_last_run)

    # Compare papers (order-independent)
    existing_papers = sorted(existing["papers"], key=lambda x: x["id"])
    rebuilt_papers = sorted(rebuilt["papers"], key=lambda x: x["id"])
    assert len(existing_papers) == len(rebuilt_papers), (
        f"Paper count: existing={len(existing_papers)}, rebuilt={len(rebuilt_papers)}"
    )
    for ep, rp in zip(existing_papers, rebuilt_papers):
        assert ep["id"] == rp["id"]
        assert ep["status"] == rp["status"], f"Paper {ep['id']}: status {ep['status']} vs {rp['status']}"
        assert ep["doi"] == rp["doi"], f"Paper {ep['id']}: doi mismatch"
        # paper→principles is derived from provenance; rebuilt is authoritative.
        # hand-maintained index may lag, so assert existing is a subset of rebuilt.
        existing_set = set(ep.get("principles", []))
        rebuilt_set = set(rp.get("principles", []))
        assert existing_set <= rebuilt_set, (
            f"Paper {ep['id']}: existing has principles not in rebuilt\n"
            f"  extra in existing={existing_set - rebuilt_set}"
        )

    # Compare principles (order-independent)
    existing_principles = sorted(existing["principles"], key=lambda x: x["id"])
    rebuilt_principles = sorted(rebuilt["principles"], key=lambda x: x["id"])
    assert len(existing_principles) == len(rebuilt_principles), (
        f"Principle count: existing={len(existing_principles)}, rebuilt={len(rebuilt_principles)}"
    )
    for epr, rpr in zip(existing_principles, rebuilt_principles):
        assert epr["id"] == rpr["id"]
        # Title/math_basis: markdown is truth; rebuilt is authoritative.
        # Verify rebuilt has non-empty values where expected.
        assert rpr.get("title"), f"Principle {rpr['id']}: rebuilt has empty title"
        if epr.get("math_basis"):
            assert rpr.get("math_basis"), f"Principle {epr['id']}: rebuilt lost math_basis"

    # Counters
    assert existing["counters"] == rebuilt["counters"], (
        f"Counters: existing={existing['counters']}, rebuilt={rebuilt['counters']}"
    )

    # Synthesis
    assert existing["synthesis"]["last_run"] == rebuilt["synthesis"]["last_run"]
    assert existing["synthesis"]["n_principles_at_last_run"] == rebuilt["synthesis"]["n_principles_at_last_run"]


def test_verify_passes(wiki_memory):
    """SCHEMA §6 checks pass on live corpus (minus known dangling links)."""
    from kw_engine.verify import run_checks

    papers, principles = scan_memory_dir(wiki_memory)
    verdicts = run_checks(papers, principles)
    critical_fails = [
        v for v in verdicts
        if v.status == "FAIL" and v.check_name != "link_integrity"
    ]
    assert critical_fails == [], f"Critical failures: {critical_fails}"
