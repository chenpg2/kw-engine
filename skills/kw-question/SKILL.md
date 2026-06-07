---
name: kw-question
description: Sharpen a vague idea, a literature gap, or a stalled project into a GOOD research question — consequential, specific, falsifiable, feasible — BEFORE committing to a technical route. Produces a structured Question Card, then optionally hands off to /kw-explore to form the technical route. Triggers: "is this a good research question", "help me sharpen my question", "我这个想法值得做吗", "把想法变成研究问题", "问题挖掘 / 具象化", "帮我磨一下研究问题".
---

# /kw-question — from a vague idea to a good research question

This is the **upstream** step. `/kw-explore` assumes you already have a question worth pursuing
and builds the technical route to attack it. `/kw-question` decides **whether the question is
worth asking at all**, and sharpens it until it is. Run this first when the user has an idea,
a gap, or a stalled project — not yet a real question.

> Method distilled from public research-craft sources — Alon & Fischbach (problem choice as a
> trainable skill), Platt's *strong inference* (rival hypotheses + discriminating tests),
> Alvesson & Sandberg (challenge hidden assumptions, not just gap-spot), the Heilmeier
> Catechism (explicit goals/risks/success-failure criteria), Hamming & Nielsen (keep a list of
> important, attackable problems) — and the synthesis in the **good-question** project
> (<https://github.com/Rimagination/good-question>). Re-expressed here; credit to them.

Outputs go in the **user's project** (a Question Card markdown). Nothing is written to the
knowledge base — a question is not yet a principle.

## The bar: a question is "good" only if it has all seven

1. **Stakes** — answering it changes theory, method, practice, policy, or the next research step.
2. **Specificity** — evidence can directly touch it; it is not a topic.
3. **Rivalry** — at least 2-3 competing explanations exist.
4. **Falsifiability** — some achievable result could weaken, revise, or kill the claim.
5. **Pilot feasibility** — a credible proof-of-concept can start within ~2 weeks (or the user's stated constraint).
6. **Negative learning** — even a failed/negative result teaches something (a boundary, a mechanism, a method).
7. **Grounding** — claims trace to public sources, or are explicitly labeled as inference (do not invent field consensus).

## Workflow

0. **Diagnose the starting point.** Classify what the user actually has: a broad interest, a
   literature gap, a half-formed idea, a draft proposal, or a stalled project. The starting
   category determines what's missing.
1. **Ground a short domain brief** (only if the question is knowledge-dependent and you're unsure).
   Keep facts (with sources) separate from inference. If the library is linked, `kw search` the
   topic to see what mechanisms already exist — but do NOT invent consensus you can't ground.
2. **Diverge — generate candidate questions** with structured lenses, e.g.:
   - challenge a hidden assumption the field takes for granted (Alvesson & Sandberg);
   - flip the default / reverse the causal arrow;
   - name the *discriminating* observation two rival explanations would disagree on (Platt);
   - shrink scope until evidence can touch it; widen until it matters.
   Produce several variants, not one.
3. **Converge — filter by the seven-point bar.** Drop candidates that are only novel, have no
   audience, cannot fail, or teach nothing when negative.
4. **Rewrite weak forms into real questions.** A topic, a method, a benchmark, or "there's a gap
   in X" is NOT a question. Convert each into a testable proposition.
5. **Editor desk-reject pass.** For each survivor, state the single strongest reviewer objection
   and either fix it or discard the candidate. Be the harsh reviewer, not the cheerleader.
6. **Emit a Question Card** for each surviving question.

## Question Card → write to `<project>/problems/<slug>/QUESTION.md`

```
- Working title:
- The question (1-2 sentences):
- Why it matters (stakes):
- Core assumption challenged:
- Competing hypotheses (2-3):
- Discriminating observation / experiment:
- Falsification conditions (what result kills or revises it):
- Two-week pilot (the cheapest credible proof-of-concept):
- Strongest reviewer objection (+ your answer):
- Best next action:
- Grounding: [sources cited | labeled inference]
```

If several survive, present them ranked and let the user pick the one to pursue.

## Handoff — the user's choice

After the card(s), ask explicitly:

> "问题已经磨好了。要用 **/kw-explore** 把它做成技术路线吗?(映射原则库 → 找缺口 → 补读论文 → 组装带出处的方案。)还是先停在这张卡片?"

- **Yes →** invoke `/kw-explore`. It takes `QUESTION.md` as its Phase 0 input: skip re-framing
  the *worth* of the question (already done here) and go straight to decomposing its **structure**
  for library matching.
- **No →** stop. The Question Card stands on its own (e.g. for a proposal abstract or a lab discussion).

Never push a question into the technical route the user hasn't chosen to pursue.
