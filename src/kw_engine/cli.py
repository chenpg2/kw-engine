"""kw CLI — deterministic substrate commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from kw_engine.store.markdown import scan_memory_dir
from kw_engine.store.json_proj import build_index_json
from kw_engine.store.sqlite import rebuild_index_db
from kw_engine.verify import run_checks

app = typer.Typer(no_args_is_help=True)


def _resolve_memory_dir(memory_dir: Path | None) -> Path:
    if memory_dir:
        return memory_dir
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / "memory" / "SCHEMA.md").exists():
            return parent / "memory"
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

    typer.echo(f"Papers: {len(papers)} total ({len(complete)} complete, {len(l1)} L1, {len(pending)} pending)")
    typer.echo(f"Principles: {len(principles)}")

    index_path = mem / "index.json"
    if index_path.exists():
        idx = json.loads(index_path.read_text())
        syn = idx.get("synthesis", {})
        n_at_last = syn.get("n_principles_at_last_run", 0)
        if len(principles) > n_at_last:
            typer.echo(f"Synthesis: STALE ({len(principles) - n_at_last} new principles since last run)")
        else:
            typer.echo(f"Synthesis: up to date (last run: {syn.get('last_run', 'never')})")


if __name__ == "__main__":
    app()
