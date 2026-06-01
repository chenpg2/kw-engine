import json
import sqlite3

from kw_engine.ui import (
    load_snapshot,
    paper_detail_lines,
    paper_rows,
    principle_detail_lines,
    principle_rows,
    reindex_memory,
    search_principle_rows,
    status_lines,
    verdict_summary,
)
from kw_engine.verify import Verdict


def test_load_snapshot_and_status_lines(sample_memory):
    snapshot = load_snapshot(sample_memory)

    assert len(snapshot.papers) == 1
    assert len(snapshot.principles) == 1
    assert snapshot.complete_papers == 1
    assert snapshot.pending_papers == 0
    assert snapshot.synthesis_status == "STALE (1 new principles)"
    assert "Papers: 1 total" in "\n".join(status_lines(snapshot))


def test_rows_and_detail_lines(sample_memory):
    snapshot = load_snapshot(sample_memory)

    papers = paper_rows(snapshot)
    principles = principle_rows(snapshot)

    assert papers[0].id == "test-paper"
    assert principles[0].id == "P-0001"
    assert "Test Paper" in "\n".join(paper_detail_lines(snapshot.papers[0]))
    assert "contrasts:P-0002" in "\n".join(principle_detail_lines(snapshot.principles[0]))


def test_reindex_memory_rebuilds_index_and_sqlite(sample_memory):
    (sample_memory / "index.json").write_text(json.dumps({
        "version": 1,
        "counters": {"principle": 0},
        "papers": [],
        "principles": [],
        "synthesis": {
            "last_run": "2026-01-01T00:00:00Z",
            "n_principles_at_last_run": 1,
        },
    }))

    message = reindex_memory(sample_memory)

    assert message == "Reindexed 1 papers and 1 principles"
    index_data = json.loads((sample_memory / "index.json").read_text())
    assert index_data["synthesis"]["last_run"] == "2026-01-01T00:00:00Z"
    assert index_data["synthesis"]["n_principles_at_last_run"] == 1
    assert index_data["counters"]["principle"] == 1

    db_path = sample_memory.parent / ".kw" / "index.db"
    assert db_path.exists()
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT title FROM principles WHERE id='P-0001'").fetchone()
    conn.close()
    assert row == ("Test Principle",)


def test_search_principle_rows(sample_memory):
    reindex_memory(sample_memory)
    snapshot = load_snapshot(sample_memory)

    rows = search_principle_rows(sample_memory, snapshot, "basis one")

    assert rows[0].id == "P-0001"
    assert rows[0].kind == "principle"


def test_verdict_summary():
    assert verdict_summary([Verdict("x", "PASS", "ok")]) == "verify: all checks PASS"
    assert verdict_summary([Verdict("x", "FAIL", "bad")]) == "verify: 1 failure(s)"
