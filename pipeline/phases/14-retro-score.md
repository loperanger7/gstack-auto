# Phase 14: Retrospective & Scoring
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack retro/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write score.json to {PHASE_ARTIFACTS}/score.json
# - Write retro to {PHASE_ARTIFACTS}/retro.md
# - Write highlight to {PHASE_ARTIFACTS}/highlight.md
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously

## Your Task

Score this run honestly and produce a retrospective. You are the judge.
Be harsh. A generous score helps no one.

## Scoring Process

### 1. Gather Evidence

Read ALL prior phase artifacts:
- `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md` — the plan
- `{PHASE_ARTIFACTS}/phase-02-plan-eng.md` — the engineering plan
- `{PHASE_ARTIFACTS}/phase-03-implement.md` — implementation log
- `{PHASE_ARTIFACTS}/phase-04-review.md` — review findings
- `{PHASE_ARTIFACTS}/phase-05-ship.md` — ship log
- `{PHASE_ARTIFACTS}/phase-06-qa.md` — QA report
- Any bug-fix phase artifacts (07-11) if they exist
- `{PHASE_ARTIFACTS}/phase-12-design-review.md` — design audit (if exists)
- `{PHASE_ARTIFACTS}/phase-13-design-fix.md` — design fix log (if exists)
- `{PHASE_ARTIFACTS}/design-scores.json` — design scores (if exists)

Read the actual code in `output/`.

Read the original product spec (provided below).

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

### 2. Score Dimensions

Read `pipeline/scoring/rubric.md` for detailed criteria. Score each
dimension 0-10. When a style inspiration is set, evaluate code quality
through that engineer's lens — does this code reflect their principles?

**Functionality (weight: see below)**
Does it work? Do the success criteria pass?

**Code Quality (weight: see below)**
Is the code clean, simple, well-structured? Would a good engineer
be comfortable maintaining it?

**Test Coverage (weight: see below)**
Are there tests? Do they cover the important paths? Do they actually
test behavior (not just existence)?

**UX Polish (weight: see below)**
If it has a UI: does it look reasonable? Is it usable? If CLI: is the
output clear? Are errors helpful?

**Spec Adherence (weight: see below)**
Does it do what the spec asked for? Nothing more, nothing less?

**Design Quality (weight: see below) — only if design review ran**
Check if `{PHASE_ARTIFACTS}/design-scores.json` exists. If it does:
- Read the `designScore` (letter grade) and `numericScore`
- Use the numeric score directly as this dimension's value (0-10)
- Include the AI Slop score in your narrative
If no design-scores.json exists, omit this dimension entirely.

### 3. Compute Average

**Dual weight tables** — use 6-dimension weights when design_quality is
present, 5-dimension weights when it is not:

With design_quality (6 dimensions):
  (F×0.30 + Q×0.20 + T×0.15 + U×0.10 + S×0.15 + D×0.10)

Without design_quality (5 dimensions):
  (F×0.30 + Q×0.20 + T×0.15 + U×0.15 + S×0.20)

Apply penalties:
- If bugs_remaining > 0: subtract 1.0 per remaining bug (max -3.0)
- If fix_cycles_used == max (3): subtract 2.0 (exhausted fix budget)

Floor at 0.0, ceiling at 10.0.

### 4. Write Narrative

"Why I Built It This Way" — 2-3 paragraphs explaining:
- The key architectural decision and why
- What tradeoff you'd make differently with more time
- What surprised you during implementation
- If design review ran: what the design audit revealed and how fixes improved it

### 5. Code Highlight

Find the single most elegant or well-crafted piece of code from `output/`.
Copy it (10-30 lines max) with a one-sentence explanation of why it's good.

## Product Spec (for reference)

{PRODUCT_SPEC}

## Output Files

### {PHASE_ARTIFACTS}/score.json

When design_quality IS present:
```json
{
  "functionality": [0-10],
  "code_quality": [0-10],
  "test_coverage": [0-10],
  "ux_polish": [0-10],
  "spec_adherence": [0-10],
  "design_quality": [0-10],
  "average": [weighted average after penalties],
  "bugs_remaining": [count from QA],
  "fix_cycles_used": [0-3],
  "narrative": "[Why I Built It This Way — 2-3 paragraphs]",
  "highlight": "[code snippet + explanation]"
}
```

When design_quality is NOT present (no HTML output, design phases skipped):
```json
{
  "functionality": [0-10],
  "code_quality": [0-10],
  "test_coverage": [0-10],
  "ux_polish": [0-10],
  "spec_adherence": [0-10],
  "average": [weighted average after penalties],
  "bugs_remaining": [count from QA],
  "fix_cycles_used": [0-3],
  "narrative": "[Why I Built It This Way — 2-3 paragraphs]",
  "highlight": "[code snippet + explanation]"
}
```

### {PHASE_ARTIFACTS}/retro.md

```markdown
# Retrospective — Run {RUN_ID}

## Score Card
| Dimension       | Score | Notes                    |
|-----------------|-------|--------------------------|
| Functionality   | X/10  | [one-line justification] |
| Code Quality    | X/10  | [one-line justification] |
| Test Coverage   | X/10  | [one-line justification] |
| UX Polish       | X/10  | [one-line justification] |
| Spec Adherence  | X/10  | [one-line justification] |
| Design Quality  | X/10  | [if applicable]          |
| **Average**     | X/10  | [after penalties]        |

## Penalties Applied
- [if any]

## What Went Well
- [2-3 bullets]

## What Could Be Better
- [2-3 bullets]

## If I Had More Time
- [1-2 bullets]
```

### {PHASE_ARTIFACTS}/highlight.md

```markdown
# Code Highlight — Run {RUN_ID}

[one-sentence explanation of why this code is good]

\`\`\`[language]
[10-30 lines of the best code from this run]
\`\`\`
```
