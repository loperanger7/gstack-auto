# Phase 04: Adversarial Engineering Review
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# ═══════════════════════════════════════════════════════════════
#  THIS PHASE IS EXECUTED BY THE ORCHESTRATOR, NOT THE WORKTREE
#  AGENT. The worktree agent does NOT read or execute this file.
# ═══════════════════════════════════════════════════════════════

## What This Phase Does

After all parallel runs complete Phase 03, the orchestrator runs an
adversarial engineering review of each run's engineering plan artifact:

```
{PHASE_ARTIFACTS}/phase-03-plan-eng.md
```

The orchestrator uses a secondary Claude instance (or Codex) to challenge
the engineering plan as a staff engineer who has shipped and maintained
production systems and knows exactly where junior/mid engineers cut corners.

## Adversarial Review Criteria

The reviewer challenges:

1. **File plan completeness** — Are there missing files? (e.g., missing error
   handler, missing loading state component, missing environment config). Are
   any listed files clearly unnecessary bloat?
2. **Data flow gaps** — Does the diagram account for async operations? Are
   there unhandled states (loading, partial failure, race conditions)?
3. **Dependency risks** — Are there dependencies that are unnecessary, poorly
   maintained, or that introduce supply-chain risk? Are API dependencies
   missing rate-limit handling?
4. **Test plan adequacy** — Are the tests actually testing behavior or just
   structure? Are critical paths untested? Is the test framework a good fit?
5. **Edge case blind spots** — What user inputs or environment conditions
   were not accounted for? What happens when the API is slow, the user has
   a slow network, or the data is empty on first load?
6. **Design system coherence** — Does the DESIGN.md specification in the
   plan actually reflect the Design Style from Phase 01? Are there internal
   contradictions (e.g., "minimal" style but 12 custom colors)?
7. **Implementation order logic** — Is the proposed order actually
   executable? Will file N depend on something not yet written?

## Output

The orchestrator writes adversarial findings for each run to:

```
{PHASE_ARTIFACTS}/phase-04-adversarial-eng.md
```

These findings are injected into Phase 05 (design plan) via the
`{ADVERSARIAL_FINDINGS}` template variable.

## Worktree Agent Behavior

The worktree agent resumes at Phase 05 with `{ADVERSARIAL_FINDINGS}` already
populated. It does not run this phase file — it only consumes the output.

If `{ADVERSARIAL_FINDINGS}` is empty (orchestrator skipped this phase), the
Phase 05 agent proceeds without adversarial context and notes this in its
artifact.
