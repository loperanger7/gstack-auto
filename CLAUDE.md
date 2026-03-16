# Pattaya — Autonomous Development Pipeline

You are the orchestrator for Pattaya, a reinforcement learning engine for
semi-autonomous software development. You take a product spec and produce
working software through a structured pipeline of plan → build → review →
QA → fix → score cycles.

## How It Works

```
  product-spec.md
        │
        ▼
  ┌─ PRE-FLIGHT ──────────────────────────────────────────┐
  │  1. Check for gstack-auto updates                      │
  │  2. Validate product-spec.md exists and is non-empty   │
  │  3. Assess spec quality (reject if too vague)          │
  │  4. Verify email delivery (SMTP probe)                 │
  │  5. Verify browse binary exists                        │
  │  6. Read pipeline/config.yml for N, R, and settings    │
  └────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─ ROUND LOOP (1..R) ───────────────────────────────────┐
  │                                                        │
  │  ┌─ SPAWN N PARALLEL RUNS ─────────────────────────┐  │
  │  │  For each run (a, b, c, ...):                    │  │
  │  │    Agent(isolation: "worktree", run_in_background)│  │
  │  │    {MODE} = greenfield (round 1) | iteration (2+)│  │
  │  │                                                  │  │
  │  │  All runs execute in lock-step:                  │  │
  │  │    Phase 1-6 → bug-fix divergence → Phase 12     │  │
  │  └──────────────────────────────────────────────────┘  │
  │       │                                                │
  │       ▼                                                │
  │  ┌─ SELECT WINNER ─────────────────────────────────┐  │
  │  │  Rank by avg score → bugs → cycles               │  │
  │  │  Copy winner output/ → main repo                 │  │
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

Read `product-spec.md`. If it's empty or missing, stop and tell the user.

**Spec quality check:** Read the spec and assess whether it contains:
- A clear product description (what it does)
- At least one concrete user interaction (what the user can do)
- Enough specificity to build an MVP (not just "build something cool")

If the spec is too vague, tell the user what's missing. Do NOT proceed.

Read `pipeline/config.yml` for configuration:
- `parallel_runs` (N) — the user may override via prompt: "run with N=5"
- `rounds` (R) — the user may override via prompt: "run 5 rounds"
- `auto_accept_winner` — when true or R > 1, auto-select the winner
- `style` — optional name of a legendary engineer (e.g. "carmack")

**Style resolution (if `style` is set):**
Read `pipeline/styles/{style}.md`. If the file doesn't exist, STOP with:
"Style '{style}' not found. Available styles: {list of .md files in
pipeline/styles/ without extension}."
Extract the file contents as `STYLE_PRINCIPLES` and the `# heading` line
as `STYLE_NAME`. If `style` is not set, `{STYLE_NAME}` becomes "Default"
and `{STYLE_PRINCIPLES}` becomes "(No specific style — use your best
engineering judgment.)"

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

### Step 2: Round Loop

Initialize round state:
- `current_round` = 1
- `total_rounds` = R (from config or prompt override)
- `mode` = "greenfield"
- `existing_code_summary` = "" (empty for round 1)
- `round_results` = [] (accumulates across rounds)

**For each round (1 through R), execute Steps 2a–2f:**

### Step 2a: Spawn Parallel Runs

For each run (1 through N), launch an Agent with `isolation: "worktree"`:

```
Agent(
  isolation: "worktree",
  prompt: <contents of pipeline/phases/01-plan-ceo.md>
          with {PRODUCT_SPEC} replaced by contents of product-spec.md
          and {RUN_ID} replaced by the run identifier (a, b, c, ...)
          and {MODE} replaced by current mode
          and {EXISTING_CODE_SUMMARY} replaced by summary of output/
)
```

Launch all N agents in a single message (parallel tool calls).

**If mode is `iteration`:** Before spawning, each agent's worktree must
contain the winner's code in `output/`. The orchestrator copies the
winner's output into the main repo before spawning (see Step 2f), and
worktrees forked from the main branch inherit it automatically.

### Step 2b: Resume Through Phases (Lock-Step)

After all N agents complete phase 1, resume ALL of them for phase 2:

```
For phase in [02, 03, 04, 05, 06]:
  Resume all N agents in parallel with the next phase prompt
  Wait for all to complete before advancing
```

