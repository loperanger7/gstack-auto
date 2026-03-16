# Phase 07: Bug Fix Planning
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# DERIVED FROM: pipeline/phases/01-plan-ceo.md
# Also derived from: gstack plan-ceo-review/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIFFERENCES FROM PHASE 01:
# - Scope is LOCKED. Do NOT add features. Only fix bugs.
# - Input is the QA report, not the product spec.
# - Output is a bug fix plan, not a product plan.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-07-plan-bugfix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously
# - Do NOT expand scope. Fix bugs. Nothing else.

## Mode: {MODE}

## Your Task

Read the QA report at `{PHASE_ARTIFACTS}/phase-06-qa.md` (or the most
recent `phase-11-qa-confirm.md` if this is a repeat fix cycle).

Plan fixes for every bug found. Do NOT add features, improve UX, refactor
code, or do anything that isn't directly fixing a reported bug.

## Process

1. Read the QA report.
2. List every bug with its classification (Critical/Major/Minor).
3. For each bug:
   - Root cause analysis (one sentence)
   - Which file(s) need to change
   - What the fix is (one sentence)
4. Order by severity (Critical first, then Major, then Minor).

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-07-plan-bugfix.md`:

```markdown
# Bug Fix Plan — Run {RUN_ID}

## Bugs to Fix (ordered by severity)

### Critical
1. [bug description]
   - Root cause: [one sentence]
   - Files: [file list]
   - Fix: [one sentence]

### Major
1. [bug description]
   - Root cause: [one sentence]
   - Files: [file list]
   - Fix: [one sentence]

### Minor
1. [bug description]
   - Root cause: [one sentence]
   - Files: [file list]
   - Fix: [one sentence]

## Scope Guard
This plan fixes [N] bugs. It adds 0 features. It refactors 0 things.
```
