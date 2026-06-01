---
name: kw-init
description: Scaffold a new knowledge engine workspace OR link to an existing shared knowledge base. Use when starting a new knowledge base or connecting a project to an existing one.
---

# /kw-init — scaffold or link a knowledge engine workspace

**Two modes:**

## Mode 1: Link to an existing knowledge base (most common)

If a shared knowledge base already exists (e.g. `~/Downloads/soft/knowledge_wiki/memory/`),
link this project to it instead of creating a new one:

```bash
kw link ~/Downloads/soft/knowledge_wiki/memory/
```

This creates `.kw/config.yaml` with `paths.memory` pointing to the shared library.
All `kw` commands (`search`, `verify`, `status`, etc.) now use the shared knowledge.

## Mode 2: Create a new knowledge base from scratch

Run this once in any repo to set up a fresh, empty knowledge engine.

## What it creates

```
<project-root>/
├── .kw/
│   └── config.yaml          # Engine config (model routing, fetch policy)
├── memory/
│   ├── SCHEMA.md            # Data structure contract
│   ├── index.json           # Central index (starts empty)
│   ├── papers/              # L1 faithful readings
│   ├── principles/          # L2 abstract principles
│   ├── synthesis/           # L3 design-space, contradictions, gaps
│   └── golden/              # Exemplar records for quality reference
├── paper/                   # Raw PDFs (gitignored)
├── process/
│   ├── extract-template.md  # L1 extraction rubric
│   └── distill-rubric.md    # L2 distillation rubric
└── problems/                # Use-case pointers
```

## Procedure

1. Check if `memory/SCHEMA.md` already exists. If yes, report "Already initialized" and STOP.
2. Create the directory structure above.
3. Write `.kw/config.yaml` from the template below.
4. Write `memory/SCHEMA.md` from the kw-engine package's canonical schema.
5. Write `memory/index.json` with the empty initial state.
6. Write `process/extract-template.md` and `process/distill-rubric.md`.
7. Add `paper/*.pdf` and `.kw/index.db` to `.gitignore` if not already present.
8. Report: "Knowledge engine initialized. Run `/kw` to start ingesting papers."

## Config template (.kw/config.yaml)

```yaml
version: 1

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
  fallback_order: [with_fallback, arxiv, biorxiv, medrxiv, pubmed, crossref, openalex, semantic, curl_oa]
  validate:
    magic_bytes: "%PDF-"
    min_bytes: 10240
    max_bytes: 52428800
  scihub: false
  paywalled_via_browse: true
  idempotent: true

active_expansion:
  enabled: false
```

## Initial index.json

```json
{
  "version": 1,
  "counters": { "principle": 0 },
  "papers": [],
  "principles": [],
  "synthesis": { "last_run": null, "n_principles_at_last_run": 0 }
}
```
