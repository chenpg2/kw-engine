"""Embedded kw-engine workspace templates — identical to `kw init` output."""

INITIAL_INDEX_JSON = """{
  "version": 1,
  "counters": {
    "principle": 0
  },
  "papers": [],
  "principles": [],
  "synthesis": {
    "last_run": null,
    "n_principles_at_last_run": 0
  }
}
"""

CONFIG_YAML = """version: 1
paths:
  papers_src: paper/
  memory: memory/
  index: memory/index.json
  process: process/
  problems: problems/
  logs: .kw/logs/
loop1:
  synthesize_after_n_papers: 5
process_versions:
  extract_template: extract-template@v1
  distill_rubric: distill-rubric@v1
model_routing:
  kw-fetcher: sonnet
  kw-reader: sonnet
  kw-distiller: opus
  kw-synthesizer: opus
  kw-verifier: sonnet
fetch:
  fallback_order:
  - with_fallback
  - arxiv
  - biorxiv
  - medrxiv
  - pubmed
  - crossref
  - openalex
  - semantic
  - curl_oa
  validate:
    magic_bytes: '%PDF-'
    min_bytes: 10240
    max_bytes: 52428800
  scihub: false
  paywalled_via_browse: true
  idempotent: true
active_expansion:
  enabled: false
"""

SCHEMA_MD = """# Memory Contract (phase A)

This file is the **single source of truth** for how memory is structured and accessed.
All skills/subagents MUST read/write memory ONLY through the operations in §4 —
never via ad-hoc file paths. (Phase C will implement these same operations as code;
upper layers must not change.)

## 1. Paper record (Layer 1 — faithful) — `memory/papers/<id>.md`
- `id`: paper id = source PDF filename stem (e.g. `gkaf1205`).
- YAML front-matter + markdown body. Required front-matter fields:
```yaml
id: gkaf1205
doi: null            # or DOI string if found
bib: { title: "", authors: "", venue: "", year: null }
problem_addressed: ""   # the concrete problem THIS paper solves (faithful, cite §)
method_summary: ""      # the method/algorithm (faithful)
math_used: ""           # mathematics used (faithful, name the machinery)
claimed_mechanism: ""   # WHY the authors claim it works (faithful)
key_evidence: ""        # key experiments/results + section locators
status: complete        # complete | incomplete
extract_template_version: extract-template@v1
```
Body: longer faithful notes, quotes with section locators. **No abstraction here.**

## 2. Principle record (Layer 2 — abstract, transferable) — `memory/principles/<pid>.md`
- `pid`: `P-0001` (4-digit, zero-padded, allocated from `index.json.counters.principle`).
```yaml
id: P-0001
title: ""                 # one-line general principle
abstraction_level: ""     # domain-stripped statement
problem_signature:        # WHEN it applies (problem structure properties)
  - ""
math_basis: []            # math machinery, lowercase-hyphen tags
mechanism: ""             # how the math attacks that structure
rationale: ""             # WHY structure<->mechanism connects (first principles)
data_regime:              # required data scale / conditions
  - ""
falsifiable_prediction: ""# a testable prediction implied by the principle
boundaries: ""            # when it breaks / assumptions
provenance: []            # ["gkaf1205 §3.2", ...] — MUST be real paper ids
rubric_version: distill-rubric@v1
links: []                 # ["generalizes:P-0003", "contrasts:P-0011"]
```
Body: longer derivation, evidence quotes, transfer notes.

## 3. Link schema (graph edge)
- Stored inline in each principle's `links` and mirrored in `index.json`.
- Form: `"<type>:<pid>"`. `type` ∈ {generalizes, specializes, composes, contrasts, contradicts, applies_to}.

## 4. Memory operations (file conventions — the A→C seam)
Implement each as the following file behavior. Skills/subagents invoke them by name.

- **add_paper(id)**: create `memory/papers/<id>.md` from `process/extract-template.md`;
  append `{id, status, ...}` to `index.json.papers` (status starts `pending`).
- **add_principle(record)**: allocate `pid` = `P-` + zero-pad(`counters.principle`+1);
  increment `counters.principle`; write `memory/principles/<pid>.md`; append projection
  `{id, title, problem_signature, math_basis, provenance, rubric_version, links}` to
  `index.json.principles`.
- **add_link(from_pid, to_pid, type)**: append `"<type>:<to_pid>"` to `from_pid`'s
  `links` (front-matter + index projection). (Optionally add the inverse on `to_pid`.)
- **search_principles(signature)**: read `index.json.principles`; rank by semantic match
  of `problem_signature`/`math_basis` to the query `signature`; return ranked `pid`s.
  (Reader then opens the matching `memory/principles/<pid>.md` files.)
- **get_synthesis()**: read `memory/synthesis/{design-space,contradictions,gaps}.md`.
- **list_gaps()**: read `memory/synthesis/gaps.md`.

## 5. `index.json` shape
```json
{
  "version": 1,
  "counters": { "principle": 0 },
  "papers": [
    { "id": "gkaf1205", "status": "pending|L1|L2|complete",
      "doi": null, "title": "", "principles": [] }
  ],
  "principles": [
    { "id": "P-0001", "title": "", "problem_signature": [],
      "math_basis": [], "provenance": [], "rubric_version": "", "links": [] }
  ],
  "synthesis": { "last_run": null, "n_principles_at_last_run": 0 }
}
```

## 6. Invariants (verifier enforces — see kw-verifier)
- Every `provenance` entry resolves to a real `papers[].id`.
- Every `links` target `pid` exists in `principles[]`.
- No principle has empty `problem_signature`, `mechanism`, `rationale`, or
  `falsifiable_prediction` (else `status: incomplete`, flagged — never silently accepted).
- L1 records contain NO abstraction; L2 records contain NO un-stripped biology
  (domain terms only inside `provenance`/body quotes).
- `counters.principle` == number of `principles[]` entries.
"""

