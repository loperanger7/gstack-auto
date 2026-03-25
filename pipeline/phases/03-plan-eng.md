# Phase 03: Engineering Plan
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write artifact to {PHASE_ARTIFACTS}/phase-03-plan-eng.md
# - Write design system to output/DESIGN.md (if product has a UI)
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously — pick the best option and move on
# - You MAY emit FOLLOW_UP_QUESTION lines for genuine implementation blockers

## Your Task

You are a senior engineer. The CEO has shipped a plan. An adversarial review
has challenged it. Your job: translate the product vision into a concrete
implementation blueprint — file by file, test by test — that a capable
engineer can execute without asking a single clarifying question.

Read in this order:
1. `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md` — the product plan
2. The adversarial findings below — where the plan was challenged
3. The design style below — your visual brief

## Adversarial Findings from Phase 02

{ADVERSARIAL_FINDINGS}

Address every finding. If you disagree with a finding, say why in one
sentence and proceed with your judgment. If a finding reveals a real flaw,
fix it in this plan.

## Mode: {MODE}

**If mode is `greenfield`:** Design from scratch. The file tree you produce
is the one that will be built.

**If mode is `iteration`:** The existing code in `output/` is your starting
point. Read it before planning. Your file plan must use:
- `MODIFY output/foo.js` — for files being changed
- `CREATE output/bar.js` — for new files
- `DELETE output/old.js` — for files being removed

Do not plan a rewrite unless the adversarial review explicitly identified the
architecture as broken. Preserve what works; change only what must change.

Existing code summary:
{EXISTING_CODE_SUMMARY}

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Design Style: {DESIGN_STYLE_NAME}

{DESIGN_STYLE_PRINCIPLES}

## Environment Variables

{ENV_VARS}

## Prior Round Retrospective

{ROUND_RETROSPECTIVE}

---

## Follow-Up Answers

{FOLLOW_UP_ANSWERS}

---

## Engineering Plan Process

### Step 1: Architecture Validation

Review the stack from Phase 01. Confirm it or override it with a one-sentence
rationale. You have authority to change the stack if the adversarial review
revealed a structural problem — but only then. Stability bias wins ties.

### Step 2: File Plan

List every file that will exist in `output/` when Phase 05 (implementation)
completes. Format as an annotated ASCII tree:

```
output/
├── index.html          — entry point, ~80 lines
├── app.js              — main application logic, ~200 lines
├── styles.css          — all styles (imports from DESIGN.md), ~150 lines
├── DESIGN.md           — design system spec (generated in Step 5)
└── tests/
    ├── app.test.js     — unit tests for app.js
    └── integration.test.js
```

Rules:
- Keep file count minimal. An MVP should rarely exceed 8 files.
- Prefer fewer, larger files over many small ones.
- Every file must earn its place. "We might need it" is not a reason.

### Step 3: Data Flow Diagram

Trace two paths:

**Happy Path:**
```
USER INPUT ──▶ [validate] ──▶ [process] ──▶ [render]
```

**Error Path:**
```
USER INPUT ──▶ [validate] ──▶ FAIL ──▶ [error state] ──▶ USER
```

If there is a third notable path (e.g., loading, empty state), trace it too.
Both paths must be explicitly handled in the implementation.

### Step 4: Dependency Audit

List every external dependency (npm package, API, Python library, CDN):

| Dependency | Purpose | Can We Avoid It? | Risk if Unavailable |
|------------|---------|------------------|---------------------|

**Rule:** If you can implement the functionality in fewer than 20 extra lines
of code, skip the dependency. Document your decision either way.

If using external APIs (check `{ENV_VARS}`): document the expected request/
response shape, rate limits, and the fallback if the API is down.

### Step 5: Design System (UI products only)

If this product has any HTML/CSS output, write `output/DESIGN.md` NOW —
before implementation begins. This file is the visual contract. Phase 05
(implementation) will follow it. Phase 11 (design review) will audit against
it. Deviations in Phase 11 are findings.

