# Phase 09: Bug Fix Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# DERIVED FROM: pipeline/phases/04-review.md
# Also derived from: gstack review/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIFFERENCES FROM PHASE 04:
# - Only review the bug fix changes, not the entire codebase.
# - Verify that fixes don't introduce new bugs or expand scope.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-09-review-fix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously — fix issues directly

## Your Task

Review the bug fixes from Phase 08. Verify:
1. Each fix actually addresses the reported bug.
2. No fix introduces a new bug.
3. No fix expands scope (adds features, refactors unrelated code).
4. Tests were added for each fix.

Read the fix log at `{PHASE_ARTIFACTS}/phase-08-implement-fix.md`.
Then inspect the actual code changes in `output/`.

## Review Checklist

For each fix:
- [ ] Fix addresses the root cause (not just the symptom)
- [ ] Fix is minimal (no unnecessary changes)
- [ ] A test exists that would have caught the original bug
- [ ] No new security issues introduced
- [ ] No scope expansion (feature addition, refactoring)

If any fix fails these checks: fix the fix.

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-09-review-fix.md`:

```markdown
# Bug Fix Review — Run {RUN_ID}

## Fix Verification
1. [bug]: VERIFIED / NEEDS REWORK — [notes]

## Scope Check
- New features added: 0 (must be 0)
- Files modified outside bug scope: [list or none]

## Issues Found & Fixed
1. [if any corrections were needed]

## Test Results
[paste test output]
```
