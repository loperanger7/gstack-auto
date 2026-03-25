# Phase 08: Final Adversarial Review (Pre-Implementation)
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# ═══════════════════════════════════════════════════════════════
#  THIS PHASE IS EXECUTED BY THE ORCHESTRATOR, NOT THE WORKTREE
#  AGENT. The worktree agent does NOT read or execute this file.
# ═══════════════════════════════════════════════════════════════

## What This Phase Does

After all parallel runs complete Phase 07, the orchestrator runs a final
adversarial review of each run's reconciled engineering plan:

```
{PHASE_ARTIFACTS}/phase-07-plan-eng-v2.md
```

This is the last gate before implementation. The orchestrator uses a
secondary Claude instance (or Codex) to act as a senior tech lead doing
a pre-implementation plan review — the kind of review that catches the
mistakes that become expensive the moment code is written.

## Adversarial Review Criteria

The reviewer asks:

1. **Is the file plan actually final?** Are there components or behaviors
   in the design plan (Phase 05) that still don't have corresponding files
   in the Phase 07 plan? Are there files in the plan that nothing depends
   on (dead files)?

2. **Is the implementation order safe?** If followed exactly, will the
   implementer ever need a file that hasn't been created yet? Are there
   circular dependencies in the order?

3. **Are the tests actually testable?** For each named test case: can it be
   written without mocking the entire application? Are any test cases
   actually integration tests mislabeled as unit tests (or vice versa)?

4. **Is the Definition of Done complete?** Are there obvious success
   conditions from the Phase 01 success criteria that aren't covered by
   the DoD checklist? Is the test command actually runnable in a fresh
   environment?

5. **Are there unresolved conflicts?** Did Phase 07 accept adversarial
   findings from Phase 06 and then forget to actually change the plan to
   reflect the resolution? (Verbal acceptance without implementation
   change is a common failure mode.)

6. **CSS architecture correctness:** Will the specified custom properties
   cover all the design plan's component states? Are there interaction
   states (hover, focus, disabled) that will need color tokens not
   defined in the custom properties?

7. **Scope drift check:** Compare the Phase 01 MVP definition against the
   Phase 07 file plan. Has scope crept? Are there files that implement
   features clearly marked "Must NOT Have (Yet)" in Phase 01?

## Output

The orchestrator writes adversarial findings for each run to:

```
{PHASE_ARTIFACTS}/phase-08-adversarial-final.md
```

These findings are injected into the implementation phase via the
`{ADVERSARIAL_FINDINGS}` template variable.

## Worktree Agent Behavior

The worktree agent resumes at the implementation phase with
`{ADVERSARIAL_FINDINGS}` already populated. It does not run this phase
file — it only consumes the output. The implementer must address all
findings before beginning to write code.

If `{ADVERSARIAL_FINDINGS}` is empty (orchestrator skipped this phase),
the implementer proceeds without pre-implementation adversarial context
and notes this in the implementation log.
