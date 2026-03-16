# TODOS — Pattaya

## P1 — High Priority

### Build step for prompt composition (DRY)
Create a `gen-prompts.ts` script (like gstack's `gen-skill-docs`) that
composes the 5 derived phase prompts from shared fragments + diff sections.
Currently the derived prompts are manual copies with `DERIVED FROM` headers.
A build step would make updates atomic. Blocked by: Phase 1 prompts being
stable enough to templatize.
**Effort: M**

### Differentiation strategy for parallel runs
When spawning N parallel runs, each should approach the spec differently
(e.g., different frameworks, different architectures). Without explicit
variation, parallel runs may converge on identical solutions. Diversity
in the population is what makes evolutionary search work.
**Effort: M**

### Deep-link to conductor.build
Add an "Open in Conductor" button that launches conductor.build with the
project workspace pre-loaded, eliminating copy-paste entirely. Blocked on
knowing Conductor's URL scheme or web API for opening workspaces. The
copy-to-clipboard prompt was shipped as the universal fallback.
**Effort: S** (once URL scheme is known)
**Depends on:** Conductor exposing a URL scheme or web API

## P2 — Medium Priority

### Auto-deployment with preview URLs
After the winning run is selected, auto-deploy it (Vercel/Netlify/Railway)
and include a live preview URL in the email. Requires detecting tech stack,
choosing platform, configuring deploy, handling failures.
**Effort: L**

### User email reply loop
Monitor for user's email reply containing scope expansion instructions,
then start a new pipeline cycle inheriting the winning run's codebase.
Requires Gmail polling, reply parsing, cycle restart logic.
**Effort: L**
**Unblocked by:** email config (v0.1.1.0) — SMTP send works, polling is the remaining gap

### Live progress notifications
Send email updates during pipeline run (not just at end).
E.g., "Phase 3/12: Implementation complete." Prevents the 30+ minute
silence that feels like it's broken.
**Effort: S**
**Unblocked by:** email config (v0.1.1.0) — SMTP infrastructure now available

### Persistent learning / knowledge base
Store what worked (high-scoring patterns) and what didn't across runs.
Future runs consult this history to bias toward successful approaches.
Risk of overfitting to past successes.
**Effort: M**

## P3 — Low Priority

### Auto-probe email on setup page load
When setup.html loads and .env already exists, silently POST /test-email
in the background and show a green/red dot in the collapsed email status
line. Removes the manual "Test Connection" click for returning users.
Risk: SMTP probe adds ~2s latency to page load; transient failures could
show false red. Mitigate by showing "checking..." state and only going
red on definitive auth failures.
**Effort: S**
**Depends on:** Collapsible email section (done in setup.html launchpad redesign)

### One-click branch selection in email
Include git checkout commands in email for each run's worktree branch.
Zero friction between "I like this one" and "I'm working on it."
**Effort: S**
**Unblocked by:** email config (v0.1.1.0) — email delivery now works

## Completed

(none yet)
