"""The reasoning pipeline: L1 read → L2 distill → L3 synthesize → Ask.
LLM does the reasoning; Workspace does the deterministic storage.
Invalid model output is surfaced (logged/raised), never silently coerced.

Qt-free — UI runs these in worker threads and receives log lines via callback:
    log(level, text)  with level in {"info", "warn", "error", "success"}.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path

from .l10n import tr
from .llm import LLMClient, LLMError, flex_int, flex_list, flex_str
from .models import LINK_TYPES, Bib, PaperFull, SearchHit, paper_id_from_provenance
from .store import StoreError, Workspace
from . import prompts


@dataclass
class AskResult:
    signature: list[str]
    math_basis: list[str]
    answer: str
    hits: list[SearchHit] = field(default_factory=list)


def _today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def extract_pdf_text(path: Path, max_chars: int) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise StoreError("pypdf is not installed") from e
    try:
        reader = PdfReader(str(path))
    except Exception as e:
        raise StoreError(f"FAIL: cannot parse {path.name}: {e}") from e
    out: list[str] = []
    total = 0
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        chunk = f"\n\n[page {i + 1}]\n{text}"
        out.append(chunk)
        total += len(chunk)
        if total > max_chars:
            break
    full = "".join(out)
    if len(full) > max_chars:
        full = full[:max_chars] + "\n\n[TRUNCATED — remainder of the PDF omitted]"
    if len(full.strip()) <= 100:
        raise StoreError(f"FAIL: no extractable text in {path.name} (scanned PDF without OCR?)")
    return full


def _normalize_opt(s) -> str | None:
    if not isinstance(s, str):
        return None
    v = s.strip()
    if not v or v.lower() == "null" or v == "UNKNOWN":
        return None
    if v.startswith("https://doi.org/"):
        v = v[len("https://doi.org/"):]
    return v


class Pipeline:
    def __init__(self, workspace: Workspace, client: LLMClient, log=None):
        self.ws = workspace
        self.client = client
        self._log = log or (lambda level, text: None)

    def info(self, t: str): self._log("info", t)
    def warn(self, t: str): self._log("warn", t)
    def error(self, t: str): self._log("error", t)
    def success(self, t: str): self._log("success", t)

    # ------------------------------------------------------------------ L1
    def run_l1(self, paper_id: str) -> None:
        pdf = self.ws.pdf_path(paper_id)
        if not pdf.exists():
            raise StoreError(tr(f"找不到 paper/{paper_id}.pdf — 请先导入 PDF",
                                f"paper/{paper_id}.pdf not found — import the PDF first"))
        self.info(f"[L1] extracting text from paper/{paper_id}.pdf …")
        text = extract_pdf_text(pdf, self.client.settings.max_pdf_chars)
        model = self.client.settings.fast_model_effective
        self.info(f"[L1] {len(text)} chars → {model}")

        resp = self.client.complete_json(
            system=prompts.L1_SYSTEM,
            user=prompts.l1_user(paper_id, text),
            model=model,
        )
        if not isinstance(resp, dict):
            raise LLMError("L1 model output is not a JSON object")

        bib_raw = resp.get("bib") if isinstance(resp.get("bib"), dict) else {}
        record_status = "incomplete" if flex_str(resp, "status").lower() == "incomplete" else "complete"
        paper = PaperFull(
            id=paper_id,
            doi=_normalize_opt(resp.get("doi")),
            arxiv=_normalize_opt(resp.get("arxiv")),
            bib=Bib(
                title=flex_str(bib_raw, "title"),
                authors=flex_str(bib_raw, "authors"),
                venue=flex_str(bib_raw, "venue"),
                year=flex_int(bib_raw, "year"),
            ),
            problem_addressed=flex_str(resp, "problem_addressed"),
            method_summary=flex_str(resp, "method_summary"),
            math_used=flex_str(resp, "math_used"),
            claimed_mechanism=flex_str(resp, "claimed_mechanism"),
            key_evidence=flex_str(resp, "key_evidence"),
            status=record_status,
        )
        # Record carries its faithful-completeness status; the index tracks pipeline stage L1.
        self.ws.write_paper_record(paper, flex_str(resp, "notes"), index_status="L1")

        unknowns = [name for name, v in [
            ("problem_addressed", paper.problem_addressed),
            ("method_summary", paper.method_summary),
            ("math_used", paper.math_used),
            ("claimed_mechanism", paper.claimed_mechanism),
            ("key_evidence", paper.key_evidence),
        ] if "UNKNOWN" in v or not v]
        if unknowns:
            self.warn(f"[L1] UNKNOWN/empty fields: {', '.join(unknowns)}")
        self.success(f"[L1] wrote memory/papers/{paper_id}.md (record: {record_status}, index: L1)")

    # ------------------------------------------------------------------ L2
    def run_l2(self, paper_id: str) -> list[str]:
        l1_text = self.ws.paper_path(paper_id).read_text(encoding="utf-8")
        idx = self.ws.read_index()
        known_paper_ids = {p["id"] for p in idx["papers"]}
        existing_pids = {p["id"] for p in idx["principles"]}

        import json as _json
        projections = [
            {"id": p["id"], "title": p.get("title", ""),
             "problem_signature": p.get("problem_signature") or [],
             "math_basis": p.get("math_basis") or []}
            for p in idx["principles"]
        ]
        proj_json = _json.dumps(projections, ensure_ascii=False, indent=2)

        model = self.client.settings.strong_model
        self.info(f"[L2] distilling {paper_id} with {model} "
                  f"({len(existing_pids)} existing principles for dedup)")
        resp = self.client.complete_json(
            system=prompts.L2_SYSTEM,
            user=prompts.l2_user(paper_id, l1_text, proj_json),
            model=model,
        )
        if not isinstance(resp, dict):
            raise LLMError("L2 model output is not a JSON object")

        for reason in flex_list(resp, "skipped"):
            self.info(f"[L2] model skipped an idea: {reason}")

        created: list[str] = []
        drafts = resp.get("principles") if isinstance(resp.get("principles"), list) else []
        for raw in drafts:
            if not isinstance(raw, dict):
                continue
            title = flex_str(raw, "title")
            missing = [name for name, bad in [
                ("title", not title),
                ("abstraction_level", not flex_str(raw, "abstraction_level")),
                ("problem_signature", not flex_list(raw, "problem_signature")),
                ("mechanism", not flex_str(raw, "mechanism")),
                ("rationale", not flex_str(raw, "rationale")),
                ("falsifiable_prediction", not flex_str(raw, "falsifiable_prediction")),
            ] if bad]
            if missing:
                self.error(f"[L2] rejected draft '{title}': empty {', '.join(missing)}")
                continue
            provenance = self._repair_provenance(flex_list(raw, "provenance"),
                                                 paper_id, known_paper_ids)
            if not provenance:
                self.error(f"[L2] rejected draft '{title}': no resolvable provenance")
                continue
            links: list[str] = []
            for link in flex_list(raw, "links"):
                if ":" in link:
                    ltype, target = link.split(":", 1)
                    if target in existing_pids and ltype in LINK_TYPES:
                        links.append(link)
                        continue
                self.warn(f"[L2] dropped link '{link}' on '{title}' (unknown target or type)")
            notes = flex_str(raw, "notes")
            pid = self.ws.add_principle(
                title=title,
                abstraction_level=flex_str(raw, "abstraction_level"),
                problem_signature=flex_list(raw, "problem_signature"),
                math_basis=flex_list(raw, "math_basis"),
                mechanism=flex_str(raw, "mechanism"),
                rationale=flex_str(raw, "rationale"),
                data_regime=flex_list(raw, "data_regime"),
                falsifiable_prediction=flex_str(raw, "falsifiable_prediction"),
                boundaries=flex_str(raw, "boundaries"),
                provenance=provenance,
                links=links,
                body_notes=notes or None,
            )
            existing_pids.add(pid)
            created.append(pid)
            self.success(f"[L2] {pid} — {title}")

        updates = resp.get("existing_updates") if isinstance(resp.get("existing_updates"), list) else []
        for upd in updates:
            if not isinstance(upd, dict):
                continue
            pid = flex_str(upd, "pid")
            if pid not in existing_pids:
                self.warn(f"[L2] dropped update for unknown principle '{pid}'")
                continue
            entries = self._repair_provenance(flex_list(upd, "add_provenance"),
                                              paper_id, known_paper_ids)
            if not entries:
                self.warn(f"[L2] update for {pid} had no resolvable provenance")
                continue
            added = self.ws.append_provenance(pid, entries)
            if added:
                reason = flex_str(upd, "reason")
                self.success(f"[L2] {pid} ← provenance {'; '.join(added)} ({reason})")

        self.ws.update_index_paper(paper_id, status="complete", add_principles=created)
        if not created and not updates:
            self.warn(f"[L2] no principles created for {paper_id}")
        return created

    def _repair_provenance(self, entries: list[str], paper_id: str,
                           known: set[str]) -> list[str]:
        """Deterministic, logged repair — unresolvable entries are dropped loudly."""
        out: list[str] = []
        for raw in entries:
            e = raw.strip()
            if not e:
                continue
            ref = paper_id_from_provenance(e)
            if ref in known:
                out.append(e)
            elif e.startswith(("§", "Fig", "fig", "p.", "Table", "Sec")):
                self.info(f"[L2] repaired locator-only provenance '{e}' → '{paper_id} {e}'")
                out.append(f"{paper_id} {e}")
            else:
                self.warn(f"[L2] dropped provenance '{e}' (paper id '{ref}' not in library)")
        return out

    # ------------------------------------------------------------------ L3
    def run_l3(self) -> None:
        _, principles = self.ws.scan_markdown()
        if not principles:
            raise StoreError(tr("库中还没有原则，先处理几篇论文",
                                "No principles in the library yet — process some papers first"))
        import json as _json
        dump = [{
            "id": p.id, "title": p.title, "abstraction_level": p.abstraction_level,
            "problem_signature": p.problem_signature, "math_basis": p.math_basis,
            "mechanism": p.mechanism, "rationale": p.rationale,
            "data_regime": p.data_regime, "falsifiable_prediction": p.falsifiable_prediction,
            "boundaries": p.boundaries, "provenance": p.provenance, "links": p.links,
        } for p in principles]
        model = self.client.settings.strong_model
        self.info(f"[L3] synthesizing {len(principles)} principles with {model}")
        resp = self.client.complete_json(
            system=prompts.L3_SYSTEM,
            user=prompts.l3_user(_today(), _json.dumps(dump, ensure_ascii=False, indent=2)),
            model=model,
        )
        if not isinstance(resp, dict):
            raise LLMError("L3 model output is not a JSON object")

        design = flex_str(resp, "design_space")
        gaps = flex_str(resp, "gaps")
        contradictions = flex_str(resp, "contradictions")
        if not design or not gaps:
            raise LLMError("Model returned empty synthesis documents — nothing was written")
        if not contradictions:
            self.warn("[L3] model returned empty contradictions document; writing an explicit 'none' record")
            contradictions = (f"# Contradictions\n\n_No contradictions identified in this "
                              f"synthesis run ({_today()})._\n")

        pids = {p.id for p in principles}
        applied = 0
        links = resp.get("links") if isinstance(resp.get("links"), list) else []
        for link in links:
            if not isinstance(link, dict):
                continue
            f, t, lt = flex_str(link, "from"), flex_str(link, "to"), flex_str(link, "type")
            if f in pids and t in pids and f != t and lt in LINK_TYPES:
                self.ws.add_link(f, t, lt)
                applied += 1
            else:
                self.warn(f"[L3] dropped invalid link {f} -{lt}-> {t}")

        self.ws.write_synthesis_docs(design, contradictions, gaps, _today())
        self.success(f"[L3] wrote design-space.md, contradictions.md, gaps.md · {applied} links applied")
        for i, gap in enumerate(flex_list(resp, "top_gaps")[:3]):
            self.info(f"[L3] top gap {i + 1}: {gap}")

    # ------------------------------------------------------------------ Ask
    def ask(self, question: str) -> AskResult:
        self.info("[ask] extracting problem structure …")
        extract = self.client.complete_json(
            system=prompts.ASK_EXTRACT_SYSTEM,
            user=question,
            model=self.client.settings.fast_model_effective,
        )
        if not isinstance(extract, dict):
            raise LLMError("Ask-extract model output is not a JSON object")
        signature = flex_list(extract, "problem_signature")
        math_basis = flex_list(extract, "math_basis")
        query = " ".join([flex_str(extract, "query")] + signature + math_basis)
        self.info(f"[ask] signature: {' · '.join(signature)}")

        hits = self.ws.search_principles(query, top_k=10)
        if not hits:
            return AskResult(
                signature=signature, math_basis=math_basis,
                answer=tr(
                    "库中没有与该问题结构匹配的原则 — 这是当前知识库的一个空白（gap）。可以围绕该结构补充文献后再试。",
                    "No principle in the library matches this problem structure — that is a gap in "
                    "the current knowledge base. Acquire literature around this structure and try again.",
                ),
                hits=[],
            )
        records = ""
        for hit in hits[:5]:
            try:
                text = self.ws.principle_path(hit.id).read_text(encoding="utf-8")
            except OSError:
                continue
            records += f"\n### {hit.id} (score {hit.score})\n\n{text}\n"
        self.info(f"[ask] composing answer from {min(5, len(hits))} matched principles …")
        answer = self.client.complete(
            system=prompts.ASK_COMPOSE_SYSTEM,
            user=prompts.ask_compose_user(question, records),
            model=self.client.settings.strong_model,
        )
        self.success("[ask] done")
        return AskResult(signature=signature, math_basis=math_basis, answer=answer, hits=hits)
