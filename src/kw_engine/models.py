"""Pydantic v2 models mirroring memory/SCHEMA.md §1-§5."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

PaperStatus = Literal["pending", "L1", "L2", "complete", "incomplete"]
LinkType = Literal[
    "generalizes", "specializes", "composes", "composed-by",
    "contrasts", "contradicts", "applies_to",
]


def paper_id_from_provenance(prov: str) -> str:
    """Extract paper id from provenance like 'gkaf1205 §3.2' or 'ao-decomposition[Ao2003] ��II'."""
    token = prov.split()[0]
    bracket = token.find("[")
    return token[:bracket] if bracket != -1 else token


class Bib(BaseModel):
    title: str
    authors: str
    venue: str
    year: int | None = None


class LinkEntry(BaseModel):
    link_type: LinkType
    target: str

    @classmethod
    def from_str(cls, s: str) -> LinkEntry:
        typ, target = s.split(":", 1)
        return cls(link_type=typ, target=target)

    def to_str(self) -> str:
        return f"{self.link_type}:{self.target}"


class Paper(BaseModel):
    id: str
    status: PaperStatus
    doi: str | None = None
    title: str | None = None
    principles: list[str] = []


class PaperFull(BaseModel):
    id: str
    doi: str | None = None
    arxiv: str | None = None
    bib: Bib
    problem_addressed: str
    method_summary: str
    math_used: str
    claimed_mechanism: str
    key_evidence: str
    status: PaperStatus
    extract_template_version: str = "extract-template@v1"


class Principle(BaseModel):
    id: str
    title: str
    abstraction_level: str
    problem_signature: list[str]
    math_basis: list[str]
    mechanism: str
    rationale: str
    data_regime: list[str]
    falsifiable_prediction: str
    boundaries: str
    provenance: list[str]
    rubric_version: str = "distill-rubric@v1"
    links: list[str] = []

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not v.startswith("P-") or len(v) != 6 or not v[2:].isdigit():
            raise ValueError(f"Principle id must be P-#### format, got: {v}")
        return v


class PrincipleProjection(BaseModel):
    id: str
    title: str
    problem_signature: list[str]
    math_basis: list[str]
    provenance: list[str]
    rubric_version: str
    links: list[str] = []


class SynthesisState(BaseModel):
    last_run: str | None = None
    n_principles_at_last_run: int = 0


class IndexFile(BaseModel):
    version: int = 1
    counters: dict[str, int]
    papers: list[Paper]
    principles: list[PrincipleProjection]
    synthesis: SynthesisState
