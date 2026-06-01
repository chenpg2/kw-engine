"""Terminal UI for browsing and maintaining a kw-engine memory store."""

from __future__ import annotations

import curses
import json
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap
from typing import Any, Literal

from kw_engine.models import PaperFull, Principle
from kw_engine.store.json_proj import build_index_json
from kw_engine.store.markdown import scan_memory_dir
from kw_engine.store.ops import add_paper
from kw_engine.store.search import search_principles
from kw_engine.store.sqlite import rebuild_index_db
from kw_engine.verify import Verdict, run_checks

RowKind = Literal["paper", "principle"]


@dataclass(frozen=True)
class UiRow:
    kind: RowKind
    id: str
    title: str
    meta: str


@dataclass(frozen=True)
class EngineSnapshot:
    memory_dir: Path
    papers: list[PaperFull]
    principles: list[Principle]
    synthesis_last_run: str | None
    synthesis_n_at_last_run: int

    @property
    def pending_papers(self) -> int:
        return sum(1 for paper in self.papers if paper.status == "pending")

    @property
    def l1_papers(self) -> int:
        return sum(1 for paper in self.papers if paper.status == "L1")

    @property
    def complete_papers(self) -> int:
        return sum(1 for paper in self.papers if paper.status == "complete")

    @property
    def synthesis_status(self) -> str:
        if len(self.principles) > self.synthesis_n_at_last_run:
            delta = len(self.principles) - self.synthesis_n_at_last_run
            return f"STALE ({delta} new principles)"
        last_run = self.synthesis_last_run or "never"
        return f"up to date (last run: {last_run})"


def load_snapshot(memory_dir: Path) -> EngineSnapshot:
    """Read the current markdown corpus and derived synthesis state."""
    papers, principles = scan_memory_dir(memory_dir)
    synthesis_last_run: str | None = None
    synthesis_n_at_last_run = 0

    index_path = memory_dir / "index.json"
    if index_path.exists():
        index_data: dict[str, Any] = json.loads(index_path.read_text(encoding="utf-8"))
        synthesis = index_data.get("synthesis", {})
        if isinstance(synthesis, dict):
            last_run = synthesis.get("last_run")
            if last_run is None or isinstance(last_run, str):
                synthesis_last_run = last_run
            n_at_last = synthesis.get("n_principles_at_last_run", 0)
            if isinstance(n_at_last, int):
                synthesis_n_at_last_run = n_at_last

    return EngineSnapshot(
        memory_dir=memory_dir,
        papers=papers,
        principles=principles,
        synthesis_last_run=synthesis_last_run,
        synthesis_n_at_last_run=synthesis_n_at_last_run,
    )


