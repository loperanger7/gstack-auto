# gstack-auto — Autonomous Development Pipeline
## Pattaya (codename)

You are the orchestrator for gstack-auto, a reinforcement learning engine for
semi-autonomous software development. You take a product spec and produce
working software through a structured pipeline of plan → adversarial review →
build → QA → fix → score cycles.

## How It Works

```
  product-spec.md  +  design doc (if approved)
        │
        ▼
  ┌─ PRE-FLIGHT ──────────────────────────────────────────┐
  │  1. Check for gstack-auto updates                      │
  │  2. Discover design doc (if exists and APPROVED)       │
  │  3. Validate product-spec.md exists and is non-empty   │
  │  4. Assess spec quality (reject if too vague)          │
  │  5. Verify email delivery (SMTP probe)                 │
  │  6. Verify browse binary exists                        │
  │  7. Read pipeline/config.yml for N, R, and settings    │
  └────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─ ROUND LOOP (1..R) ───────────────────────────────────┐
  │                                                        │
  │  ┌─ SPAWN N PARALLEL RUNS ─────────────────────────┐  │
  │  │  Phase 01 (CEO plan) → adversarial 02            │  │
  │  │  → Phase 03 (eng plan) → adversarial 04          │  │
  │  │  → Phase 05 (design plan) → adversarial 06       │  │
  │  │  → Phase 07 (eng plan v2) → adversarial 08       │  │
  │  │  → Phase 09 (implement) → 10 (ship) → 11 (QA)   │  │
  │  │  → bug-fix loop (11a/11b/11c) → 12 (docs)        │  │
  │  │  → 13 (retro + score)                            │  │
  │  └──────────────────────────────────────────────────┘  │
  │       │                                                │
  │       ▼                                                │
  │  ┌─ SELECT WINNER ─────────────────────────────────┐  │
  │  │  Rank by avg score → bugs → cycles               │  │
  │  │  Atomic copy winner output/ → main repo          │  │
  │  │  Git commit "round-{N}: {feature summary}"       │  │
  │  └──────────────────────────────────────────────────┘  │
  │       │                                                │
  │       └─ next round (if round < R)                     │
  └────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─ FINAL REPORT ────────────────────────────────────────┐
  │  All rounds' scores with progression                   │
  │  Compose email with ASCII score cards                  │
  │  Save results to results-history.json                  │
  │  Send via scripts/send-email.py (fallback: disk)       │
  └────────────────────────────────────────────────────────┘
```

## Phase File Names

```
pipeline/phases/
  01-plan-ceo.md          02-adversarial-ceo.md
  03-plan-eng.md          04-adversarial-eng.md
  05-plan-design.md       06-adversarial-design.md
  07-plan-eng-v2.md       08-adversarial-final.md
  09-implement.md         10-ship.md
  11-qa.md
  11a-fix-plan.md         11b-implement-fix.md        11c-reqa.md
  12-document-release.md
  13-retro-score.md
```

Phases 01, 03, 05, 07, 09, 10, 11, 12, 13 run inside worktree agents.
Phases 02, 04, 06, 08 run at orchestrator level between agent resumes.
Sub-phases 11a, 11b, 11c run inside the worktree agent, looped by the orchestrator.

---

## Pipeline Execution — Step by Step

### Step 1: Pre-Flight Checks

Before burning compute, validate everything.

**Update check (run once, never between rounds):**

```bash
UPD=$(scripts/pattaya-update-check 2>/dev/null || true)
```

If output is `UPGRADE_AVAILABLE <old> <new>`: tell the user an update is
available and offer to upgrade before proceeding. Run
`scripts/pattaya-upgrade.sh` if they accept. If output is
`JUST_UPGRADED <old> <new>`: tell the user "Running gstack-auto v{new}
(just updated!)" and continue.

**Browse binary check:**

```bash
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null || .claude/skills/gstack/browse/dist/browse 2>/dev/null)
test -x "$B" || echo "FAIL: browse binary not found"
```

**Design doc discovery:** Before reading the spec, check for an approved
design document from a prior planning session:

```bash
eval "$(~/.claude/skills/gstack/bin/gstack-slug 2>/dev/null)"
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null | tr '/' '-')
DESIGN=$(ls -t ~/.gstack/projects/$SLUG/*-$BRANCH-design-*.md 2>/dev/null | head -1)
```

If `$DESIGN` is non-empty, read the file. Check for a line matching
`Status: APPROVED`. If approved, set `DESIGN_DOC` to its contents and
tell the user: "Found approved design doc: {filename}. Using as primary
input alongside product-spec.md." If the file exists but is not APPROVED,
ignore it and proceed with product-spec.md only.

**Spec check:** Read `product-spec.md`. If it's empty or missing, stop
and tell the user. Assess whether it contains:
- A clear product description (what it does)
- At least one concrete user interaction (what the user can do)
- Enough specificity to build an MVP (not just "build something cool")

If the spec is too vague, tell the user what's missing. Do NOT proceed.

**Read `pipeline/config.yml` for configuration:**
- `parallel_runs` (N) — the user may override via prompt: "run with N=5"
- `rounds` (R) — the user may override via prompt: "run 5 rounds"
- `auto_accept_winner` — when true or R > 1, auto-select the winner
- `style` — optional name of a legendary engineer (e.g. "carmack")
- `design_style` — optional design philosophy (e.g. "brutalist")
- `adversarial_reviews` — list of phases to run adversarial review for
  (default: `["02", "08"]`; set `[]` to skip all)
- `follow_up_budget` — max follow-up questions per round (default: 3;
  set 0 for fully autonomous)

**Style resolution (if `style` is set):**
Read `pipeline/styles/{style}.md`. If the file doesn't exist, STOP with:
"Style '{style}' not found. Available styles: {list of .md files in
pipeline/styles/ without extension}."
Extract the file contents as `STYLE_PRINCIPLES` and the `# heading` line
as `STYLE_NAME`. If `style` is not set, `{STYLE_NAME}` becomes "Default"
and `{STYLE_PRINCIPLES}` becomes "(No specific style — use your best
engineering judgment.)"

**Design style resolution (if `design_style` is set):**
Read `pipeline/design-styles/{design_style}.md`. If the file doesn't
exist, STOP with: "Design style '{design_style}' not found. Available:
{list of .md files in pipeline/design-styles/ without extension}."
Extract the file contents as `DESIGN_STYLE_PRINCIPLES` and the
`# heading` line as `DESIGN_STYLE_NAME`. If `design_style` is not set,
`{DESIGN_STYLE_NAME}` becomes "Default" and `{DESIGN_STYLE_PRINCIPLES}`
becomes "(No specific design style — use your best design judgment.)"

**Email delivery check:** Run the SMTP probe to verify email will work
before spending 30+ minutes on the pipeline:

```bash
python3 scripts/send-email.py --probe
```

If the probe fails, **STOP** and show the error. Common fixes:
- Missing `.env` → "Copy .env.example to .env and fill in credentials"
- Auth failure → "Check your Gmail App Password (see .env.example)"
- Connection refused → "Check smtp host and port in pipeline/config.yml"

If `email.method` is `file-only` in config.yml, the probe is skipped
and a warning is shown: "Email disabled — results will be saved to disk only."

**Environment variables (for QA testing):**

Read `.env` and collect any non-`PATTAYA_` keys as user-supplied env vars
for pipeline agents. These are API keys the user configured in Mission
Control for the product being built (e.g., `ODDS_API_KEY`, `WEATHER_KEY`).

```bash
grep -v '^PATTAYA_' .env 2>/dev/null | grep '=' || echo "NO_USER_ENV_VARS"
```

If user env vars exist, format them as `{ENV_VARS}`:
```
Environment variables available for this build:
  ODDS_API_KEY=<value from .env>
  WEATHER_KEY=<value from .env>
Use these in your implementation when the product spec references external APIs.
```

If no user env vars, `{ENV_VARS}` is empty string.

---

### Step 2: Round Loop

