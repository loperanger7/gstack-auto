# Phase 02: Adversarial CEO Review
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# ═══════════════════════════════════════════════════════════════
#  THIS PHASE IS EXECUTED BY THE ORCHESTRATOR, NOT THE WORKTREE
#  AGENT. The worktree agent does NOT read or execute this file.
# ═══════════════════════════════════════════════════════════════

## What This Phase Does

After all parallel runs complete Phase 01, the orchestrator runs an
adversarial review of each run's CEO plan artifact:

```
{PHASE_ARTIFACTS}/phase-01-plan-ceo.md
```

The orchestrator uses a secondary Claude instance (or Codex) to stress-test
the plan from the perspective of a skeptical investor who has seen too many
products over-scoped and under-delivered.

## Adversarial Review Criteria

The reviewer challenges:

1. **Scope creep risk** — Is the "Must Have" list actually minimal? Are any
   items really "nice to haves" dressed up as requirements?
2. **Architecture fitness** — Does the chosen stack match the actual problem
   complexity? Is it over-engineered or dangerously under-powered?
3. **Success criteria validity** — Are the success criteria measurable? Would
   a human actually know if they passed or failed?
4. **Design intent coherence** — Does the selected design style actually fit
   the product and its users, or was it a random pick?
5. **Risk blind spots** — Are there obvious failure modes the CEO plan missed?
   (API rate limits, auth complexity, third-party dependency failures, etc.)

## Output

The orchestrator writes adversarial findings for each run to:

```
{PHASE_ARTIFACTS}/phase-02-adversarial-ceo.md
```

These findings are injected into Phase 03 via the `{ADVERSARIAL_FINDINGS}`
template variable.

## Worktree Agent Behavior

The worktree agent resumes at Phase 03 with `{ADVERSARIAL_FINDINGS}` already
populated. It does not run this phase file — it only consumes the output.

If `{ADVERSARIAL_FINDINGS}` is empty (orchestrator skipped this phase), the
Phase 03 agent proceeds without adversarial context and notes this in its
artifact.
