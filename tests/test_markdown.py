from kw_engine.store.markdown import read_paper_md, read_principle_md, scan_memory_dir


def test_read_paper(sample_memory):
    paper = read_paper_md(sample_memory / "papers" / "test-paper.md")
    assert paper.id == "test-paper"
    assert paper.bib.year == 2024
    assert paper.status == "complete"


def test_read_principle(sample_memory):
    p = read_principle_md(sample_memory / "principles" / "P-0001.md")
    assert p.id == "P-0001"
    assert p.problem_signature == ["Sig one"]
    assert p.links == ["contrasts:P-0002"]


def test_scan_memory_dir(sample_memory):
    papers, principles = scan_memory_dir(sample_memory)
    assert len(papers) == 1
    assert len(principles) == 1
    assert papers[0].id == "test-paper"
    assert principles[0].id == "P-0001"