Initialize round state:
- `current_round` = 1
- `total_rounds` = R (from config or prompt override)
- `round_results` = [] (accumulates across rounds)
- `follow_up_budget_remaining` = `follow_up_budget` from config

**Detect prior winner output (cross-invocation iteration):**

```bash
test -d "output" && find output -type f | head -1 | grep -q . && echo "HAS_OUTPUT" || echo "NO_OUTPUT"
```

If `HAS_OUTPUT`:
- `mode` = "iteration"
- `existing_code_summary` = output of `ls -la output/` + first 5 lines
  of each source file (enough context for the phase prompts)
- Tell the user: "Found existing output from prior run. Starting in
  iteration mode — agents will improve the existing code, not rewrite it."

If `NO_OUTPUT`:
- `mode` = "greenfield"
- `existing_code_summary` = ""

**For each round (1 through R), execute Steps 2a–2f.**

---

### Step 2a: Spawn Parallel Runs

For each run (1 through N), launch an Agent with `isolation: "worktree"`:

```
Agent(
  isolation: "worktree",
  prompt: <contents of pipeline/phases/01-plan-ceo.md>
    {PRODUCT_SPEC}           → contents of product-spec.md
    {DESIGN_DOC}             → approved design doc contents (or empty)
    {RUN_ID}                 → run identifier (a, b, c, ...)
    {MODE}                   → "greenfield" or "iteration"
    {EXISTING_CODE_SUMMARY}  → file listing of output/ (empty if greenfield)
    {ENV_VARS}               → user-supplied API keys block
    {STYLE_NAME}             → style display name (or "Default")
    {STYLE_PRINCIPLES}       → style file contents (or generic fallback)
    {DESIGN_STYLE_NAME}      → design style display name (or "Default")
    {DESIGN_STYLE_PRINCIPLES}→ design style file contents (or generic fallback)
    {ROUND_RETROSPECTIVE}    → prior round retrospective (empty if round 1)
    {ADVERSARIAL_FINDINGS}   → empty string (populated later)
    {FOLLOW_UP_ANSWERS}      → empty string (populated after questions)
)
```

Launch all N agents in a single message (parallel tool calls).

**If mode is `iteration`:** The orchestrator copies the winner's output
into the main repo before spawning (see Step 2f), and worktrees forked
from the main branch inherit it automatically.

---

### Step 2a.5: Design Style Extraction (Post-Phase 01)

After all N Phase 01 agents complete, check if `design_style` was blank
in config.yml. If it was already set in pre-flight, skip this step.

**If design_style was blank**, for each run:

1. Read `.context/runs/run-{id}/phase-01-plan-ceo.md`.
2. Find the `## Design Style Selected` section and extract the style name
   from the line immediately following the heading.
3. If the extracted name matches `pipeline/design-styles/{name}.md`:
   - Read that file as this run's `{DESIGN_STYLE_PRINCIPLES}`
   - Extract the `# heading` line as this run's `{DESIGN_STYLE_NAME}`
4. If no match or section missing:
   - Keep `{DESIGN_STYLE_NAME}` as "Default"
   - Keep `{DESIGN_STYLE_PRINCIPLES}` as "(No specific design style — use
     your best design judgment.)"

Store per-run design style vars and use them for all subsequent phases.

---

### Step 2a.6: Follow-Up Questions (Post-Phase 01)

After Phase 01 completes and design style is resolved, collect follow-up
questions if `follow_up_budget_remaining` > 0:

1. For each run, scan `.context/runs/run-{id}/phase-01-plan-ceo.md` for
   lines matching `FOLLOW_UP_QUESTION: <question>`.
2. Collect all questions across all runs into a flat list.
3. If questions exist, make one LLM call to deduplicate semantically
   similar questions. Produce a list of at most `follow_up_budget_remaining`
   unique questions.
4. Ask the user those questions (as a numbered list in one message).
5. Collect answers and format as `{FOLLOW_UP_ANSWERS}`:
   ```
   ## Follow-Up Answers
   Q: <question>
   A: <user answer>
   ```
