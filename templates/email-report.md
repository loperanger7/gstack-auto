# Pattaya Email Report Template

Use this template to compose the Gmail notification. Replace all
{PLACEHOLDERS} with actual values.

---

Subject: Pattaya Results: {SPEC_TITLE} — Best Score: {BEST_SCORE}/10

---

Body:

```
PATTAYA DEVELOPMENT PIPELINE — RESULTS
=======================================

Spec: {SPEC_TITLE}
Runs: {N_RUNS} parallel × {R_ROUNDS} round(s)
Date: {DATE}
Pipeline time: {DURATION}


{IF_MULTI_ROUND}
ROUND PROGRESSION
─────────────────

{FOR_EACH_ROUND}
Round {ROUND_NUM}: Best {ROUND_BEST_SCORE}/10 ({ROUND_WINNER})  {ROUND_BAR}  {ROUND_DELTA}
{/FOR_EACH_ROUND}

Note: Each bar is 20 chars wide. █ = 5% of max score (10).
{/IF_MULTI_ROUND}

RANKED RESULTS (Final Round)
────────────────────────────

{FOR_EACH_RUN_RANKED}
Run {RUN_ID} (Score: {AVERAGE}/10)    {WINNER_LABEL}
██████████ Functionality  {FUNC_SCORE}
██████████ Code Quality   {QUALITY_SCORE}
██████████ Test Coverage  {TEST_SCORE}
██████████ UX Polish      {UX_SCORE}
██████████ Spec Adherence {SPEC_SCORE}

Bugs remaining: {BUGS}  |  Fix cycles: {FIX_CYCLES}/3

{/FOR_EACH_RUN_RANKED}

Note: Score bars use █ (filled) and ░ (empty) blocks.
Each bar is 10 characters wide, one █ per point.
Example: 7/10 = ███████░░░


WHY I BUILT IT THIS WAY
───────────────────────

{FOR_EACH_RUN_RANKED}
--- Run {RUN_ID} ---
{NARRATIVE}

{/FOR_EACH_RUN_RANKED}


CODE HIGHLIGHTS
──────────────

{FOR_EACH_RUN_RANKED}
--- Run {RUN_ID} ---
{HIGHLIGHT}

{/FOR_EACH_RUN_RANKED}


NEXT STEPS
──────────

Reply to this email with:
- "Expand: [feature to add]" to start a new cycle building on the winner
- "Fix: [specific issue]" to run another fix cycle
- "Ship it" to finalize the winning run

Results saved locally at: .context/results-email.md
Branch: {WINNER_BRANCH}
```

---

## Score Bar Rendering

To render a score bar for value N (0-10):

```
█ repeated N times + ░ repeated (10-N) times + " " + dimension name + " " + N
```

Examples:
```
████████░░ Functionality  8
██████░░░░ Code Quality   6
█████████░ Spec Adherence 9
```
