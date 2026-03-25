#!/bin/bash
# validate-pipeline.sh — Static validation for gstack-auto pipeline v2
#
# Checks phase files, template variables, config fields, adversarial
# review config, follow-up budget, supporting files, and UI integration.
#
# Usage: ./tests/validate-pipeline.sh
# Exit code: 0 = all pass, 1 = failures found

set -euo pipefail

PASS=0
FAIL=0
PHASES_DIR="pipeline/phases"

pass() { PASS=$((PASS + 1)); echo "  ✓ $1"; }
fail() { FAIL=$((FAIL + 1)); echo "  ✗ $1"; }

echo "=== gstack-auto Pipeline v2 Validation ==="
echo ""

# --- Phase files exist ---
echo "Phase files (v2):"
V2_PHASES="01-plan-ceo 02-adversarial-ceo 03-plan-eng 04-adversarial-eng 05-plan-design 06-adversarial-design 07-plan-eng-v2 08-adversarial-final 09-implement 10-ship 11-qa 12-document-release 13-retro-score"
for phase in $V2_PHASES; do
  f="$PHASES_DIR/${phase}.md"
  if [ -f "$f" ] && [ -s "$f" ]; then
    pass "$phase.md exists and is non-empty"
  else
    fail "$phase.md missing or empty"
  fi
done

# Bug-fix sub-loop phases
for sub in 11a-fix-plan 11b-implement-fix 11c-reqa; do
  f="$PHASES_DIR/${sub}.md"
  if [ -f "$f" ] && [ -s "$f" ]; then
    pass "$sub.md exists and is non-empty"
  else
    fail "$sub.md missing or empty"
  fi
done
echo ""

# --- Autonomy directives ---
echo "Autonomy directives:"
# Agent phases (not adversarial placeholders) must have autonomy markers
AGENT_PHASES="01-plan-ceo 03-plan-eng 05-plan-design 07-plan-eng-v2 09-implement 10-ship 11-qa 11a-fix-plan 11b-implement-fix 11c-reqa 12-document-release 13-retro-score"
for phase in $AGENT_PHASES; do
  f="$PHASES_DIR/${phase}.md"
  [ ! -f "$f" ] && continue
  name=$(basename "$f")
  if grep -q "GSTACK-AUTO AUTONOMOUS PHASE" "$f"; then
    pass "$name has autonomy marker"
  else
    fail "$name missing 'GSTACK-AUTO AUTONOMOUS PHASE' marker"
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

# Adversarial placeholder phases must indicate orchestrator ownership
ADVERSARIAL_PHASES="02-adversarial-ceo 04-adversarial-eng 06-adversarial-design 08-adversarial-final"
for phase in $ADVERSARIAL_PHASES; do
  f="$PHASES_DIR/${phase}.md"
  [ ! -f "$f" ] && continue
  name=$(basename "$f")
  if grep -qi "orchestrator" "$f"; then
    pass "$name references orchestrator"
  else
    fail "$name missing orchestrator reference"
  fi
done
echo ""

# --- Forbidden skill invocations ---
echo "Namespace isolation (no /skill invocations):"
FORBIDDEN_PATTERNS='invoke /review\|invoke /ship\|invoke /qa\|invoke /retro\|invoke /plan-ceo\|invoke /plan-eng\|run /review\|run /ship\|run /qa\|run /retro\|use /review\|use /ship\|use /qa'
for phase in $AGENT_PHASES; do
  f="$PHASES_DIR/${phase}.md"
  [ ! -f "$f" ] && continue
  name=$(basename "$f")
  if grep -qi "$FORBIDDEN_PATTERNS" "$f" 2>/dev/null; then
    fail "$name contains forbidden skill invocation pattern"
  else
    pass "$name clean (no skill invocations)"
  fi
done
echo ""

# --- Template variables ---
echo "Template variables (v2):"
# Phase 01 must have all core variables
found01="$PHASES_DIR/01-plan-ceo.md"
if [ -f "$found01" ]; then
  for var in '{MODE}' '{EXISTING_CODE_SUMMARY}' '{STYLE_PRINCIPLES}' '{STYLE_NAME}' '{DESIGN_STYLE_NAME}' '{DESIGN_STYLE_PRINCIPLES}' '{PRODUCT_SPEC}' '{RUN_ID}' '{ROUND_RETROSPECTIVE}' '{ENV_VARS}' '{PHASE_ARTIFACTS}'; do
    if grep -q "$var" "$found01"; then
      pass "Phase 01 has $var"
    else
      fail "Phase 01 missing $var"
    fi
  done
fi