def reindex_memory(memory_dir: Path) -> str:
    """Rebuild index.json and SQLite from markdown, matching ``kw reindex``."""
    papers, principles = scan_memory_dir(memory_dir)
    index_path = memory_dir / "index.json"
    synthesis_last_run: str | None = None
    synthesis_n_at_last_run: int | None = None
    if index_path.exists():
        existing: dict[str, Any] = json.loads(index_path.read_text(encoding="utf-8"))
        synthesis = existing.get("synthesis", {})
        if isinstance(synthesis, dict):
            last_run = synthesis.get("last_run")
            if last_run is None or isinstance(last_run, str):
                synthesis_last_run = last_run
            n_at_last = synthesis.get("n_principles_at_last_run")
            if n_at_last is None or isinstance(n_at_last, int):
                synthesis_n_at_last_run = n_at_last

    idx = build_index_json(papers, principles, synthesis_last_run, synthesis_n_at_last_run)
    index_path.write_text(json.dumps(idx, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    kw_dir = memory_dir.parent / ".kw"
    kw_dir.mkdir(parents=True, exist_ok=True)
    rebuild_index_db(kw_dir / "index.db", papers, principles)
    return f"Reindexed {len(papers)} papers and {len(principles)} principles"


def paper_rows(snapshot: EngineSnapshot) -> list[UiRow]:
    return [
        UiRow("paper", paper.id, paper.bib.title, f"{paper.status} | {paper.bib.year or 'n.d.'}")
        for paper in snapshot.papers
    ]


def principle_rows(snapshot: EngineSnapshot) -> list[UiRow]:
    return [
        UiRow("principle", principle.id, principle.title, ", ".join(principle.math_basis[:2]))
        for principle in snapshot.principles
    ]


def search_principle_rows(memory_dir: Path, snapshot: EngineSnapshot, query: str) -> list[UiRow]:
    principles_by_id = {principle.id: principle for principle in snapshot.principles}
    rows: list[UiRow] = []
    for result in search_principles(memory_dir, query, top_k=50):
        pid = str(result.get("id", ""))
        principle = principles_by_id.get(pid)
        title = principle.title if principle else str(result.get("title", ""))
        score = result.get("score", 0)
        rows.append(UiRow("principle", pid, title, f"score={score}"))
    return rows


def status_lines(snapshot: EngineSnapshot) -> list[str]:
    return [
        f"Memory: {snapshot.memory_dir}",
        (
            f"Papers: {len(snapshot.papers)} total"
            f" ({snapshot.complete_papers} complete, {snapshot.l1_papers} L1,"
            f" {snapshot.pending_papers} pending)"
        ),
        f"Principles: {len(snapshot.principles)}",
        f"Synthesis: {snapshot.synthesis_status}",
    ]


def verdict_summary(verdicts: list[Verdict]) -> str:
    fails = [verdict for verdict in verdicts if verdict.status == "FAIL"]
    if fails:
        return f"verify: {len(fails)} failure(s)"
    return "verify: all checks PASS"


def paper_detail_lines(paper: PaperFull) -> list[str]:
    return [
        f"{paper.id} | {paper.status}",
        paper.bib.title,
        f"Authors: {paper.bib.authors}",
        f"Venue: {paper.bib.venue} {paper.bib.year or ''}".rstrip(),
        f"DOI: {paper.doi or '-'}",
        "",
        "Problem addressed:",
        paper.problem_addressed,
        "",
        "Method summary:",
        paper.method_summary,
        "",
        "Math used:",
        paper.math_used,
        "",
        "Claimed mechanism:",
        paper.claimed_mechanism,
        "",
        "Key evidence:",
        paper.key_evidence,
    ]


def principle_detail_lines(principle: Principle) -> list[str]:
    return [
        f"{principle.id} | {principle.rubric_version}",
        principle.title,
        "",
        "Abstraction:",
        principle.abstraction_level,
        "",
        "Problem signature:",
        *[f"- {item}" for item in principle.problem_signature],
        "",
        "Math basis:",
        *[f"- {item}" for item in principle.math_basis],
        "",
        "Mechanism:",
        principle.mechanism,
        "",
        "Rationale:",
        principle.rationale,
        "",
        "Data regime:",
        *[f"- {item}" for item in principle.data_regime],
        "",
        "Falsifiable prediction:",
        principle.falsifiable_prediction,
        "",
        "Boundaries:",
        principle.boundaries,
        "",
        "Provenance:",
        *[f"- {item}" for item in principle.provenance],
        "",
        "Links:",
        *([f"- {item}" for item in principle.links] or ["- none"]),
    ]


def wrap_lines(lines: list[str], width: int) -> list[str]:
    wrapped: list[str] = []
    usable_width = max(1, width)
    for line in lines:
        if not line:
            wrapped.append("")
            continue
        wrapped.extend(wrap(line, width=usable_width, break_long_words=False) or [""])
    return wrapped


class TerminalUi:
    """Small curses interface over the existing kw-engine primitives."""

    def __init__(self, screen: Any, memory_dir: Path) -> None:
        self.screen = screen
        self.memory_dir = memory_dir
        self.snapshot = load_snapshot(memory_dir)
        self.active_kind: RowKind = "principle"
        self.search_query = ""
        self.rows: list[UiRow] = []
        self.selected = 0
        self.detail_offset = 0
        self.message = "Ready"
        self.reload_rows()

    def run(self) -> None:
        self.set_cursor(0)
        self.screen.keypad(True)
        while True:
            self.render()
            key = self.screen.getch()
            if self.handle_key(key):
                return

    def reload_snapshot(self) -> None:
        self.snapshot = load_snapshot(self.memory_dir)
        self.reload_rows()

    def reload_rows(self) -> None:
        if self.search_query:
            self.rows = search_principle_rows(self.memory_dir, self.snapshot, self.search_query)
        elif self.active_kind == "paper":
            self.rows = paper_rows(self.snapshot)
        else:
            self.rows = principle_rows(self.snapshot)
        if self.rows:
            self.selected = max(0, min(self.selected, len(self.rows) - 1))
        else:
            self.selected = 0
        self.detail_offset = 0

    def handle_key(self, key: int) -> bool:
        if key in (ord("q"), 27):
            return True
        if key in (curses.KEY_UP, ord("k")):
            self.move_selection(-1)
        elif key in (curses.KEY_DOWN, ord("j")):
            self.move_selection(1)
        elif key == curses.KEY_PPAGE:
            self.move_selection(-10)
        elif key == curses.KEY_NPAGE:
            self.move_selection(10)
        elif key == curses.KEY_HOME:
            self.selected = 0
            self.detail_offset = 0
        elif key == curses.KEY_END and self.rows:
            self.selected = len(self.rows) - 1
            self.detail_offset = 0
        elif key in (ord("["), ord("b")):
            self.detail_offset = max(0, self.detail_offset - 5)
        elif key in (ord("]"), ord(" ")):
            self.detail_offset += 5
        elif key == ord("\t"):
            self.toggle_kind()
        elif key == ord("/"):
            self.prompt_search()
        elif key == ord("c"):
            self.search_query = ""
            self.message = "Search cleared"
            self.reload_rows()
        elif key == ord("r"):
            self.run_reindex()
        elif key == ord("v"):
            self.run_verify()
        elif key == ord("a"):
            self.prompt_add_paper()
        return False

    def move_selection(self, delta: int) -> None:
        if not self.rows:
            return
        self.selected = max(0, min(self.selected + delta, len(self.rows) - 1))
        self.detail_offset = 0

    def toggle_kind(self) -> None:
        self.search_query = ""
        self.active_kind = "paper" if self.active_kind == "principle" else "principle"
        self.selected = 0
        self.message = f"Showing {self.active_kind}s"
        self.reload_rows()

    def prompt_search(self) -> None:
        query = self.prompt("Search principles")
        if query is None:
            self.message = "Search cancelled"
            return
        self.search_query = query.strip()
        self.active_kind = "principle"
        self.selected = 0
        self.message = f"Search: {self.search_query}" if self.search_query else "Search cleared"
        self.reload_rows()

    def prompt_add_paper(self) -> None:
        paper_id = self.prompt("Paper id")
        if not paper_id:
            self.message = "Add paper cancelled"
            return
        title = self.prompt("Title (optional)") or ""
        doi = self.prompt("DOI (optional)") or ""
        try:
            result = add_paper(
                self.memory_dir,
                paper_id.strip(),
                doi=doi.strip() or None,
                title=title.strip() or None,
            )
        except (OSError, ValueError) as exc:
            self.message = f"Add paper failed: {exc}"
            return
        self.reload_snapshot()
        self.active_kind = "paper"
        self.reload_rows()
        self.message = (
            "Paper already exists" if result is None else f"Added paper: {paper_id.strip()}"
        )

    def run_reindex(self) -> None:
        self.message = "Reindexing..."
        self.render()
        try:
            self.message = reindex_memory(self.memory_dir)
            self.reload_snapshot()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.message = f"Reindex failed: {exc}"

    def run_verify(self) -> None:
        try:
            verdicts = run_checks(self.snapshot.papers, self.snapshot.principles)
        except ValueError as exc:
            self.message = f"Verify failed: {exc}"
            return
        self.message = verdict_summary(verdicts)

    def prompt(self, label: str) -> str | None:
        max_y, max_x = self.screen.getmaxyx()
        prompt = f"{label}: "
        self.screen.move(max_y - 1, 0)
        self.screen.clrtoeol()
        self.safe_add(max_y - 1, 0, prompt, max_x)
        curses.echo()
        self.set_cursor(1)
        try:
            raw: bytes = self.screen.getstr(
                max_y - 1,
                len(prompt),
                max(1, max_x - len(prompt) - 1),
            )
        finally:
            curses.noecho()
            self.set_cursor(0)
        return raw.decode("utf-8", errors="replace")

    def render(self) -> None:
        self.screen.erase()
        max_y, max_x = self.screen.getmaxyx()
        if max_y < 12 or max_x < 72:
            self.safe_add(0, 0, "kw-engine UI needs at least 72x12 terminal space", max_x)
            self.screen.refresh()
            return

        list_width = min(48, max(30, max_x // 3))
        detail_x = list_width + 2
        detail_width = max_x - detail_x - 1
        content_y = 4
        content_height = max_y - content_y - 2

        title = "kw-engine terminal UI"
        mode = "search" if self.search_query else self.active_kind
        self.safe_add(0, 0, title, max_x, curses.A_BOLD)
        self.safe_add(0, max_x - len(mode) - 1, mode, len(mode) + 1, curses.A_REVERSE)
        self.safe_add(1, 0, self.message, max_x)
        stats = (
            f"{len(self.snapshot.papers)} papers | {len(self.snapshot.principles)} principles"
            f" | synthesis {self.snapshot.synthesis_status}"
        )
        self.safe_add(2, 0, stats, max_x)
        self.safe_add(3, 0, "-" * max_x, max_x)

        self.draw_rows(content_y, list_width, content_height)
        self.draw_detail(content_y, detail_x, detail_width, content_height)
        footer = (
            "q quit | tab papers/principles | / search | c clear |"
            " a add paper | v verify | r reindex | [] scroll detail"
        )
        self.safe_add(max_y - 1, 0, footer, max_x, curses.A_DIM)
        self.screen.refresh()

    def draw_rows(self, start_y: int, width: int, height: int) -> None:
        title = "Search" if self.search_query else self.active_kind.title()
        heading = f"{title} ({len(self.rows)})"
        self.safe_add(start_y, 0, heading, width, curses.A_BOLD)
        visible_start = max(0, self.selected - height + 2)
        for screen_i in range(1, height):
            row_i = visible_start + screen_i - 1
            if row_i >= len(self.rows):
                break
            row = self.rows[row_i]
            attr = curses.A_REVERSE if row_i == self.selected else curses.A_NORMAL
            title = row.title or "(untitled)"
            text = f"{row.id}  {title}"
            self.safe_add(start_y + screen_i, 0, text, width, attr)
            if width > 16 and row.meta:
                meta = row.meta[: max(0, width - 4)]
                meta_x = max(0, width - len(meta) - 1)
                self.safe_add(start_y + screen_i, meta_x, meta, len(meta), attr)

    def draw_detail(self, start_y: int, x: int, width: int, height: int) -> None:
        self.safe_add(start_y, x, "Detail", width, curses.A_BOLD)
        if not self.rows:
            self.safe_add(start_y + 2, x, "No records", width)
            return
        row = self.rows[self.selected]
        lines = self.detail_for_row(row)
        wrapped = wrap_lines(lines, width)
        visible = wrapped[self.detail_offset : self.detail_offset + height - 1]
        for i, line in enumerate(visible, start=1):
            attr = curses.A_BOLD if i == 1 else curses.A_NORMAL
            self.safe_add(start_y + i, x, line, width, attr)

    def detail_for_row(self, row: UiRow) -> list[str]:
        if row.kind == "paper":
            paper = next((item for item in self.snapshot.papers if item.id == row.id), None)
            if paper is None:
                return [f"{row.id} not found"]
            return paper_detail_lines(paper)
        principle = next((item for item in self.snapshot.principles if item.id == row.id), None)
        if principle is None:
            return [f"{row.id} not found"]
        return principle_detail_lines(principle)

    def safe_add(self, y: int, x: int, text: str, width: int, attr: int = 0) -> None:
        if width <= 0:
            return
        try:
            self.screen.addnstr(y, x, text, width, attr)
        except curses.error:
            return

    def set_cursor(self, visibility: int) -> None:
        try:
            curses.curs_set(visibility)
        except curses.error:
            return


def run_ui(memory_dir: Path) -> None:
    """Launch the terminal UI."""
    curses.wrapper(lambda screen: TerminalUi(screen, memory_dir).run())