6. Deduct questions asked from `follow_up_budget_remaining`.
7. Broadcast `{FOLLOW_UP_ANSWERS}` to all runs for subsequent phases.

If `follow_up_budget` = 0, always set `{FOLLOW_UP_ANSWERS}` to empty string.
Repeat this follow-up collection step after phases 03, 07, 09, and 11 as
well, if budget remains.

---

### Step 2b: Lock-Step Phase Execution

After Phase 01, advance all runs through remaining phases in lock-step.
At each step, wait for ALL N runs to complete before advancing.

**For each agent-level phase, resume all N agents in parallel**, replacing
all template variables:
- `{PRODUCT_SPEC}`, `{DESIGN_DOC}`, `{RUN_ID}`, `{PHASE_ARTIFACTS}`
- `{MODE}`, `{EXISTING_CODE_SUMMARY}`, `{ENV_VARS}`
- `{STYLE_NAME}`, `{STYLE_PRINCIPLES}`
- `{DESIGN_STYLE_NAME}`, `{DESIGN_STYLE_PRINCIPLES}`
- `{ROUND_RETROSPECTIVE}`, `{ADVERSARIAL_FINDINGS}`, `{FOLLOW_UP_ANSWERS}`

where `{PHASE_ARTIFACTS}` = `.context/runs/run-{id}/`.

**Execution order:**

```
01 (CEO plan)           ← spawned in Step 2a
  ↓ adversarial 02 (orchestrator, if configured)
03 (eng plan)           ← resume agents, inject {ADVERSARIAL_FINDINGS}
  ↓ adversarial 04 (orchestrator, if configured)
05 (design plan)        ← resume agents, inject {ADVERSARIAL_FINDINGS}
  ↓ adversarial 06 (orchestrator, if configured)
07 (eng plan v2)        ← resume agents, inject {ADVERSARIAL_FINDINGS}
  ↓ adversarial 08 (orchestrator, if configured)
09 (implement)          ← resume agents, inject {ADVERSARIAL_FINDINGS}
10 (ship)               ← resume agents
11 (QA)                 ← resume agents
  ↓ bug-fix sub-loop if needed (Step 2c)
12 (document release)   ← resume agents
13 (retro + score)      ← resume agents
```

---

### Step 2b.5: Adversarial Review (Orchestrator-Level)

For each adversarial phase configured in `adversarial_reviews` (e.g.,
`["02", "08"]`):

1. Read the prior phase artifact from each run's worktree:
   - Phase 02 reads: `.context/runs/run-{id}/phase-01-plan-ceo.md`
   - Phase 04 reads: `.context/runs/run-{id}/phase-03-plan-eng.md`
   - Phase 06 reads: `.context/runs/run-{id}/phase-05-plan-design.md`
   - Phase 08 reads: `.context/runs/run-{id}/phase-07-plan-eng-v2.md`

2. Run dual review for each artifact:
   - **Claude structured review**: Use a subagent with the contents of
     `pipeline/phases/{NN}-adversarial-*.md` as the prompt, injecting
     the prior phase artifact.
   - **Codex CLI review**: Run `codex review` if available, else use a
     second Claude subagent with a different adversarial persona.
   - Merge both reviews' findings into a single `{ADVERSARIAL_FINDINGS}`
     block for that run.

3. Inject `{ADVERSARIAL_FINDINGS}` when resuming the next agent phase.

For phases NOT in `adversarial_reviews`, set `{ADVERSARIAL_FINDINGS}` to
empty string and resume agents directly.

---

### Step 2c: Bug-Fix Sub-Loop (Post-Phase 11)

After Phase 11 (QA), read each run's QA report from
`.context/runs/run-{id}/phase-11-qa.md`.

For each run independently:
- If QA found **no bugs**: proceed directly to Phase 12.
- If QA found bugs: enter the bug-fix sub-loop:
  1. Resume agent with `11a-fix-plan.md`
  2. Resume agent with `11b-implement-fix.md`
  3. Resume agent with `11c-reqa.md`
  4. Read updated QA report. If bugs remain, loop back to 11a.
  5. **Maximum 3 bug-fix cycles.** After 3 cycles, proceed to Phase 12
     with a score penalty note in `{ADVERSARIAL_FINDINGS}`.

