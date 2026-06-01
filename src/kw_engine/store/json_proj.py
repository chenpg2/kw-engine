"""Build index.json projection from validated pydantic models."""

from __future__ import annotations

from typing import Any

from kw_engine.models import PaperFull, Principle


def _paper_id_from_provenance(prov: str) -> str:
    """Extract paper id from 'gkaf1205 §3.2' or 'ao-decomposition[Ao2003] §II'."""
    token = prov.split()[0]
    bracket = token.find("[")
    if bracket != -1:
        token = token[:bracket]
    return token


def build_index_json(
    papers: list[PaperFull],
    principles: list[Principle],
    synthesis_last_run: str | None = None,
    synthesis_n_at_last_run: int | None = None,
) -> dict[str, Any]:
    paper_to_principles: dict[str, list[str]] = {p.id: [] for p in papers}
    for pr in principles:
        for prov in pr.provenance:
            pid = _paper_id_from_provenance(prov)
            if pid in paper_to_principles:
                if pr.id not in paper_to_principles[pid]:
                    paper_to_principles[pid].append(pr.id)

    papers_proj = []
    for p in papers:
        papers_proj.append({
            "id": p.id,
            "status": p.status,
            "doi": p.doi,
            "title": p.bib.title,
            "principles": sorted(paper_to_principles.get(p.id, [])),
        })

    principles_proj = []
    for pr in principles:
        principles_proj.append({
            "id": pr.id,
            "title": pr.title,
            "problem_signature": pr.problem_signature,
            "math_basis": pr.math_basis,
            "provenance": pr.provenance,
            "rubric_version": pr.rubric_version,
            "links": pr.links,
        })

    n_at_last = synthesis_n_at_last_run if synthesis_n_at_last_run is not None else 0

    return {
        "version": 1,
        "counters": {"principle": len(principles)},
        "papers": papers_proj,
        "principles": principles_proj,
        "synthesis": {
            "last_run": synthesis_last_run,
            "n_principles_at_last_run": n_at_last,
        },
    }
