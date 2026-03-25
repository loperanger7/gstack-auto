# Phase 09: Implementation
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: (original to gstack-auto — no gstack source)
# Last synced: 2026-03-25
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-09-implement.md
# - Read prior phase artifacts from disk, not conversation history
# - ALL generated code goes in output/ directory
# - Make ALL decisions autonomously — pick the best option and move on
# - ADVERSARIAL FINDINGS from phase 08 are your highest-priority input

## Your Task

Build (or improve) the product defined by the plans and adversarial review.
Write code that is simple, correct, and immediately runnable. Every file
earns its place. No scaffolding. No boilerplate for boilerplate's sake.

## Input Artifacts — Mechanical Extraction

Load context efficiently. Read specific `##` sections only — do not load
full files unless a section reference is insufficient.

**From `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md`:**
- Extract `## Success Criteria` — the list of user-facing behaviors you must ship
- Extract `## Scope: Out` — the features you must NOT build

**From `{PHASE_ARTIFACTS}/phase-07-plan-eng-v2.md`:**
- Extract `## Final File Plan` — the definitive list of files to create/modify
- Extract `## Final Test Plan` — the test cases to implement
- Extract `## Implementation Order` — the strict ordering to follow

**From `{PHASE_ARTIFACTS}/phase-03-implement.md` (if it exists — v1 compat):**
- Extract `## Files Created` — understand what was already built
- Extract `## Test Results` — know the baseline pass/fail state

**From `{PHASE_ARTIFACTS}/phase-05-ship.md` (if it exists — v1 compat):**
- Extract `## Pre-Ship Check` — know whether prior tests were passing

**From `{PHASE_ARTIFACTS}/phase-11a-fix-plan.md` (if it exists — iteration mode):**
- Extract `## Bugs to Fix` — the full list of root-caused bugs to address

**Adversarial findings (provided inline):**

{ADVERSARIAL_FINDINGS}

The adversarial findings are your highest-priority input. For every
finding listed:
1. Accept or rebut it with a one-line note in your implementation log.
2. If accepted: implement the fix.
3. If rebutted: explain why the finding is incorrect or inapplicable.

## Follow-Up Answers

{FOLLOW_UP_ANSWERS}

If follow-up answers are provided above, apply them to the ambiguities they
resolve before beginning implementation.

## Mode: {MODE}

**If mode is `greenfield`:** Build the MVP from scratch. Every file is new.
Follow the engineering plan from Phase 02 exactly (unless adversarial
findings supersede it).

**If mode is `iteration`:** You are improving existing code in `output/`.
Do NOT rewrite from scratch.
1. Run existing tests BEFORE touching anything:
   ```bash
   cd output && npm test 2>&1 || python3 -m pytest 2>&1 || echo "No test runner"
   ```
2. Record which tests were passing.
3. Make surgical changes — only what is needed to fix bugs or improve the
   weakest dimensions from the prior round.
4. Run tests again after each significant change.
5. Never break a passing test without an explicit, documented reason.

Prior round context:
{EXISTING_CODE_SUMMARY}

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Environment Variables

{ENV_VARS}

**IMPORTANT:** If keys are listed above, reference them as environment variables
at runtime (e.g., `process.env.ODDS_API_KEY`, `os.environ["KEY"]`). Never
hardcode these values in output files. The user will set them in their
deployment environment.

## Prior Round Retrospective

{ROUND_RETROSPECTIVE}

If a prior round retrospective is provided, apply its learnings. Pay
particular attention to patterns listed under "Patterns to Address" — these
are known failure modes that recurred across multiple runs or rounds.

## Design Constraints

If `output/DESIGN.md` exists (produced by Phase 02), read it before writing
any CSS or HTML. It is your visual blueprint:

- **Use the specified fonts.** Add the Google Fonts `<link>` tag in `<head>`.
  Do not fall back to system fonts unless DESIGN.md specifies system stack.
- **Use the specified colors.** Define CSS custom properties (variables) from
  the palette. Do not invent new colors outside the palette.
- **Use the specified spacing scale.** All margins, padding, and gaps should
  be multiples of the base unit.
- **Use the specified border-radius hierarchy.** Small for inputs, medium for
  cards, large for modals. Not uniform on everything.
