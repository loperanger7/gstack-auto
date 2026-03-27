# Changelog

All notable changes to Pattaya will be documented in this file.

## [0.1.16.0] - 2026-03-26

### Added
- **Build iteration:** Two paths from completed builds — full Iterate (opens office hours pre-seeded with parent context) and Quick Fix (one-liner description → straight to handoff).
- **Build lineage tracking:** Recursive CTE ancestor chain with depth cap of 20. Iteration badges in build list and detail views.
- **Deploy feature:** Async Fly.io re-deploy via Machines API with background thread + JSON poll endpoint. Auto-deploy hook triggers on build completion when user has deploy config.
- **Settings page:** Manage Fly API token with Fernet encryption via dedicated `DEPLOY_ENCRYPTION_KEY`. Token validation and secure clear.
- **Preseed role filtering:** Iteration sessions pre-seed parent context as `role='preseed'`, filtered from spec assembly to prevent spec contamination.
- **Migration tracking:** `_migrations` table for idempotent replay of SQL migrations. Migration 002 adds iteration columns (parent_build_id, root_session_id, fly_app_name, deploy_status, deploy_config) with backfill.
- **Auth helpers:** Extracted `require_approved_user()` to `app/auth_helpers.py` for DRY route guards.
- **Randomized heredoc delimiter:** Handoff prompt uses `SPEC_{random_hex}` to prevent shell injection.
- **33 new tests:** Full coverage of iterate, quick fix, lineage, deploy, settings, migrations, preseed filtering, and handoff prompt security.

### Fixed
- **Auth callback bool coercion:** Changed admin check from `email == admin and admin` to `bool(admin and email == admin)` preventing ValueError on falsy admin email.
- **fly_app_name injection:** Regex validation (`^[a-z0-9][a-z0-9-]{0,62}$`) prevents malicious app names in results POST.
- **conductor_url XSS:** Non-https conductor workspace URLs rejected, stored as empty string.
- **Duplicate store_nonce:** Removed dead duplicate function from models.py.
- **Orphaned nonce in create_build_atomic:** Removed nonce creation that was never consumed.

## [0.1.15.0] - 2026-03-25

### Added
- **Mission Control web service:** Flask app for running gstack-auto as a service. Google OAuth login, invite-only waitlist, admin panel for user approval.
- **Office Hours chat:** Browser-based product spec creation via Claude-powered conversational AI with SSE streaming. Template picker for common project types.
- **Build handoff ceremony:** JWT build tokens with one-time nonces and HMAC-SHA256 payload integrity. Atomic check-and-create with BEGIN IMMEDIATE for concurrent build limits.
- **Machine API endpoints:** `/api/v1/results` and `/api/v1/progress` for pipeline-to-server communication with bearer token auth and build ownership verification.
- **Build results dashboard:** Per-user build history, detail views with phase progress and scoring breakdowns.
- **Email notifications:** SMTP-based build completion alerts via `app/services/notify.py`.
- **Spend tracking:** Per-user daily token ceiling with automatic disable at limit.
- **45 integration tests:** Full coverage of auth, builds, office hours, API, admin, tokens, and spend tracking.

### Fixed
- **API IDOR vulnerability:** Build endpoints now verify `user_id` ownership on all queries.
- **Nonce TOCTOU race:** Replaced SELECT-then-UPDATE with atomic single UPDATE for nonce consumption.
- **HMAC verification gap:** Results endpoint now validates `X-Payload-SHA` header when present.
- **Build limit race condition:** Wrapped concurrent build check in BEGIN IMMEDIATE transaction.
- **Progress reopening terminal builds:** `update_build_progress` now guards against reopening completed/failed builds.
- **Nonce burn on parse failure:** Moved nonce consumption after JSON body validation so parse failures are retryable.
- **SECRET_KEY volatility:** Now requires env var (no random default that invalidates sessions on restart).

## [0.1.14.0] - 2026-03-25

