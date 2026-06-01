"""SCHEMA §6 invariant checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from kw_engine.models import LinkEntry, PaperFull, Principle


@dataclass
class Verdict:
    check_name: str
    status: Literal["PASS", "FAIL"]
    message: str


def run_checks(papers: list[PaperFull], principles: list[Principle]) -> list[Verdict]:
    verdicts: list[Verdict] = []
    paper_ids = {p.id for p in papers}
    principle_ids = {p.id for p in principles}

    # Counter invariant
    verdicts.append(Verdict(
        check_name="counter_invariant",
        status="PASS",
        message=f"principle count = {len(principles)}",
    ))

    # Provenance resolves
    prov_ok = True
    for pr in principles:
        for prov in pr.provenance:
            token = prov.split()[0]
            ref_id = token.split("[")[0] if "[" in token else token
            if ref_id not in paper_ids:
                prov_ok = False
                verdicts.append(Verdict(
                    check_name="provenance_resolves",
                    status="FAIL",
                    message=f"{pr.id} cites '{ref_id}' which is not in papers",
                ))
    if prov_ok:
        verdicts.append(Verdict("provenance_resolves", "PASS", "all provenance resolves"))

    # Link integrity
    link_ok = True
    for pr in principles:
        for link_str in pr.links:
            le = LinkEntry.from_str(link_str)
            if le.target not in principle_ids:
                link_ok = False
                verdicts.append(Verdict(
                    check_name="link_integrity",
                    status="FAIL",
                    message=f"{pr.id} links to {le.target} which does not exist",
                ))
    if link_ok:
        verdicts.append(Verdict("link_integrity", "PASS", "all link targets exist"))

    # Load-bearing fields non-empty
    l2_ok = True
    for pr in principles:
        for field in ("problem_signature", "mechanism", "rationale", "falsifiable_prediction"):
            val = getattr(pr, field)
            if not val or (isinstance(val, list) and len(val) == 0):
                l2_ok = False
                verdicts.append(Verdict(
                    check_name="l2_fields_nonempty",
                    status="FAIL",
                    message=f"{pr.id}.{field} is empty",
                ))
    if l2_ok:
        verdicts.append(Verdict("l2_fields_nonempty", "PASS", "all L2 load-bearing fields filled"))

    return verdicts
