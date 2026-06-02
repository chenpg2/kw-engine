---
name: kw
description: Single entry for the knowledge engine. Detects state and offers choices — fetch papers by id/DOI/title, absorb all new papers (L1→L2), run L3 synthesis. Use when the user says "process the knowledge base", "/kw", "fetch this paper", or drops new papers.
---

# /kw — knowledge engine (Loop 1)

You are the orchestrator. Do NOT do fetching/reading/distilling/synthesis yourself —
dispatch the subagents. Read `.kw/config.yaml` and `memory/index.json` first.

**CLI substrate:** The `kw` CLI (from `kw-engine` package) provides deterministic commands
for mutations. Subagents should use these instead of hand-editing index.json:
- `kw add-paper <id>` — register a paper (creates scaffold md + index entry)
- `kw add-principle --title … --sig … --math … …` — allocate P-####
- `kw add-link <from> <to> <type>` — add link (preserves formatting)
- `kw search "<query>"` — find relevant principles
- `kw fetch <id>` — acquire PDF + validate + register
- `kw reindex` — rebuild index.json + SQLite from markdown
- `kw verify` — check SCHEMA §6 invariants
- `kw status` — show engine state

**Hard boundary (cost + separation):** never call `read_*`/`search_*`/`download_*` MCP
tools or read a paper PDF in this (opus) loop — that wastes opus on text-ingestion and
bypasses the engine. Acquisition runs on `kw-fetcher`; reading runs on `kw-reader`. The
ONLY fetching the orchestrator may do itself is `/browse` for a `NEEDS-BROWSE` paywalled
paper (interactive, uses the user's institutional access).

**Model enforcement — MUST pass `model` explicitly on every Agent dispatch:**
| subagent       | model   | subagent_type    |
|----------------|---------|------------------|
| kw-fetcher     | sonnet  | kw-fetcher       |
| kw-reader      | sonnet  | kw-reader        |
| kw-distiller   | opus    | kw-distiller     |
| kw-synthesizer | opus    | kw-synthesizer   |
| kw-verifier    | sonnet  | kw-verifier      |

Frontmatter `model:` alone does NOT guarantee the model — the Agent tool inherits the
parent session model by default. You MUST pass BOTH `subagent_type` AND `model` in every
Agent call. Example:
```
Agent({ subagent_type: "kw-reader", model: "sonnet", prompt: "..." })
```
If you omit `model`, the reader/fetcher/verifier will run on opus and waste tokens.

## Step 1 — detect state
- missing PDFs = ids the user asked for (or referenced) with no valid `paper/<id>.pdf`.
- new papers = PDFs in `paper/` whose id is `pending`/`L1` (not `complete`) in index.
- synthesis stale = `index.synthesis.n_principles_at_last_run` < current principle count.

## Step 2 — present a short choice menu (edge-of-process choices)
Offer only the relevant actions, e.g.:
- "(a) 吸收全部 N 篇新论文  (b) 仅跑 L3 综合  (c) 抽查质量(verifier)  (d) 查看 gaps"
Wait for the user's pick. Never auto-run a heavy action without a pick.

## Action: fetch
For each requested `identifier` (arXiv id / DOI / title), dispatch with
`Agent({ subagent_type: "kw-fetcher", model: "sonnet", prompt: "..." })` — in parallel
when there are several. Collect its one-line verdicts and surface them:
- `OK`/`SKIP` → a valid `paper/<id>.pdf` now exists (registered `pending`).
- `NEEDS-BROWSE: <id> | doi= | url=` → fetch it yourself with `/browse` (institutional
  access), save to `paper/<id>.pdf`, then re-run `add_paper(id)` so it registers `pending`.
- `AMBIGUOUS`/`FAIL` → report loudly; ask the user to disambiguate or supply the PDF.
Never fabricate a PDF. Then offer to absorb the freshly fetched papers.

## Action: absorb-all
0. **Fetch gate:** for any requested id lacking a valid `paper/<id>.pdf`, run **fetch**
   (above) first. Only papers with a real validated PDF proceed.
For EACH new paper (process all at once — no per-paper command):
1. `Agent({ subagent_type: "kw-reader", model: "sonnet", prompt: "id=<id>" })` → L1.
2. `Agent({ subagent_type: "kw-distiller", model: "opus", prompt: "id=<id>" })` → L2.
Then `Agent({ subagent_type: "kw-verifier", model: "sonnet", prompt: "scope=all" })`.
Report: papers absorbed, principles created, any verifier FAILs (surface them — do not hide).

**Rubric self-improvement (capture step).** For each verifier FAIL or quality issue you
observe this batch (an abstraction leaking domain nouns, a weak rationale, a missed dedup),
generalize it into ONE reusable rule and capture it:
```
kw rubric add --rule "<the general rule>" --trigger "<the specific failure, e.g. P-0047 leaked 'Lactobacillus'>"
```
This stages the lesson — it does NOT touch the live rubric. When candidates accumulate,
run `kw rubric review` (Codex audits consistency, proposes a cleaned rubric) then, after
you read the proposal, `kw rubric promote`. This is the validation gate that prevents drift.

**Then present the post-absorb choice:** "(a) 现在跑 L3 综合  (b) 先抽查某篇  (c) 继续投喂更多".
If a PDF fails to parse, report it loudly and continue with the rest.

## Action: synthesize
Dispatch `kw-synthesizer` (pass today's date). Report clusters/contradictions/gaps + top 3 gaps.

## Action: spot-check
Dispatch `kw-verifier` for the chosen scope; report verdicts.

## Action: gaps
Read `memory/synthesis/gaps.md` and summarize (note: filling gaps = active expansion, Plan 4, default off).

Reproducibility: after any action, append a one-line run record (action, ids touched,
subagents+models, date) to `.kw/logs/runs.log`.