### Added
- **v2 pipeline architecture:** 13 skill-modeled phases replacing v1's 13 custom phases. New phase sequence: CEO Plan → Adversarial → Eng Plan → Adversarial → Design Plan → Adversarial → Eng Plan v2 → Adversarial → Implement → Ship → QA → Document → Score.
- **Dual adversarial review system:** Configurable cross-model review (Claude + Codex) at phases 02, 04, 06, 08. Orchestrator-level execution with `{ADVERSARIAL_FINDINGS}` injection into subsequent phases.
- **Follow-up question system:** Budget-controlled mid-run questions (`follow_up_budget` in config.yml). Phases 01, 03, 07, 09, 11 can emit `FOLLOW_UP_QUESTION:` lines. Orchestrator deduplicates across N parallel runs via LLM call and broadcasts answers via `{FOLLOW_UP_ANSWERS}`.
- **Design doc discovery:** Orchestrator checks `~/.gstack/projects/` for approved `/office-hours` design docs before reading product-spec.md. Design doc is injected as `{DESIGN_DOC}` — a binding constraint for phase 01.
- **Bug-fix sub-loop phases:** 11a (fix plan), 11b (implement fix), 11c (re-QA) — dedicated sub-phases replacing v1's shared fix phases.
- **16 v2 phase prompt files:** 01-plan-ceo.md through 13-retro-score.md plus 11a/11b/11c sub-loop, all with autonomy markers, template variables, and no-skill/no-AskUserQuestion directives.
- **153 validation checks:** Complete v2 test suite covering phase files, autonomy directives, namespace isolation, template variables, follow-up question support, design DNA, config, dead code cleanup, CLAUDE.md v2 content, and server integration.

### Changed
- **CLAUDE.md:** Full v2 orchestrator rewrite — gstack-auto branding, adversarial review orchestration, follow-up question system, design doc discovery, safe winner copy (atomic temp dir swap), partial failure handling.
- **pipeline/config.yml:** Added `adversarial_reviews: ["02", "08"]` and `follow_up_budget: 3`. Updated header to "gstack-auto Pipeline Configuration (v2)".
- **index.html + dashboard.html:** Updated PHASE_NAMES to v2 (13 phases with adversarial review labels).
- **README.md:** Updated pipeline diagram, phase list, getting started (office hours entry point), and config examples for v2.
- **TODOS.md:** Removed superseded v1 items, added v2 items (follow-up question validation, cross-run scoring, style adherence dimension, N>3 differentiation).

### Fixed
- **XSS in index.html:** `ai_slop_grade` now escaped with `esc()`. `colorDots()` CSS injection prevented with allowlist regex for safe color values.
- **Stale artifact references in phase 09:** Fixed v1 artifact names (`phase-03-implement.md`) to v2 (`phase-07-plan-eng-v2.md`).

### Removed
- **pipeline/gen-phases.mjs:** Dead v1 code (auto-generated bug-fix loop phases).
- **pipeline/phase-config.json:** Dead v1 code (phase generation config).
- **12 v1 phase files:** 02-plan-eng.md, 03-implement.md, 04-review.md, 05-ship.md, 06-qa.md, 07-plan-bugfix.md, 08-implement-fix.md, 09-review-and-commit-fix.md, 10-qa-confirm.md, 11-design-review.md, 12-design-fix.md.

## [0.1.13.0] - 2026-03-18

### Added
- **Multi-tenant Twitter SaaS:** Complete FastAPI application with Google OAuth, per-user Twitter OAuth 1.0a, 8-table SQLite schema, encrypted credentials, admin panel, engagement leaderboard, mobile swipe approval, and 3-step onboarding wizard.
- **Pipeline phase prompt updates:** Synced phases 04 (review), 06 (QA), 07 (plan-bugfix), 08 (implement-fix), 11 (design-review), and 13 (retro-score) to gstack v0.7.3+ artifact formats — 4-pass review structure, 8-category health scoring, 10-category design audit with dual weight tables.
- **Atomic send claims:** `claim_reply_for_send()` with `UPDATE ... WHERE ... RETURNING` prevents duplicate Twitter posts from concurrent scheduler invocations.
- **Engagement upsert race fix:** Replaced SELECT-then-INSERT/UPDATE with `INSERT ... ON CONFLICT DO UPDATE` for engagement tracking.
- **LLM output validation:** Variant label allowlist (`A`–`E`) rejects unexpected Claude output before DB write.
- **239 tests passing:** Full test coverage for multi-tenant app including crypto, jobs, drafter, DB, routes, edge cases, and regression suites.