EXTRACT_TEMPLATE_MD = """# extract-template@v1 — Layer 1 faithful reading

Produce a `memory/papers/<id>.md` per the SCHEMA §1. Rules:
- FAITHFUL ONLY. Report what the paper says; do NOT generalize or editorialize.
- Every claim cites a section/figure locator (e.g. "§3.2", "Fig 2").
- If a required field cannot be filled from the text, write `UNKNOWN` and set
  `status: incomplete` (never invent).

Fill exactly these front-matter fields (SCHEMA §1):
- bib (title/authors/venue/year), doi if present
- problem_addressed — the concrete problem this paper solves
- method_summary — the method/algorithm, named
- math_used — the mathematical machinery, named (e.g. "entropic optimal transport")
- claimed_mechanism — the authors' stated reason it works
- key_evidence — the key results + locators

Body: faithful notes, direct quotes with locators for anything that will feed L2.
Set `extract_template_version: extract-template@v1`.
"""

DISTILL_RUBRIC_MD = """# distill-rubric@v1 — Layer 2 first-principles distillation

Input: a `memory/papers/<id>.md` (L1). Output: one or more principle records
(SCHEMA §2) via `add_principle`. This is where abstraction happens.

For each distinct transferable idea in the paper, produce a principle that:
1. **Strips the biology.** `abstraction_level` states the idea with NO domain terms.
   (Domain specifics live only in `provenance` and body quotes.)
2. **Captures the mapping** — the three load-bearing fields:
   - `problem_signature`: the STRUCTURAL properties a problem must have for this to apply
     (not "microbiome data" but "two unlabeled sample sets with a meaningful cost geometry").
   - `mechanism` + `math_basis`: the mathematical machinery and how it attacks that structure.
   - `rationale`: the FIRST-PRINCIPLES reason the structure↔mechanism mapping holds.
3. **States limits & testability:**
   - `data_regime`: required data scale/conditions (e.g. "needs N≳hundreds; robust to sparsity").
   - `falsifiable_prediction`: a concrete test that would confirm/refute the mechanism.
   - `boundaries`: assumptions / when it breaks.
4. **Cites provenance**: real `<paperid> §loc` only.
5. **Proposes links** to existing principles (generalizes/contrasts/...) when evident.

Quality bar (verifier checks): no empty load-bearing field; `abstraction_level` free of
un-stripped domain nouns; `rationale` explains WHY (not just restating the mechanism).
Set `rubric_version: distill-rubric@v1` on every principle.
"""
