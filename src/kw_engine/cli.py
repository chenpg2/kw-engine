"""kw CLI — deterministic substrate commands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer

from kw_engine.init import init_workspace
from kw_engine.store.json_proj import build_index_json
from kw_engine.store.markdown import scan_memory_dir
from kw_engine.store.ops import add_link, add_paper, add_principle
from kw_engine.store.sqlite import rebuild_index_db
from kw_engine.verify import run_checks

app = typer.Typer(no_args_is_help=True)
kb_app = typer.Typer(help="Manage named knowledge bases (global registry)")
app.add_typer(kb_app, name="kb")
rubric_app = typer.Typer(
    help="Self-improve the distillation rubric (capture failures, gate, promote)"
)
app.add_typer(rubric_app, name="rubric")

_REGISTRY_PATH = Path.home() / ".kw" / "registry.yaml"


def _load_registry() -> dict[str, str]:
    import yaml

    if not _REGISTRY_PATH.exists():
        return {}
    try:
        data = yaml.safe_load(_REGISTRY_PATH.read_text()) or {}
    except yaml.YAMLError:
        return {}
    kbs = data.get("knowledge_bases", {})
    if not isinstance(kbs, dict):
        return {}
    result: dict[str, str] = {str(k): str(v) for k, v in kbs.items()}
    return result


def _save_registry(kbs: dict[str, str]) -> None:
    import tempfile

    import yaml

    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.dump(
        {"knowledge_bases": kbs}, default_flow_style=False, sort_keys=True
    )
    with tempfile.NamedTemporaryFile(
        mode="w", dir=_REGISTRY_PATH.parent, suffix=".yaml", delete=False
    ) as tf:
        tf.write(content)
        tmp = Path(tf.name)
    tmp.replace(_REGISTRY_PATH)


def _resolve_memory_dir(memory_dir: Path | None) -> Path:
    if memory_dir:
        return memory_dir.resolve()
    # Walk up from cwd but stop at git root or .kw boundary (don't leak into parent projects)
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        # Check .kw/config.yaml for a linked memory path
        config_path = parent / ".kw" / "config.yaml"
        if config_path.exists():
            import yaml
            try:
                cfg = yaml.safe_load(config_path.read_text()) or {}
            except yaml.YAMLError:
                cfg = {}
            paths = cfg.get("paths", {})
            if isinstance(paths, dict):
                linked = paths.get("memory")
                if linked:
                    linked_path = Path(str(linked)).expanduser().resolve()
                    if (linked_path / "SCHEMA.md").exists():
                        return linked_path
        # Check for local memory/SCHEMA.md
        if (parent / "memory" / "SCHEMA.md").exists():
            return (parent / "memory").resolve()
        # Stop at git root — don't climb into parent projects
        if (parent / ".git").exists():
            break
    typer.echo("ERROR: cannot find memory/ directory", err=True)
    typer.echo(
        "Hint: run 'kw link <name-or-path>' to connect to a knowledge base",
        err=True,
    )
    raise typer.Exit(1)


@kb_app.command("add")
def kb_add(
    name: str = typer.Argument(help="Name for this knowledge base (e.g. microbiome)"),
    memory_path: str = typer.Argument(help="Path to the memory/ directory"),
) -> None:
    """Register a named knowledge base in the global registry."""
    resolved = Path(memory_path).expanduser().resolve()
    if not (resolved / "SCHEMA.md").exists():
        typer.echo(f"ERROR: {resolved} does not contain SCHEMA.md", err=True)
        raise typer.Exit(1)

    kbs = _load_registry()
    kbs[name] = str(resolved)
    _save_registry(kbs)
    typer.echo(f"Registered: {name} → {resolved}")


@kb_app.command("list")
def kb_list() -> None:
    """List all registered knowledge bases."""
    kbs = _load_registry()
    if not kbs:
        typer.echo("No knowledge bases registered. Use 'kw kb add <name> <path>'.")
        return
    for name, path in sorted(kbs.items()):
        exists = "ok" if Path(path).exists() else "MISSING"
        typer.echo(f"  {name:20s} {path}  [{exists}]")


@kb_app.command("remove")
def kb_remove(
    name: str = typer.Argument(help="Name of the knowledge base to remove"),
) -> None:
    """Remove a knowledge base from the registry (does not delete files)."""
    kbs = _load_registry()
    if name not in kbs:
        typer.echo(f"ERROR: '{name}' not in registry", err=True)
        raise typer.Exit(1)
    del kbs[name]
    _save_registry(kbs)
    typer.echo(f"Removed: {name}")


@app.command()
def link(
    name_or_path: str = typer.Argument(
        help="Registry name (e.g. microbiome) or path to memory/ directory"
    ),
    target: Path = typer.Argument(
        ".", help="Project directory to link (default: current directory)"
    ),
) -> None:
    """Link a project to a knowledge base (by name or path)."""
    import yaml

    # Resolve: check registry first, then treat as path
    kbs = _load_registry()
    if name_or_path in kbs:
        resolved = Path(kbs[name_or_path]).resolve()
        typer.echo(f"Using registered knowledge base: {name_or_path}")
    else:
        resolved = Path(name_or_path).expanduser().resolve()

    if not (resolved / "SCHEMA.md").exists():
        typer.echo(f"ERROR: {resolved} does not contain SCHEMA.md", err=True)
        raise typer.Exit(1)

    target_dir = target.resolve()
    kw_dir = target_dir / ".kw"
    kw_dir.mkdir(parents=True, exist_ok=True)
    config_path = kw_dir / "config.yaml"

    if config_path.exists():
        cfg = yaml.safe_load(config_path.read_text()) or {}
    else:
        cfg = {"version": 1}

    if "paths" not in cfg:
        cfg["paths"] = {}
    cfg["paths"]["memory"] = str(resolved)

    config_path.write_text(
        yaml.dump(cfg, default_flow_style=False, sort_keys=False)
    )
    typer.echo(f"Linked: {target_dir} → {resolved}")
    typer.echo("All kw commands in this project now use this knowledge base.")


@app.command()
def reindex(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
    kw_dir: Path = typer.Option(None, help="Path to .kw/ directory for SQLite"),
) -> None:
    """Rebuild index.json + SQLite from markdown source of truth."""
    mem = _resolve_memory_dir(memory_dir)
    papers, principles = scan_memory_dir(mem)

    # Preserve existing synthesis state
    index_path = mem / "index.json"
    synthesis_last_run: str | None = None
    synthesis_n_at_last_run: int | None = None
    if index_path.exists():
        existing = json.loads(index_path.read_text())
        syn = existing.get("synthesis", {})
        synthesis_last_run = syn.get("last_run")
        synthesis_n_at_last_run = syn.get("n_principles_at_last_run")

    idx = build_index_json(papers, principles, synthesis_last_run, synthesis_n_at_last_run)
    index_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n")
    typer.echo(f"index.json: {len(papers)} papers, {len(principles)} principles")

    if kw_dir is None:
        kw_dir = mem.parent / ".kw"
    kw_dir.mkdir(parents=True, exist_ok=True)
    db_path = kw_dir / "index.db"
    rebuild_index_db(db_path, papers, principles)
    typer.echo(f"index.db: rebuilt at {db_path}")


@app.command()
def verify(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Run SCHEMA §6 invariant checks."""
    mem = _resolve_memory_dir(memory_dir)
    papers, principles = scan_memory_dir(mem)
    verdicts = run_checks(papers, principles)

    fails = [v for v in verdicts if v.status == "FAIL"]
    for v in verdicts:
        icon = "PASS" if v.status == "PASS" else "FAIL"
        typer.echo(f"  [{icon}] {v.check_name}: {v.message}")

    if fails:
        typer.echo(f"\n{len(fails)} FAIL(s)")
        raise typer.Exit(1)
    else:
        typer.echo("\nAll checks PASS")


