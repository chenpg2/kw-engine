# extract-template@v1 — Layer 1 faithful reading

Produce a `memory/papers/<id>.md` per the SCHEMA §1. Rules:
- FAITHFUL ONLY. Report what the paper says; do NOT generalize or editorialize.
- Every claim cites a section/figure locator (e.g. "§3.2", "Fig 2").
- If a required field cannot be filled from the text, write `UNKNOWN` and set
  `status: incomplete` (never invent).

Fill exactly these front-matter fields (SCHEMA §1):
- bib (title/authors/venue/year), doi if present
- problem_addressed — the concrete problem this paper solves
- method_summary — the method/algorithm, named
- math_used — the mathematical machinery, named (e.g. "entropic optimal transport")
- claimed_mechanism — the authors' stated reason it works
- key_evidence — the key results + locators

Body: faithful notes, direct quotes with locators for anything that will feed L2.
Set `extract_template_version: extract-template@v1`.
