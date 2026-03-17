# TODOS — Pattaya

## P1 — High Priority

### Build step for prompt composition (DRY)
Create a `gen-prompts.ts` script (like gstack's `gen-skill-docs`) that
composes the 5 derived phase prompts from shared fragments + diff sections.
Currently the derived prompts are manual copies with `DERIVED FROM` headers.
A build step would make updates atomic. Blocked by: Phase 1 prompts being
stable enough to templatize.
**Effort: M**

### ~~Differentiation strategy for parallel runs~~ ✓ DONE
Run A/B/C now have distinct approach biases: A→code quality,
B→UX polish, C→robustness. Added to phase 01 prompt via
`## Differentiation` section.

### Deep-link to conductor.build
Add an "Open in Conductor" button that launches conductor.build with the
project workspace pre-loaded, eliminating copy-paste entirely. Blocked on
knowing Conductor's URL scheme or web API for opening workspaces. The
copy-to-clipboard prompt was shipped as the universal fallback.
**Effort: S** (once URL scheme is known)
**Depends on:** Conductor exposing a URL scheme or web API

## P2 — Medium Priority

### Round-over-round early stopping
When running multi-round (rounds > 1), detect if a round's winner scores
LOWER than the previous round's winner. If so, stop early and keep the
best round's output rather than wasting compute on regression rounds.
Implementation: compare `round_results[-1].winner_score` with the new
winner's score after Step 2e. If lower, skip to Step 3 (final report).
**Effort: S**
**Depends on:** Multi-round pipeline (v0.2.0)

### Auto-deployment with preview URLs (partially done)
GitHub Pages deployment is now available via "Create Repo" in Mission Control.
Remaining: support additional deploy targets (Vercel, Netlify, Railway) for
projects that need a backend or custom build step. Requires detecting tech
stack, choosing platform, configuring deploy, handling failures.
**Effort: M** (reduced — GitHub Pages covers the common case)

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

### Custom inline style principles
Allow `style: custom` with a `style_principles:` multi-line block in
config.yml instead of referencing a built-in profile. For users whose
engineering philosophy doesn't map to a named engineer. Requires parsing
multi-line YAML values and handling the precedence when both `style:` and
`style_principles:` are set.
**Effort: S**
**Depends on:** Style inspiration feature (v0.1.4.0)

## P3 — Low Priority

### Score history sparklines
Add inline SVG sparkline charts to the dashboard results cards showing
how each scoring dimension changed across rounds. Requires storing
per-round per-run scores in results-history.json and rendering tiny
line charts (no library needed — inline SVG path elements). Most useful
when rounds > 1.
**Effort: M**
**Depends on:** Multi-round pipeline (v0.2.0), results-history.json persistence

### Project history browser
Let users see past projects (spec title, date, best score) and switch
between them. `results-history.json` already accumulates this data.
Once "New Project" exists, users will run multiple projects and want
to revisit old ones. Needs a list view UI and archive/restore logic.
**Effort: M**
**Depends on:** New Project feature (v0.1.7.0)

### Keyboard shortcuts for dashboard
Add keyboard navigation to Mission Control: `j`/`k` to move between run
cards, `p` to toggle preview, `d` to jump to diff compare, `g` to toggle
config panel, `?` to show shortcut overlay. Keep it opt-in (no conflicts
with browser shortcuts).
**Effort: S**

### Auto-probe email on page load
When index.html (Mission Control) loads and .env already exists, silently POST /test-email
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

### Design review pipeline (phases 12-14)
Added design audit (phase 12) and design fix (phase 13) phases to the
pipeline. Retro/scoring moved to phase 14 with dual weight tables.
Includes AI slop detection, DESIGN.md generation, design style profiles,
before/after screenshots, and dashboard integration with AI Slop badge
and design system preview.

### Differentiation strategy for parallel runs
Run A/B/C have distinct approach biases in phase 01 prompt.

### Multi-round pipeline with auto-accept winner
Pipeline supports `rounds: N` in config.yml. Each round auto-selects
the winner, commits it to git with a feature summary, and feeds it as
input to the next round. Dashboard shows round progression.