### Fixed
- Admin route missing `RedirectResponse` import causing NameError on user toggle.
- Session middleware hardcoded fallback secret renamed to `INSECURE-DEV-ONLY` (app exits before serving if `AUTH_SECRET_KEY` missing).

### Removed
- Nested `output/output/` duplicate directory (46 files, 8,234 lines).
- Committed `__pycache__/` and `.pytest_cache/` files from tracking.

## [0.1.12.1] - 2026-03-18

### Changed
- **Gitignore output/ and product-spec.md:** Pipeline-generated code (`output/`), user product specs (`product-spec.md`), and scoring history (`results-history.json`) are now gitignored. These are per-user artifacts that shouldn't be tracked in the repo.

## [0.1.12.0] - 2026-03-17

### Added
- **gen-phases build system:** `pipeline/gen-phases.mjs` generates 4 derived phases (07-10) from base phases, eliminating manual copy-paste. Zero dependencies — just Node.js builtins. Fail-closed: validates all section overrides match real headings before writing anything.
- **Test-first methodology:** Phase 03 (implement) now instructs agents to write a failing test before implementation, not after.
- **Fix-First code review:** Phase 04 (review) agents now auto-fix mechanical issues (dead code, stale comments) and log each fix as `[AUTO-FIXED]`, instead of just listing findings.
- **Regression test generation:** Phase 06 (QA) and Phase 10 (QA confirm) agents now write regression tests in `output/tests/regression/` for each bug they fix, so bugs don't recur across rounds.
- **Self-improving pipeline:** New `{ROUND_RETROSPECTIVE}` template variable and CLAUDE.md Step 2e.5 — after each round, the orchestrator writes a retrospective to `.context/retrospective/round-N.md`. Round 2+ agents see what went wrong in the prior round before planning.
- **Test health metrics:** Phase 13 (retro/scoring) now includes `test_count` and `regression_tests_added` in score.json. Used as tiebreaker in winner selection.

### Changed
- **Pipeline reduced from 14 phases to 13:** Merged phases 09 (review-fix) and 10 (ship-fix) into a single `09-review-and-commit-fix.md` — the boundary between reviewing and committing a bug fix was artificial.
- **Phase 05 (ship) radically simplified:** Stripped from 86 lines to ~55 lines. Removed Greptile comments, TODOS.md management, update checks — all wrong for autonomous agents in worktrees. Now just: run tests, clean up, commit.
- **Renumbered phases:** 11→10 (qa-confirm), 12→11 (design-review), 13→12 (design-fix), 14→13 (retro-score). All CLAUDE.md orchestration references updated.
- **All gstack hashes synced to v0.6.1** (hash: 9d47619e). Zero stale phases.
- Winner selection tiebreaker now includes `test_count` (more tests = better).

## [0.1.11.0] - 2026-03-17

### Fixed
- `{ENV_VARS}` placeholder now present in all build and QA phase prompts (phases 01, 02, 03, 06, 07, 08, 11) — API keys saved in Mission Control were silently dropped and never reached pipeline agents
- Added anti-hardcode warning to implementation phases (03, 08): agents now instructed to reference API keys via environment variables, never baked into output files
- Added export instructions to QA phases (06, 11): agents now instructed to `export KEY=VALUE` before starting the app under test

### Changed
- CLAUDE.md Step 2a: added `{ENV_VARS}`, `{STYLE_NAME}`, `{STYLE_PRINCIPLES}` to the Phase 01 spawn substitution list (were missing, causing silent no-ops)
- CLAUDE.md Step 2c: added note to apply same template variable substitutions as Step 2b for bug-fix phases (07–11)
- CLAUDE.md: fixed stale description of `{ENV_VARS}` ("for QA testing" → "for implementation and testing")

## [0.1.10.1] - 2026-03-17

### Changed
- Run Again bar button text updated to "Run again with winning output" to communicate iteration mode
- Added sub-line below the Run Again bar showing winner score: "Agents will iterate on the X.X/10 winner — not start fresh."

## [0.1.10.0] - 2026-03-17

### Added
- Per-row [✓ Save] button on env var rows — appears when key+value are filled, triggers immediate `/save-config` POST, disappears after save
- Inline error label per env var row on save failure
- Duplicate key detection with red border + "duplicate" label in real time
- Enter key shortcut: Enter in key field focuses value field; Enter in value field triggers save
- Test 7: per-row single-key POST round-trip server test (7/7 passing)

