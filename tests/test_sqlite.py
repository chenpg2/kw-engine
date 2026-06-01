import sqlite3
from pathlib import Path
from kw_engine.store.sqlite import create_schema, rebuild_index_db
from kw_engine.store.markdown import scan_memory_dir


def test_create_schema(tmp_path):
    db_path = tmp_path / "index.db"
    conn = create_schema(db_path)
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    assert "papers" in tables
    assert "principles" in tables
    assert "links" in tables
    conn.close()


def test_rebuild_index_db(sample_memory, tmp_path):
    db_path = tmp_path / "index.db"
    papers, principles = scan_memory_dir(sample_memory)
    rebuild_index_db(db_path, papers, principles)

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id, status, doi FROM papers").fetchone()
    assert row[0] == "test-paper"
    assert row[1] == "complete"

    row = conn.execute("SELECT id, title FROM principles").fetchone()
    assert row[0] == "P-0001"
    assert row[1] == "Test Principle"

    row = conn.execute("SELECT source_id, target_id, link_type FROM links").fetchone()
    assert row == ("P-0001", "P-0002", "contrasts")
    conn.close()
