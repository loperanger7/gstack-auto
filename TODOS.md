# TODOS — gstack-auto

## P1 — High Priority

### Follow-up question validation
When collecting pending-questions.md from worktree agents, validate the
format before parsing. Malformed files (missing confidence tags, empty
lines, binary content) should be caught and skipped with a warning in the
round retrospective — not silently ignored.
**Effort: S**
**Context:** Identified during v2 eng review as a critical gap. The follow-up
system depends on agents writing well-formatted questions, but LLMs can
produce unexpected output. Without validation, bad questions are silently
dropped, which looks like the pipeline working when it isn't.

### Deep-link to conductor.build
Add an "Open in Conductor" button that launches conductor.build with the
project workspace pre-loaded, eliminating copy-paste entirely. Blocked on
knowing Conductor's URL scheme or web API for opening workspaces. The
copy-to-clipboard prompt was shipped as the universal fallback.
**Effort: S** (once URL scheme is known)
**Depends on:** Conductor exposing a URL scheme or web API

### Conductor deep link / programmatic handoff
Investigate Conductor's URL scheme or web API for opening workspaces
programmatically. Currently the handoff is manual (copy prompt, open
Conductor, paste). A deep link would eliminate copy-paste entirely.
**Effort: S** (once URL scheme is known)
**Depends on:** Conductor exposing a URL scheme or web API
**Context:** Identified during gstack-auto-as-a-service CEO review.
Existing "Deep-link to conductor.build" TODO above covers the same gap —
merge when investigation completes.

## P2 — Medium Priority

### API key rotation for office hours Claude API
The web service uses a single server-side Anthropic API key for office
hours chat. Add rotation support: multiple keys with round-robin or
failover, admin alerting on auth failures, and a config UI to add/remove
keys without restarting the server.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service CEO review.
Single key is acceptable for launch but becomes a single point of failure.

### Pipeline results webhook from Conductor
Add a webhook endpoint that Conductor can call to push incremental build
progress (phase completion, scores). Currently the pipeline POSTs final
results only. Incremental updates would enable real-time SSE progress
in Mission Control during builds.
**Effort: M**
**Depends on:** Conductor supporting outbound webhooks or the pipeline
being modified to POST progress at each phase boundary.
**Context:** Identified during gstack-auto-as-a-service CEO review.

### Chat keyboard accessibility for office hours
The office hours chat is the core new UI pattern. Keyboard users need:
focus management when new messages arrive, Escape to stop streaming,
arrow keys to navigate message history, and screen reader announcements
for assistant responses (aria-live region). Without this, keyboard-only
and screen reader users can't use the primary product feature.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service design review.

### Mobile chat viewport management
On mobile, the software keyboard pushes the viewport up and can hide the
chat input field or cause scroll jumps during streaming responses. Needs
explicit handling via the Visual Viewport API or fixed-bottom input with
dynamic padding. Without it, mobile chat feels broken on iOS/Android.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service design review.

### Admin audit log
Add an `admin_audit_log` table: `(admin_id, action, target_user_id,
timestamp, details)`. Log every admin action (user approval, revocation,
session viewing). Without this, a compromised admin account leaves no
forensic trail.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service adversarial review.
Both Codex and Claude subagent flagged this independently.

### Handoff conversion tracking
Track how many users complete office hours vs. how many ever POST results
back. If the ratio is below 30%, the manual Conductor handoff is the #1
priority to fix. Add metrics: `sessions_completed` count, `builds_with_results`
count, conversion funnel in admin dashboard.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service adversarial review.
Claude subagent flagged manual handoff as the highest product risk.

### Round-over-round early stopping
When running multi-round (rounds > 1), detect if a round's winner scores
LOWER than the previous round's winner. If so, stop early and keep the
best round's output rather than wasting compute on regression rounds.
Implementation: compare `round_results[-1].winner_score` with the new
winner's score after Step 2e. If lower, skip to Step 3 (final report).
**Effort: S**