# Phase 09 (implement) must have adversarial findings and follow-up answers
found09="$PHASES_DIR/09-implement.md"
if [ -f "$found09" ]; then
  for var in '{ADVERSARIAL_FINDINGS}' '{FOLLOW_UP_ANSWERS}' '{STYLE_PRINCIPLES}' '{ENV_VARS}'; do
    if grep -q "$var" "$found09"; then
      pass "Phase 09 has $var"
    else
      fail "Phase 09 missing $var"
    fi
  done
fi

# Phase 13 (retro-score) must reference v2 phase artifact paths
found13="$PHASES_DIR/13-retro-score.md"
if [ -f "$found13" ]; then
  if grep -q 'phase-01-plan-ceo' "$found13"; then
    pass "Phase 13 references v2 artifact paths"
  else
    fail "Phase 13 uses stale v1 artifact paths"
  fi
  if grep -q 'test_count' "$found13"; then
    pass "Phase 13 has test_count in scoring"
  else
    fail "Phase 13 missing test_count"
  fi
fi
echo ""

# --- Follow-up question support ---
echo "Follow-up question support:"
for phase in 01-plan-ceo 03-plan-eng 07-plan-eng-v2 09-implement 11-qa; do
  f="$PHASES_DIR/${phase}.md"
  [ ! -f "$f" ] && continue
  if grep -q 'pending-questions' "$f"; then
    pass "$phase has follow-up question support"
  else
    fail "$phase missing pending-questions reference"
  fi
done
echo ""

# --- Design DNA ---
echo "Design DNA (v2):"
if [ -f "$found01" ] && grep -q 'Design Intent' "$found01"; then
  pass "Phase 01 has Design Intent section"
else
  fail "Phase 01 missing Design Intent section"
fi
if [ -f "$found01" ] && grep -q 'Design Style Selected' "$found01"; then
  pass "Phase 01 has Design Style Selected output"
else
  fail "Phase 01 missing Design Style Selected output"
fi

found05="$PHASES_DIR/05-plan-design.md"
if [ -f "$found05" ]; then
  if grep -q '{DESIGN_STYLE_NAME}' "$found05"; then
    pass "Phase 05 has {DESIGN_STYLE_NAME}"
  else
    fail "Phase 05 missing {DESIGN_STYLE_NAME}"
  fi
  if grep -q '{DESIGN_STYLE_PRINCIPLES}' "$found05"; then
    pass "Phase 05 has {DESIGN_STYLE_PRINCIPLES}"
  else
    fail "Phase 05 missing {DESIGN_STYLE_PRINCIPLES}"
  fi
fi
echo ""

# --- Config validation (v2) ---
echo "Config validation (v2):"
for field in parallel_runs rounds auto_accept_winner style max_fix_cycles design_review design_style adversarial_reviews follow_up_budget; do
  if grep -q "${field}:" "pipeline/config.yml"; then
    pass "config.yml has $field"
  else
    fail "config.yml missing $field"
  fi
done

# Verify adversarial_reviews is a list
if grep -q 'adversarial_reviews:' "pipeline/config.yml"; then
  pass "adversarial_reviews is configured"
else
  fail "adversarial_reviews is not configured"
fi
echo ""

# --- Dead code removed ---
echo "Dead code cleanup:"
if [ -f "pipeline/gen-phases.mjs" ]; then
  fail "gen-phases.mjs still exists (should be deleted in v2)"
else
  pass "gen-phases.mjs deleted"
fi
if [ -f "pipeline/phase-config.json" ]; then
  fail "phase-config.json still exists (should be deleted in v2)"
else
  pass "phase-config.json deleted"
fi
echo ""

# --- Supporting files ---
echo "Supporting files:"
for f in "pipeline/config.yml" "pipeline/scoring/rubric.md" "templates/email-report.md" "CLAUDE.md"; do
  if [ -f "$f" ] && [ -s "$f" ]; then
    pass "$f exists and is non-empty"
  else
    fail "$f missing or empty"
  fi
done

