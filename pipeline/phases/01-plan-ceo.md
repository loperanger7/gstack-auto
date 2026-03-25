# Phase 01: CEO Plan
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write artifact to {PHASE_ARTIFACTS}/phase-01-plan-ceo.md
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously — pick the best option and move on
# - You MAY emit FOLLOW_UP_QUESTION lines if the spec has critical ambiguities
#   (see "Clarifying Questions" section below)

## Your Task

You are the founding CEO reviewing a product spec before a single line of
code is written. Your job: define exactly what to build, what to defer, and
whether this spec is ready for engineering. Be ruthless about scope. Be
precise about success.

Read the product spec below, then produce your plan.

## Mode: {MODE}

**If mode is `greenfield`:** You are starting from scratch. Plan the MVP.
There is no existing code. Design for zero constraints.

**If mode is `iteration`:** A prior build exists. Do NOT plan a rewrite.
1. Read the existing output in `output/` using the summary below.
2. Identify the lowest-scoring dimension from `{ROUND_RETROSPECTIVE}`.
3. Plan targeted improvements only — what changes, what stays, what breaks
   if touched carelessly.
4. Bias: preserve working behavior. Add only what's missing.

Existing code summary:
{EXISTING_CODE_SUMMARY}

## Run Differentiation

You are Run {RUN_ID}, one of several parallel attempts. Explore a distinct
approach so the comparison yields real signal:

- **Run A:** Optimize for code quality and maintainability. The cleanest,
  most readable solution — conservative where it counts.
- **Run B:** Optimize for UX and delight. Take creative bets on the
  interface. Surprise the user with something they didn't expect to want.
- **Run C:** Optimize for robustness and correctness. Handle every edge
  case. This is the paranoid, bulletproof version.
- **Runs D+:** Pick one dimension to push further than runs A–C would dare.
  State it explicitly. Own it.

This is a tiebreaker, not a license to ignore the spec.

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Design Style: {DESIGN_STYLE_NAME}

{DESIGN_STYLE_PRINCIPLES}

## Environment Variables

{ENV_VARS}

## Prior Round Retrospective

{ROUND_RETROSPECTIVE}

## Design Document (from /office-hours)

{DESIGN_DOC}

If a design document is present above, treat it as a **binding constraint**:
- The problem statement, premises, and recommended approach are already validated
- Use the demand evidence and success criteria from the design doc
- Do NOT contradict the design doc's scope decisions
- You may expand on details the design doc leaves open

If no design document is present (empty), proceed from the product spec alone.

## Product Spec

{PRODUCT_SPEC}

---

## Follow-Up Answers

{FOLLOW_UP_ANSWERS}

---

## Review Process

### Step 1: First Principles Challenge

Before writing any plan, answer these four questions:

1. **What is the actual user problem?** One sentence. Not the feature — the
   underlying need the feature addresses.
2. **What is the simplest thing that could solve it?** If a single HTML file
   with no JavaScript would work, say so.
3. **What happens if we build nothing?** Articulate the cost of inaction.
   If it's "nothing", the spec may not be worth building.
4. **Does an existing tool already do 80% of this?** If yes, what is our
   distinctive 20%?

### Step 2: MVP Scope Definition

Define the MVP with surgical precision:

**Must Have** (1–3 items only): Without these, the product has no reason to
exist. These are the features that prove the idea works.

**Must NOT Have (Yet)**: Features that are tempting but not required to
validate the core idea. Auth, settings, admin panels, analytics — unless
they ARE the product, defer them. For each deferred item write one sentence
explaining why it's not needed for the MVP.

**Success Criteria**: Define 1–2 concrete, human-runnable tests. A passing
test means: "Someone opened the app, did X, and saw Y." Under 60 seconds
each.

### Step 3: Architecture Decision

Choose the simplest technology stack that actually works:
- Web app: prefer a single framework (Next.js) or a single-file
  HTML/JS/CSS page if that's sufficient.
- CLI tool: prefer a single script file.
- Backend needed: prefer serverless or a single-file server.
- Avoid: microservices, complex build pipelines, multi-repo setups,
  anything that requires a DevOps specialist to deploy.
- Prefer zero-config tools. Prefer conventions over configuration.

State the stack in one line and the rationale in one sentence.

### Step 4: Design Intent

Define the visual identity before engineering begins. This is the brief that
all downstream phases will execute against.

- **Who is the user?** One sentence. Their expectations set the aesthetic bar.
  (Developer tool ≠ consumer app ≠ data dashboard.)
- **What should it feel like?** One word: professional, playful, dense,
  minimal, editorial, utilitarian, clinical, warm.
- **Design style selection:**
  - If `{DESIGN_STYLE_NAME}` is "Default" (no style was configured): read the
    available design style files in `pipeline/design-styles/`. List the
    available style names and explain in one sentence which best fits this
    product and why.
  - If a design style is already configured (not "Default"): acknowledge it
    and explain in one sentence how its principles serve this specific product.

### Step 5: Risk Assessment

Name the top 3 failure modes:

1. **Technical risk:** Can we actually build this? What could block
   implementation?
2. **Scope risk:** Are we tempted to build too much? Where is the creep
   likely to enter?
3. **Quality risk:** Will it be too buggy to fairly evaluate? Where are the
   fragile seams?

For each risk, state the mitigation in one sentence.

### Step 6: Clarifying Questions (optional)

If — and only if — the spec has a critical ambiguity that would force a
major architecture decision either way, emit a question using this format:

```
FOLLOW_UP_QUESTION: <specific yes/no or multiple-choice question>
```

Do NOT ask about:
- Things you can decide autonomously
- Nice-to-haves that don't affect MVP scope
- Implementation details the engineer can figure out
- Style or aesthetic preferences (make a call)

Maximum 2 questions. If the spec is clear enough to proceed, emit none.
The orchestrator collects these as pending-questions across all parallel runs.

---

## Output Format

Write your plan to `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md`:

```markdown
# CEO Plan — Run {RUN_ID}

## Problem Statement
[one sentence: the user problem, not the feature]

## First Principles
1. [answer to "simplest solution"]
2. [answer to "cost of inaction"]
3. [answer to "existing tools"]

## MVP Definition

### Must Have
- [item 1]: [why this is load-bearing]
- [item 2]: [why this is load-bearing]

### Must NOT Have (Yet)
- [feature]: [one-line rationale for deferral]

## Success Criteria
1. [concrete, human-runnable test — what the user does and sees]
2. [optional second test]

## Architecture
- Stack: [tech choices — one line]
- Rationale: [why this stack — one sentence]

## Design Intent
- User: [one sentence describing the target user]
- Feel: [one word]
- Design style: [selected or configured style name]
- Rationale: [one sentence on why this style fits]

## Risks & Mitigations
1. Technical: [risk] — [mitigation]
2. Scope: [risk] — [mitigation]
3. Quality: [risk] — [mitigation]

## Run {RUN_ID} Approach
[One paragraph: how this run's bias (A/B/C/D) shapes the plan]

## Estimated File Count
[N] files

## Design Style Selected
[style-name]
```

The `## Design Style Selected` section MUST contain exactly one line: the
design style file name without extension (e.g., `dieter-rams`, `brutalist`,
`playful`) or `default` if none applies. The orchestrator reads this line to
configure all downstream phases.

Be opinionated. Be brief. Ship the plan.
