<div align="center">

<img src="banner.png" alt="kw-engine banner" width="100%">

# kw-engine

**Stop re-reading papers. Start reusing the *why*.**

A methodology evolution engine that distills transferable problem-solving principles from literature — so when you hit a new problem, you search by its *structure* and get back a mechanism that works, plus the reason it works.

[![CI](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/chenpg2/kw-engine/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Tests](https://img.shields.io/badge/tests-41%20passing-brightgreen)
![Types](https://img.shields.io/badge/mypy-strict-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**English** · [简体中文](README.zh-CN.md)

</div>

---

## The problem

You read a paper, extract a clever trick, and forget it. Six months later you face a problem that the *same trick* would solve — but it was in a different field, used different words, and your notes are a pile of PDFs. Your bottleneck was never finding papers. It was **reusing the underlying method across domains.**

kw-engine treats that as the actual problem.

## What it does

It distills literature through three layers, stripping away the domain and keeping the transferable logic:

```
 Paper PDF
   │
   ├─  L1  faithful extraction   what the paper says, with section locators — no interpretation
   │
   ├─  L2  abstraction           strip the biology/domain, keep the transferable core:
   │                               problem-signature   ·  WHEN it applies (problem structure)
   │                               ↔ mechanism + math  ·  WHAT to do
   │                               ↔ rationale         ·  WHY the structure↔mechanism mapping holds
   │
   └─  L3  synthesis             cluster principles into a design-space map; surface
                                  contradictions and GAPS — where the knowledge evolves
```

Then the payoff:

```
New problem arrives  →  search by its structure  →  matched mechanism + rationale + when-it-breaks
```

## Why it's different

|  | What it retrieves | Indexed by |
|---|---|---|
| **RAG / vector search** | text chunks | surface semantics |
| **Zotero / citation managers** | references & PDFs | metadata, tags |
| **Skill libraries** (e.g. Voyager) | executable task code | task name |
| **kw-engine** | **mechanism + why-it-works + when-it-fails** | **problem structure** |

It's not a search index over text — it's a compiler from *empirical results* to *reusable problem-solving strategies*.

## Why it self-evolves

Three ingredients let the loop pick its own next move instead of waiting for a human to choose what to read.

**1 · Distillation is a quotient map.** L2 abstraction strips the domain — it maps a concrete method `m` to an equivalence class under *"same problem structure, same mechanism"*:

```
φ :  concrete method  ──►  ( problem_signature , math_basis , mechanism , rationale )
```

Two methods from unrelated fields with the *same* structure map to the same class. That's exactly why a microbiome trick and a diffusion-model trick can land in one cluster: φ collapses **domain distance** and exposes **structural distance**. Transfer is the quotient working as designed.

**2 · The known set induces a coverage map — and therefore gaps.** Given the current principle set `P`, L3 synthesis partitions it over a design space whose axes are the recurring structural properties. A **gap** is a region that is under-populated, or where `rationale` / `falsifiable_prediction` is weak. Crucially a gap is *computed from `P` itself* — an endogenous objective, not an external prompt.

**3 · The loop is closed and monotone.**

```
 P_n  ──synthesize──►  gaps(P_n)  ──acquire + distill──►  P_{n+1} = P_n ⊕ new principles
```

`⊕` is a **dedup-and-link merge**: a new principle either extends `P` or attaches to an existing one as added provenance / `generalizes` / `contrasts`. So the graph only accumulates — it never forgets — and re-synthesizing over a richer `P_{n+1}` yields *sharper* gaps. That feedback (knowledge state → next objective → richer state) is the "self" in self-evolving.

In spirit this is **active learning over a design space**: gaps play the role of coverage/uncertainty sampling, and each round acquires the evidence that most reduces an under-covered region.

> **Honest note.** The map φ and the gap judgment are performed by LLM reasoning, not a closed-form operator; the engine's job is to maintain the structured, deduplicated state that makes the loop *closeable and reproducible*. There is no convergence theorem here — the monotone accumulation + dedup *is* the mechanism, not a proof of it.

## Highlights

- 🧪 **Structure-indexed retrieval** — query by the shape of your problem, not keywords
- 🧬 **Domain-stripped principles** — a microbiome trick and a diffusion-model trick land in the same cluster when their *math structure* matches
- 🔁 **Knowledge that evolves** — L3 synthesis surfaces real gaps, which become your next reading list
- 🪶 **Markdown is the source of truth** — git-diffable, reviewable records; SQLite + JSON are rebuildable indices
- ⚛️ **Deterministic & atomic** — every mutation is temp-file-rename + file-locked; no half-written state
- 🤖 **Two-tier by design** — LLM agents do the reasoning; a typed Python CLI does the bookkeeping (cheap model reads, strong model abstracts)
- 🔌 **Ships as a Claude Code plugin** — `/kw` orchestrates the whole loop; or drive the `kw` CLI yourself
- ✅ **Production-grade substrate** — 41 tests, `mypy --strict`, `ruff`, CI on Python 3.11–3.13

## Install

```bash
# As a CLI tool (recommended — gives you the `kw` command)
uv tool install git+https://github.com/chenpg2/kw-engine

# Or as a project dependency
uv add git+https://github.com/chenpg2/kw-engine

# Or clone for development
git clone https://github.com/chenpg2/kw-engine
cd kw-engine && uv sync
```

### Install as a Claude Code plugin

Run these in your terminal (not inside a Claude Code session):

```bash
claude plugins marketplace add chenpg2/kw-engine
claude plugins install kw-engine@kw-engine
```

This registers the `/kw` and `/kw-init` skills plus the five sub-agents. Then install the CLI substrate they call:

```bash
uv tool install git+https://github.com/chenpg2/kw-engine
```

> The plugin provides the *reasoning* (skills + agents); the `kw` CLI provides the *deterministic substrate*. You want both.

## Quick start

```bash
# 1. Initialize a workspace in any repo
kw init
kw status                                  # 0 papers, 0 principles — empty engine

# 2. Acquire a paper (multi-source open-access fallback + PDF validation)
kw fetch 2304.04740

# 3. Register and distill (agents fill these after reading; or do it by hand)
kw add-paper 2304.04740 --title "Flow Matching for Generative Modeling"
kw add-principle \
  --title "Reduce hard dynamics optimization to static coupling + regression onto bridges" \
  --abstract "When a theorem identifies the dynamic optimum as a mixture of simple conditional bridges, replace path optimization with a coupling + closed-form regression." \
  --sig "unpaired marginal snapshots" --sig "continuous-time generative process" \
  --math "optimal-transport" --math "conditional-flow" \
  --mechanism "Solve a static coupling, then regress a vector field onto closed-form conditional bridges." \
  --rationale "The dynamic least-action optimum decomposes into per-pair bridges, so the hard part collapses to a coupling problem." \
  --regime "needs paired or OT-coupleable marginals; N large enough to estimate the coupling" \
  --prediction "straightening the coupling reduces sampling steps without retraining" \
  --boundaries "fails if the bridge family doesn't match the true conditional process" \
  --prov "2304.04740 §3.2"

# 4. The payoff — search by problem structure
kw search "optimal transport dynamics"

# 5. Keep it honest
kw verify                                  # checks provenance, links, required fields
```

### Or let Claude Code drive it

Installed as a plugin, just run the skill — it orchestrates fetch → read → distill → synthesize → verify across sub-agents, with the right model on each step:

```
/kw          # detects state, offers a menu, runs the loop — you never hand-edit a file
/kw-init     # scaffold a workspace from natural language
```

## CLI reference

| Command | Purpose |
|---|---|
| `kw init [dir]` | Scaffold a workspace (`memory/`, `.kw/`, `process/`, `paper/`) |
| `kw fetch <id\|doi\|title>` | Acquire a PDF via OA fallback chain + validate + register |
| `kw add-paper <id>` | Register a paper (scaffold record + index entry) |
| `kw add-principle …` | Allocate `P-####`, write the principle, update index + SQLite |
| `kw add-link <from> <to> <type>` | Link principles (`generalizes`/`contrasts`/`composes`/…) |
| `kw search "<query>"` | Retrieve principles by problem-signature / math-basis |
| `kw reindex` | Rebuild `index.json` + SQLite from markdown |
| `kw verify` | Check integrity invariants (provenance, links, required fields) |
| `kw status` | Counts, pending papers, synthesis staleness |

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
- **Atomic writes.** Temp-file rename + `flock` on the index; no pid collisions, no torn writes.
- **No silent fallback.** Validation errors raise; the engine never writes a placeholder record.

## Honest scope

kw-engine is a **tool and a method**, not a benchmarked research claim. It does not (yet) prove that structure-indexed retrieval beats RAG on a downstream task — that would need a controlled evaluation. What it *does* give you today is a disciplined, reproducible substrate for building and querying a transferable-methodology library, with the LLM reasoning cleanly separated from deterministic storage.

## Development

```bash
uv sync
uv run pytest -v          # 41 tests
uv run ruff check .       # lint
uv run mypy src/          # strict type check
```

## License

MIT © 2026