# Design doc OR product-spec.md should exist (at least one entry point)
if [ -f "product-spec.md" ] || ls ~/.gstack/projects/*/joshuagoldbard-*-design-*.md >/dev/null 2>&1; then
  pass "At least one entry point exists (design doc or product-spec.md)"
else
  fail "No entry point found (need design doc or product-spec.md)"
fi
echo ""

# --- CLAUDE.md v2 content ---
echo "CLAUDE.md v2 content:"
if grep -q 'gstack-auto' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md uses 'gstack-auto' branding"
else
  fail "CLAUDE.md missing 'gstack-auto' branding"
fi
if grep -q 'adversarial' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md has adversarial review logic"
else
  fail "CLAUDE.md missing adversarial review logic"
fi
if grep -q 'ROUND_RETROSPECTIVE' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md has ROUND_RETROSPECTIVE"
else
  fail "CLAUDE.md missing ROUND_RETROSPECTIVE"
fi
if grep -q 'follow_up_budget\|pending-questions\|FOLLOW_UP_ANSWERS' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md has follow-up question system"
else
  fail "CLAUDE.md missing follow-up question system"
fi
if grep -q 'design.*doc\|design-\*\.md\|gstack-slug' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md has design doc discovery"
else
  fail "CLAUDE.md missing design doc discovery"
fi
# Safe winner copy (no bare rm -rf output/ without temp dir)
if grep -q 'mktemp\|TEMP_OUTPUT\|atomic' CLAUDE.md 2>/dev/null; then
  pass "CLAUDE.md uses safe winner copy (temp dir)"
else
  fail "CLAUDE.md uses unsafe rm -rf output/ pattern"
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

# --- Style profiles ---
echo "Style profiles:"
STYLES_DIR="pipeline/styles"
for style in carmack antirez abramov metz holowaychuk majors marlinspike; do
  sf="$STYLES_DIR/${style}.md"
  if [ -f "$sf" ] && [ -s "$sf" ]; then
    pass "${style}.md exists"
  else
    fail "${style}.md missing or empty"
  fi
done

DESIGN_STYLES_DIR="pipeline/design-styles"
for ds in dieter-rams brutalist playful; do
  dsf="$DESIGN_STYLES_DIR/${ds}.md"
  if [ -f "$dsf" ] && [ -s "$dsf" ]; then
    pass "${ds}.md exists"
  else
    fail "${ds}.md missing or empty"
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
echo ""

# --- Email configuration ---
echo "Email configuration:"
if grep -q "^email:" "pipeline/config.yml"; then
  pass "config.yml has email section"
else
  fail "config.yml missing email section"
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
echo ""

# --- Winner selection (mock score.json) ---
echo "Winner selection logic:"
TMPSCORES=$(mktemp -d)
mkdir -p "$TMPSCORES/run-a" "$TMPSCORES/run-b" "$TMPSCORES/run-c"
echo '{"average": 6.2, "bugs_remaining": 0, "fix_cycles_used": 1}' > "$TMPSCORES/run-a/score.json"
echo '{"average": 7.6, "bugs_remaining": 0, "fix_cycles_used": 1}' > "$TMPSCORES/run-b/score.json"
echo '{"average": 7.1, "bugs_remaining": 1, "fix_cycles_used": 2}' > "$TMPSCORES/run-c/score.json"

WINNER=$(python3 -c "
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
  pass "Tie-breaking by bugs_remaining (run-b: 0 bugs wins)"
else
  fail "Tie-breaking expected run-b, got: $WINNER2"
fi

# Test partial failure: only 1 of 3 runs has valid score
rm -f "$TMPSCORES/run-a/score.json" "$TMPSCORES/run-c/score.json"
WINNER3=$(python3 -c "
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
print(runs[0][3] if runs else 'NO_WINNER')
" 2>/dev/null)

if [ "$WINNER3" = "run-b" ]; then
  pass "Partial failure: selects from available runs (run-b)"
else
  fail "Partial failure: expected run-b, got: $WINNER3"
fi
rm -rf "$TMPSCORES"
echo ""

# --- Browse binary ---
echo "Browse binary:"
if [ -x ~/.claude/skills/gstack/browse/dist/browse ] || [ -x .claude/skills/gstack/browse/dist/browse ]; then
  pass "Browse binary accessible"
else
  fail "Browse binary not found (QA phase will skip screenshots)"
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

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/")
  [ "$code" = "200" ] && pass "GET / returns 200" || fail "GET / returned $code"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/style.css")
  [ "$code" = "200" ] && pass "GET /style.css returns 200" || fail "GET /style.css returned $code"

  body=$(curl -s "$BASE/results")
  if echo "$body" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    pass "GET /results returns valid JSON"
  else
    fail "GET /results returned invalid JSON"
  fi

  code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE/output/../../.env")
  [ "$code" = "403" ] || [ "$code" = "404" ] && pass "Path traversal blocked ($code)" || fail "Path traversal NOT blocked ($code)"

  # Config endpoint should include v2 fields
  cfg_body=$(curl -s "$BASE/current-config")
  for field in parallel_runs rounds; do
    if echo "$cfg_body" | python3 -c "import sys,json; d=json.load(sys.stdin); assert '$field' in d" 2>/dev/null; then
      pass "GET /current-config includes $field"
    else
      fail "GET /current-config missing $field"
    fi
  done
fi

if [ -n "$SERVER_PID" ]; then kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null || true; fi
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