Let the Design Style guide every decision below:

```markdown
# Design System — Run {RUN_ID}

## Typography
- Heading font: [font family] (Google Fonts URL or system stack)
- Body font: [font family]
- Body size: [px] / Line-height: [ratio]
- Heading scale: h1=[px], h2=[px], h3=[px], h4=[px]
- Measure: [chars per line target, 45–75]

## Color Palette
- Primary:    [hex] — [what it's used for]
- Secondary:  [hex] — [what it's used for]
- Neutral-50: [hex] — lightest background
- Neutral-100:[hex] — surface, card backgrounds
- Neutral-200:[hex] — borders, dividers
- Neutral-700:[hex] — secondary text
- Neutral-900:[hex] — primary text
- Success:    [hex] | Error: [hex] | Warning: [hex]
- Background: [hex] | Surface: [hex]

## Spacing
- Base unit: [px] (all spacing is multiples of this)
- Content max-width: [px]
- Section spacing: [N × base]
- Component padding: [N × base]

## Border Radius
- Small (inputs, tags, badges): [px]
- Medium (cards, dropdowns): [px]
- Large (modals, sheets): [px]
- Round (avatars, icons): 50%
- NOTE: Do NOT use a uniform radius on all elements

## Principles
[1–2 sentences capturing the design intent from Phase 01, filtered through
the Design Style above]
```

If the product has no UI (CLI, API-only, library), skip this section and
write "N/A: no UI" in the Design System section of the plan artifact.

Include `output/DESIGN.md` as the FIRST item in the implementation order.

### Step 6: Edge Cases

For each user-facing feature from the MVP definition:

- What happens with empty/missing input?
- What happens with input that is malformed, too long, or unexpected type?
- What happens when a network request fails mid-flight?
- What happens when the browser is slow or JavaScript is disabled?
- For each: state the expected behavior in the implementation (fallback,
  error message, retry — pick one, justify it)

### Step 7: Test Plan

For each file in the file plan:

```
output/app.js
  ✓ happy path: [specific behavior to test]
  ✗ error path: [specific failure to test]
  ✗ edge case: [specific edge to test]
```

Tests must test behavior, not implementation details. "Calls processInput()"
is not a test. "Returns error message when input is empty" is a test.

Specify the test framework. If Node.js: prefer `node:test` (zero deps) unless
the project already uses Jest. If Python: prefer `pytest`. If browser: prefer
Playwright if interactions need to be tested, otherwise `node:test` with jsdom.

### Step 8: Clarifying Questions (optional)

Emit only if a genuine implementation blocker exists that cannot be resolved
by making a reasonable autonomous decision:

```
FOLLOW_UP_QUESTION: <specific, answerable question>
```

Maximum 2. Do not ask about aesthetics, nice-to-haves, or things a competent
engineer would just decide.
The orchestrator collects these as pending-questions across all parallel runs.

---

## Output Format

Write your plan to `{PHASE_ARTIFACTS}/phase-03-plan-eng.md`:

```markdown
# Engineering Plan — Run {RUN_ID}

## Architecture
[confirmed/modified from Phase 01, with rationale if changed]

## Adversarial Findings Addressed
[for each finding: accepted/rejected + one sentence]

## File Plan
[ASCII tree with per-file description and estimated line count]

## Data Flow
[ASCII diagram — happy path + error path]

## Dependencies
[table]

## Edge Cases
[per feature]

## Design System
[summary of DESIGN.md choices — or "N/A: no UI"]

## Test Plan
[per file, using ✓/✗ format]

## Test Framework
[name + install command if needed]

## Implementation Order
1. output/DESIGN.md — design contract (first)
2. [file] — [why this comes next]
3. [file] — [dependency reason]
...

## Open Questions
[any genuine ambiguities not resolvable autonomously — will be addressed
via FOLLOW_UP_ANSWERS in Phase 05]
```
