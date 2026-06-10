"""Data models mirroring kw_engine/models.py (SCHEMA §1–§5), dependency-free.

No silent fallback: validation raises ValueError, never coerces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PAPER_STATUSES = {"pending", "L1", "L2", "complete", "incomplete"}
LINK_TYPES = {
    "generalizes", "specializes", "composes", "composed-by",
    "contrasts", "contradicts", "applies_to",
}

EXTRACT_TEMPLATE_VERSION = "extract-template@v1"
RUBRIC_VERSION = "distill-rubric@v1"


def paper_id_from_provenance(prov: str) -> str:
    """Extract paper id from provenance like 'gkaf1205 §3.2' or 'x[Ao2003] §II'."""
    token = prov.split()[0] if prov.split() else prov
    bracket = token.find("[")
    return token[:bracket] if bracket != -1 else token


def locator_from_provenance(prov: str) -> str:
    parts = prov.split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def validate_pid(pid: str) -> None:
    if not (pid.startswith("P-") and len(pid) == 6 and pid[2:].isdigit()):
        raise ValueError(f"Principle id must be P-#### format, got: {pid}")


@dataclass
class Bib:
    title: str = ""
    authors: str = ""
    venue: str = ""
    year: int | None = None


@dataclass
class PaperFull:
    id: str
    bib: Bib
    problem_addressed: str
    method_summary: str
    math_used: str
    claimed_mechanism: str
    key_evidence: str
    status: str
    doi: str | None = None
    arxiv: str | None = None
    extract_template_version: str = EXTRACT_TEMPLATE_VERSION

    @classmethod
    def from_frontmatter(cls, fm: dict, file: str) -> "PaperFull":
        def require(key: str):
            if key not in fm:
                raise ValueError(f"{file}: missing required field '{key}'")
            return fm[key]

        def s(v) -> str:
            return "" if v is None else str(v)

        pid = require("id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"{file}: 'id' must be a non-empty string")
        status = s(require("status"))
        if status not in PAPER_STATUSES:
            raise ValueError(f"{file}: invalid status '{status}'")
        bib_raw = require("bib")
        if not isinstance(bib_raw, dict):
            raise ValueError(f"{file}: 'bib' must be a mapping")
        year = bib_raw.get("year")
        if year is not None and not isinstance(year, int):
            try:
                year = int(year)
            except (TypeError, ValueError):
                raise ValueError(f"{file}: bib.year must be an integer or null") from None
        return cls(
            id=pid,
            doi=fm.get("doi") if isinstance(fm.get("doi"), str) else None,
            arxiv=fm.get("arxiv") if isinstance(fm.get("arxiv"), str) else None,
            bib=Bib(title=s(bib_raw.get("title")), authors=s(bib_raw.get("authors")),
                    venue=s(bib_raw.get("venue")), year=year),
            problem_addressed=s(require("problem_addressed")),
            method_summary=s(require("method_summary")),
            math_used=s(require("math_used")),
            claimed_mechanism=s(require("claimed_mechanism")),
            key_evidence=s(require("key_evidence")),
            status=status,
            extract_template_version=s(fm.get("extract_template_version") or EXTRACT_TEMPLATE_VERSION),
        )


@dataclass
class Principle:
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
    rubric_version: str = RUBRIC_VERSION
    links: list[str] = field(default_factory=list)

    @classmethod
    def from_frontmatter(cls, fm: dict, file: str) -> "Principle":
        def require(key: str):
            if key not in fm:
                raise ValueError(f"{file}: missing required field '{key}'")
            return fm[key]

        def s(v) -> str:
            return "" if v is None else str(v)

        def sl(v) -> list[str]:
            if v is None:
                return []
            if isinstance(v, list):
                return [str(x) for x in v if x is not None and str(x)]
            return [str(v)] if str(v) else []

        pid = s(require("id"))
        validate_pid(pid)
        return cls(
            id=pid,
            title=s(require("title")),
            abstraction_level=s(require("abstraction_level")),
            problem_signature=sl(require("problem_signature")),
            math_basis=sl(require("math_basis")),
            mechanism=s(require("mechanism")),
            rationale=s(require("rationale")),
            data_regime=sl(require("data_regime")),
            falsifiable_prediction=s(require("falsifiable_prediction")),
            boundaries=s(require("boundaries")),
            provenance=sl(require("provenance")),
            rubric_version=s(fm.get("rubric_version") or RUBRIC_VERSION),
            links=sl(fm.get("links")),
        )


@dataclass
class Verdict:
    check_name: str
    passed: bool
    message: str


@dataclass
class StatusSummary:
    papers_total: int
    papers_by_status: dict
    principles: int
    pending_papers: list[str]
    l1_papers: list[str]
    synthesis_last_run: str | None
    synthesis_stale: bool
    new_since_synthesis: int


@dataclass
class SearchHit:
    id: str
    title: str
    score: int
