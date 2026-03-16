# Changelog

All notable changes to Pattaya will be documented in this file.

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
