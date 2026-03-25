# Phase 11a: Bug Fix Planning
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack debug/SKILL.md @ v0.7.3
# Last synced: 2026-03-25
#
# NOTE: This phase only runs if phase-11-qa.md contains bugs (BUGS_FOUND > 0).
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-11a-fix-plan.md
# - Read prior phase artifacts from disk, not conversation history
# - SCOPE LOCK: Plan fixes for bugs only. Zero feature additions.
# - Make ALL decisions autonomously

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE INVESTIGATION.**

Fixing symptoms creates whack-a-mole debugging. For every bug in the QA
report, identify the root cause BEFORE planning the fix.

## Your Task

Read the QA report at `{PHASE_ARTIFACTS}/phase-11-qa.md` (or the most
recent `phase-11c-reqa.md` if this is a subsequent fix cycle).

Plan fixes for every Critical and Major bug found. Also plan fixes for
Medium bugs if time budget allows (estimate < 30 min total). Minor bugs
may be deferred to the documentation phase.

Do NOT add features, improve UX, refactor code, or do anything that is
not directly fixing a reported bug.

## Review Process

### 1. Bug Triage

List every bug from the QA report with its classification
(Critical / Major / Medium / Minor). Count them.

If BUGS_FOUND is 0 in the QA report: this phase should not have been
invoked. Write a one-line note to that effect and stop.

### 2. Root Cause Analysis

For each Critical and Major bug, apply the debug methodology:

**Step A — Collect symptoms:** Read the error description and reproduction
steps from the QA report.

**Step B — Read the code:** Trace the code path from the symptom back to
potential causes. Read the relevant files in `output/`.

**Step C — Pattern matching:**

| Pattern | Signature | Where to look |
|---------|-----------|---------------|
| Race condition | Intermittent, timing-dependent | Concurrent access to shared state |
| Nil/null propagation | TypeError, AttributeError | Missing guards on optional values |
| State corruption | Inconsistent data, partial updates | Transactions, callbacks, hooks |
| Off-by-one | Boundary conditions fail | Loop bounds, index math, pagination |
| Missing validation | Invalid input causes crash | Input handlers, API boundary |
| Integration failure | Timeout, unexpected API response | External API calls, service boundaries |
| Stale state | Shows old data | Local state, cache invalidation |

**Step D — Form hypothesis:** Write a specific, testable claim. Not
"something is broken" but "the save button handler does not await the
async response before navigating away, so the write completes after the
route change, losing the data."

**3-Strike Rule:** If you form 3 hypotheses for a single bug and none
explain the symptoms, STOP. Write down what you know and what you ruled
out. Mark the bug as "root cause unknown — needs deeper investigation."
Plan a diagnostic fix (add logging/assertions) rather than a speculative
one.

### 3. Risk Assessment

For each planned fix, estimate the blast radius:
- **Low:** Changes 1 file, touches < 10 lines, purely additive
- **Medium:** Changes 1-3 files, modifies existing logic
- **High:** Changes >3 files, or touches shared utilities/base classes

If a fix has HIGH blast radius, ask: are you fixing the right layer?
A large fix often means the root cause is elsewhere.

### 4. Fix Ordering

Order by: Critical first → Major → Medium.
Within each severity: highest confidence root cause first.

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-11a-fix-plan.md`:

```markdown
# Bug Fix Plan — Run {RUN_ID}

## Bug Triage Summary
- Critical: [N]
- Major: [N]
- Medium: [N] ([N] planned, [N] deferred)
- Minor: [N] (all deferred to Phase 12)

## Fixes to Implement (ordered by severity)

### Critical
1. [bug description from QA report]
   - Symptom: [what QA observed]
   - Root cause hypothesis: [specific, testable claim]
   - Pattern: [race condition / nil propagation / etc. / none]
   - Files to change: [list]
   - Fix: [one sentence]
   - Regression test: [one sentence describing what to test]
   - Blast radius: LOW / MEDIUM / HIGH

### Major
1. [bug description]
   - Symptom: [observation]
   - Root cause hypothesis: [specific claim]
   - Pattern: [pattern or none]
   - Files to change: [list]
   - Fix: [one sentence]
   - Regression test: [one sentence]
   - Blast radius: LOW / MEDIUM / HIGH

### Medium (if in scope)
1. [bug description]
   - Root cause hypothesis: [specific claim]
   - Fix: [one sentence]
   - Blast radius: LOW / MEDIUM / HIGH

## Deferred (won't fix this cycle)
- [Minor bug]: [reason — e.g., low impact, risky to fix]

## Unknown Root Cause
- [bug description]: [3 hypotheses tested and why each failed]

## Scope Guard
This plan fixes [N] bugs. It adds 0 features. It refactors 0 things.
Total bugs in scope: Critical=[N] + Major=[N] + Medium=[N] = [total].
```