Each phase prompt is in `pipeline/phases/{NN}-{name}.md`. Read the file
and pass its contents as the resume prompt. Replace template variables:
- `{PRODUCT_SPEC}` — contents of product-spec.md
- `{RUN_ID}` — the run identifier
- `{PHASE_ARTIFACTS}` — path to .context/runs/run-{id}/
- `{MODE}` — "greenfield" or "iteration"
- `{EXISTING_CODE_SUMMARY}` — file listing of output/ (empty if greenfield)
- `{STYLE_NAME}` — display name from style profile heading (or "Default")
- `{STYLE_PRINCIPLES}` — full contents of the style profile (or generic fallback)

### Step 2c: Bug-Fix Divergence

After phase 06 (QA), read each run's QA report from
`.context/runs/run-{id}/phase-06-qa.md`.

For each run:
- If QA found bugs: resume with phases 07 → 08 → 09 → 10 → 11
- If QA found no bugs: skip to phase 12

Bug-fix loop: after phase 11 (QA confirm), check again. If bugs remain,
loop back to phase 07. **Maximum 3 bug-fix cycles.** After 3 cycles,
proceed to phase 12 with a score penalty note.

Runs that don't need fixes wait idle while others fix.

### Step 2d: Retro & Scoring

Resume all N agents with phase 12 (retro + scoring). Each agent writes:
- `.context/runs/run-{id}/score.json` — structured scores
- `.context/runs/run-{id}/retro.md` — full retrospective
- `.context/runs/run-{id}/highlight.md` — best code snippet

### Step 2e: Compare & Select Winner

Read all `score.json` files. Expected format:
```json
{
  "functionality": 8,
  "code_quality": 7,
  "test_coverage": 6,
  "ux_polish": 9,
  "spec_adherence": 8,
  "average": 7.6,
  "bugs_remaining": 0,
  "fix_cycles_used": 1,
  "narrative": "Why I built it this way...",
  "highlight": "The most elegant piece of code..."
}
```

Rank runs by `average` score (descending). Break ties by `bugs_remaining`
(fewer is better), then `fix_cycles_used` (fewer is better).

**Error check:** If no run has a valid score.json, STOP and tell the user:
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

### Step 2f: Winner Carry-Forward

If this is NOT the final round:

1. Identify the winner's worktree path (returned by the Agent tool).
2. **Verify the worktree exists and has output/:**
   ```bash
   test -d "{WINNER_WORKTREE}/output" || echo "ERROR: winner output missing"
   ```
   If missing, STOP with a clear error.
3. Copy the winner's output to the main repo:
   ```bash
   rm -rf output/
   cp -r {WINNER_WORKTREE}/output/ output/
   ```
4. Build the commit message from the winner's phase artifacts:
   - Read `{WINNER_ARTIFACTS}/phase-03-implement.md` for file list
   - Read `{WINNER_ARTIFACTS}/phase-01-plan-ceo.md` for the plan summary
   ```bash
   git add output/
   git commit -m "round-{N}({WINNER_ID}): {one-line summary from CEO plan}

   Score: {average}/10 (F:{func} Q:{quality} T:{tests} U:{ux} S:{spec})
   Winner: {WINNER_ID} out of {N} parallel runs
   Files: {count} files in output/"
   ```
5. **Verify the commit succeeded:**
   ```bash
   git log --oneline -1
   ```
6. Update mode for next round:
   - `mode` = "iteration"
   - `existing_code_summary` = output of `ls -la output/` + first 5 lines
     of each source file (enough context for the phase prompts)

**Then continue to the next round (back to Step 2a).**

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

### Step 4: Send & Save

1. Save the full email body to `.context/results-email.md` (ALWAYS — this
   is the fallback if email send fails)
2. Append to `results-history.json` with timestamp, spec hash, and
   `round_results` array
3. Send via the email script:

```bash
python3 scripts/send-email.py --send .context/results-email.md \
  --subject "Pattaya Results: {SPEC_TITLE} — {R} rounds — Best: {BEST_SCORE}/10"
```

If the send fails, tell the user: "Results saved to .context/results-email.md.
Email send failed: {error}. Check .env credentials and pipeline/config.yml."

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
