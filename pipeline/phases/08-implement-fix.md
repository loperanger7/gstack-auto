# Phase 08: Bug Fix Implementation
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack debug/SKILL.md @ v0.7.3
# Gstack source hash: c4f679d8
# Last synced: 2026-03-18
#
# DIFFERENCES FROM PHASE 03:
# - Input is the bug fix plan (Phase 07), not the engineering plan.
# - Only fix bugs. Do NOT add features or refactor.
# - Do NOT create new files unless absolutely necessary for a fix.
# - Verify root cause hypothesis BEFORE writing fix code.
# - Write a failing test FIRST that reproduces the bug, then fix it.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-08-implement-fix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously
# - SCOPE LOCK: Fix bugs only. Zero feature additions.

## Iron Law

**NO FIXES WITHOUT ROOT CAUSE VERIFICATION.**

Before writing ANY fix code, verify the root cause hypothesis from Phase 07.
A fix applied to the wrong root cause creates a new bug disguised as a fix.

## Your Task

Read the bug fix plan at `{PHASE_ARTIFACTS}/phase-07-plan-bugfix.md`.
Implement every fix using hypothesis-first, test-first methodology.

## Mode: {MODE}

**If mode is `iteration`:** You are modifying existing code in `output/`,
not writing from scratch. Read the existing files first. Make surgical
changes per the bug fix plan. Run existing tests before AND after your
changes — break nothing that was passing.

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Environment Variables

{ENV_VARS}

**IMPORTANT:** If keys are listed above, reference them as environment variables
at runtime (e.g., `process.env.ODDS_API_KEY`, `os.environ["KEY"]`). Never
hardcode these values in output files.

## Process

For each bug in the fix plan (in severity order):

### Step 1: Verify Root Cause

Before writing fix code, confirm the hypothesis from Phase 07:

1. Read the code at the suspected root cause location.
2. Add a temporary log statement, assertion, or debug output to verify.
3. Run the reproduction scenario.
4. Does the evidence match the hypothesis?

**If hypothesis confirmed:** Proceed to Step 2.

**If hypothesis wrong:** Re-investigate:
- Re-read the code path from symptom to cause
- Check the pattern analysis table for alternative patterns
- Form a new hypothesis and test it

**3-strike rule:** If 3 hypotheses fail for a single bug, document it
as UNRESOLVED and move to the next bug. Do not guess. An unresolved
bug with honest documentation is better than a wrong fix.

### Step 2: Write Failing Test

Write a regression test that:
- Reproduces the exact bug scenario (the precondition that triggers it)
- FAILS without the fix (proves the test is meaningful)
- Will PASS after the fix (proves the fix works)

### Step 3: Implement Minimal Fix

- Fix the root cause, not the symptom.
- **Minimal diff:** Fewest files touched, fewest lines changed.
- Resist the urge to refactor adjacent code.
- No drive-by improvements.

### Step 4: Verify

- Run the regression test — it should now PASS.
- Run the full test suite — no regressions allowed.
- Remove any temporary debug instrumentation from Step 1.

## Rules

- **Minimal diff.** Change as few lines as possible per fix.
- **No drive-by improvements.** If you see something ugly near the bug,
  leave it alone.
- **Test first.** Every bug gets a regression test BEFORE the fix.
- **Fix the root cause, not the symptom.** Verified hypothesis required.
- **If a fix touches >5 files:** Reconsider. That's a large blast radius
  for a bug fix — you may be fixing the wrong layer.

## Red Flags (slow down if you see these)

- "Quick fix for now" — there is no "for now." Fix it right or mark it
  UNRESOLVED.
- Proposing a fix before tracing data flow — you're guessing.
- Each fix reveals a new problem elsewhere — wrong layer, not wrong code.
- The same module appears in multiple bugs — architectural smell, not
  individual bugs.

## Completion Log

Write to `{PHASE_ARTIFACTS}/phase-08-implement-fix.md`:

```markdown
# Bug Fix Implementation — Run {RUN_ID}

## Fixes Applied
1. [bug description]
   - Root cause verified: YES/NO (hypothesis: [one sentence])
   - Fix: [file:line] — [what was changed]
   - Regression test: [test file:test name]
   - Status: VERIFIED / BEST_EFFORT / UNRESOLVED

## Unresolved Bugs
1. [bug description]
   - Hypotheses tested: [list of 3 hypotheses and why each failed]
   - Recommendation: [what to investigate next]

## Test Results After All Fixes
[paste full test output]

## Files Modified
- [file]: [summary]

## Debug Summary
BUGS_PLANNED: [N]
BUGS_FIXED: [N]
BUGS_UNRESOLVED: [N]
REGRESSIONS: [N]
```
