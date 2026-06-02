<div align="center">

<img src="banner.png" alt="kw-engine banner" width="100%">

# kw-engine

**Stop re-reading papers. Start reusing the *why*.**

A methodology evolution engine: it distills transferable problem-solving principles from literature, so when you hit a new problem you search by its *structure* and get back a mechanism that works — plus the reason it works and when it breaks.

[![CI](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-52%20passing-brightgreen)
![Types](https://img.shields.io/badge/mypy-strict-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**English** · [简体中文](README.zh-CN.md)

</div>

---

## The problem

You read a paper, extract a clever trick, and forget it. Six months later you face a problem the *same trick* would solve — but it was in another field, used different words, and your notes are a pile of PDFs. Your bottleneck was never finding papers. It was **reusing the underlying method across domains.**

kw-engine treats that as the actual problem.

## What it does

It distills literature through three layers, stripping the domain and keeping the transferable logic:

```
 Paper PDF
   │
   ├─  L1  faithful extraction   what the paper says, with section locators — no interpretation
   │
   ├─  L2  abstraction           strip the domain, keep the transferable core:
   │                               problem-signature   ·  WHEN it applies (problem structure)
   │                               ↔ mechanism + math  ·  WHAT to do
   │                               ↔ rationale         ·  WHY structure ↔ mechanism holds
   │
   └─  L3  synthesis             cluster principles into a design-space map; surface
                                  contradictions and GAPS — your next reading list
```

Then the payoff:

```
New problem  →  search by its structure  →  matched mechanism + rationale + when-it-breaks
```

It's not a search index over text. It's a compiler from *empirical results* to *reusable problem-solving strategies*. (The math of why this works is at the [end](#under-the-hood-why-the-loops-converge).)

## How it compares

|  | What it retrieves | Indexed by |
|---|---|---|
| **RAG / vector search** | text chunks | surface semantics |
| **Zotero / citation managers** | references & PDFs | metadata, tags |
| **Skill libraries** (e.g. Voyager) | executable task code | task name |
| **kw-engine** | **mechanism + why-it-works + when-it-fails** | **problem structure** |

---

## Get started

### 1. Install the CLI

```bash
uv tool install git+https://github.com/chenpg2/kw-engine   # gives you the `kw` command
```

### 2. (Optional) Install the Claude Code plugin

The plugin adds the reasoning layer — the `/kw` skill and five sub-agents that read, distill, and synthesize for you. Run in your terminal:

```bash
claude plugins marketplace add chenpg2/kw-engine
claude plugins install kw-engine@kw-engine
```

> The `kw` CLI is the deterministic substrate; the plugin is the LLM reasoning that drives it. For the full experience you want both; the CLI alone works fine for manual use.

### 3. Sixty-second tour

```bash
kw init                                    # scaffold a workspace (memory/, .kw/, process/, paper/)
kw fetch 2304.04740                        # acquire a PDF (open-access fallback chain + validation)
kw add-paper 2304.04740 --title "Flow Matching for Generative Modeling"
kw add-principle \
  --title "Reduce hard dynamics optimization to static coupling + regression onto bridges" \
  --sig "unpaired marginal snapshots" --sig "continuous-time generative process" \
  --math "optimal-transport" --math "conditional-flow" \
  --mechanism "Solve a static coupling, then regress a vector field onto closed-form bridges." \
  --rationale "The dynamic optimum decomposes into per-pair bridges, so it collapses to a coupling." \
  --regime "needs paired or OT-coupleable marginals; N large enough to estimate the coupling" \
  --prediction "straightening the coupling reduces sampling steps without retraining" \
  --boundaries "fails if the bridge family doesn't match the true conditional process" \
  --prov "2304.04740 §3.2"

kw search "optimal transport dynamics"     # ← the payoff: retrieve by problem structure
kw verify                                  # check integrity (provenance, links, required fields)
kw ui                                      # optional: browse/search/verify in a terminal UI
```

### Let Claude Code drive it

With the plugin installed, you never hand-edit a record — the skill orchestrates the whole loop, using the cheap model to read and the strong model to abstract:

```
/kw          # detects state, offers a menu, runs fetch → read → distill → synthesize → verify
/kw-init     # scaffold a workspace from natural language
```

---

## Knowledge bases: one library, many projects

A knowledge base lives in one place; any project links to it by name. No copies.

```bash
# Register topic-specific libraries once (stored in ~/.kw/registry.yaml)
kw kb add microbiome  ~/research/microbiome-kb/memory
kw kb add causal      ~/research/causal-inference-kb/memory
kw kb list

# In any project, link by name — every kw command now uses that library
cd ~/my-project
kw link microbiome
kw search "simplex dynamics"

# Switch topics anytime
kw link causal
kw search "intervention identifiability"
```

`kw link` writes a small `.kw/config.yaml` pointing at the shared library. Multiple projects can share one knowledge base at the same time.

---

## How it improves itself

There are two loops. **Loop 1 is the core** — it's how the knowledge evolves and runs whenever you absorb papers. **Loop 2 is optional** — an opt-in enhancement for when you want the distiller itself to get better over time. The engine is fully functional with Loop 2 switched off (you just never run the `kw rubric` commands).

### Loop 1 — the knowledge grows (core, gap-driven)

`L3 synthesis` clusters what you know into a design-space map and computes **gaps** — problem structures with no good mechanism yet. Gaps become your next reading list. Each new paper is deduped and linked into the graph, so re-synthesizing yields *sharper* gaps. The objective (what to read next) is generated by the current state, not handed in from outside.

### Loop 2 — the distiller sharpens (optional, semi-automatic)

*Skip this entirely and the engine still works — the distiller just keeps using its static rubric.* Turn it on when you've absorbed enough papers to notice recurring distillation mistakes worth fixing once and for all.

Every distillation failure (an abstraction that leaked a domain noun, a weak rationale, a missed dedup) can become a rule that improves the rubric the distiller follows. This is the cheap core of [SkillOpt](https://github.com/microsoft/SkillOpt)-style "let failures edit the skill," without the training harness — because the failure signals are already produced for free by the verifier.

**It is deliberately not fully automatic.** Capturing a lesson is cheap and safe; changing the live rubric is gated by review:

| Step | Command | Who runs it | Why |
|---|---|---|---|
| **Capture** | `kw rubric add` | the `/kw` agent, during a batch | turn a specific failure into a general rule (staged, does **not** touch the live rubric) |
| **Review** | `kw rubric review` | **you** | Codex audits the staged rules against the live rubric for consistency, proposes a cleaned version |
| **Promote** | `kw rubric promote` | **you**, after reading the proposal | swap the reviewed rubric in; archives the old one, clears the queue |

The manual `review` + `promote` are the **validation gate**: they stop the rubric from drifting, bloating, or accumulating contradictions. A bad rule never silently reaches the live rubric. (Want a `--auto` promote when Codex certifies a pure-addition? That's a planned opt-in; the safe default stays manual.)

#### No command line? Just ask Claude

With the plugin installed you never type a `kw` command — you drive Loop 2 in plain language and Claude runs the tools:

1. **While you read papers**, Claude captures distillation lessons on its own. You do nothing.
2. **When you want to apply them**, say:
   > *"Review the distiller rubric and show me what would change."*

   Claude runs the audit and summarizes the proposed changes in plain language.
3. **To make it live**, say:
   > *"Looks good, apply it."*

   Claude promotes it. It always shows you the proposal and asks first — the live rubric never changes silently.

That's all of Loop 2 without a terminal: read papers as usual, then occasionally say *"review the rubric"* and *"apply it."*

---

## CLI reference

| Command | Purpose |
|---|---|
| **Knowledge bases** | |
| `kw kb add <name> <path>` | Register a named knowledge base |
| `kw kb list` / `kw kb remove <name>` | List / unregister (files untouched) |
| `kw link <name-or-path>` | Link the current project to a knowledge base |
| **Workspace** | |
| `kw init [dir]` | Scaffold a new workspace |
| `kw status` | Counts, pending papers, synthesis staleness |
| `kw ui` | Terminal UI to browse, search, verify, reindex |
| `kw reindex` | Rebuild `index.json` + SQLite from markdown |
| `kw verify` | Check integrity invariants |
| **Papers & principles** | |
| `kw fetch <id\|doi\|title>` | Acquire a PDF (OA fallback chain) + validate + register |
| `kw add-paper <id>` | Register a paper |
| `kw add-principle …` | Allocate `P-####`, write the principle, update index + SQLite |
| `kw add-link <from> <to> <type>` | Link principles (`generalizes`/`contrasts`/`composes`/…) |
| `kw search "<query>"` | Retrieve principles by problem-signature / math-basis |
| **Self-improving rubric** (see [Loop 2](#loop-2--the-distiller-sharpens-semi-automatic)) | |
| `kw rubric add --rule … --trigger …` | Capture a lesson from a failure (staged) |
| `kw rubric status` | Show pending candidate rules |
| `kw rubric review` | Codex audits candidates → proposes a cleaned rubric |
| `kw rubric promote` | Promote the reviewed rubric to live |

---

## Architecture

```
 memory/papers/*.md          ┐
 memory/principles/*.md       ├─ source of truth (git-tracked, human-readable)
 memory/synthesis/*.md        ┘
        │  kw reindex
        ▼
 memory/index.json     (diffable catalog projection, committed)
 .kw/index.db          (SQLite query index, gitignored, rebuildable)
```

- **Markdown is truth.** Indices are derived — delete and rebuild any time.
- **Atomic writes.** Temp-file rename + `flock` on the index; no torn writes, no pid collisions.
- **No silent fallback.** Validation errors raise; the engine never writes a placeholder record.
- **Two-tier by design.** LLM agents reason; a typed Python CLI does the bookkeeping (cheap model reads, strong model abstracts).

---

## Under the hood: why the loops converge

For the curious — the mechanism behind "self-evolving," in three steps.

**1 · Distillation is a quotient map.** L2 abstraction maps a concrete method `m` to an equivalence class under *"same problem structure, same mechanism"*:

```
φ :  concrete method  ──►  ( problem_signature , math_basis , mechanism , rationale )
```

Two methods from unrelated fields with the *same* structure map to the same class — which is why a microbiome trick and a diffusion-model trick can cluster together. φ collapses **domain distance** and exposes **structural distance**. Transfer is the quotient working as designed.

**2 · The known set induces its own objective.** Over the current principle set `P`, synthesis defines a coverage map; a **gap** is an under-populated region. The gap is *computed from `P`* — an endogenous target, not an external prompt.

**3 · The loop is closed and monotone.**

```
 P_n  ──synthesize──►  gaps(P_n)  ──acquire + distill──►  P_{n+1} = P_n ⊕ new principles
```

`⊕` is a dedup-and-link merge: a new principle either extends `P` or attaches to an existing one. The graph only accumulates, so re-synthesizing over a richer `P_{n+1}` yields sharper gaps. That feedback — knowledge state → next objective → richer state — is the "self" in self-evolving. In spirit it is **active learning over a design space**.

> **Honest scope.** kw-engine is a tool and a method, not a benchmarked research claim. It does not yet prove structure-indexed retrieval beats RAG on a downstream task — that needs a controlled evaluation. What it gives you today is a disciplined, reproducible substrate for building and querying a transferable-methodology library, with reasoning cleanly separated from deterministic storage.

---

## Development

```bash
uv sync
uv run pytest -v          # 52 tests
uv run ruff check .       # lint
uv run mypy src/          # strict type check
```

## License

MIT © 2026
