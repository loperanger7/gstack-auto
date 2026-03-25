# Phase 11c: Re-QA (Post Bug Fix)
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack qa/SKILL.md @ v2.0.0
# Last synced: 2026-03-25
#
# PURPOSE: Verify fixes resolved the bugs found in phase-11-qa.md.
# Check for regressions introduced by the fixes.
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-11c-reqa.md
# - Screenshots go to {PHASE_ARTIFACTS}/screenshots/reqa/
# - Read prior phase artifacts from disk, not conversation history
# - Make ALL decisions autonomously

## Your Task

Re-run targeted QA to verify all fixes from Phase 11b resolved the bugs
found in Phase 11 (or the prior re-QA cycle). Also run a regression sweep
to confirm the fixes did not introduce new failures.

You are NOT doing a full re-run of all QA. Focus on:
1. The specific bugs that were fixed (verify each one is gone)
2. The surrounding code paths (check for regressions from fixes)
3. Any bugs flagged as UNRESOLVED in Phase 11b (confirm still present)

## Setup

```bash
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null || .claude/skills/gstack/browse/dist/browse 2>/dev/null)

cd output
if [ -f "package.json" ] && grep -q '"start"' package.json; then
  npm start &
  sleep 3
  APP_URL="http://localhost:3000"
elif [ -f "package.json" ] && grep -q '"dev"' package.json; then
  npm run dev &
  sleep 3
  APP_URL="http://localhost:3000"
else
  ENTRY=$(ls index.html 2>/dev/null || ls *.html 2>/dev/null | head -1)
  APP_URL="file://$(pwd)/$ENTRY"
fi

mkdir -p {PHASE_ARTIFACTS}/screenshots/reqa
```

## Re-QA Process

### 1. Read the Fix Inventory

Read `{PHASE_ARTIFACTS}/phase-11b-implement-fix.md`.
Extract:
- Every bug marked VERIFIED or BEST_EFFORT (need to confirm fixed)
- Every bug marked UNRESOLVED (need to confirm still present — expected)
- Total REGRESSION_TESTS_WRITTEN count

### 2. Smoke Test

Confirm the app still starts:
```bash
$B goto "$APP_URL"
$B console --errors
$B screenshot "{PHASE_ARTIFACTS}/screenshots/reqa/smoke.png"
```

If the app won't start after fixes, that is a Critical regression.
Log it and stop — there is nothing further to test.

### 3. Verify Each Fixed Bug

For each bug marked VERIFIED or BEST_EFFORT in the fix plan:

1. Reproduce the exact steps from the original QA report.
2. Observe the outcome.
3. Record: FIXED / STILL_PRESENT / PARTIAL_FIX.
4. Take a screenshot as evidence.

```bash
$B goto "$APP_URL"
# reproduce the steps...
$B screenshot "{PHASE_ARTIFACTS}/screenshots/reqa/fix-{N}-verification.png"
```

**PARTIAL_FIX** means: the immediate symptom is gone but a related
failure mode is still present. Log it as a new bug (same severity as
original, with description of what remains).

### 4. Run Regression Tests

```bash
cd output && npm test 2>&1 || python3 -m pytest -v 2>&1
```

Specifically note whether all regression tests added in Phase 11b pass:
```bash
cd output && npm test tests/regression/ 2>&1 || \
python3 -m pytest tests/regression/ -v 2>&1
```

A failing regression test means a bug was re-introduced. That is a
regression — log it as a new bug at the same severity as the original.

### 5. Regression Sweep

For the files modified during Phase 11b, test the adjacent behavior:

- If a form submission was fixed: test related form interactions
- If a state update was fixed: test nearby state mutations
- If an API call was fixed: test the error path of that same call
- If CSS was changed: check the element on mobile viewport

```bash
$B viewport 375 812
$B screenshot "{PHASE_ARTIFACTS}/screenshots/reqa/mobile-post-fix.png"
$B viewport 1280 720
```

### 6. Success Criteria Spot-Check

Re-run any success criteria that were FAIL in Phase 11. Confirm they now PASS.

## Outcome Determination

**RE-QA CLEAR** if:
- All VERIFIED bugs are now FIXED (no STILL_PRESENT)
- No new Critical or Major regressions introduced
- All regression tests pass
- Full test suite passes

**BUGS_REMAIN** if:
- Any VERIFIED bug is STILL_PRESENT or PARTIAL_FIX
- Any new Critical or Major regression was introduced
- Any regression test fails

If BUGS_REMAIN, the orchestrator will loop back to Phase 11a (up to 3
total fix cycles). Include a clear list of remaining bugs so Phase 11a
can plan the next round of fixes.

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-11c-reqa.md`:

```markdown
# Re-QA Report — Run {RUN_ID}

## Smoke Test
- App starts: YES / NO
- Console errors: NONE / [list]

## Fix Verification
| # | Bug Description | Original Severity | Status |
|---|----------------|-------------------|--------|
| 1 | [description]  | Critical/Major/Medium | FIXED / STILL_PRESENT / PARTIAL_FIX |
| 2 | ...            | ...               | ...    |

## Unresolved Bugs (expected to remain)
| # | Bug Description | Status |
|---|----------------|--------|
| 1 | [description]  | CONFIRMED_PRESENT (as expected) |

## Regression Tests
- All regression tests pass: YES / NO
- [list any failures]

## New Regressions Found
### Critical
1. [description] — [which fix introduced this] — [steps to reproduce]

### Major
1. [description] — [which fix introduced this] — [steps to reproduce]

## Success Criteria Re-Check
1. [criterion]: PASS / FAIL

## Screenshots
- smoke.png: post-fix smoke test
- fix-N-verification.png: per-fix evidence
- mobile-post-fix.png: mobile viewport after fixes

## Summary
BUGS_VERIFIED_FIXED: [N]
BUGS_STILL_PRESENT: [N]
BUGS_PARTIAL_FIX: [N]
NEW_REGRESSIONS: [N]
ALL_TESTS_PASS: YES / NO

## Outcome
RE-QA CLEAR — all bugs fixed
```
OR
```
BUGS_REMAIN: [N] bugs still need fixing
Remaining bugs:
1. [description] — [severity] — [reproduction steps]
```
