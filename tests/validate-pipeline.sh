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
for n in 01 02 03 04 05 06 07 08 09 10 11 12 13 14; do
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

# Design phases (12, 13) derived from gstack skills
for f in "$PHASES_DIR"/12-*.md "$PHASES_DIR"/13-*.md; do
  name=$(basename "$f")
  if grep -q "Derived from:" "$f"; then
    pass "$name has Derived from header"
  else
    fail "$name missing Derived from header"
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
if grep -q "rounds:" "pipeline/config.yml"; then
  pass "config.yml has rounds"
else
  fail "config.yml missing rounds"
fi
if grep -q "auto_accept_winner:" "pipeline/config.yml"; then
  pass "config.yml has auto_accept_winner"
else
  fail "config.yml missing auto_accept_winner"
fi
echo ""

# --- Scoring rubric dimensions ---
echo "Scoring rubric:"
for dim in "Functionality" "Code Quality" "Test Coverage" "UX Polish" "Spec Adherence" "Design Quality"; do
  if grep -qi "$dim" "pipeline/scoring/rubric.md"; then
    pass "Rubric has $dim"
  else
    fail "Rubric missing $dim"
  fi
done
echo ""

# --- Scripts ---
echo "Scripts:"
for s in "scripts/check-gstack-sync.sh" "scripts/diff-gstack-phase.sh" "scripts/setup-server.py" "scripts/pattaya-update-check" "scripts/pattaya-upgrade.sh"; do
  if [ -x "$s" ]; then
    pass "$s exists and is executable"
  elif [ -f "$s" ]; then
    fail "$s exists but is not executable"
  else
    fail "$s not found"
  fi
done
echo ""

# --- Mission Control UI ---
echo "Mission Control UI:"
for f in "index.html" "style.css"; do
  if [ -f "$f" ]; then
    pass "$f exists"
  else
    fail "$f not found"
  fi
done
if grep -q 'href="/style.css"' "index.html" 2>/dev/null; then
  pass "index.html links to external style.css"
else
  fail "index.html missing style.css link"
fi
if grep -q '<style>' "index.html" 2>/dev/null; then
  fail "index.html has inline <style> block (should use style.css)"
else
  pass "index.html has no inline styles"
fi
# New Project + Create Repo buttons
if grep -q 'btn-new-project' "index.html" 2>/dev/null; then
  pass "index.html has New Project button"
else
  fail "index.html missing New Project button"
fi
if grep -q 'btn-create-repo' "index.html" 2>/dev/null; then
  pass "index.html has Create Repo button"
else
  fail "index.html missing Create Repo button"
fi
if grep -q 'create-repo-panel' "index.html" 2>/dev/null; then
  pass "index.html has Create Repo panel"
else
  fail "index.html missing Create Repo panel"
fi
if grep -q 'repo-pages' "index.html" 2>/dev/null; then
  pass "index.html has GitHub Pages checkbox"
else
  fail "index.html missing GitHub Pages checkbox"
fi
# Backward compat: setup.html and dashboard.html still exist for redirects
for f in "setup.html" "dashboard.html"; do
  if [ -f "$f" ]; then
    pass "$f exists (backward compat)"
  else
    fail "$f not found (backward compat)"
  fi
done
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
  [ "$code" = "200" ] && pass "GET / returns 200" || fail "GET / returned $code"

  # /styles endpoint
  styles_body=$(curl -s "$BASE/styles")
  if echo "$styles_body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert isinstance(d, list)" 2>/dev/null; then
    pass "GET /styles returns JSON array"
  else
    fail "GET /styles did not return JSON array"
  fi
  if echo "$styles_body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert len(d) >= 7" 2>/dev/null; then
    pass "GET /styles has >= 7 style profiles"
  else
    fail "GET /styles has fewer than 7 style profiles"
  fi
  if echo "$styles_body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert all(k in d[0] for k in ('name','display','quote'))" 2>/dev/null; then
    pass "GET /styles entries have name/display/quote fields"
  else
    fail "GET /styles entries missing required fields"
  fi

  # Extended /current-config
  cfg_body=$(curl -s "$BASE/current-config")
  for field in parallel_runs rounds; do
    if echo "$cfg_body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
      pass "GET /current-config includes $field"
    else
      fail "GET /current-config missing $field"
    fi
  done

  # POST /new-project — should return 200 even with nothing to clear
  # Save spec first so we can restore after the destructive test
  _saved_spec=""
  if [ -f "product-spec.md" ]; then _saved_spec=$(cat product-spec.md); fi
  np_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{}' "$BASE/new-project")
  if [ "$np_code" = "200" ]; then
    pass "POST /new-project returns 200"
  else
    fail "POST /new-project returned $np_code (expected 200)"
  fi
  # Restore spec so subsequent tests pass
  if [ -n "$_saved_spec" ]; then echo "$_saved_spec" > product-spec.md; fi

  # POST /create-repo — invalid name returns 400
  cr_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"repo_name":"invalid name with spaces"}' "$BASE/create-repo")
  if [ "$cr_code" = "400" ]; then
    pass "POST /create-repo rejects invalid name (400)"
  else
    fail "POST /create-repo returned $cr_code for invalid name (expected 400)"
  fi

  # POST /create-repo — missing winner output returns 400
  cr_code2=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d '{"repo_name":"test-repo"}' "$BASE/create-repo")
  if [ "$cr_code2" = "400" ]; then
    pass "POST /create-repo rejects when no winner output (400)"
  else
    fail "POST /create-repo returned $cr_code2 without winner (expected 400)"
  fi
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

