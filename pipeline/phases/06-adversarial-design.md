# Phase 06: Adversarial Design Review
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
#
# ═══════════════════════════════════════════════════════════════
#  THIS PHASE IS EXECUTED BY THE ORCHESTRATOR, NOT THE WORKTREE
#  AGENT. The worktree agent does NOT read or execute this file.
# ═══════════════════════════════════════════════════════════════

## What This Phase Does

After all parallel runs complete Phase 05, the orchestrator runs an
adversarial design review of each run's design plan artifact:

```
{PHASE_ARTIFACTS}/phase-05-plan-design.md
```

The orchestrator uses a secondary Claude instance (or Codex) to challenge
the design plan as a senior designer who has spent years watching engineers
execute visual specs and knows exactly where good intentions collapse into
mediocre implementations.

## Adversarial Review Criteria

The reviewer challenges:

1. **Layout realism** — Do the ASCII sketches and layout descriptions map
   to CSS that can actually be written? Are there layout choices (e.g.,
   "full bleed with contained text and edge-to-edge image") that require
   non-obvious implementation techniques? Flag anything that will be
   ambiguous in Phase 07.

2. **Component state completeness** — Are there missing interaction states
   that will look broken in production? Common omissions: `focus-visible`
   rings, `disabled` opacity, skeleton shapes that don't match real content,
   empty states with no call-to-action.

3. **Typography application gaps** — Is every text element covered by the
   typography table? Will the implementer need to invent type styles not
   in the spec? (Gaps become inconsistencies.)

4. **Design system contradictions** — Does the plan contradict DESIGN.md?
   (e.g., plan says "card with 24px padding" but DESIGN.md base unit is
   6px — 24px isn't a valid multiple.) Are there semantic color tokens used
   in contexts that break their meaning?

5. **Anti-pattern residue** — Did the design plan genuinely eliminate all
   flagged anti-patterns, or just acknowledge them without replacing them
   with better alternatives?

6. **Responsive spec gaps** — Are there screen states (e.g., a table that
   overflows on mobile, a modal that needs to become a sheet on small
   screens) that the responsive spec didn't address?

7. **Engineering-design conflicts** — Does the design plan require components
   or interactions that aren't accounted for in the Phase 03 file plan? Flag
   any net-new complexity introduced by design that engineering didn't plan for.

## Output

The orchestrator writes adversarial findings for each run to:

```
{PHASE_ARTIFACTS}/phase-06-adversarial-design.md
```

These findings are injected into Phase 07 (eng plan v2) via the
`{ADVERSARIAL_FINDINGS}` template variable.

## Worktree Agent Behavior

The worktree agent resumes at Phase 07 with `{ADVERSARIAL_FINDINGS}` already
populated. It does not run this phase file — it only consumes the output.

If `{ADVERSARIAL_FINDINGS}` is empty (orchestrator skipped this phase), the
Phase 07 agent proceeds without adversarial context and notes this in its
artifact.
