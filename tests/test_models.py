import pytest
from pydantic import ValidationError

from kw_engine.models import (
    Bib,
    IndexFile,
    LinkEntry,
    Paper,
    PaperFull,
    Principle,
    PrincipleProjection,
    SynthesisState,
)


def test_paper_valid():
    p = Paper(
        id="gkaf1205",
        status="complete",
        doi="10.1093/nar/gkaf1205",
        title="gutMSNP",
        principles=["P-0001"],
    )
    assert p.id == "gkaf1205"
    assert p.status == "complete"


def test_paper_status_enum():
    with pytest.raises(ValidationError):
        Paper(id="x", status="invalid", doi=None, title=None, principles=[])


def test_principle_valid():
    p = Principle(
        id="P-0001",
        title="Fine-grained signal",
        abstraction_level="stripped",
        problem_signature=["sig"],
        math_basis=["test"],
        mechanism="mech",
        rationale="rat",
        data_regime=["regime"],
        falsifiable_prediction="pred",
        boundaries="bounds",
        provenance=["gkaf1205 §3"],
        rubric_version="distill-rubric@v1",
        links=[],
    )
    assert p.id == "P-0001"


def test_principle_id_format():
    with pytest.raises(ValidationError):
        Principle(
            id="0001",
            title="x", abstraction_level="x",
            problem_signature=[], math_basis=[], mechanism="x",
            rationale="x", data_regime=[], falsifiable_prediction="x",
            boundaries="x", provenance=[], rubric_version="v1", links=[],
        )


def test_link_entry_parse():
    le = LinkEntry.from_str("contrasts:P-0005")
    assert le.link_type == "contrasts"
    assert le.target == "P-0005"


def test_link_entry_roundtrip():
    le = LinkEntry.from_str("generalizes:P-0010")
    assert le.to_str() == "generalizes:P-0010"


def test_index_counter_invariant():
    idx = IndexFile(
        version=1,
        counters={"principle": 1},
        papers=[],
        principles=[PrincipleProjection(
            id="P-0001", title="t", problem_signature=[],
            math_basis=[], provenance=[], rubric_version="v1", links=[],
        )],
        synthesis=SynthesisState(last_run=None, n_principles_at_last_run=0),
    )
    assert idx.counters["principle"] == len(idx.principles)


def test_paper_full_with_arxiv():
    p = PaperFull(
        id="seedat-te-cde",
        doi=None,
        arxiv="2206.08311",
        bib=Bib(title="TE-CDE", authors="Seedat et al.", venue="ICML", year=2022),
        problem_addressed="problem",
        method_summary="method",
        math_used="math",
        claimed_mechanism="mechanism",
        key_evidence="evidence",
        status="complete",
    )
    assert p.arxiv == "2206.08311"
    assert p.doi is None
