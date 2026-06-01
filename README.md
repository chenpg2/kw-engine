# kw-engine

Deterministic substrate for a knowledge engine — ingest academic papers into a reusable, domain-stripped principle library.

## What it does

Papers flow through three layers:
- **L1 (faithful):** structured extraction with section locators
- **L2 (abstract):** transferable first-principles (problem-signature ↔ mechanism ↔ rationale)
- **L3 (synthesis):** cross-paper design-space map, contradictions, and gaps

The engine separates concerns:
- **Reasoning** (read/distill/synthesize) stays in LLM agents
- **Substrate** (this package) provides deterministic, atomic CLI commands for mutations and queries

## Installation

```bash
# From source
git clone <repo-url>
cd kw-engine
uv sync
```

## Quick Start

```bash
# Initialize a new workspace
uv run kw init

# Register a paper
uv run kw add-paper 2304.04740 --doi "10.48550/arXiv.2304.04740" --title "Flow Matching"

# Add a principle (agents call this after distillation)
uv run kw add-principle \
  --title "Reduce dynamics to static coupling + regression" \
  --abstract "..." \
  --sig "unpaired marginals" --sig "continuous-time process" \
  --math "optimal-transport" --math "conditional-flow" \
  --mechanism "..." \
  --rationale "..." \
  --regime "N≥100 samples per marginal" \
  --prediction "..." \
  --boundaries "..." \
  --prov "2304.04740 §3.2"

# Search for relevant principles
uv run kw search "optimal transport dynamics"

# Verify integrity
uv run kw verify

# Rebuild index (after manual edits)
uv run kw reindex

# Fetch a paper PDF
uv run kw fetch 2304.04740
```

## CLI Commands

| Command | Purpose |
|---------|---------|
| `kw init [dir]` | Scaffold a new workspace |
| `kw add-paper <id>` | Register a paper (creates scaffold + index entry) |
| `kw add-principle` | Allocate P-####, create md, update index + SQLite |
| `kw add-link <from> <to> <type>` | Add a link between principles |
| `kw search "<query>"` | Keyword-match principles by signature/math_basis |
| `kw fetch <id>` | Acquire PDF + validate + register |
| `kw reindex` | Rebuild index.json + SQLite from markdown |
| `kw verify` | Check SCHEMA §6 invariants |
| `kw status` | Show engine state |

## Architecture

```
Markdown (source of truth)     →  index.json (diffable projection)
memory/papers/*.md                 ↘
memory/principles/*.md          →  .kw/index.db (query index, gitignored)
```

- **Markdown is truth.** SQLite + index.json are derived (`kw reindex` rebuilds both).
- **Atomic writes.** All mutations use temp-file rename + file lock.
- **No silent fallback.** Validation errors raise, never coerce.

## Claude Code Plugin

kw-engine ships as a Claude Code plugin with:
- `/kw` skill — orchestrator for the paper ingestion loop
- `/kw-init` skill — scaffold via natural language
- 5 agents: kw-fetcher, kw-reader, kw-distiller, kw-synthesizer, kw-verifier

## Development

```bash
uv sync
uv run pytest -v          # 41 tests
uv run ruff check .       # lint
uv run mypy src/          # type check
```

## License

MIT
