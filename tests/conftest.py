from pathlib import Path
import pytest


@pytest.fixture
def sample_memory(tmp_path: Path) -> Path:
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "papers").mkdir()
    (mem / "principles").mkdir()

    (mem / "papers" / "test-paper.md").write_text(
        '---\n'
        'id: test-paper\n'
        'doi: "10.1234/test"\n'
        'bib:\n'
        '  title: "Test Paper"\n'
        '  authors: "A Author"\n'
        '  venue: "Test Venue"\n'
        '  year: 2024\n'
        'problem_addressed: "A problem"\n'
        'method_summary: "A method"\n'
        'math_used: "Some math"\n'
        'claimed_mechanism: "A mechanism"\n'
        'key_evidence: "Evidence §1"\n'
        'status: complete\n'
        'extract_template_version: extract-template@v1\n'
        '---\n\n'
        'Body text here.\n'
    )

    (mem / "principles" / "P-0001.md").write_text(
        '---\n'
        'id: P-0001\n'
        'title: "Test Principle"\n'
        'abstraction_level: "Abstract statement"\n'
        'problem_signature:\n'
        '  - "Sig one"\n'
        'math_basis:\n'
        '  - "basis-one"\n'
        'mechanism: "A mechanism"\n'
        'rationale: "A rationale"\n'
        'data_regime:\n'
        '  - "regime"\n'
        'falsifiable_prediction: "prediction"\n'
        'boundaries: "bounds"\n'
        'provenance:\n'
        '  - "test-paper §1"\n'
        'rubric_version: distill-rubric@v1\n'
        'links:\n'
        '  - "contrasts:P-0002"\n'
        '---\n\n'
        'Body text.\n'
    )
    return mem
