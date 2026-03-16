# Phase 08: Bug Fix Implementation
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# DERIVED FROM: pipeline/phases/03-implement.md
# Derived from: (original to Pattaya — no gstack source)
# Last synced: 2026-03-15
#
# DIFFERENCES FROM PHASE 03:
# - Input is the bug fix plan (Phase 07), not the engineering plan.
# - Only fix bugs. Do NOT add features or refactor.
# - Do NOT create new files unless absolutely necessary for a fix.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-08-implement-fix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously
# - SCOPE LOCK: Fix bugs only. Zero feature additions.

## Mode: {MODE}

## Your Task

Read the bug fix plan at `{PHASE_ARTIFACTS}/phase-07-plan-bugfix.md`.
Implement every fix. Run tests after each fix.

## Process

1. Read the bug fix plan.
2. For each bug (in severity order):
   a. Make the minimal code change that fixes the bug.
   b. Add or update a test that would have caught the bug.
   c. Run tests to verify the fix doesn't break anything else.
3. After all fixes: run the full test suite.

## Rules

- **Minimal diff.** Change as few lines as possible per fix.
- **No drive-by improvements.** If you see something ugly near the bug,
  leave it alone.
- **Every fix gets a test.** If the bug could have been caught by a test,
  write that test.
- **Fix the bug, not the symptom.** Root cause, not band-aid.

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-08-implement-fix.md`:

```markdown
# Bug Fix Implementation — Run {RUN_ID}

## Fixes Applied
1. [bug]: [file:line] — [what was changed]
   - Test added: [test file:test name]

## Test Results After Fixes
[paste test output]

## Files Modified
- [file]: [summary]
```