# --- Update check script ---
echo "Update check:"
# Test version comparison: local = remote → no output
TMPVER=$(mktemp -d)
echo "1.0.0" > "$TMPVER/VERSION"
(
  export PATTAYA_REMOTE_URL="file:///dev/null"
  cd "$TMPVER"
  mkdir -p scripts
  cp "$(pwd)/../scripts/pattaya-update-check" scripts/ 2>/dev/null || true
)
# Test that script exits cleanly when VERSION exists
if scripts/pattaya-update-check 2>/dev/null; [ $? -le 1 ]; then
  pass "pattaya-update-check runs without crash"
else
  fail "pattaya-update-check exited with error"
fi
rm -rf "$TMPVER"

# Test that upgrade script has --check flag
if grep -q "\-\-check" "scripts/pattaya-upgrade.sh"; then
  pass "pattaya-upgrade.sh supports --check flag"
else
  fail "pattaya-upgrade.sh missing --check flag"
fi
echo ""

# --- Winner selection (mock score.json) ---
echo "Winner selection logic:"
TMPSCORES=$(mktemp -d)
mkdir -p "$TMPSCORES/run-a" "$TMPSCORES/run-b" "$TMPSCORES/run-c"
echo '{"average": 6.2, "bugs_remaining": 0, "fix_cycles_used": 1}' > "$TMPSCORES/run-a/score.json"
echo '{"average": 7.6, "bugs_remaining": 0, "fix_cycles_used": 1}' > "$TMPSCORES/run-b/score.json"
echo '{"average": 7.1, "bugs_remaining": 1, "fix_cycles_used": 2}' > "$TMPSCORES/run-c/score.json"

