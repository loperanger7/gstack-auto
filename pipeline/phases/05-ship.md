# Phase 05: Ship
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack ship/SKILL.md @ v0.6.1
# Gstack source hash: 9d47619e
# Last synced: 2026-03-17
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-05-ship.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Mode: {MODE}

## Your Task

Prepare the code for commit. Run final checks and create a clean commit.

## Process

1. Run all tests:
   ```bash
   cd output && npm test 2>&1 || echo "No test runner"
   ```
   If tests fail: fix the code, not the test (unless the test is wrong).

2. Clean up:
   - Remove `.DS_Store`, `node_modules/`, `*.log` files
   - Ensure `.gitignore` exists and covers: node_modules, .env, *.log, .DS_Store

3. Stage and commit:
   **If mode is `greenfield`:**
   ```bash
   git add output/
   git commit -m "feat({RUN_ID}): implement MVP — [one-line description]"
   ```
   **If mode is `iteration`:**
   ```bash
   git add output/
   git commit -m "improve({RUN_ID}): [what changed] — [weakest dimension targeted]"
   ```

4. Verify:
   ```bash
   git status
   git log --oneline -1
   ```

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-05-ship.md`:

```markdown
# Ship Log — Run {RUN_ID}

## Pre-Ship Check
- Tests: PASS/FAIL
- Gitignore: PRESENT/CREATED

## Commit
- Hash: [short hash]
- Message: [commit message]

## Verification
- Working tree: clean/dirty
```
