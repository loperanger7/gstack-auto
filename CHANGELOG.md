# Changelog

All notable changes to Pattaya will be documented in this file.

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
