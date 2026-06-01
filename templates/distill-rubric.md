# distill-rubric@v1 — Layer 2 first-principles distillation

Input: a `memory/papers/<id>.md` (L1). Output: one or more principle records
(SCHEMA §2) via `add_principle`. This is where abstraction happens.

For each distinct transferable idea in the paper, produce a principle that:
1. **Strips the biology.** `abstraction_level` states the idea with NO domain terms.
   (Domain specifics live only in `provenance` and body quotes.)
2. **Captures the mapping** — the three load-bearing fields:
   - `problem_signature`: the STRUCTURAL properties a problem must have for this to apply
     (not "microbiome data" but "two unlabeled sample sets with a meaningful cost geometry").
   - `mechanism` + `math_basis`: the mathematical machinery and how it attacks that structure.
   - `rationale`: the FIRST-PRINCIPLES reason the structure↔mechanism mapping holds.
3. **States limits & testability:**
   - `data_regime`: required data scale/conditions (e.g. "needs N≳hundreds; robust to sparsity").
   - `falsifiable_prediction`: a concrete test that would confirm/refute the mechanism.
   - `boundaries`: assumptions / when it breaks.
4. **Cites provenance**: real `<paperid> §loc` only.
5. **Proposes links** to existing principles (generalizes/contrasts/...) when evident.

Quality bar (verifier checks): no empty load-bearing field; `abstraction_level` free of
un-stripped domain nouns; `rationale` explains WHY (not just restating the mechanism).
Set `rubric_version: distill-rubric@v1` on every principle.