### Fixed
- Visual inconsistency: `.env-row input[type="text"]` (key name field) now matches password field appearance — identical padding, border, background, font, and focus transition

## [0.1.9.0] - 2026-03-17

### Added
- Design review pipeline: phase 12 (design audit) and phase 13 (design fix) inserted before scoring
- AI Slop detection: 30-item condensed checklist catching purple gradients, 3-column grids, and generic AI patterns
- DESIGN.md generation: phase 12 extracts design system (fonts, colors, spacing) from rendered output
- Design style profiles: `pipeline/design-styles/` with dieter-rams, brutalist, and playful philosophies
- Design Quality as 6th scoring dimension (10% weight) with letter-grade rubric
- Dual weight tables: 6-dim weights when design_quality present, 5-dim for backward compatibility
- AI Slop badge and design system preview (color dots + font name) in Mission Control score cards
- Design Report Card section in email template with per-category grades
- `design_review` and `design_style` config options in pipeline/config.yml
- `{DESIGN_STYLE_NAME}` and `{DESIGN_STYLE_PRINCIPLES}` template variables for phases 12-13
- Auto-detect skip: design phases skipped when output has no .html files
- Before/after screenshot capture in phase 13 (design fix)
- Font upgrade detection with pairing recommendations by product type

### Changed
- Retro/scoring moved from phase 12 to phase 14
- Pipeline diagram updated: Phase 1-6 → bug-fix → design 12-13 → Score 14
- Validation suite expanded from 171 to 200 checks (design phases, styles, config)
- `buildPrompt()` now includes design_quality when present in clipboard text

### Fixed
- Dangling markdown code fence in CLAUDE.md after score.json schema

## [0.1.8.0] - 2026-03-17

### Added
- Environment Variables section in Mission Control — dynamic key-value rows for API keys and secrets
- Generic env var management: add, edit, delete keys from the web UI with values stored in `.env`
- Sentinel protocol: only modified keys are sent on save; untouched saved values are never exposed or overwritten
- Duplicate key name prevention and PATTAYA_ prefix rejection in the frontend
- `{ENV_VARS}` template variable — pipeline agents receive user-configured API keys during QA testing
- `--port` flag for setup-server.py (used by tests)
- Smoke test suite (`tests/test-env-vars.py`) — 6 tests covering save, load, round-trip, SMTP coexistence, deletion, and prefix blocking

### Fixed
- `.env` write safety: `save_config()` now uses read-modify-write instead of overwriting the entire file, so saving SMTP credentials no longer clobbers user env vars (and vice versa)
- Delete handler in env var UI correctly preserves the deletion signal for saved keys

### Changed
- Pre-flight checks now collect non-PATTAYA_ env vars from `.env` and pass them to pipeline agents

## [0.1.7.1] - 2026-03-16

### Fixed
- Pipeline now detects existing winner output from prior runs and starts in iteration mode instead of greenfield — enables cross-invocation iteration
- Final round winner is now committed to git (previously only intermediate rounds were committed, so winner code was lost between conversations)
- Removed `output/` from `.gitignore` so winner code persists in the repository

### Changed
- Pipeline config defaults: parallel_runs 5→3, rounds 10→7

## [0.1.7.0] - 2026-03-16

### Added
- "New Project" button in Mission Control — clears results and output, returns to SETUP state while preserving email config and credentials
- "Create Repo" button — publishes winner output as a new GitHub repository via `gh` CLI
- GitHub Pages integration — optional one-click deployment with public repo (checkbox toggle, private by default)
- Auto-suggested repo name from spec title via slugify
- Server-side repo name validation (`^[a-zA-Z0-9._-]{1,100}$`) with defense-in-depth (client + server)
- Local-first create-repo flow: git init + commit locally before creating remote, avoiding orphan repos on push failure
- `POST /new-project` endpoint — clears `.context/runs/`, `output/`, and `product-spec.md`
- `POST /create-repo` endpoint — validates, creates GitHub repo, pushes winner-final, optionally enables Pages
- 7 new validation checks: New Project button, Create Repo button/panel, GitHub Pages checkbox, endpoint tests
- Project history browser TODO (P3) for future multi-project support

