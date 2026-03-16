# Changelog

All notable changes to Pattaya will be documented in this file.

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
