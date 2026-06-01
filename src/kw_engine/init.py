"""Initialize a knowledge engine workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

_INITIAL_INDEX: dict[str, Any] = {
    "version": 1,
    "counters": {"principle": 0},
    "papers": [],
    "principles": [],
    "synthesis": {"last_run": None, "n_principles_at_last_run": 0},
}

_CONFIG_TEMPLATE: dict[str, Any] = {
    "version": 1,
    "paths": {
        "papers_src": "paper/",
        "memory": "memory/",
        "index": "memory/index.json",
        "process": "process/",
        "problems": "problems/",
        "logs": ".kw/logs/",
    },
    "loop1": {"synthesize_after_n_papers": 5},
    "process_versions": {
        "extract_template": "extract-template@v1",
        "distill_rubric": "distill-rubric@v1",
    },
    "model_routing": {
        "kw-fetcher": "sonnet",
        "kw-reader": "sonnet",
        "kw-distiller": "opus",
        "kw-synthesizer": "opus",
        "kw-verifier": "sonnet",
    },
    "fetch": {
        "fallback_order": [
            "with_fallback", "arxiv", "biorxiv", "medrxiv",
            "pubmed", "crossref", "openalex", "semantic", "curl_oa",
        ],
        "validate": {"magic_bytes": "%PDF-", "min_bytes": 10240, "max_bytes": 52428800},
        "scihub": False,
        "paywalled_via_browse": True,
        "idempotent": True,
    },
    "active_expansion": {"enabled": False},
}


def _template_path() -> Path:
    """Resolve the templates/ directory bundled with the package."""
    # Try relative to this file (development install)
    pkg_dir = Path(__file__).parent.parent.parent / "templates"
    if pkg_dir.exists():
        return pkg_dir
    # Fallback: installed package
    raise FileNotFoundError("templates/ directory not found")


def init_workspace(target: Path) -> None:
    """Scaffold a knowledge engine workspace at target directory.

    Idempotent: creates directories and files only if they don't exist.
    Never overwrites existing files (preserves user data).
    """
    templates = _template_path()

    # Create directories
    dirs = [
        target / ".kw" / "logs",
        target / "memory" / "papers",
        target / "memory" / "principles",
        target / "memory" / "synthesis",
        target / "memory" / "golden",
        target / "paper",
        target / "process",
        target / "problems",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # Write config (only if not exists)
    config_path = target / ".kw" / "config.yaml"
    if not config_path.exists():
        config_path.write_text(
            yaml.dump(_CONFIG_TEMPLATE, default_flow_style=False, sort_keys=False)
        )

    # Write index.json (only if not exists)
    index_path = target / "memory" / "index.json"
    if not index_path.exists():
        index_path.write_text(json.dumps(_INITIAL_INDEX, indent=2) + "\n")

    # Copy templates (only if not exists)
    template_files = {
        "SCHEMA.md": target / "memory" / "SCHEMA.md",
        "extract-template.md": target / "process" / "extract-template.md",
        "distill-rubric.md": target / "process" / "distill-rubric.md",
    }
    for src_name, dest in template_files.items():
        if not dest.exists():
            src = templates / src_name
            if src.exists():
                dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