### Fixed
- `/results` API early return when no runs directory exists now includes all standard fields (`spec_title`, `style_name`, `round_history`, `has_winner_output`)

### Changed
- "Auto-deployment with preview URLs" TODO updated: GitHub Pages covers the common case, remaining scope narrowed to Vercel/Netlify/Railway
- Validation suite expanded from 164 to 171 checks

## [0.1.6.0] - 2026-03-16

### Added
- Auto-serve winner: pipeline auto-starts local server and opens Mission Control after completion (CLAUDE.md Step 4.5)
- "View Winner" button in Mission Control results view, linking to `/output/winner-final/index.html`
- `has_winner_output` field in `/results` API — checks for `output/winner-final/index.html`
- Configuration bar replaces gear icon — full-width collapsible bar with arrow indicator and keyboard support
- Active phase dot with pulse animation in progress cards
- CRT scanline overlay for Akira aesthetic

### Changed
- Color palette: dark Akira red (`#c0392b`), teal CTA buttons (`#4ecdc4`), blue working state
- Section headings now have left accent border
- Winner card glow uses dark red instead of lime green
- Score bars use cyan (high) and blue (mid) instead of green and lime

## [0.1.5.0] - 2026-03-16

### Added
- Mission Control: unified single-page UI (`index.html`) replacing separate setup.html and dashboard.html
- 4-state page: SETUP → READY → MONITORING → RESULTS, detected from `/current-config` + `/results` + `/styles`
- Collapsible config panel with gear toggle, expanded in SETUP mode, collapsed otherwise
- Pipeline config UI: parallel runs, rounds, style inspiration dropdown with live principle preview
- Config presets: Quick Test (2 runs, 1 round), Standard (3 runs, 1 round), Thorough (3 runs, 3 rounds)
- `/styles` API endpoint returning style profile metadata (name, display, quote, principles)
- "Run again" button that copies Conductor command to clipboard
- `update_config_value()` and `get_config_value()` helpers for regex-based config.yml updates
- Server tests for `/styles` endpoint and extended `/current-config` fields
- TODO: score history sparklines (P3), keyboard shortcuts (P3)

### Changed
- `/current-config` now returns `parallel_runs`, `rounds`, `style` in addition to email and spec
- `/save-config` accepts and persists `parallel_runs`, `rounds`, `style` via config.yml
- `/`, `/setup`, `/dashboard` all serve index.html (backward-compatible routing)
- Validation suite expanded from 160 to 164 checks
- README validation count updated

## [0.1.4.0] - 2026-03-16

### Added
- Style inspiration: `style:` config field selects a legendary engineer's coding philosophy
- 7 built-in style profiles: Carmack, Antirez (Sanfilippo), Abramov, Metz, Holowaychuk, Majors, Marlinspike
- Each profile encodes concrete principles, review focus, and a signature quote
- `{STYLE_NAME}` and `{STYLE_PRINCIPLES}` template variables in phases 01, 03, 04, 12
- Style name displayed in dashboard header and email report
- `/results` API returns `style_name` from config
- 24 new validation checks: style profiles exist, have headings, template vars present in phases
- TODO: custom inline style principles (P2)

### Changed
- Phase 01 differentiation section notes that style and run bias compound
- Phase 12 scoring evaluates code quality through the selected engineer's lens
- README config example includes `style:` field with available options
- Validation suite expanded from 136 to 160 checks

## [0.1.3.0] - 2026-03-16

### Added
- Multi-round pipeline: `rounds: N` in config.yml runs N sequential rounds, auto-selecting the winner each round and feeding it into the next
- Winner carry-forward: copies winner's output/ to main repo and creates a git commit with score card and feature summary after each round
- Auto-upgrade system: `scripts/pattaya-update-check` (version comparison, 12h cache, escalating snooze) and `scripts/pattaya-upgrade.sh` (git and vendored installs)
- Differentiation strategy: Run A (code quality), Run B (UX polish), Run C (robustness) approach biases in phase 01 prompt
- `{MODE}` template variable (greenfield/iteration) across phases 01-05, 07-08 for round 2+ behavior
- `{EXISTING_CODE_SUMMARY}` template variable in phase 01 for iteration context
- Dashboard round progression view with score bars and round-over-round deltas
- Round history in `/results` API from `results-history.json`
- `auto_accept_winner` config option for single-round manual selection
- Round progression section in email report template
- 14 new validation tests: config keys, upgrade scripts, winner selection with tie-breaking, {MODE} in phase prompts, {EXISTING_CODE_SUMMARY}
- TODO: round-over-round early stopping (P2)

