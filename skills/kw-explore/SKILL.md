---
name: kw-explore
description: Problem-driven research loop — start from YOUR project or idea plus a pile of papers (even if insufficient), decompose it into a problem structure, map it onto the principle library, fill the gaps with targeted reading, and assemble a principle-grounded design. Iterates as you read more. Use when the user has a research problem or project to push forward — not just papers to absorb. Triggers: "improve my project", "I have an idea and some papers", "help me design X", "用这些论文迭代我的项目", "推进我的研究".
---

# /kw-explore — drive a research project with the principle library

This is the **problem-driven** loop. (`/kw` is the corpus-driven loop: absorb papers, synthesize
globally. `/kw-explore` starts from the user's actual problem and pulls the library toward solving
it.) It is the workflow that turns the engine from a knowledge library into a research accelerator.

You are the orchestrator. Dispatch the `kw-*` subagents for reading/distilling (model boundary
below); do the framing/mapping/assembly reasoning yourself.

**Separation of concerns (hard rule).** Use-case outputs — the problem decomposition, the design,
the handoff — go in the **user's project** (cwd). Reusable principles go into the **linked
knowledge base** (`kw status` shows which one). Never mix: the knowledge base stays domain-general
and reusable across projects.

**Model boundary (same as /kw).** The orchestrator never reads PDFs or calls `read_*`/`search_*`/
`download_*` MCP tools. Acquisition → `kw-fetcher` (sonnet); reading → `kw-reader` (sonnet);
distilling → `kw-distiller` (opus). Pass `model` explicitly on every Agent dispatch.

Prerequisite: the project must be linked to a knowledge base. If `kw status` errors, run
`kw link <name-or-path>` (or `/kw-init`) first.

---

## Phase 0 — Frame the problem (the most important step)

A good decomposition is most of the value. Do not skip to fetching papers.

1. Interview the user just enough to extract a **problem signature**: the *structural* axes of
   their problem, pushed toward the form the library indexes by — structural properties, not
   domain narrative. (E.g. not "vaginal microbiome typing" but "compositional/simplex-constrained
   data", "continuous spectrum + possible discrete sub-structure", "cross-population
   transferability", "must encode temporal dynamics".)
2. **Challenge the framing.** Find the load-bearing structural difficulty, not the surface
   complaint. (The CST example: the real defect was "resolution too low — classifying in a space
   where the signal has already been integrated out", not "the clusters are wrong".)
3. Write `<project>/problems/<slug>/PROBLEM.md`: the signature axes, plus what any solution MUST
   satisfy (the constraints — e.g. "must work on both targeted-amplicon AND shotgun data").
4. **Show the decomposition to the user and confirm it before proceeding.** A wrong signature
   wastes the whole loop downstream.

## Phase 1 — Absorb the seed papers (if any)

For each seed paper the user has (or names), run the standard absorb loop:
`kw-fetcher` (if no local PDF) → `kw-reader` → `kw-distiller` → then `kw-verifier scope=all`.
New principles land in the linked knowledge base. If the user has no papers yet, skip to Phase 2
(the library may already cover part of the problem) and lean on Phase 3.

## Phase 2 — Map the problem onto the library (coverage)

For each axis of the problem signature, run `kw search "<axis keywords>"`.
Build a **coverage map** and show it to the user:
- **Covered:** axis → matching principle(s) by pid + one-line mechanism.
- **Gaps:** axes with no matching mechanism — these are *this problem's* gaps (distinct from the
  global design-space gaps in `memory/synthesis/gaps.md`).

"A pile of papers that's not enough" shows up here as gaps. That's expected — Phase 3 closes them.

## Phase 3 — Fill the gaps (iterate, user-gated)

For each gap, propose specific papers or searches that would supply the missing mechanism (name
candidate authors/titles/DOIs). On the user's pick:
1. `kw-fetcher` the chosen papers → absorb (reader → distiller → verifier).
2. Re-run the relevant `kw search` and update the coverage map.
Report each round: which gaps closed, which remain. Loop until coverage is good enough OR the user
stops. Never auto-run many fetch rounds without a pick — keep the human steering.

## Phase 4 — Assemble a principle-grounded design

Compose the matched principles into a candidate design/solution for the user's project:
- Each design decision **cites the principle(s) it rests on** — build a traceability matrix
  (module → primary pids → supporting pids).
- Include concrete specs where the principles imply them (equations, data requirements, a
  validation plan).
- **Mark every module still without principle support** as a remaining gap + risk.
Write/update `<project>/docs/DESIGN.md`. (See the PRISM design as a worked example of the target
shape: modules, math specs, data requirements, validation plan, traceability matrix, risks.)

## Phase 5 — Iterate / handoff

The design is living — each future round of reading sharpens it. Write/update
`<project>/plan/HANDOFF.md`: current state, decisions made (with rationale), the next gaps to fill,
and the exact commands/prompts to resume. Also write a short `<project>/docs/RATIONALE.md`
capturing WHY the design is shaped this way (the problem signature + the direction choices) so a
fresh session can continue seamlessly.

---

Reproducibility: after each phase, append a one-line run record (phase, ids touched,
subagents+models, date) to `.kw/logs/runs.log`.

After Phase 4, offer: "(a) 补更多 gap  (b) 深化某个模块的设计  (c) 跑 L3 综合看全局  (d) 收尾写 handoff".
