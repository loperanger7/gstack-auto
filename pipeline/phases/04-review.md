# Phase 04: Code Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack review/SKILL.md @ v0.7.3
# Gstack source hash: c4f679d8
# Last synced: 2026-03-18
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-04-review.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously — fix issues directly

## Your Task

Review the code written in Phase 03. Find bugs, security issues, and
quality problems. Fix them directly — do not ask for permission.

## Mode: {MODE}

**If mode is `iteration`:** Focus your review on the CHANGES made this
round. Don't re-review unchanged code unless a change introduces a
regression risk in adjacent code. Check for scope drift: did the
implementation add anything not in the engineering plan?

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Review Process — Two-Pass

### Pass 1: CRITICAL Issues (fix immediately)

Scan all files in `output/` for these high-severity categories:

#### SQL & Data Safety
- String interpolation in SQL — use parameterized queries
- Check-then-set patterns that should be atomic (TOCTOU races)
- Write operations without error handling
- Missing validation before persistence
- N+1 queries: missing eager loading for associations used in loops

#### Race Conditions & Concurrency
- Read-check-write without uniqueness constraints
- find_or_create patterns on columns without unique DB index
- Status transitions without atomic WHERE old_status = ?
- Concurrent access to shared mutable state

#### Security
- SQL injection, command injection, XSS, path traversal
- Hardcoded secrets, credentials, API keys
- Missing input validation at system boundaries
- `html_safe` / `raw()` on user-controlled data

#### LLM Output Trust Boundary
- LLM-generated values written to DB without format validation
- Structured tool output accepted without type/shape checks

#### Correctness
- Off-by-one errors
- Null/undefined dereference
- Unhandled promise rejections or uncaught exceptions
- Type mismatches

For each critical issue: fix it immediately in the code.

### Pass 2: INFORMATIONAL Issues (fix if quick, note if not)

1. **Dead code** — remove it
2. **Duplicated logic** — extract if >3 lines repeated >2 times
3. **Misleading names** — rename
4. **Missing error handling** — add it
5. **Missing tests** — write them
6. **Console.log/print debugging** — remove it
7. **Overly complex functions** — simplify if possible in <5 minutes
8. **Magic numbers** — extract to named constants if used in multiple places
9. **Stale comments** — update or remove

**Log each fix:** For every issue fixed in Pass 1 or Pass 2, append to your
review output: `[AUTO-FIXED] file:line — what was done`. This creates a
traceable record of every automated fix.

### Pass 3: Design Review (conditional)

**Only run this pass if `output/` contains frontend files:**
Check for `.html`, `.css`, `.jsx`, `.tsx`, `.vue`, `.svelte` files.

If frontend files exist, check for these code-level design anti-patterns:

#### AI Slop Detection (highest priority)
- Purple/violet/indigo gradients or blue-to-purple color schemes
- The 3-column feature grid (icon-in-circle + title + description x3)
- Icons in colored circles as section decoration
- Centered everything (`text-align: center` on all headings/cards)
- Uniform bubbly border-radius (same large radius on everything)
- Generic hero copy ("Welcome to [X]", "Unlock the power of...")

#### Typography
- Body text font-size < 16px
- More than 3 font families
- Heading hierarchy skipping levels (h1 → h3 without h2)
- Blacklisted fonts (Papyrus, Comic Sans, Lobster, Impact)

#### Spacing & Layout
- Arbitrary spacing values not on a 4px/8px scale
- Fixed widths without responsive handling
- Missing max-width on text containers
- `!important` in CSS (specificity escape hatch)

#### Interaction States
- Interactive elements missing hover/focus states
- `outline: none` without replacement focus indicator
- Touch targets < 44px on interactive elements

#### DESIGN.md Alignment
If `output/DESIGN.md` exists, check that code matches stated design system:
- Colors match the palette
- Fonts match the typography section
- Spacing values match the scale

### Pass 4: Architecture Check

- Does the code match the engineering plan from Phase 02?
- Are there unnecessary abstractions?
- Are there missing abstractions (copy-pasted code blocks)?
- Is the dependency count justified?

## After Review

Run all tests. If any fail after your fixes, fix the regression.

## Output Format

Write your review to `{PHASE_ARTIFACTS}/phase-04-review.md`:

```markdown
# Code Review — Run {RUN_ID}

## Pass 1: Critical Issues Found & Fixed
1. [AUTO-FIXED] [file:line] [category] [issue] — [what you did]

## Pass 2: Informational Issues Found & Fixed
1. [AUTO-FIXED] [file:line] [issue] — [what you did]

## Pass 2: Issues Noted (not fixed)
1. [file:line] [issue] — DEFERRED: [why]

## Pass 3: Design Review
[Skip this section if no frontend files found]
### AI Slop: [CLEAN / N items found]
### Typography: [CLEAN / N items found]
### Spacing: [CLEAN / N items found]
### Interaction States: [CLEAN / N items found]
### DESIGN.md Alignment: [ALIGNED / N deviations found]

## Pass 4: Architecture Assessment
[1-2 paragraphs]

## Scope Drift Check (iteration mode only)
[List any additions not in the Phase 02 engineering plan]

## Test Results After Review
[paste test output]

## Files Modified
- [file]: [summary of changes]

## Review Summary
CRITICAL_FIXED: [N]
INFORMATIONAL_FIXED: [N]
DESIGN_ISSUES: [N]
DEFERRED: [N]
```
