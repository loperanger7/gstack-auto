# Phase 07: Bug Fix Planning
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack debug/SKILL.md @ v0.7.3
# Gstack source hash: c4f679d8
# Last synced: 2026-03-18
#
# DIFFERENCES FROM PHASE 03:
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
# - SCOPE LOCK: Fix bugs only. Zero feature additions.

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION.**

Fixing symptoms creates whack-a-mole debugging. Every fix that doesn't
address root cause makes the next bug harder to find. For each bug in
the QA report, identify the root cause BEFORE planning the fix.

## Your Task

Read the QA report at `{PHASE_ARTIFACTS}/phase-06-qa.md` (or the most
recent `phase-10-qa-confirm.md` if this is a repeat fix cycle).

Plan fixes for every bug found. Do NOT add features, improve UX, refactor
code, or do anything that isn't directly fixing a reported bug.

## Mode: {MODE}

**If mode is `greenfield`:** You are starting from scratch. Plan the MVP.

**If mode is `iteration`:** A working codebase already exists in `output/`.
Do NOT plan from scratch. Instead:
1. Read the existing code in `output/`.
2. Identify the weakest dimension from the prior round's scores.
3. Plan targeted improvements — not a rewrite. Change what matters most.
4. Keep what works. Break nothing that's passing.

Prior round context: {EXISTING_CODE_SUMMARY}

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Environment Variables

{ENV_VARS}

## Prior Round Retrospective

{ROUND_RETROSPECTIVE}

## Review Process

### 1. Bug Triage

Read the QA report. List every bug with its classification
(Critical/Major/Minor).

### 2. Root Cause Analysis

For each bug, apply the /debug methodology:

**Step A — Collect symptoms:** Read the error description and reproduction
steps from the QA report.

**Step B — Read the code:** Trace the code path from the symptom back to
potential causes. Check recently modified files.

**Step C — Pattern matching:** Check if the bug matches a known pattern:

| Pattern | Signature | Where to look |
|---------|-----------|---------------|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | TypeError, AttributeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Integration failure | Timeout, unexpected response | External API calls, service boundaries |
| Configuration drift | Works locally, fails in QA | Env vars, feature flags, DB state |
| Stale cache | Shows old data | Redis, CDN, browser cache |

**Step D — Form hypothesis:** Write a specific, testable claim about what
is wrong and why. Not "something is broken" but "the user_id foreign key
constraint fails because the users table migration runs after the tweets
table migration."

**3-Strike Rule:** If you form 3 hypotheses for a single bug and none
explain the symptoms, STOP. Do not guess a fourth time. Instead:
1. Write down what you know and what you ruled out.
2. Mark the bug as "root cause unknown — needs deeper investigation."
3. Plan a diagnostic fix (add logging/tracing) instead of a speculative fix.

### 3. Fix Planning

For each bug:
- Root cause hypothesis (one sentence)
- Which file(s) need to change
- What the fix is (one sentence)
- What regression test to write (one sentence)

**Red flags — if you see any of these, plan more carefully:**
- A fix that touches >5 files → likely wrong layer, not wrong code
- The same module appearing in multiple bugs → architectural smell
- A fix that "should work" but you can't explain why the current code
  doesn't → you don't have the root cause yet

### 4. Fix Ordering

Order by severity: Critical first, then Major, then Minor.
Within each severity, order by confidence in root cause (highest first).

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-07-plan-bugfix.md`:

```markdown
# Bug Fix Plan — Run {RUN_ID}

## Iron Law Check
For each bug below, root cause was identified before planning the fix.

## Bugs to Fix (ordered by severity)

### Critical
1. [bug description]
   - Symptom: [what the QA report observed]
   - Root cause: [specific, testable hypothesis]
   - Pattern: [race condition / nil propagation / etc. / none]
   - Files: [file list]
   - Fix: [one sentence]
   - Regression test: [one sentence describing the test]

### Major
1. [bug description]
   - Symptom: [what the QA report observed]
   - Root cause: [specific, testable hypothesis]
   - Pattern: [pattern name or none]
   - Files: [file list]
   - Fix: [one sentence]
   - Regression test: [one sentence describing the test]

### Minor
1. [bug description]
   - Symptom: [what the QA report observed]
   - Root cause: [specific, testable hypothesis]
   - Pattern: [pattern name or none]
   - Files: [file list]
   - Fix: [one sentence]
   - Regression test: [one sentence describing the test]

## Scope Guard
This plan fixes [N] bugs. It adds 0 features. It refactors 0 things.
Each bug has a root cause hypothesis and a planned regression test.
```
