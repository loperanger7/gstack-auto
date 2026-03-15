# Phase 11: QA Confirmation
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# DERIVED FROM: pipeline/phases/06-qa.md
# Also derived from: gstack qa/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIFFERENCES FROM PHASE 06:
# - Focus on verifying that previously reported bugs are fixed.
# - Re-test success criteria.
# - Do NOT expand testing scope beyond original QA findings.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-11-qa-confirm.md
# - Screenshots go to {PHASE_ARTIFACTS}/screenshots/
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Your Task

Verify that all bugs from Phase 06 (or the previous Phase 11) are fixed.
Re-run the success criteria. Report any remaining bugs.

## Process

1. Read the most recent QA report:
   - `{PHASE_ARTIFACTS}/phase-06-qa.md` (first fix cycle)
   - Or the previous `phase-11-qa-confirm.md` (subsequent cycles)

2. For each bug that was reported:
   - Reproduce the steps from the bug report
   - Verify the bug is fixed
   - Mark as FIXED or STILL_BROKEN

3. Re-verify success criteria from Phase 01.

4. Run the test suite.

5. Do one quick exploratory pass — did the fixes break anything new?

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-11-qa-confirm.md`:

```markdown
# QA Confirmation — Run {RUN_ID}

## Bug Verification
1. [bug]: FIXED / STILL_BROKEN
2. [bug]: FIXED / STILL_BROKEN

## Success Criteria Re-Check
1. [criterion]: PASS/FAIL
2. [criterion]: PASS/FAIL

## Regression Check
- New bugs found: [count or none]
- [details if any]

## Test Suite
- Passed: [n]
- Failed: [n]

BUGS_FOUND: [total remaining]
CRITICAL_BUGS: [count]
RECOMMENDATION: FIX_NEEDED / SHIP_READY
```
