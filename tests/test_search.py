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