- **Respect the max content width.** Set it on the main container.

If `output/DESIGN.md` does not exist, use your best judgment — but lean
toward clean, minimal defaults rather than decorative choices.

## Design Anti-Patterns (DO NOT)

These patterns signal "generated, not designed." Avoid them:

1. Purple/violet/indigo gradient backgrounds
2. The 3-column feature grid (icon-in-circle + title + description x3)
3. Icons in colored circles as decoration
4. Centered everything — use left-aligned content for body text
5. Uniform bubbly border-radius on all elements
6. Decorative blobs, floating circles, wavy SVG dividers
7. Emoji as design elements (in headings, cards, or buttons)
8. Colored left-border accent on cards
9. Generic hero copy ("Welcome to [X]", "Unlock the power of...")
10. Cookie-cutter section rhythm (hero → features → testimonials → CTA)

Phase 11 will flag these as findings. Avoid them now.

## Implementation Principles

Write code as if the best engineer you know will read it tomorrow:

- **Clarity over cleverness.** If a reader needs to pause to understand
  a line, rewrite it.
- **Small functions that do one thing.** If a function needs a comment
  explaining what it does, its name is wrong.
- **Handle errors at the boundary.** Validate inputs where they enter
  the system. Trust data inside the system.
- **No dead code.** No commented-out blocks. No "just in case" imports.
- **No premature abstraction.** Three similar blocks of code is fine.
  An abstraction with one caller is wrong.
- **Tests are not optional.** For every feature, write at least one
  test that proves it works and one that proves it fails gracefully.

## Emitting Follow-Up Questions

If you encounter a genuine implementation ambiguity that cannot be resolved
from the spec, prior artifacts, or adversarial findings, emit a question
on its own line in this format:

```
FOLLOW_UP_QUESTION: <specific, unambiguous question>
```

Emit at most 3 questions. Each must be actionable (the answer determines
exactly what code to write). Do NOT emit questions about preference or
opinion — make the decision yourself and document your rationale.

The orchestrator collects these as pending-questions across all parallel runs.
After emitting questions, continue implementing everything you CAN decide
autonomously. Mark the ambiguous code block with a `TODO: awaiting answer`
comment so the orchestrator knows where to apply the answer.

## Process

1. Resolve adversarial findings: accept or rebut each one.
2. If mode is iteration: run existing tests and record baseline.
3. Read the file plan from the engineering plan (Phase 07 artifact: `phase-07-plan-eng-v2.md`).
4. For each file to create or modify:
   a. Write a failing test that defines the expected behavior.
   b. Write the implementation until the test passes.
   c. Verify both work together by running the tests.
5. After all files are written:
   a. Run the full test suite.
   b. Fix failures in code (not in tests) unless the test is clearly wrong.
   c. Verify success criteria from Phase 01.
6. If any accepted adversarial finding was not fixable, document why.

## Output Directory Structure

All code goes in `output/`:
```
output/
├── [project files per engineering plan]
├── tests/
│   └── [test files, including regression/]
├── package.json (if applicable)
└── README.md (one paragraph: what it is, how to run it)
```

The README.md should contain:
- One sentence: what this is.
- How to install dependencies (if any).
- How to run it.
- How to run tests.

Nothing else. No badges, no contributing guide, no license section.

## Completion Log

Write to `{PHASE_ARTIFACTS}/phase-09-implement.md`:

```markdown
# Implementation Log — Run {RUN_ID}

## Adversarial Findings Resolution
| # | Finding | Decision | Action |
|---|---------|----------|--------|
| 1 | [finding summary] | ACCEPTED / REBUTTED | [fix applied or reason rebutted] |

## Files Created / Modified
- output/[file]: [what it does]

## Tests Written
- output/tests/[file]: [what it tests]

## Test Results
[paste full test output — pass/fail count, any errors]

## Success Criteria Check
1. [criterion from Phase 01]: PASS / FAIL — [one line detail]
2. [criterion from Phase 01]: PASS / FAIL — [one line detail]

## Decisions Made
- [any deviation from the plan, with rationale]

## Unresolved Items
- [any accepted finding that could not be fully fixed, with explanation]
```