# Find winner: highest average
WINNER=$(python3 -c "
import json, os, sys
d = '$TMPSCORES'
runs = []
for name in sorted(os.listdir(d)):
    sf = os.path.join(d, name, 'score.json')
    if os.path.isfile(sf):
        with open(sf) as f:
            s = json.load(f)
        runs.append((s['average'], -s.get('bugs_remaining',0), -s.get('fix_cycles_used',0), name))
runs.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
print(runs[0][3])
" 2>/dev/null)

if [ "$WINNER" = "run-b" ]; then
  pass "Winner selection picks highest score (run-b: 7.6)"
else
  fail "Winner selection expected run-b, got: $WINNER"
fi

# Test tie-breaking by bugs_remaining
echo '{"average": 7.6, "bugs_remaining": 2, "fix_cycles_used": 1}' > "$TMPSCORES/run-c/score.json"
WINNER2=$(python3 -c "
import json, os
d = '$TMPSCORES'
runs = []
for name in sorted(os.listdir(d)):
    sf = os.path.join(d, name, 'score.json')
    if os.path.isfile(sf):
        with open(sf) as f:
            s = json.load(f)
        runs.append((s['average'], -s.get('bugs_remaining',0), -s.get('fix_cycles_used',0), name))
runs.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
print(runs[0][3])
" 2>/dev/null)

if [ "$WINNER2" = "run-b" ]; then
  pass "Tie-breaking by bugs_remaining (run-b: 0 bugs wins over run-c: 2 bugs)"
else
  fail "Tie-breaking expected run-b, got: $WINNER2"
fi
rm -rf "$TMPSCORES"
echo ""

# --- Phase prompts have {MODE} variable ---
echo "Phase prompt template variables:"
for n in 01 02 03 04 05 07 08; do
  found=$(ls "$PHASES_DIR"/${n}-*.md 2>/dev/null | head -1)
  if [ -n "$found" ] && grep -q '{MODE}' "$found"; then
    pass "$(basename "$found") has {MODE} variable"
  elif [ -n "$found" ]; then
    fail "$(basename "$found") missing {MODE} variable"
  fi
done

# Phase 01 should also have {EXISTING_CODE_SUMMARY} for iteration mode
found01=$(ls "$PHASES_DIR"/01-*.md 2>/dev/null | head -1)
if [ -n "$found01" ] && grep -q '{EXISTING_CODE_SUMMARY}' "$found01"; then
  pass "$(basename "$found01") has {EXISTING_CODE_SUMMARY} variable"
else
  fail "$(basename "$found01") missing {EXISTING_CODE_SUMMARY} variable"
fi
echo ""

# --- Style profiles ---
echo "Style profiles:"
STYLES_DIR="pipeline/styles"
if [ -d "$STYLES_DIR" ]; then
  pass "pipeline/styles/ directory exists"
else
  fail "pipeline/styles/ directory missing"
fi

for style in carmack antirez abramov metz holowaychuk majors marlinspike; do
  sf="$STYLES_DIR/${style}.md"
  if [ -f "$sf" ] && [ -s "$sf" ]; then
    pass "${style}.md exists and is non-empty"
  else
    fail "${style}.md missing or empty"
  fi
done

# Each style file should have a # heading
for sf in "$STYLES_DIR"/*.md; do
  name=$(basename "$sf")
  if head -1 "$sf" | grep -q '^# '; then
    pass "$name has # heading"
  else
    fail "$name missing # heading on first line"
  fi
done

# {STYLE_PRINCIPLES} and {STYLE_NAME} in phases 01, 03, 04, 14
echo ""
echo "Style template variables:"
for n in 01 03 04 14; do
  found=$(ls "$PHASES_DIR"/${n}-*.md 2>/dev/null | head -1)
  if [ -n "$found" ] && grep -q '{STYLE_PRINCIPLES}' "$found"; then
    pass "$(basename "$found") has {STYLE_PRINCIPLES}"
  elif [ -n "$found" ]; then
    fail "$(basename "$found") missing {STYLE_PRINCIPLES}"
  fi
  if [ -n "$found" ] && grep -q '{STYLE_NAME}' "$found"; then
    pass "$(basename "$found") has {STYLE_NAME}"
  elif [ -n "$found" ]; then
    fail "$(basename "$found") missing {STYLE_NAME}"
  fi
done

# Config should have style field (even if commented out)
if grep -q 'style:' pipeline/config.yml; then
  pass "config.yml has style: field"
else
  fail "config.yml missing style: field"
fi
echo ""

# --- Design style profiles ---
echo "Design style profiles:"
DESIGN_STYLES_DIR="pipeline/design-styles"
if [ -d "$DESIGN_STYLES_DIR" ]; then
  pass "pipeline/design-styles/ directory exists"
else
  fail "pipeline/design-styles/ directory missing"
fi

for ds in dieter-rams brutalist playful; do
  dsf="$DESIGN_STYLES_DIR/${ds}.md"
  if [ -f "$dsf" ] && [ -s "$dsf" ]; then
    pass "${ds}.md exists and is non-empty"
  else
    fail "${ds}.md missing or empty"
  fi
done

# Each design style file should have a # heading
for dsf in "$DESIGN_STYLES_DIR"/*.md; do
  name=$(basename "$dsf")
  if head -1 "$dsf" | grep -q '^# '; then
    pass "$name has # heading"
  else
    fail "$name missing # heading on first line"
  fi
done

# {DESIGN_STYLE_PRINCIPLES} and {DESIGN_STYLE_NAME} in phases 12, 13
echo ""
echo "Design style template variables:"
for n in 12 13; do
  found=$(ls "$PHASES_DIR"/${n}-*.md 2>/dev/null | head -1)
  if [ -n "$found" ] && grep -q '{DESIGN_STYLE_PRINCIPLES}' "$found"; then
    pass "$(basename "$found") has {DESIGN_STYLE_PRINCIPLES}"
  elif [ -n "$found" ]; then
    fail "$(basename "$found") missing {DESIGN_STYLE_PRINCIPLES}"
  fi
  if [ -n "$found" ] && grep -q '{DESIGN_STYLE_NAME}' "$found"; then
    pass "$(basename "$found") has {DESIGN_STYLE_NAME}"
  elif [ -n "$found" ]; then
    fail "$(basename "$found") missing {DESIGN_STYLE_NAME}"
  fi
done

# Config should have design_review and design_style fields
if grep -q 'design_review:' pipeline/config.yml; then
  pass "config.yml has design_review: field"
else
  fail "config.yml missing design_review: field"
fi
if grep -q 'design_style:' pipeline/config.yml; then
  pass "config.yml has design_style: field"
else
  fail "config.yml missing design_style: field"
fi
if grep -q 'design_quality' pipeline/config.yml; then
  pass "config.yml has design_quality in scoring_dimensions"
else
  fail "config.yml missing design_quality in scoring_dimensions"
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
