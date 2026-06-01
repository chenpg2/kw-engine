import json

from kw_engine.store.search import search_principles


def test_search_by_signature(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    idx = {"version": 1, "counters": {"principle": 2}, "papers": [],
           "principles": [
               {"id": "P-0001", "title": "clustering method",
                "problem_signature": ["high-dimensional data", "unknown cluster count"],
                "math_basis": ["dirichlet-process", "variational-inference"],
                "provenance": [], "rubric_version": "v1", "links": []},
               {"id": "P-0002", "title": "regression method",
                "problem_signature": ["noisy observations", "linear relationship"],
                "math_basis": ["least-squares", "ridge-regularization"],
                "provenance": [], "rubric_version": "v1", "links": []},
           ],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    results = search_principles(mem, "high-dimensional clustering")
    assert results[0]["id"] == "P-0001"


def test_search_by_math_basis(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    idx = {"version": 1, "counters": {"principle": 2}, "papers": [],
           "principles": [
               {"id": "P-0001", "title": "t1",
                "problem_signature": ["x"], "math_basis": ["optimal-transport", "wasserstein"],
                "provenance": [], "rubric_version": "v1", "links": []},
               {"id": "P-0002", "title": "t2",
                "problem_signature": ["y"], "math_basis": ["gradient-descent"],
                "provenance": [], "rubric_version": "v1", "links": []},
           ],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    results = search_principles(mem, "optimal transport wasserstein")
    assert results[0]["id"] == "P-0001"


def test_search_returns_empty_on_no_match(tmp_path):
    mem = tmp_path / "memory"
    mem.mkdir()
    idx = {"version": 1, "counters": {"principle": 1}, "papers": [],
           "principles": [
               {"id": "P-0001", "title": "t", "problem_signature": ["a"],
                "math_basis": ["b"], "provenance": [], "rubric_version": "v1", "links": []},
           ],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    results = search_principles(mem, "zzz-no-match-xxx")
    assert len(results) == 0 or results[0].get("score", 0) == 0


def test_search_via_sqlite(tmp_path):
    """Search uses SQLite when index.db is available."""
    from kw_engine.store.markdown import scan_memory_dir
    from kw_engine.store.sqlite import rebuild_index_db

    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()

    # Write a principle markdown file
    (mem / "principles" / "P-0001.md").write_text(
        '---\nid: P-0001\ntitle: "OT method"\nabstraction_level: "a"\n'
        'problem_signature:\n  - "optimal transport between measures"\n'
        'math_basis:\n  - "wasserstein-distance"\nmechanism: "m"\n'
        'rationale: "r"\ndata_regime:\n  - "d"\nfalsifiable_prediction: "f"\n'
        'boundaries: "b"\nprovenance:\n  - "p1 §1"\nrubric_version: distill-rubric@v1\n'
        'links: []\n---\nBody.\n'
    )

    # Build SQLite
    kw_dir = tmp_path / ".kw"
    kw_dir.mkdir()
    papers, principles = scan_memory_dir(mem)
    rebuild_index_db(kw_dir / "index.db", papers, principles)

    # Also write index.json for the fallback path
    idx = {"version": 1, "counters": {"principle": 1}, "papers": [],
           "principles": [{"id": "P-0001", "title": "OT method",
               "problem_signature": ["optimal transport between measures"],
               "math_basis": ["wasserstein-distance"],
               "provenance": ["p1 §1"], "rubric_version": "v1", "links": []}],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    results = search_principles(mem, "optimal transport wasserstein")
    assert len(results) > 0
    assert results[0]["id"] == "P-0001"
