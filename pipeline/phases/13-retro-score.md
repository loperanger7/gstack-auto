# Phase 13: Retrospective & Scoring
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack retro/SKILL.md @ v0.3.9
# Last synced: 2026-03-25
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
Be harsh. A generous score helps no one — the orchestrator uses these
scores to rank runs and pick a winner. Inflated scores corrupt the signal.

## Scoring Process

### 1. Gather Evidence

Read ALL prior phase artifacts for this run. Use mechanical extraction —
pull specific sections rather than loading full files:

- `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md` → `## Success Criteria` section
- `{PHASE_ARTIFACTS}/phase-09-implement.md` (or `phase-03-implement.md`) →
  `## Files Created`, `## Test Results`, `## Success Criteria Check`
- `{PHASE_ARTIFACTS}/phase-10-ship.md` (or `phase-05-ship.md`) →
  `## Tests`, `## Overall`
- `{PHASE_ARTIFACTS}/phase-11-qa.md` → `## Bugs Found`, `## Health Score`,
  `BUGS_FOUND`, `CRITICAL_BUGS`, `HEALTH_SCORE`
- `{PHASE_ARTIFACTS}/phase-11b-implement-fix.md` (if it exists) →
  `BUGS_FIXED`, `BUGS_UNRESOLVED`, `REGRESSION_TESTS_WRITTEN`
- `{PHASE_ARTIFACTS}/phase-11c-reqa.md` (if it exists) →
  `BUGS_STILL_PRESENT`, `NEW_REGRESSIONS`
- `{PHASE_ARTIFACTS}/design-scores.json` (if it exists) →
  `numericScore`, `designScore`, `aiSlopScore`

Read the actual code in `output/`. Don't score the plan — score the
delivered artifact.

Read the original product spec (provided below).

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

When a style inspiration is set, evaluate code quality through that
engineer's lens — does the code reflect their principles?

### 2. Score Each Dimension (0–10)

**Functionality (0–10)**
Does the app do what the spec requires?
- 10: Every success criterion passes, handles edge cases gracefully
- 7: All primary flows work, minor edge cases fail or missing
- 5: Most primary flows work, one success criterion fails
- 3: Core functionality partially works, key flows broken
- 0: App doesn't start or main feature is completely absent

**Code Quality (0–10)**
Is the code clean, simple, and maintainable?
- 10: Clear names, small functions, no dead code, easy to follow
- 7: Generally clean, minor issues (some long functions, occasional unclear names)
- 5: Functional but messy — hard to follow, or inconsistent style
- 3: Significant quality issues — duplicated logic, tangled dependencies
- 0: Unreadable, copy-paste chaos, or major architectural problems

When style inspiration is set: evaluate by that engineer's principles.
A Carmack run that ships working C with clever data structures should
score differently than a run that adds layers for no reason.

**Test Coverage (0–10)**
Are there tests? Do they cover the important paths?
- 10: Critical paths tested, edge cases tested, regression tests for any bugs found
- 7: Happy path covered for all features, some edge cases
- 5: Some tests, major paths not covered or tests test existence not behavior
- 3: A few tests that don't actually test anything meaningful
- 0: No tests at all

**UX Polish (0–10)**
If it has a UI: does it look reasonable and work smoothly?
If it's a CLI: is the output clear, errors helpful?
- 10: Delightful — clear hierarchy, fast, error states designed, accessibility considered
- 7: Solid — functional, reasonably clean, no major frustrations
- 5: Usable but rough — confusion possible, missing states, visual issues
- 3: Frustrating — unclear feedback, broken states, poor error messages
- 0: Unusable or broken visually

**Spec Adherence (0–10)**
Does it match the product spec — nothing more, nothing less?
- 10: Implements exactly the spec, no missing features, no scope creep
- 7: Minor omissions or one over-built feature, but core spec met
- 5: One significant spec gap or notable feature added that wasn't asked for
- 3: Multiple spec gaps or significant divergence from stated requirements
- 0: Doesn't match the spec in any meaningful way

**Design Quality (0–10) — only if design review ran**
Check if `{PHASE_ARTIFACTS}/design-scores.json` exists.
If it does: use the `numericScore` value directly as this dimension's score.
If it doesn't exist: omit this dimension entirely from scoring.

### 3. Compute Weighted Average