### Cross-run scoring
Currently each agent scores its own work (self-grading). A separate
scoring agent that reads ALL runs' output/ and produces comparative
scores would be more reliable. The self-grading bias means "best
self-promoter wins" rather than "best code wins."
**Effort: M**
**Context:** Identified during v2 adversarial review. Fundamental
architecture change — deferred to post-v2 stabilization.

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
E.g., "Phase 9/13: Implementation complete." Prevents the 30+ minute
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

### Style adherence scoring dimension
Add a "style_adherence" scoring dimension that evaluates whether the
implementation actually follows the legendary engineer's principles, not
just whether the code is generically good. Currently style injection is
pure vibes — a 7.0 with Carmack style and 7.0 with Marlinspike style
are scored identically because the rubric doesn't differentiate.
**Effort: S**
**Context:** Identified during v2 adversarial review.

## P3 — Low Priority

### Chat history retention policy
Define and implement a retention policy for office hours chat messages.
Options: auto-delete after N days, archive completed sessions, let users
export/delete their own history. Without a policy, the messages table
grows unbounded and stale conversations clutter the UI.
**Effort: S**
**Context:** Identified during gstack-auto-as-a-service CEO review.

### Visual references in Phase 01
Have the CEO persona name 2-3 real websites whose look and feel match
the product's audience (e.g., "feel like Linear", "feel like Notion").
Gives Phase 03 and 05 concrete aesthetic anchors beyond abstract design
style principles. Risk: LLM may hallucinate outdated sites, but
directional guidance is still valuable.
**Effort: S**

### Score history sparklines
Add inline SVG sparkline charts to the dashboard results cards showing
how each scoring dimension changed across rounds. Requires storing
per-round per-run scores in results-history.json and rendering tiny
line charts (no library needed — inline SVG path elements). Most useful
when rounds > 1.
**Effort: M**
**Depends on:** results-history.json persistence

### Project history browser
Let users see past projects (spec title, date, best score) and switch
between them. `results-history.json` already accumulates this data.
Once "New Project" exists, users will run multiple projects and want
to revisit old ones. Needs a list view UI and archive/restore logic.
**Effort: M**

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

### N>3 differentiation strategy
Current differentiation (Run A=quality, B=UX, C=robustness) caps at 3
meaningful biases. Runs D+ get vacuous "pick a dimension" which leads to
convergent solutions. Need structured biases for N=5 and N=7.
**Effort: S**
**Context:** Identified during v2 adversarial review.

## Completed

### ~~Build step for prompt composition (DRY)~~ ✓ DONE → SUPERSEDED
Originally implemented as `pipeline/gen-phases.mjs` + `pipeline/phase-config.json`.
Deleted in v2 pipeline rewrite — v2 uses explicit phase files with no generation.
**Completed:** v0.1.12.0 (2026-03-17) | **Superseded:** v2 pipeline (2026-03-25)

### Design review pipeline (v1 phases 11-13 → v2 Phase 05)
Design review moved from post-implementation audit to pre-implementation
planning phase (Phase 05) in v2. Design principles are now defined before
code is written, not evaluated after.

### Differentiation strategy for parallel runs
Run A/B/C have distinct approach biases in phase 01 prompt.

### Multi-round pipeline with auto-accept winner
Pipeline supports `rounds: N` in config.yml. Each round auto-selects
the winner, commits it to git with a feature summary, and feeds it as
input to the next round. Dashboard shows round progression.

### v2 Pipeline Rewrite
Replaced 13-phase v1 pipeline with skill-based v2 pipeline featuring:
- Office hours / design doc as entry point (replaces blank product-spec.md)
- Dual adversarial review (Claude + Codex) at configurable phases
- 4 planning phases before implementation (CEO → Eng → Design → Eng v2)
- Mid-run follow-up question system (3 per round, shared)
- Document release phase (Phase 12)
**Completed:** 2026-03-25
