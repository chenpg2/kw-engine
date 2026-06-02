<div align="center">

<img src="banner.png" alt="kw-engine banner" width="100%">

# kw-engine

**Stop re-reading papers. Start reusing the *why*.**

A methodology evolution engine: it distills transferable problem-solving principles from literature, so when you hit a new problem you search by its *structure* and get back a mechanism that works — plus the reason it works and when it breaks.

You drive it by **talking to Claude Code**. No file editing, no commands.

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

kw-engine runs inside **Claude Code**. Install it once, then you just talk to Claude about your papers.

### Install (one time)

Three lines in your terminal — the only commands you'll ever need:

```bash
uv tool install git+https://github.com/chenpg2/kw-engine     # the engine
claude plugins marketplace add chenpg2/kw-engine             # the Claude Code plugin…
claude plugins install kw-engine@kw-engine                   # …skills + agents that drive it
```

After this, everything happens in conversation.

### Then just talk to Claude

Open Claude Code in any folder and say what you want. Claude uses the engine for you and shows you the results — you never touch a file or a command.

| You say… | Claude does |
|---|---|
| *"Set up a knowledge base here."* | scaffolds the workspace |
| *"Process this paper: arxiv 2304.04740"* | fetches the PDF, reads it, distills principles, shows you what it learned |
| *"What do we know about optimal transport?"* | searches by problem structure → matching mechanisms + why they work |
| *"What are the gaps in our knowledge?"* | shows under-covered regions — your next reading list |
| *"Here's my project and some papers — help me push it forward."* | runs the **project-driven loop** (below) |
| *"Improve the distiller — review the rubric and apply it."* | runs the self-improvement loop (asks before changing anything) |

Prefer a guided menu? Type `/kw` and Claude walks you through fetch → read → distill → synthesize → verify.

> **Like the terminal, or want to script it?** Every action above also has a `kw` command — see the [CLI reference](#cli-reference-for-scripting--automation) at the end. It's optional.

### Drive your own project (the main event)

This is what the engine is *for*. You arrive with a research problem or a half-formed idea and a pile of papers — maybe not enough of them — and want to push the project forward. Say:

> *"I want to design a better X. Here are my papers. Help me work it out."*

Claude runs `/kw-explore`, a problem-driven loop:

1. **Frames the problem** — decomposes your idea into its *structural* axes (and challenges the framing to find the real difficulty), then confirms it with you.
2. **Absorbs your papers** into principles.
3. **Maps your problem onto the library** — shows which sub-problems already have a proven mechanism and which are still **gaps** (this is where "not enough papers" surfaces concretely).
4. **Fills the gaps** — proposes targeted papers to read, fetches and absorbs the ones you pick, re-maps. Repeat until covered.
5. **Assembles a design** — composes the matched principles into a candidate solution where *every decision cites the principle it rests on*, and flags whatever still has no support.
6. **Hands off** — writes a living design doc + rationale + next-steps into *your project*, so a fresh session continues seamlessly.

Your design lives in your project; the reusable principles go into the knowledge base. Each future round of reading sharpens the design.

### Working with multiple topics

Keep separate knowledge bases for separate research areas and tell Claude which to use:

> *"Register my microbiome knowledge base at `~/research/microbiome-kb`."*
> *"Switch this project to the causal-inference knowledge base."*
> *"What do we know about intervention identifiability?"*

One library can back many projects at once — nothing is copied.

---

## How it improves itself

Two loops. **Loop 1 is the core** — it's how the knowledge evolves, and it runs whenever you absorb papers. **Loop 2 is optional** — turn it on when you want the distiller itself to get better over time. The engine is fully functional with Loop 2 off.

### Loop 1 — the knowledge grows (core, gap-driven)

Synthesis clusters what you know into a design-space map and computes **gaps** — problem structures with no good mechanism yet. Gaps become your next reading list. Each new paper is deduped and linked into the graph, so re-synthesizing yields *sharper* gaps. The objective (what to read next) is generated by the current state, not handed in from outside. Just keep asking Claude to process papers and *"show me the gaps."*

### Loop 2 — the distiller sharpens (optional)

Every distillation mistake (an abstraction that leaked a domain noun, a weak rationale) can become a rule that improves how the distiller works. This is the cheap core of [SkillOpt](https://github.com/microsoft/SkillOpt)-style "let failures edit the skill," without the training harness.

**You drive it in plain language:**

1. **While you read papers**, Claude notes the lessons on its own — you do nothing.
2. **When you want to apply them**, say: *"Review the distiller rubric and show me what would change."* Claude audits the lessons (an independent Codex check for consistency) and summarizes the proposed changes.
3. **To make it live**, say: *"Looks good, apply it."*

Claude always shows you the proposal and asks first — the rubric never changes silently. That approval step is the **validation gate** that keeps it from drifting or bloating. Skip Loop 2 entirely and the distiller just keeps using its current rubric.

---

## Architecture

```
 memory/papers/*.md          ┐
 memory/principles/*.md       ├─ source of truth (git-tracked, human-readable)
 memory/synthesis/*.md        ┘
        │  (rebuild)
        ▼
 memory/index.json     (diffable catalog projection, committed)
 .kw/index.db          (SQLite query index, gitignored, rebuildable)
```

- **Markdown is truth.** Indices are derived — delete and rebuild any time.
- **Atomic writes.** Temp-file rename + `flock`; no torn writes, no pid collisions.
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

**2 · The known set induces its own objective.** Over the current principle set `P`, synthesis defines a coverage map; a **gap** is an under-populated region — an endogenous target computed from `P`, not an external prompt.

**3 · The loop is closed and monotone.**

```
 P_n  ──synthesize──►  gaps(P_n)  ──acquire + distill──►  P_{n+1} = P_n ⊕ new principles
```

`⊕` is a dedup-and-link merge: a new principle either extends `P` or attaches to an existing one. The graph only accumulates, so re-synthesizing over a richer `P_{n+1}` yields sharper gaps. That feedback — knowledge state → next objective → richer state — is the "self" in self-evolving. In spirit it is **active learning over a design space**.

> **Honest scope.** kw-engine is a tool and a method, not a benchmarked research claim. It does not yet prove structure-indexed retrieval beats RAG on a downstream task — that needs a controlled evaluation. What it gives you today is a disciplined, reproducible substrate for building and querying a transferable-methodology library, with reasoning cleanly separated from deterministic storage.

---

## CLI reference (for scripting / automation)

Everything Claude does maps to a `kw` command. **You don't need these for normal use** — they're here for scripting the engine, automation, or running it without Claude.

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
| **Self-improving rubric** (optional, see [Loop 2](#loop-2--the-distiller-sharpens-optional)) | |
| `kw rubric add --rule … --trigger …` | Capture a lesson from a failure (staged) |
| `kw rubric status` / `kw rubric review` / `kw rubric promote` | Audit → propose → make live |

<details>
<summary>What a fully-specified principle looks like (one <code>kw add-principle</code> call)</summary>

```bash
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
```

When you talk to Claude, it fills all of this in for you from the paper.
</details>

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
