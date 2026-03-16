# Phase 04: Code Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack review/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-04-review.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously — fix issues directly

## Your Task

Review the code written in Phase 03. Find bugs, security issues, and
quality problems. Fix them directly — do not ask for permission.

## Mode: {MODE}

**If mode is `iteration`:** Focus your review on the CHANGES made this
round. Don't re-review unchanged code unless a change introduces a
regression risk in adjacent code.

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Review Process

### Pass 1: Critical Issues (fix immediately)

Scan all files in `output/` for:

1. **Security holes**
   - SQL injection, command injection, XSS, path traversal
   - Hardcoded secrets, credentials, API keys
   - Missing input validation at system boundaries

2. **Correctness bugs**
   - Off-by-one errors
   - Null/undefined dereference
   - Unhandled promise rejections or uncaught exceptions
   - Race conditions in async code
   - Type mismatches

3. **Data integrity**
   - Write operations without error handling
   - Missing validation before persistence
   - Inconsistent state on partial failure

For each critical issue found: fix it immediately in the code.

### Pass 2: Quality Issues (fix if quick, note if not)

1. **Dead code** — remove it
2. **Duplicated logic** — extract if >3 lines repeated >2 times
3. **Misleading names** — rename
4. **Missing error handling** — add it
5. **Missing tests** — write them
6. **Console.log/print debugging** — remove it
7. **Overly complex functions** — simplify if possible in <5 minutes

### Pass 3: Architecture Check

- Does the code match the engineering plan from Phase 02?
- Are there unnecessary abstractions?
- Are there missing abstractions (copy-pasted code blocks)?
- Is the dependency count justified?

## After Review

Run all tests. If any fail after your fixes, fix the regression.

## Output Format

Write your review to `{PHASE_ARTIFACTS}/phase-04-review.md`:

```markdown
# Code Review — Run {RUN_ID}

## Critical Issues Found & Fixed
1. [file:line] [issue] — FIXED: [what you did]

## Quality Issues Found & Fixed
1. [file:line] [issue] — FIXED: [what you did]

## Quality Issues Noted (not fixed)
1. [file:line] [issue] — DEFERRED: [why]

## Architecture Assessment
[1-2 paragraphs]

## Test Results After Review
[paste test output]

## Files Modified
- [file]: [summary of changes]
```
