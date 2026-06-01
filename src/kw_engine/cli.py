"""kw CLI — deterministic substrate commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from kw_engine.init import init_workspace
from kw_engine.store.json_proj import build_index_json
from kw_engine.store.markdown import scan_memory_dir
from kw_engine.store.ops import add_link, add_paper, add_principle
from kw_engine.store.sqlite import rebuild_index_db
from kw_engine.verify import run_checks

app = typer.Typer(no_args_is_help=True)


def _resolve_memory_dir(memory_dir: Path | None) -> Path:
    if memory_dir:
        return memory_dir.resolve()
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "memory" / "SCHEMA.md").exists():
            return (parent / "memory").resolve()
    typer.echo("ERROR: cannot find memory/ directory (no SCHEMA.md found)", err=True)
    raise typer.Exit(1)


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


if __name__ == "__main__":
    app()
