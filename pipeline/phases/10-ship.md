# Phase 10: Ship
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack ship/SKILL.md @ v0.6.1
# Last synced: 2026-03-25
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-10-ship.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Mode: {MODE}

## Your Task

Validate the code in `output/` is ship-ready. Run all checks. Fix anything
that fails. Commit the result.

## Process

### 1. Validate All Files Exist and Are Non-Empty

```bash
find output -type f | sort | while read f; do
  [ -s "$f" ] && echo "OK: $f" || echo "EMPTY: $f"
done
```

If any file is empty, investigate: was it created but not populated?
Fix it before proceeding.

### 2. Run Linter Checks

**JavaScript/TypeScript:**
```bash
cd output && npx eslint . --max-warnings=0 2>&1 || echo "No eslint config"
```

**Python:**
```bash
cd output && python3 -m flake8 . --max-line-length=100 2>&1 || echo "No flake8"
```

Fix all errors. Warnings are acceptable but note them.

### 3. Run the Test Suite

```bash
cd output && npm test 2>&1 || python3 -m pytest -v 2>&1 || echo "No test runner found"
```

If tests fail:
- Fix the code, not the test (unless the test is demonstrably wrong).
- Re-run until all tests pass.
- If a test cannot be fixed without a major code change, document it
  explicitly and mark it as KNOWN_FAILURE in the ship log.

### 4. Security Scan

Check for common security issues:

**Hardcoded secrets:**
```bash
grep -rn --include="*.js" --include="*.ts" --include="*.py" --include="*.env" \
  -E "(api_key|apikey|secret|password|token)\s*=\s*['\"][^'\"]{8,}" \
  output/ 2>/dev/null || echo "No hardcoded secrets found"
```

If secrets are found: replace with environment variable references immediately.

**XSS vectors (JavaScript):**
```bash
grep -rn --include="*.js" --include="*.html" \
  -E "innerHTML\s*=|dangerouslySetInnerHTML|document\.write\(" \
  output/ 2>/dev/null || echo "No obvious XSS vectors"
```

Review any matches. If user-supplied data flows to innerHTML, flag as HIGH.

**SQL injection (Python/Node):**
```bash
grep -rn --include="*.py" --include="*.js" \
  -E 'execute\s*\(\s*[f"\x27]|query\s*\+\s*|"\s*\+\s*(req\.|user|input)' \
  output/ 2>/dev/null || echo "No obvious SQL injection patterns"
```

### 5. Verify the App Can Start

**For web apps with a package.json start script:**
```bash
cd output && timeout 10 npm start &
SERVER_PID=$!
sleep 3
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/ || \
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ || \
echo "App did not respond"
kill $SERVER_PID 2>/dev/null
```

**For Python apps:**
```bash
cd output && timeout 5 python3 -c "import app" 2>&1 || \
timeout 5 python3 -c "import main" 2>&1 || echo "No importable main module"
```

**For static HTML apps:**
```bash
ls output/index.html && echo "Static app: OK" || echo "No index.html"
```

### 6. Clean Up

```bash
rm -rf output/.DS_Store output/node_modules/.cache output/**/*.log
```

Ensure `.gitignore` exists in `output/` and covers:
- `node_modules/`
- `.env`
- `*.log`
- `.DS_Store`
- `__pycache__/`
- `*.pyc`

If `.gitignore` doesn't exist, create it.

### 7. Stage and Commit

**If mode is `greenfield`:**
```bash
git add output/
git commit -m "feat({RUN_ID}): implement MVP — [one-line description from Phase 09]"
```

**If mode is `iteration`:**
```bash
git add output/
git commit -m "improve({RUN_ID}): [what changed] — [weakest dimension targeted]"
```

Verify the commit landed:
```bash
git status
git log --oneline -1
```

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-10-ship.md`:

```markdown
# Ship Log — Run {RUN_ID}

## File Validation
- Total files: [N]
- Empty files found: [N] (list if any)
- Status: PASS / FAIL

## Linter
- ESLint / Flake8: PASS / FAIL / NOT_APPLICABLE
- Warnings: [N]
- Errors fixed: [list any errors found and fixed]

## Tests
- Total: [N]
- Passed: [N]
- Failed: [N]
- Known failures: [list with reason]
- Status: PASS / FAIL

## Security
- Hardcoded secrets: NONE / [description if found + status]
- XSS vectors: NONE / [description if found + status]
- SQL injection: NONE / [description if found + status]

## App Start
- Start check: PASS / FAIL / STATIC
- URL tested: [url or N/A]

## Cleanup
- .gitignore: PRESENT / CREATED
- Temp files removed: YES

## Commit
- Hash: [short hash]
- Message: [commit message]

## Verification
- Working tree: clean / dirty

## Overall: SHIP_READY / BLOCKED
```

If status is BLOCKED, list the specific issues preventing ship and what
would be needed to resolve them. The orchestrator will not advance to QA
if critical issues are unresolved.
