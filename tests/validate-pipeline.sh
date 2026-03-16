#!/bin/bash
# validate-pipeline.sh — Tier 1 static validation for Pattaya pipeline
#
# Checks that all phase files exist, have correct headers, don't contain
# forbidden skill invocations, and that supporting files are valid.
#
# Usage: ./tests/validate-pipeline.sh
# Exit code: 0 = all pass, 1 = failures found

set -euo pipefail

PASS=0
FAIL=0
PHASES_DIR="pipeline/phases"

pass() { PASS=$((PASS + 1)); echo "  ✓ $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ✗ $1"; }

echo "=== Pattaya Pipeline Validation ==="
echo ""

# --- Phase files exist ---
echo "Phase files:"
for n in 01 02 03 04 05 06 07 08 09 10 11 12; do
  found=$(ls "$PHASES_DIR"/${n}-*.md 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    pass "Phase $n exists: $(basename "$found")"
  else
    fail "Phase $n: no file matching ${n}-*.md"
  fi
done
echo ""

# --- Autonomy directives ---
echo "Autonomy directives:"
for f in "$PHASES_DIR"/*.md; do
  name=$(basename "$f")
  if grep -q "PATTAYA AUTONOMOUS PHASE" "$f"; then
    pass "$name has autonomy marker"
  else
    fail "$name missing 'PATTAYA AUTONOMOUS PHASE' marker"
  fi

  if grep -q "Do NOT invoke /skills" "$f"; then
    pass "$name has no-skills directive"
  else
    fail "$name missing 'Do NOT invoke /skills' directive"
  fi

  if grep -q "Do NOT.* AskUserQuestion\|Do NOT.*use AskUserQuestion" "$f"; then
    pass "$name has no-AskUserQuestion directive"
  else
    fail "$name missing AskUserQuestion prohibition"
  fi
done
echo ""

# --- Forbidden skill invocations ---
echo "Namespace isolation (no /skill invocations):"
FORBIDDEN_PATTERNS='invoke /review\|invoke /ship\|invoke /qa\|invoke /retro\|invoke /plan-ceo\|invoke /plan-eng\|run /review\|run /ship\|run /qa\|run /retro\|use /review\|use /ship\|use /qa'
for f in "$PHASES_DIR"/*.md; do
  name=$(basename "$f")
  # Check for patterns that suggest invoking a gstack skill (not just mentioning it)
  if grep -qi "$FORBIDDEN_PATTERNS" "$f" 2>/dev/null; then
    fail "$name contains forbidden skill invocation pattern"
  else
    pass "$name clean (no skill invocations)"
  fi
done
echo ""

# --- Derived phase headers ---
echo "Derived phase tracking:"
for f in "$PHASES_DIR"/07-*.md "$PHASES_DIR"/08-*.md "$PHASES_DIR"/09-*.md "$PHASES_DIR"/10-*.md "$PHASES_DIR"/11-*.md; do
  name=$(basename "$f")
  if grep -q "^# DERIVED FROM:" "$f"; then
    pass "$name has DERIVED FROM header"
  else
    fail "$name missing DERIVED FROM header"
  fi
  if grep -q "^# DIFFERENCES" "$f"; then
    pass "$name has DIFFERENCES section"
  else
    fail "$name missing DIFFERENCES section"
  fi
done
echo ""

# --- Gstack source tracking ---
echo "Gstack source hashes:"
for f in "$PHASES_DIR"/*.md; do
  name=$(basename "$f")
  if grep -q "original to Pattaya" "$f"; then
    pass "$name is original (no gstack source needed)"
  elif grep -q "^# Gstack source hash:" "$f"; then
    pass "$name has gstack source hash"
  elif grep -q "DERIVED FROM.*pipeline/phases" "$f" && ! grep -q "Gstack source hash" "$f"; then
    # Derived phases that reference gstack via "Also derived from"
    if grep -q "^# Gstack source hash:" "$f" || grep -q "Also derived from" "$f"; then
      pass "$name has gstack tracking via parent"
    else
      fail "$name derived from gstack but missing source hash"
    fi
  else
    fail "$name missing gstack source hash or 'original to Pattaya' marker"
  fi
done
echo ""

# --- Supporting files ---
echo "Supporting files:"
for f in "pipeline/config.yml" "pipeline/scoring/rubric.md" "templates/email-report.md" "CLAUDE.md" "product-spec.md"; do
  if [ -f "$f" ]; then
    if [ -s "$f" ]; then
      pass "$f exists and is non-empty"
    else
      fail "$f exists but is empty"
    fi
  else
    fail "$f not found"
  fi
done
echo ""

# --- Config validation ---
echo "Config validation:"
if grep -q "parallel_runs:" "pipeline/config.yml"; then
  pass "config.yml has parallel_runs"
else
  fail "config.yml missing parallel_runs"
fi
if grep -q "max_fix_cycles:" "pipeline/config.yml"; then
  pass "config.yml has max_fix_cycles"
else
  fail "config.yml missing max_fix_cycles"
fi
echo ""

# --- Scoring rubric dimensions ---
echo "Scoring rubric:"
for dim in "Functionality" "Code Quality" "Test Coverage" "UX Polish" "Spec Adherence"; do
  if grep -qi "$dim" "pipeline/scoring/rubric.md"; then
    pass "Rubric has $dim"
  else
    fail "Rubric missing $dim"
  fi
done
echo ""

# --- Scripts ---
echo "Scripts:"
for s in "scripts/check-gstack-sync.sh" "scripts/diff-gstack-phase.sh" "scripts/setup-server.py"; do
  if [ -x "$s" ]; then
    pass "$s exists and is executable"
  elif [ -f "$s" ]; then
    fail "$s exists but is not executable"
  else
    fail "$s not found"
  fi
done
echo ""

# --- Setup UI & Dashboard ---
echo "Setup UI & Dashboard:"
for f in "setup.html" "dashboard.html" "style.css"; do
  if [ -f "$f" ]; then
    pass "$f exists"
  else
    fail "$f not found"
  fi
done
if grep -q 'href="/style.css"' "setup.html" 2>/dev/null; then
  pass "setup.html links to external style.css"
else
  fail "setup.html missing style.css link"
fi
if grep -q 'href="/style.css"' "dashboard.html" 2>/dev/null; then
  pass "dashboard.html links to external style.css"
else
  fail "dashboard.html missing style.css link"
fi
if grep -q '<style>' "setup.html" 2>/dev/null; then
  fail "setup.html still has inline <style> block (should use style.css)"
else
  pass "setup.html has no inline styles"
fi
if grep -q 'href="/dashboard"' "setup.html" 2>/dev/null; then
  pass "setup.html links to dashboard"
else
  fail "setup.html missing dashboard link"
fi
echo ""

# --- Server Integration ---
echo "Server integration:"
SERVER_PID=""
SERVER_PORT=""

python3 scripts/setup-server.py &>/dev/null &
SERVER_PID=$!
sleep 1

if kill -0 "$SERVER_PID" 2>/dev/null; then
  for p in 8080 8081 8082; do
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$p/" 2>/dev/null | grep -q "200"; then
      SERVER_PORT=$p
      break
    fi
  done
fi

if [ -z "$SERVER_PORT" ]; then
  echo "  (skipping server tests — could not start server)"
else
  BASE="http://127.0.0.1:$SERVER_PORT"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/setup")
  [ "$code" = "200" ] && pass "GET /setup returns 200" || fail "GET /setup returned $code"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/dashboard")
  [ "$code" = "200" ] && pass "GET /dashboard returns 200" || fail "GET /dashboard returned $code"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/style.css")
  [ "$code" = "200" ] && pass "GET /style.css returns 200" || fail "GET /style.css returned $code"

  body=$(curl -s "$BASE/results")
  if echo "$body" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    pass "GET /results returns valid JSON"
  else
    fail "GET /results returned invalid JSON"
  fi

  if echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'spec_title' in d" 2>/dev/null; then
    pass "GET /results includes spec_title field"
  else
    fail "GET /results missing spec_title field"
  fi

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/output/../../.env")
  [ "$code" = "403" ] || [ "$code" = "404" ] && pass "Path traversal blocked ($code)" || fail "Path traversal NOT blocked ($code)"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/")
  [ "$code" = "200" ] && pass "GET / smart route returns 200" || fail "GET / returned $code"
fi

if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null || true; fi
echo ""

# --- Email configuration ---
echo "Email configuration:"
if grep -q "^email:" "pipeline/config.yml"; then
  pass "config.yml has email section"
else
  fail "config.yml missing email section"
fi
if grep -q "  to:" "pipeline/config.yml"; then
  pass "config.yml has email.to"
else
  fail "config.yml missing email.to"
fi
if grep -q "  method:" "pipeline/config.yml"; then
  pass "config.yml has email.method"
else
  fail "config.yml missing email.method"
fi
if [ -x "scripts/send-email.py" ]; then
  pass "scripts/send-email.py exists and is executable"
else
  fail "scripts/send-email.py not found or not executable"
fi
if [ -f ".env.example" ]; then
  pass ".env.example exists"
else
  fail ".env.example not found"
fi
if grep -q "PATTAYA_SMTP_USER" ".env.example"; then
  pass ".env.example documents PATTAYA_SMTP_USER"
else
  fail ".env.example missing PATTAYA_SMTP_USER"
fi
if grep -q "PATTAYA_SMTP_PASS" ".env.example"; then
  pass ".env.example documents PATTAYA_SMTP_PASS"
else
  fail ".env.example missing PATTAYA_SMTP_PASS"
fi
if python3 scripts/send-email.py --help 2>&1 | grep -q "\-\-probe"; then
  pass "send-email.py accepts --probe flag"
else
  fail "send-email.py missing --probe flag"
fi
echo ""

# --- Browse binary ---
echo "Browse binary:"
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null && echo "found" || echo "")
if [ -n "$B" ]; then
  pass "Browse binary accessible"
else
  fail "Browse binary not found (QA phase will skip screenshots)"
fi
echo ""

# --- Summary ---
echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "VALIDATION FAILED"
  exit 1
else
  echo "ALL CHECKS PASSED"
  exit 0
fi
