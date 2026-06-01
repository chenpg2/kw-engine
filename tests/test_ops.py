import json

from kw_engine.store.ops import add_link, add_paper, add_principle


def test_add_paper(tmp_path):
    """add_paper creates a markdown file and registers in index.json."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    # Create minimal index
    idx = {"version": 1, "counters": {"principle": 0}, "papers": [], "principles": [],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    add_paper(mem, "test-id", doi="10.1234/test", title="Test Paper")

    # Check markdown was created
    md_path = mem / "papers" / "test-id.md"
    assert md_path.exists()
    content = md_path.read_text()
    assert "id: test-id" in content
    assert "status: pending" in content

    # Check index.json was updated
    new_idx = json.loads((mem / "index.json").read_text())
    assert any(p["id"] == "test-id" for p in new_idx["papers"])
    paper = next(p for p in new_idx["papers"] if p["id"] == "test-id")
    assert paper["status"] == "pending"
    assert paper["doi"] == "10.1234/test"


def test_add_paper_idempotent(tmp_path):
    """add_paper does nothing if paper already exists."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    idx = {"version": 1, "counters": {"principle": 0}, "papers": [],
           "principles": [], "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    add_paper(mem, "dup-id")
    add_paper(mem, "dup-id")  # second call

    new_idx = json.loads((mem / "index.json").read_text())
    assert sum(1 for p in new_idx["papers"] if p["id"] == "dup-id") == 1


def test_add_principle(tmp_path):
    """add_principle allocates pid, creates md, updates index."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    idx = {"version": 1, "counters": {"principle": 0}, "papers": [
        {"id": "paper1", "status": "complete", "doi": None, "title": "P1", "principles": []}
    ], "principles": [], "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    pid = add_principle(
        mem,
        title="Test Principle",
        abstraction_level="Abstract statement",
        problem_signature=["sig1"],
        math_basis=["basis1"],
        mechanism="A mechanism",
        rationale="A rationale",
        data_regime=["regime1"],
        falsifiable_prediction="prediction",
        boundaries="bounds",
        provenance=["paper1 §3"],
    )

    assert pid == "P-0001"

    # Check markdown
    md_path = mem / "principles" / "P-0001.md"
    assert md_path.exists()
    content = md_path.read_text()
    assert "id: P-0001" in content
    assert "Test Principle" in content

    # Check index
    new_idx = json.loads((mem / "index.json").read_text())
    assert new_idx["counters"]["principle"] == 1
    assert len(new_idx["principles"]) == 1
    assert new_idx["principles"][0]["id"] == "P-0001"


def test_add_principle_increments_counter(tmp_path):
    """Second add_principle gets P-0002."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()
    idx = {"version": 1, "counters": {"principle": 1}, "papers": [
        {"id": "p1", "status": "complete", "doi": None, "title": "P", "principles": []}
    ], "principles": [{"id": "P-0001", "title": "t", "problem_signature": [],
        "math_basis": [], "provenance": [], "rubric_version": "v1", "links": []}],
        "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    pid = add_principle(
        mem, title="Second", abstraction_level="a", problem_signature=["s"],
        math_basis=["b"], mechanism="m", rationale="r", data_regime=["d"],
        falsifiable_prediction="f", boundaries="b", provenance=["p1 §1"],
    )

    assert pid == "P-0002"
    new_idx = json.loads((mem / "index.json").read_text())
    assert new_idx["counters"]["principle"] == 2


def test_add_link(tmp_path):
    """add_link updates frontmatter and index."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()

    # Create a principle file with empty links
    (mem / "principles" / "P-0001.md").write_text(
        '---\nid: P-0001\ntitle: "T"\nabstraction_level: "a"\n'
        'problem_signature:\n  - "s"\nmath_basis:\n  - "b"\n'
        'mechanism: "m"\nrationale: "r"\ndata_regime:\n  - "d"\n'
        'falsifiable_prediction: "f"\nboundaries: "b"\n'
        'provenance:\n  - "p1 §1"\nrubric_version: distill-rubric@v1\n'
        'links: []\n---\nBody.\n'
    )

    idx = {"version": 1, "counters": {"principle": 2}, "papers": [],
           "principles": [
               {"id": "P-0001", "title": "T", "problem_signature": ["s"],
                "math_basis": ["b"], "provenance": ["p1 §1"], "rubric_version": "v1", "links": []},
               {"id": "P-0002", "title": "T2", "problem_signature": ["s"],
                "math_basis": ["b"], "provenance": ["p1 §2"], "rubric_version": "v1", "links": []},
           ],
           "synthesis": {"last_run": None, "n_principles_at_last_run": 0}}
    (mem / "index.json").write_text(json.dumps(idx))

    add_link(mem, "P-0001", "P-0002", "generalizes")

    # Check markdown updated
    content = (mem / "principles" / "P-0001.md").read_text()
    assert "generalizes:P-0002" in content

    # Check index updated
    new_idx = json.loads((mem / "index.json").read_text())
    p1 = next(p for p in new_idx["principles"] if p["id"] == "P-0001")
    assert "generalizes:P-0002" in p1["links"]
