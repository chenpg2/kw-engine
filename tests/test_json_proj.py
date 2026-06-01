import json
from kw_engine.store.json_proj import build_index_json
from kw_engine.store.markdown import scan_memory_dir


def test_build_index_json(sample_memory):
    papers, principles = scan_memory_dir(sample_memory)
    result = build_index_json(papers, principles)
    assert result["version"] == 1
    assert result["counters"]["principle"] == 1
    assert len(result["papers"]) == 1
    assert result["papers"][0]["id"] == "test-paper"
    assert result["papers"][0]["status"] == "complete"
    assert len(result["principles"]) == 1
    assert result["principles"][0]["id"] == "P-0001"
    json.dumps(result)


def test_paper_projection_has_principles_list(sample_memory):
    papers, principles = scan_memory_dir(sample_memory)
    result = build_index_json(papers, principles)
    assert "principles" in result["papers"][0]
    assert result["papers"][0]["principles"] == ["P-0001"]