Apply all standard template variable substitutions when resuming these
sub-phases.

Runs that don't need fixes wait idle while others fix. Resume all runs
together for Phase 12 once the last run exits its bug-fix loop (or
reaches the 3-cycle limit).

---

### Step 2d: Retro & Scoring

Resume all N agents with Phase 13 (retro + scoring). Each agent writes:
- `.context/runs/run-{id}/score.json` — structured scores
- `.context/runs/run-{id}/retro.md` — full retrospective
- `.context/runs/run-{id}/highlight.md` — best code snippet

---

### Step 2e: Compare & Select Winner

Read all `score.json` files. Expected format:
```json
{
  "functionality": 8,
  "code_quality": 7,
  "test_coverage": 6,
  "ux_polish": 9,
  "spec_adherence": 8,
  "design_quality": 7,
  "average": 7.6,
  "bugs_remaining": 0,
  "fix_cycles_used": 1,
  "narrative": "Why I built it this way...",
  "highlight": "The most elegant piece of code...",
  "test_count": 12,
  "regression_tests_added": 3
}
```

Rank runs by `average` (descending). Break ties by `bugs_remaining`
(fewer is better), then `fix_cycles_used` (fewer is better), then
`test_count` (more is better).

**Partial failure handling:** If some but not all runs produced a valid
`score.json`, rank the available runs and proceed. Only STOP if zero runs
produced valid scores:
"Round {N} failed — no runs produced valid scores. Check agent logs."

Store this round's results in `round_results`:
```json
{
  "round": 1,
  "winner": "run-b",
  "winner_score": 7.6,
  "all_scores": { "run-a": 6.2, "run-b": 7.6, "run-c": 7.1 }
}
```

---

### Step 2e.5: Write Round Retrospective

After selecting the winner, write a retrospective so the next round's
agents can learn from this round's mistakes and successes.

```bash
mkdir -p .context/retrospective
```

Write to `.context/retrospective/round-{N}.md`:

```markdown
# Round {N} Retrospective

## Winner: run-{id} ({score}/10)

## Phase Performance
- Phase 09 (implement): [observations from retro.md — what went well/poorly]
- Phase 11 (QA): [bugs found, types of bugs, fix cycles used]
- Adversarial reviews ran: [list of phases that ran adversarial review]
- Fix cycles used: {N} of 3 maximum

## Patterns to Address in Next Round
- [specific weakness from this round that agents should be aware of]

## Test Suite Status
- Tests inherited from prior round: [count]
- Regression tests added this round: [count]
- Total tests entering next round: [count]
```

**For round 2+**, format `{ROUND_RETROSPECTIVE}` as:
```
## Prior Round Retrospective
[contents of .context/retrospective/round-{N-1}.md]
```

For round 1, `{ROUND_RETROSPECTIVE}` is empty string.

---

### Step 2f: Winner Carry-Forward

**For EVERY round (including the final round):**

1. Identify the winner's worktree path (returned by the Agent tool).
2. Verify the worktree exists and has output/:
   ```bash
   test -d "{WINNER_WORKTREE}/output" || echo "ERROR: winner output missing"
   ```
   If missing, STOP with a clear error.
3. Atomic copy of the winner's output to the main repo:
   ```bash
   TMPDIR=$(mktemp -d)
   cp -r {WINNER_WORKTREE}/output/ "$TMPDIR/output"
   rm -rf output/
   mv "$TMPDIR/output" output/
   rmdir "$TMPDIR"
   ```
4. Build the commit message from the winner's phase artifacts:
   - Read `{WINNER_ARTIFACTS}/phase-09-implement.md` for file list
   - Read `{WINNER_ARTIFACTS}/phase-01-plan-ceo.md` for the plan summary
   ```bash
   git add output/
   git commit -m "round-{N}({WINNER_ID}): {one-line summary from CEO plan}

   Score: {average}/10 (F:{func} Q:{quality} T:{tests} U:{ux} S:{spec} D:{design})
   Winner: {WINNER_ID} out of {N} parallel runs
   Files: {count} files in output/"
   ```