@app.command()
def status(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Show engine state: counts, pending papers, synthesis staleness."""
    mem = _resolve_memory_dir(memory_dir)
    papers, principles = scan_memory_dir(mem)

    pending = [p for p in papers if p.status == "pending"]
    l1 = [p for p in papers if p.status == "L1"]
    complete = [p for p in papers if p.status == "complete"]

    typer.echo(
        f"Papers: {len(papers)} total"
        f" ({len(complete)} complete, {len(l1)} L1, {len(pending)} pending)"
    )
    typer.echo(f"Principles: {len(principles)}")

    index_path = mem / "index.json"
    if index_path.exists():
        idx = json.loads(index_path.read_text())
        syn = idx.get("synthesis", {})
        n_at_last = syn.get("n_principles_at_last_run", 0)
        if len(principles) > n_at_last:
            delta = len(principles) - n_at_last
            typer.echo(f"Synthesis: STALE ({delta} new principles since last run)")
        else:
            typer.echo(f"Synthesis: up to date (last run: {syn.get('last_run', 'never')})")


@app.command()
def ui(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Open the terminal UI for browsing and maintaining a knowledge base."""
    from kw_engine.ui import run_ui

    mem = _resolve_memory_dir(memory_dir)
    run_ui(mem)


@app.command("init")
def cmd_init(
    target: Path = typer.Argument(
        ".", help="Target directory to initialize (default: current directory)"
    ),
) -> None:
    """Scaffold a knowledge engine workspace (memory/, .kw/, process/, paper/)."""
    target = target.resolve()
    init_workspace(target)
    typer.echo(f"Knowledge engine initialized at {target}")
    typer.echo("Run 'kw status' to see the empty engine state.")


@app.command("add-paper")
def cmd_add_paper(
    paper_id: str = typer.Argument(help="Paper id (PDF filename stem)"),
    doi: str = typer.Option(None, help="DOI if known"),
    title: str = typer.Option(None, help="Paper title if known"),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Register a new paper (creates scaffold md + index entry)."""
    mem = _resolve_memory_dir(memory_dir)
    result = add_paper(mem, paper_id, doi=doi, title=title)
    if result is None:
        typer.echo(f"SKIP: {paper_id} already exists")
    else:
        typer.echo(f"OK: {result}")


@app.command("add-principle")
def cmd_add_principle(
    title: str = typer.Option(..., help="One-line principle title"),
    abstraction_level: str = typer.Option(..., "--abstract", help="Domain-stripped statement"),
    problem_signature: list[str] = typer.Option(..., "--sig", help="Problem signature items"),
    math_basis: list[str] = typer.Option(..., "--math", help="Math basis tags"),
    mechanism: str = typer.Option(..., help="How math attacks the structure"),
    rationale: str = typer.Option(..., help="Why structure<->mechanism connects"),
    data_regime: list[str] = typer.Option(..., "--regime", help="Required data conditions"),
    falsifiable_prediction: str = typer.Option(..., "--prediction", help="Testable prediction"),
    boundaries: str = typer.Option(..., help="When it breaks / assumptions"),
    provenance: list[str] = typer.Option(
        ..., "--prov", help="Paper citations (e.g. 'gkaf1205 §3')"
    ),
    links: list[str] = typer.Option([], "--link", help="Links (e.g. 'contrasts:P-0001')"),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Allocate a new principle (P-####), create md, update index."""
    mem = _resolve_memory_dir(memory_dir)
    pid = add_principle(
        mem,
        title=title,
        abstraction_level=abstraction_level,
        problem_signature=problem_signature,
        math_basis=math_basis,
        mechanism=mechanism,
        rationale=rationale,
        data_regime=data_regime,
        falsifiable_prediction=falsifiable_prediction,
        boundaries=boundaries,
        provenance=provenance,
        links=links if links else None,
    )
    typer.echo(f"OK: {pid}")


@app.command()
def search(
    query: str = typer.Argument(help="Search query (keywords from problem signatures or math basis)"),  # noqa: E501
    top_k: int = typer.Option(10, "-n", help="Max results"),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Search principles by problem_signature and math_basis keywords."""
    from kw_engine.store.search import search_principles
    mem = _resolve_memory_dir(memory_dir)
    results = search_principles(mem, query, top_k=top_k)
    if not results:
        typer.echo("No matching principles found.")
        raise typer.Exit(0)
    for r in results:
        typer.echo(f"  {r['id']} (score={r['score']}) {r['title']}")


@app.command()
def fetch(
    paper_id: str = typer.Argument(help="Paper id, DOI, or arXiv id"),
    doi: str = typer.Option(None, help="DOI if known"),
    title: str = typer.Option(None, help="Paper title if known"),
    papers_dir: Path = typer.Option(None, help="Directory for PDFs (default: ../paper/)"),
    paper_search_dir: str = typer.Option(None, "--paper-search", help="Path to paper-search repo"),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Fetch a paper PDF and register it."""
    from kw_engine.fetch import fetch_paper
    mem = _resolve_memory_dir(memory_dir)
    result = fetch_paper(
        mem, paper_id,
        papers_dir=papers_dir.resolve() if papers_dir else None,
        doi=doi, title=title,
        paper_search_dir=paper_search_dir,
    )
    typer.echo(result)
    if result.startswith("FAIL"):
        raise typer.Exit(1)


@app.command("add-link")
def cmd_add_link(
    from_pid: str = typer.Argument(help="Source principle id (e.g. P-0001)"),
    to_pid: str = typer.Argument(help="Target principle id (e.g. P-0002)"),
    link_type: str = typer.Argument(
        help=(
            "Link type: generalizes|specializes|composes|contrasts"
            "|contradicts|applies_to|composed-by"
        )
    ),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Add a link between two principles."""
    mem = _resolve_memory_dir(memory_dir)
    add_link(mem, from_pid, to_pid, link_type)
    typer.echo(f"OK: {from_pid} --{link_type}--> {to_pid}")


@rubric_app.command("add")
def rubric_add(
    rule: str = typer.Option(..., "--rule", help="The candidate rule (a lesson from a failure)"),
    trigger: str = typer.Option("", "--trigger", help="What failure triggered this rule"),
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Capture a candidate rubric rule from a distillation failure."""
    from kw_engine.rubric import add_candidate

    mem = _resolve_memory_dir(memory_dir)
    process_dir = mem.parent / "process"
    process_dir.mkdir(exist_ok=True)
    add_candidate(process_dir, rule=rule, trigger=trigger)
    typer.echo("Candidate rule added. Run 'kw rubric review' when ready to audit.")


@rubric_app.command("status")
def rubric_status(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Show how many candidate rules are awaiting review."""
    from kw_engine.rubric import count_candidates

    mem = _resolve_memory_dir(memory_dir)
    process_dir = mem.parent / "process"
    n = count_candidates(process_dir)
    typer.echo(f"Pending candidate rules: {n}")
    if n:
        typer.echo("Run 'kw rubric review' to audit + propose a cleaned rubric.")


@rubric_app.command("review")
def rubric_review(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Audit candidates against the live rubric (Codex gate), write a proposed rubric."""
    import subprocess

    from kw_engine.rubric import assemble_review_bundle, count_candidates

    mem = _resolve_memory_dir(memory_dir)
    process_dir = mem.parent / "process"
    if count_candidates(process_dir) == 0:
        typer.echo("No candidate rules to review.")
        raise typer.Exit(0)

    bundle = assemble_review_bundle(process_dir)
    bundle_path = process_dir / "distill-rubric.review-bundle.txt"
    bundle_path.write_text(bundle, encoding="utf-8")
    proposed_path = process_dir / "distill-rubric.proposed.md"

    if shutil.which("codex") is None:
        typer.echo("codex CLI not found. Review bundle written to:")
        typer.echo(f"  {bundle_path}")
        typer.echo("Run your reviewer on it, save the revised rubric to:")
        typer.echo(f"  {proposed_path}")
        typer.echo("Then run 'kw rubric promote'.")
        return

    typer.echo("Running Codex audit (validation gate)...")
    # Point Codex at the bundle FILE (small argv) rather than inlining the whole
    # bundle as an argument — avoids OS argv-size limits on large rubrics.
    codex_prompt = (
        f"Read the file {bundle_path} and follow the instructions inside it. "
        "Output ONLY the full revised rubric markdown, nothing else."
    )
    try:
        result = subprocess.run(
            ["codex", "exec", codex_prompt],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        typer.echo(f"Codex invocation failed: {e}", err=True)
        typer.echo(f"Review bundle at {bundle_path}; produce {proposed_path} manually.")
        raise typer.Exit(1) from e

    output = result.stdout.strip()
    if not output:
        typer.echo("Codex returned no output. Review manually:", err=True)
        typer.echo(f"  bundle: {bundle_path}")
        raise typer.Exit(1)

    proposed_path.write_text(output + "\n", encoding="utf-8")
    typer.echo(f"Proposed rubric written to {proposed_path}")
    typer.echo("Review it, then run 'kw rubric promote' to make it live.")


@rubric_app.command("promote")
def rubric_promote(
    memory_dir: Path = typer.Option(None, help="Path to memory/ directory"),
) -> None:
    """Promote the proposed rubric to live (archives old, clears candidates)."""
    from kw_engine.rubric import promote

    mem = _resolve_memory_dir(memory_dir)
    process_dir = mem.parent / "process"
    try:
        promote(process_dir)
    except FileNotFoundError as e:
        typer.echo(f"ERROR: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo("Rubric promoted. Old version archived, candidates cleared.")


if __name__ == "__main__":
    app()
