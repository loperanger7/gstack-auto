# Phase 10: Ship Bug Fixes
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# DERIVED FROM: pipeline/phases/05-ship.md
# Also derived from: gstack ship/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIFFERENCES FROM PHASE 05:
# - Commit message uses "fix:" prefix instead of "feat:"
# - Only commits bug fix changes
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-10-ship-fix.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Your Task

Commit the bug fixes. Same process as Phase 05 but for fixes only.

## Process

1. Run all tests. If any fail, fix them first.
2. Clean up debug artifacts.
3. Stage and commit:
   ```bash
   git add output/
   git commit -m "fix: [one-line description of bugs fixed]"
   ```
4. Verify clean working tree.

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-10-ship-fix.md`:

```markdown
# Ship Fix Log — Run {RUN_ID}

## Pre-Ship Check
- Tests: PASS/FAIL

## Commit
- Hash: [short hash]
- Message: [commit message]

## Verification
- Working tree: clean/dirty
```