### Changed
- CLAUDE.md pipeline restructured: Steps 2-5 wrapped in round loop (Steps 2a-2f), pre-flight includes update check
- Architecture diagram updated to show round loop and winner selection
- Phase prompts support iteration mode (modify existing code vs greenfield)
- Phase 05 commit messages include run ID and mode-aware format
- Email subject includes round count
- Validation suite expanded from 122 to 136 checks

## [0.1.2.0] - 2026-03-15

### Added
- Pasteable Conductor prompt in "Build on this" panel with spec title and score breakdown
- Copy-to-clipboard button with `execCommand` fallback for non-secure contexts
- Visual "Copied!" feedback animation on copy button
- Click-to-select on prompt text for manual copy
- `spec_title` field in `/results` API response
- Server test for `spec_title` field in validate-pipeline.sh
- TODO: deep-link to conductor.build (deferred, blocked on URL scheme)

### Changed
- "Build on this" panel now shows a single pasteable prompt instead of `cd` + generic instructions

## [0.1.1.1] - 2026-03-15

### Changed
- Dashboard: allow multiple preview iframes and build panels open simultaneously (removed single-preview restriction)
- README: updated gstack install instructions to use Garry Tan's official install method from the gstack repo

## [0.1.1.0] - 2026-03-15

### Added
- Results dashboard (`dashboard.html`) with ranked score cards, winner crown, live app preview iframes, desktop/mobile viewport toggle, "Build on this" command panels, and unified diff comparison between runs
- Shared design system (`style.css`) extracted from setup.html — dark theme, monospace, CSS variables, zero inline styles
- Setup server (`scripts/setup-server.py`) with smart routing (GET / serves dashboard if results exist, setup otherwise), static file serving with path traversal protection, `/results` JSON API, `/diff` endpoint, `/current-config`, `/save-config`, `/test-email`
- Setup launchpad (`setup.html`) with collapsible email section, spec quality hints, 3 quick-start templates (weather, bookshelf, todo), "What Happens Next" post-save panel, dashboard navigation
- Email delivery via SMTP (`scripts/send-email.py`) with `--probe` pre-flight check and `--send` for pipeline results
- `.env.example` documenting required SMTP credentials
- Email configuration section in `pipeline/config.yml` (smtp host/port/credentials, file-only fallback)
- Server integration tests in validation suite (6 endpoint checks including path traversal)
- Setup UI & Dashboard validation checks (7 static checks for file existence, CSS extraction, cross-linking)
- Live pipeline progress polling on dashboard (5s interval, phase dots, auto-stops when scored)

### Changed
- CLAUDE.md updated: Gmail MCP references replaced with SMTP email delivery, added pre-flight probe instructions and error guidance
- Validation suite expanded from 97 to 119 checks
- TODOS.md updated with unblocked-by annotations for email-dependent items

## [0.1.0.0] - 2026-03-15

### Added
- 12-phase autonomous development pipeline (plan → build → review → ship → QA → fix → score)
- 7 unique phase prompts + 5 derived variants, all with autonomy directives and namespace isolation
- N parallel runs via Claude Agent tool with git worktree isolation
- Lock-step parallel execution with bug-fix divergence handling (max 3 cycles)
- 5-dimension structured scoring rubric (functionality, code quality, test coverage, UX polish, spec adherence)
- Gmail notification with ASCII score bar charts, narratives, and code highlights
- Orchestrator CLAUDE.md with 9-step pipeline (pre-flight → spawn → resume → fix → score → email)
- Product spec template with structured sections and success criteria
- Pipeline config (parallel_runs, max_fix_cycles, scoring dimensions, penalties)
- gstack sync tooling: version-tracked phase headers, `check-gstack-sync.sh`, `diff-gstack-phase.sh`
- Tier 1 validation suite (97 static checks: phase existence, autonomy directives, namespace isolation, derived tracking, config validity)
- TODOS.md with 7 deferred items across P1-P3 priorities