**With design_quality (6 dimensions):**
```
average = (F×0.30 + Q×0.20 + T×0.15 + U×0.10 + S×0.15 + D×0.10)
```

**Without design_quality (5 dimensions):**
```
average = (F×0.30 + Q×0.20 + T×0.15 + U×0.15 + S×0.20)
```

**Apply penalties:**
- `bugs_remaining > 0`: subtract 1.0 per remaining bug (max −3.0)
  Count bugs_remaining from the most recent QA artifact:
  `BUGS_STILL_PRESENT` from phase-11c-reqa.md, or `BUGS_FOUND` from
  phase-11-qa.md if no fix cycle ran, or 0 if "QA CLEAR" appears.
- `fix_cycles_used == 3` (exhausted): subtract 2.0
  Count fix cycles by checking how many phase-11a/11b/11c sets exist.

Floor at 0.0. Ceiling at 10.0. Round to 1 decimal.

### 4. Count Tests and Regressions

```bash
find output/tests -name "*.test.*" -o -name "*.spec.*" 2>/dev/null | wc -l
find output/tests/regression -type f 2>/dev/null | wc -l
```

If no tests/ directory exists, count is 0.

### 5. Write Narrative

"Why I Built It This Way" — 2-3 paragraphs explaining:
- The key architectural decision and why you made it
- The tradeoff you'd revisit with more time
- What surprised you during implementation
- If design review ran: what the design audit revealed and how the fixes improved it

Be specific. "I used React because it's popular" is not a narrative.
"I kept state in a single top-level object rather than distributed
context because the spec has only two user-facing views and the
added complexity of context wasn't warranted" is a narrative.

### 6. Find the Code Highlight

Identify the single most elegant, well-crafted, or interesting piece of
code from `output/`. It should be 10–30 lines. Copy it exactly.

Good candidates:
- A clean algorithm that solves the core problem elegantly
- A well-designed data structure that makes other code simple
- An error handler that is both correct and user-friendly
- A test that reads like a specification

Write a one-sentence explanation of why this code is good — what
principle it exemplifies, what makes it worth reading.

## Product Spec (for reference)

{PRODUCT_SPEC}

## Output Files

### {PHASE_ARTIFACTS}/score.json

**When design_quality IS present:**
```json
{
  "functionality": 0,
  "code_quality": 0,
  "test_coverage": 0,
  "ux_polish": 0,
  "spec_adherence": 0,
  "design_quality": 0,
  "average": 0.0,
  "bugs_remaining": 0,
  "fix_cycles_used": 0,
  "narrative": "Why I Built It This Way paragraph(s)",
  "highlight": "Code snippet + one-sentence explanation",
  "test_count": 0,
  "regression_tests_added": 0
}
```

**When design_quality is NOT present (no HTML output, design phases skipped):**
```json
{
  "functionality": 0,
  "code_quality": 0,
  "test_coverage": 0,
  "ux_polish": 0,
  "spec_adherence": 0,
  "average": 0.0,
  "bugs_remaining": 0,
  "fix_cycles_used": 0,
  "narrative": "Why I Built It This Way paragraph(s)",
  "highlight": "Code snippet + one-sentence explanation",
  "test_count": 0,
  "regression_tests_added": 0
}
```

Replace all `0` placeholders with actual values. `narrative` and
`highlight` must be non-empty strings (not null, not empty string).

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
| **Average**     | X.X/10 | [after penalties]       |

## Penalties Applied
- [if any, describe which and the math; or "None"]

## What Went Well
- [2-3 specific bullets — reference concrete examples from the code or QA]

## What Could Be Better
- [2-3 specific bullets — not vague, actionable for next round]

## If I Had More Time
- [1-2 bullets — honest assessment of biggest gaps]

## Test Health
- Test files in output/: [N]
- Regression tests added this run: [N]
- Test framework detected: [name or "none"]

## Prior Round Retrospective Applied
{ROUND_RETROSPECTIVE}
- Patterns addressed: [which prior-round patterns were successfully avoided]
- Patterns that recurred: [any that appeared again despite the retrospective]
```

### {PHASE_ARTIFACTS}/highlight.md

```markdown
# Code Highlight — Run {RUN_ID}

[one-sentence explanation of why this code is good]

\`\`\`[language]
[10-30 lines of the best code from this run]
\`\`\`
```
