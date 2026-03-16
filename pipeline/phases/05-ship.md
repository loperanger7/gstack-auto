# Phase 05: Ship
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack ship/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-05-ship.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Mode: {MODE}

## Your Task

Prepare the code for commit. Run final checks, ensure everything passes,
and create a clean git commit.

## Ship Process

### 1. Pre-Ship Checks

```bash
# Run all tests
cd output && npm test 2>&1 || echo "Tests need fixing"

# Check for uncommitted debug artifacts
grep -r "console\.log\|debugger\|TODO\|FIXME\|HACK" output/ --include="*.js" --include="*.ts" --include="*.jsx" --include="*.tsx" -l 2>/dev/null
```

If tests fail: fix them. If debug artifacts found: remove them.

### 2. Clean Up

- Remove any `.DS_Store`, `node_modules`, `*.log` files
- Ensure `.gitignore` is present and covers: node_modules, .env, *.log,
  .DS_Store, dist/ (if applicable)
- Ensure `package-lock.json` or equivalent lockfile exists (if applicable)

### 3. Git Commit

Stage and commit all files in `output/`:

**If mode is `greenfield`:**
```bash
git add output/
git commit -m "feat({RUN_ID}): implement MVP — [one-line description of what was built]"
```

**If mode is `iteration`:**
```bash
git add output/
git commit -m "improve({RUN_ID}): [what was improved] — [weakest dimension targeted]"
```

Use a descriptive commit message that says WHAT was built or changed.

### 4. Verify

After committing, verify the working tree is clean:
```bash
git status
git log --oneline -1
```

## Output Format

Write your ship log to `{PHASE_ARTIFACTS}/phase-05-ship.md`:

```markdown
# Ship Log — Run {RUN_ID}

## Pre-Ship Check Results
- Tests: PASS/FAIL
- Debug artifacts: CLEAN/[list of cleaned files]
- Gitignore: PRESENT/CREATED

## Commit
- Hash: [short hash]
- Message: [commit message]

## Verification
- Working tree: clean/dirty
```
