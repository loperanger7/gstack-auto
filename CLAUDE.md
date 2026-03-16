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
  │  1. Validate product-spec.md exists and is non-empty   │
  │  2. Assess spec quality (reject if too vague)          │
  │  3. Verify email delivery (SMTP probe)                 │
  │  4. Verify browse binary exists                        │
  │  5. Read pipeline/config.yml for N and settings        │
  └────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─ SPAWN N PARALLEL RUNS ───────────────────────────────┐
  │  For each run (a, b, c, ...):                          │
  │    Agent(isolation: "worktree", run_in_background)      │
  │                                                        │
  │  All runs execute in lock-step:                        │
  │    Phase 1-6 together → bug-fix divergence → Phase 12  │
  └────────────────────────────────────────────────────────┘
        │
        ▼
  ┌─ COLLECT & COMPARE ───────────────────────────────────┐
  │  Read .context/runs/run-{id}/score.json from each      │
  │  Rank by average score                                 │
  │  Compose email with ASCII score cards                  │
  │  Save results to results-history.json                  │
  │  Send via scripts/send-email.py (fallback: disk)       │
  └────────────────────────────────────────────────────────┘
```

## Pipeline Execution — Step by Step

### Step 1: Pre-Flight Checks

Before burning compute, validate everything:

```bash
# Check browse binary
B=$(~/.claude/skills/gstack/browse/dist/browse 2>/dev/null || .claude/skills/gstack/browse/dist/browse 2>/dev/null)
test -x "$B" || echo "FAIL: browse binary not found"
```

Read `product-spec.md`. If it's empty or missing, stop and tell the user.

**Spec quality check:** Read the spec and assess whether it contains:
- A clear product description (what it does)
- At least one concrete user interaction (what the user can do)
- Enough specificity to build an MVP (not just "build something cool")

If the spec is too vague, tell the user what's missing. Do NOT proceed.

Read `pipeline/config.yml` for configuration. The user may override N
in their invocation prompt (e.g., "run with N=5").

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

### Step 2: Spawn Parallel Runs

For each run (1 through N), launch an Agent with `isolation: "worktree"`:

```
Agent(
  isolation: "worktree",
  prompt: <contents of pipeline/phases/01-plan-ceo.md>
          with {PRODUCT_SPEC} replaced by contents of product-spec.md
          and {RUN_ID} replaced by the run identifier (a, b, c, ...)
)
```

Launch all N agents in a single message (parallel tool calls).

### Step 3: Resume Through Phases (Lock-Step)

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

### Step 4: Bug-Fix Divergence

After phase 06 (QA), read each run's QA report from
`.context/runs/run-{id}/phase-06-qa.md`.

For each run:
- If QA found bugs: resume with phases 07 → 08 → 09 → 10 → 11
- If QA found no bugs: skip to phase 12

Bug-fix loop: after phase 11 (QA confirm), check again. If bugs remain,
loop back to phase 07. **Maximum 3 bug-fix cycles.** After 3 cycles,
proceed to phase 12 with a score penalty note.

Runs that don't need fixes wait idle while others fix.

### Step 5: Retro & Scoring

Resume all N agents with phase 12 (retro + scoring). Each agent writes:
- `.context/runs/run-{id}/score.json` — structured scores
- `.context/runs/run-{id}/retro.md` — full retrospective
- `.context/runs/run-{id}/highlight.md` — best code snippet

### Step 6: Compare & Report

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

### Step 7: Compose Email

Read `templates/email-report.md` for the format. Build the email body with:
- Ranked results with ASCII score bar charts
- "Why I Built It This Way" narrative per run
- Code highlight reel per run
- QA screenshot references
- Git branch name for each run's worktree

### Step 8: Send & Save

1. Save the full email body to `.context/results-email.md` (ALWAYS — this
   is the fallback if email send fails)
2. Append to `results-history.json` with timestamp and spec hash
3. Send via the email script:

```bash
python3 scripts/send-email.py --send .context/results-email.md \
  --subject "Pattaya Results: {SPEC_TITLE} — Best Score: {BEST_SCORE}/10"
```

If the send fails, tell the user: "Results saved to .context/results-email.md.
Email send failed: {error}. Check .env credentials and pipeline/config.yml."

### Step 9: Staleness Check

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
