# Phase 07: Engineering Plan v2 (Design-Reconciled)
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write artifact to {PHASE_ARTIFACTS}/phase-07-plan-eng-v2.md
# - Update output/DESIGN.md if final token changes are needed
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously — pick the best option and move on
# - You MAY emit FOLLOW_UP_QUESTION lines for genuine implementation blockers

## Your Task

You are the lead engineer. You now have three inputs that must be reconciled:

1. The engineering plan (Phase 03) — what can be built
2. The design plan (Phase 05) — what must be built visually
3. The adversarial design review (Phase 06) — where they conflict

Your job: produce the final, definitive implementation plan that a skilled
engineer can execute without ambiguity. Every conflict is resolved here.
Every file is listed. Every test case is named. This is the last plan before
code is written.

Read in this order:
1. `{PHASE_ARTIFACTS}/phase-03-plan-eng.md` — original engineering plan
2. `{PHASE_ARTIFACTS}/phase-05-plan-design.md` — design plan
3. `output/DESIGN.md` — current design system spec
4. The adversarial findings below — the conflicts to resolve

## Adversarial Findings from Phase 06

{ADVERSARIAL_FINDINGS}

Resolve every finding. State your resolution in one sentence each:
- "Accepted: [what changed]"
- "Rejected: [why, and what you're doing instead]"
- "Partially accepted: [what was taken, what was left]"

## Mode: {MODE}

**If mode is `iteration`:** Your job is a targeted diff, not a rewrite.
Identify only the files that need to change based on the combined Phase 05
design plan and Phase 06 adversarial findings. List unchanged files as
"UNCHANGED". Do not touch what isn't broken.

Existing output summary:
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

## Reconciliation Process

### Step 1: Conflict Resolution Log

For each conflict between Phase 03 and Phase 05, produce a one-line decision:

```
CONFLICT: [description of the conflict]
RESOLUTION: [what was decided and why]
```

Common conflicts to look for:
- Design requires a component that isn't in the engineering file plan
- Design specifies a layout approach that requires a different CSS strategy
  than engineering assumed (e.g., design says CSS Grid, engineering planned Flexbox)
- Design adds new files or significantly increases scope of existing files
- Engineering's DESIGN.md token values conflict with design plan's usage

### Step 2: Final File Plan

The definitive file tree. Every file that will exist when implementation
is complete. No more additions after this point.

```
output/
├── DESIGN.md           — design token spec (locked after this phase)
├── index.html          — [purpose], ~[N] lines
├── app.js              — [purpose], ~[N] lines
├── styles.css          — [purpose], ~[N] lines
└── tests/
    ├── app.test.js     — [what's tested]
    └── ...
```

Mark each file:
- `NEW` — does not exist yet
- `MODIFY` — exists, will be changed (iteration mode only)
- `STABLE` — exists, will not be touched (iteration mode only)

Estimated line count per file. If a file will exceed 400 lines, split it
or explain why it can't be split.

### Step 3: CSS Architecture

Specify the CSS approach that implements the design plan:

**Strategy:** [CSS custom properties + vanilla CSS / Tailwind / CSS Modules /
styled-components — pick one and own it]

**Custom properties:** List every CSS variable that will be defined:
```css
:root {
  --color-primary: [hex from DESIGN.md];
  --color-bg: [hex];
  --font-heading: [family];
  --font-body: [family];
  --space-base: [px];
  --space-sm: calc(var(--space-base) * 0.5);
  --space-md: calc(var(--space-base) * 1);
  --space-lg: calc(var(--space-base) * 2);
  --space-xl: calc(var(--space-base) * 4);
  --radius-sm: [px];
  --radius-md: [px];
  --radius-lg: [px];
  --max-width: [px];
}
```

**Layout approach:** [which CSS technique handles each major layout zone]

**Responsive strategy:** [mobile-first with `min-width` breakpoints, or
desktop-first with `max-width` — pick one, state breakpoint values]

**Font loading:** Specify the exact `<link>` tags for Google Fonts (if used),
including `preconnect` for performance. If system fonts: specify the full
stack string.

### Step 4: Final Test Plan

Enumerate every test case by name. These are the exact tests Phase 08
(implementation) will write. No surprises.

```
## [filename].test.[ext]

Unit tests:
  - [test name]: [what behavior it verifies]
  - [test name]: [what behavior it verifies]

Integration tests:
  - [test name]: [what user flow it covers]

Edge case tests:
  - [test name]: [what edge condition it covers]
```

Total expected test count: [N]

Tests must be runnable with a single command. Specify that command:
```bash
[test run command]
```

No test should require network access, external APIs, or a running server
(unless it's an e2e test explicitly labeled as such and gated separately).

### Step 5: Implementation Order (strict)

The order Phase 08 will follow. Each file depends only on files listed
above it:

```
1.  output/DESIGN.md          — tokens locked; no changes after this
2.  output/styles.css         — custom properties + base styles
3.  output/[core logic file]  — pure logic, no DOM dependency
4.  output/tests/[logic].test — proves core logic works before UI
5.  output/index.html         — structure only, no inline styles
6.  output/app.js             — DOM + event wiring
7.  output/tests/[ui].test    — UI behavior tests
8.  output/README.md          — last, once we know what was built
```

Adjust for the actual file plan. The rule: test the logic before wiring
the UI. Write the UI structure before wiring behavior. Write README last.

### Step 6: Definition of Done

Specify the exact conditions that must be true before Phase 08 marks
implementation complete:

```
□ All [N] unit tests pass
□ All [N] integration tests pass
□ No console errors on page load
□ App loads in < 2s on simulated throttled connection (Chrome DevTools 3G)
□ Viewport 375px: no horizontal scroll, all touch targets ≥ 44px
□ Viewport 1280px: content max-width respected, no overflow
□ Success criterion 1 from Phase 01 manually verified: [description]
□ Success criterion 2 from Phase 01 manually verified: [description]
□ All ENV_VARS referenced at runtime, not hardcoded
□ No dead code, commented-out blocks, or debug console.logs
```

### Step 7: Clarifying Questions (optional)

Emit only if a genuine implementation blocker exists:

```
FOLLOW_UP_QUESTION: <specific, answerable question>
```

Maximum 2. At this stage in the pipeline, almost everything should be
resolvable autonomously.
The orchestrator collects these as pending-questions across all parallel runs.

---

## Output Format

Write your plan to `{PHASE_ARTIFACTS}/phase-07-plan-eng-v2.md`:

```markdown
# Engineering Plan v2 (Final) — Run {RUN_ID}

## Conflict Resolution Log
[per conflict: CONFLICT + RESOLUTION]

## Adversarial Findings Addressed
[per finding: accepted/rejected/partially + rationale]

## Final File Plan
[annotated ASCII tree with NEW/MODIFY/STABLE markers]

## CSS Architecture
[strategy + custom properties + layout + responsive + font loading]

## Final Test Plan
[per test file: unit + integration + edge case tests by name]

## Test Command
\`\`\`bash
[single command to run all tests]
\`\`\`

## Implementation Order
[numbered list: file → reason]

## Definition of Done
[checkbox list]

## DESIGN.md Final State
[any last changes to output/DESIGN.md, or "locked — no changes"]
```

This is the final plan. Lock it. Implementation begins next.
