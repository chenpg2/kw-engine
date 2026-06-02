"""Self-improvement of the distillation rubric — capture failures, gate, promote.

Minimal version of a SkillOpt-style loop: failures from absorb batches become
candidate rules; a Codex audit checks consistency before any rule reaches the
live rubric (the validation gate); promote is an explicit, archived swap.
"""

from __future__ import annotations

import shutil
from pathlib import Path

_LIVE = "distill-rubric.md"
_CANDIDATES = "distill-rubric.candidates.md"
_PROPOSED = "distill-rubric.proposed.md"
_ARCHIVE_DIR = ".rubric-archive"

_CANDIDATE_HEADER = "# Distill-rubric candidate rules (awaiting review)\n\n"


def _candidates_path(process_dir: Path) -> Path:
    return process_dir / _CANDIDATES


def add_candidate(process_dir: Path, *, rule: str, trigger: str = "") -> None:
    """Append a candidate rule (a lesson from a failure) to the staging file."""
    path = _candidates_path(process_dir)
    if not path.exists():
        path.write_text(_CANDIDATE_HEADER, encoding="utf-8")
    entry = f"- **Rule:** {rule}\n"
    if trigger:
        entry += f"  - _trigger:_ {trigger}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(entry)


def count_candidates(process_dir: Path) -> int:
    """Count candidate rules awaiting review."""
    path = _candidates_path(process_dir)
    if not path.exists():
        return 0
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("- **Rule:**")
    )


def assemble_review_bundle(process_dir: Path) -> str:
    """Build the text bundle Codex audits: current rubric + candidate rules."""
    live = (process_dir / _LIVE).read_text(encoding="utf-8")
    cand_path = _candidates_path(process_dir)
    candidates = cand_path.read_text(encoding="utf-8") if cand_path.exists() else "(none)"
    return (
        "You are auditing a distillation rubric for an academic-knowledge engine.\n"
        "Below is the CURRENT RUBRIC and a set of CANDIDATE RULES proposed from "
        "recent distillation failures.\n\n"
        "Your job (the validation gate):\n"
        "1. Integrate candidate rules that genuinely improve the rubric.\n"
        "2. REJECT candidates that duplicate, contradict, or over-narrow existing rules.\n"
        "3. Merge/deduplicate; keep the rubric coherent and concise (do not let it bloat).\n"
        "4. Bump the version tag (e.g. @v1 -> @v2).\n"
        "Output ONLY the full revised rubric markdown, nothing else.\n\n"
        "===== CURRENT RUBRIC =====\n"
        f"{live}\n\n"
        "===== CANDIDATE RULES =====\n"
        f"{candidates}\n"
    )


def promote(process_dir: Path) -> None:
    """Swap the proposed rubric into live, archive the old live, clear candidates.

    Raises FileNotFoundError if no proposed rubric exists (review not run).
    """
    proposed = process_dir / _PROPOSED
    if not proposed.exists():
        raise FileNotFoundError(
            f"No proposed rubric at {proposed}. Run 'kw rubric review' first."
        )
    live = process_dir / _LIVE
    new_content = proposed.read_text(encoding="utf-8")

    # Archive current live. Number by MAX existing index + 1 (never reuse a number
    # even if older archives were deleted) to avoid silently overwriting history.
    archive_dir = process_dir / _ARCHIVE_DIR
    archive_dir.mkdir(exist_ok=True)
    max_n = 0
    for f in archive_dir.glob("distill-rubric-*.md"):
        stem = f.stem.rsplit("-", 1)[-1]
        if stem.isdigit():
            max_n = max(max_n, int(stem))
    if live.exists():
        shutil.copy2(live, archive_dir / f"distill-rubric-{max_n + 1:03d}.md")

    # Write live atomically (temp + rename) so live is never half-written.
    tmp = live.with_suffix(".md.tmp")
    tmp.write_text(new_content, encoding="utf-8")
    tmp.replace(live)

    # Clear candidates BEFORE removing proposed, so a crash here still leaves
    # `proposed` present and the whole promote re-runnable (converges, idempotent).
    cand_path = _candidates_path(process_dir)
    if cand_path.exists():
        cand_path.write_text(_CANDIDATE_HEADER, encoding="utf-8")

    proposed.unlink()
