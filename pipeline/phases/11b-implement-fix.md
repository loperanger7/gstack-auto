# Phase 11b: Bug Fix Implementation
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack debug/SKILL.md @ v0.7.3
# Last synced: 2026-03-25
#
# DIFFERENCES FROM PHASE 09:
# - Input is the bug fix plan (Phase 11a), not the engineering plan.
# - Only fix bugs. Do NOT add features or refactor.
# - Do NOT create new files unless absolutely necessary for a fix.
# - Verify root cause hypothesis BEFORE writing fix code.
# - Write a failing regression test FIRST, then fix it.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-11b-implement-fix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously
# - SCOPE LOCK: Fix bugs only. Zero feature additions.

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE VERIFICATION.**

Before writing ANY fix code, verify the root cause hypothesis from Phase
11a. A fix applied to the wrong root cause creates a new bug disguised as
a fix — and Phase 11c will catch it.

## Your Task

Read the bug fix plan at `{PHASE_ARTIFACTS}/phase-11a-fix-plan.md`.
Implement every in-scope fix using hypothesis-first, test-first methodology.

## Process

For each bug in the fix plan (in the exact priority order specified):

### Step 1: Verify Root Cause

1. Read the code at the suspected root cause location.
2. Trace the data or execution flow from input to the failure point.
3. Confirm the hypothesis matches what you observe in the code.

**If hypothesis confirmed:** Proceed to Step 2.

**If hypothesis is wrong:**
- Re-read the code path
- Check adjacent patterns in the bug pattern table
- Form a new hypothesis and test it

**3-Strike Rule:** If 3 hypotheses fail, document it as UNRESOLVED.
Do not guess a fourth time. Mark it in the completion log and continue
to the next bug. An honest UNRESOLVED is better than a wrong fix.

### Step 2: Write Failing Regression Test

Write a regression test that:
- Reproduces the exact bug scenario (precondition + trigger action)
- FAILS without the fix (proves the test is meaningful)
- Will PASS after the fix (proves the fix works)
- Includes attribution:
  ```
  # Regression: [bug description]
  # Found by QA Phase 11, Run {RUN_ID}
  ```

Place it in `output/tests/regression/`.

Run the test — confirm it fails before writing the fix:
```bash
cd output && npm test tests/regression/ 2>&1 || python3 -m pytest tests/regression/ -v 2>&1
```

### Step 3: Implement Minimal Fix

- Fix the root cause, not the symptom.
- **Minimal diff:** Fewest files touched, fewest lines changed.
- Resist the urge to refactor adjacent code.
- No drive-by improvements.
- Do not rename variables, reorganize imports, or clean up unrelated code.

### Step 4: Verify

1. Run the regression test — it must now PASS.
2. Run the full test suite — no regressions allowed:
   ```bash
   cd output && npm test 2>&1 || python3 -m pytest -v 2>&1
   ```
3. Remove any temporary debug logging added in Step 1.
4. If the full suite has a NEW failure, roll back this fix, re-investigate,
   and try again.

## Rules

- **Minimal diff.** Change as few lines as possible per fix.
- **No drive-by improvements.** If you see something ugly near the bug, leave it.
- **Test first.** Every bug gets a regression test BEFORE the fix.
- **Fix the root cause, not the symptom.** Verified hypothesis required.
- **Blast radius guard:** If a fix touches >5 files, stop and reconsider
  whether you are fixing the right layer.

## Completion Log

Write to `{PHASE_ARTIFACTS}/phase-11b-implement-fix.md`:

```markdown
# Bug Fix Implementation — Run {RUN_ID}

## Fixes Applied
1. [bug description]
   - Root cause verified: YES / NO
   - Hypothesis: [one sentence]
   - Fix: [file:line range] — [what was changed]
   - Regression test: [test file : test name]
   - Full suite after fix: PASS / FAIL ([N] failures)
   - Status: VERIFIED / BEST_EFFORT / UNRESOLVED

## Unresolved Bugs
1. [bug description]
   - Hypotheses tested:
     1. [hypothesis] — ruled out because [reason]
     2. [hypothesis] — ruled out because [reason]
     3. [hypothesis] — ruled out because [reason]
   - Recommendation: [what to investigate next cycle]

## Final Test Results
[paste full test output — pass/fail count, error messages]

## Files Modified
- [file]: [summary of changes]

## Summary
BUGS_PLANNED: [N]
BUGS_FIXED: [N]
BUGS_UNRESOLVED: [N]
REGRESSION_TESTS_WRITTEN: [N]
REGRESSIONS_INTRODUCED: [N]
```
