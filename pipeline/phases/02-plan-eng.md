# Phase 02: Engineering Plan Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack plan-eng-review/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-02-plan-eng.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously — pick the best option and move on

## Your Task

You are a senior engineer reviewing the CEO's plan from Phase 01.
Your job: turn the product vision into a concrete implementation plan
with file-by-file specificity.

Read the CEO plan at `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md`.

## Mode: {MODE}

**If mode is `iteration`:** The existing code in `output/` is your starting
point. Your file plan should describe CHANGES to existing files, not a
greenfield file tree. Use "MODIFY output/foo.js" vs "CREATE output/foo.js".
Read the existing code first. Your plan must preserve what works.

## Review Process

### 1. Architecture Validation

Review the stack choice from Phase 01. Either confirm or override it
with a one-sentence rationale. Then produce:

```
FILE PLAN:
  output/
  ├── [file 1] — [what it does, ~lines]
  ├── [file 2] — [what it does, ~lines]
  └── ...
```

Keep the file count as low as possible. A great MVP might be 1-5 files.
Prefer fewer, larger files over many small ones for an MVP.

### 2. Data Flow Diagram

```
  USER INPUT ──▶ [component] ──▶ [component] ──▶ OUTPUT
       │              │              │
       ▼              ▼              ▼
    [validate]    [process]      [render]
```

Trace the happy path. Then trace the error path. Both must be handled.

### 3. Dependency Audit

List every external dependency (npm package, API, service):
- Name
- Why it's needed (can we avoid it?)
- Risk if it's unavailable

**Rule:** If you can do it without a dependency in <20 extra lines of
code, skip the dependency.

### 4. Edge Cases

For each user-facing feature in the MVP, list:
- What happens with empty input?
- What happens with very large input?
- What happens when the network is down (if applicable)?
- What happens on a slow connection (if applicable)?

### 5. Test Plan

For each file in the file plan:
- What's the one test that proves it works?
- What's the one test that proves it handles failure?

## Output Format

Write your plan to `{PHASE_ARTIFACTS}/phase-02-plan-eng.md` with:

```markdown
# Engineering Plan — Run {RUN_ID}

## Architecture Confirmation
[confirmed or overridden, with rationale]

## File Plan
[ASCII tree with descriptions]

## Data Flow
[ASCII diagram]

## Dependencies
| Package | Purpose | Avoidable? |
|---------|---------|------------|

## Edge Cases
[per feature]

## Test Plan
[per file]

## Implementation Order
1. [file] — start here because [reason]
2. [file] — then this because [dependency]
...
```