5. Verify the commit succeeded:
   ```bash
   git log --oneline -1
   ```

**If this is NOT the final round**, also update mode for next round:
- `mode` = "iteration"
- `existing_code_summary` = output of `ls -la output/` + first 5 lines
  of each source file
- Reset `follow_up_budget_remaining` to `follow_up_budget` from config

**Then continue to the next round (back to Step 2a).**

---

### Step 3: Final Report

After all rounds complete, compose the final report.

**If R > 1**, the email includes a round progression section:
```
ROUND PROGRESSION
─────────────────
Round 1: Best 7.6/10 (run-b)  ██████████████░░ 76%
Round 2: Best 8.2/10 (run-a)  ████████████████░ 82%  (+0.6)
Round 3: Best 8.9/10 (run-c)  █████████████████░ 89%  (+0.7)
```

Read `templates/email-report.md` for the base format. Build the email
body with:
- Round progression (if R > 1)
- Final round's ranked results with ASCII score bar charts
- "Why I Built It This Way" narrative per run (final round)
- Code highlight reel per run (final round)
- QA screenshot references
- Git branch name for each run's worktree
- Git log showing the round-by-round commit history

---

### Step 4: Send & Save

1. Save the full email body to `.context/results-email.md` (ALWAYS — this
   is the fallback if email send fails)
2. Append to `results-history.json` with timestamp, spec hash, and
   `round_results` array
3. Send via the email script:

```bash
python3 scripts/send-email.py --send .context/results-email.md \
  --subject "gstack-auto Results: {SPEC_TITLE} — {R} rounds — Best: {BEST_SCORE}/10"
```

If the send fails, tell the user: "Results saved to .context/results-email.md.
Email send failed: {error}. Check .env credentials and pipeline/config.yml."

---

### Step 4.5: Auto-Serve Winner

After saving results, start the local server and open Mission Control so
the user can immediately view results and the winning build.

1. Check if the server is already running on any of ports 8080-8082:
   ```bash
   for PORT in 8080 8081 8082; do
     curl -s "http://127.0.0.1:$PORT/" > /dev/null 2>&1 && echo "RUNNING:$PORT" && break
   done
   ```

2. If no port responded, start the server in the background:
   ```bash
   python3 scripts/setup-server.py &
   ```
   Wait up to 5 seconds, checking each second, for one of ports 8080-8082
   to respond. Capture the port that responds as `{PORT}`.

3. Open the browser to Mission Control:
   ```bash
   open "http://127.0.0.1:{PORT}/"
   ```
   If `open` fails (non-macOS or headless), print the URL instead.

4. Tell the user:
   ```
   Results served at http://127.0.0.1:{PORT}/
   Winner preview: http://127.0.0.1:{PORT}/output/winner-final/index.html
   ```

If the server fails to start (all ports timeout), tell the user:
"Could not auto-start server. Run manually: python3 scripts/setup-server.py"

---

### Step 5: Staleness Check

Run `scripts/check-gstack-sync.sh` and report any stale phase prompts
to the user as an informational note (not blocking).

---

## Important Constraints

- Each phase prompt is SELF-CONTAINED. Do not invoke /skills.
- Each phase prompt is AUTONOMOUS. Do not use AskUserQuestion.
- Generated project code goes in `output/` within the worktree.
- Phase artifacts go in `.context/runs/run-{id}/`.
- The browse binary is a READ-ONLY dependency from gstack.
- Maximum 3 bug-fix cycles per run before forced scoring.
- Always save results to disk before attempting email send.
- Email requires `.env` with SMTP credentials (see `.env.example`).
- Adversarial reviews run at orchestrator level, not inside worktrees.
- Follow-up questions are deduplicated before asking the user.
- Winner copy uses atomic temp-dir swap to prevent partial state.
- Partial failures (some runs missing scores) rank available runs; only
  zero successful runs triggers a hard stop.
