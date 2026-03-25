# Phase 12: Documentation & Release
# GSTACK-AUTO AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: (original to gstack-auto — no gstack source)
# Last synced: 2026-03-25
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-12-document.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously

## Your Task

Finalize documentation and prepare the project for handoff. The goal is
that any developer (or the user themselves) can pick up this codebase and
understand it immediately without asking questions.

## Process

### 1. README.md

Write (or rewrite) `output/README.md`. It must contain:

**Required sections:**
- **What this is** — one paragraph: problem it solves + how to use it
- **Quick start** — numbered steps from clone to running app:
  ```
  1. npm install
  2. cp .env.example .env  (if applicable)
  3. npm start
  ```
- **Configuration** — table of every environment variable (name, purpose,
  default if any). If the product spec references API keys or external
  services, every one must appear here.
- **Running tests** — exact command to run the test suite
- **Architecture** — 3-5 bullet points: the key files, what each does,
  and the data flow between them. Not a full tour — just enough context
  to navigate the codebase.

**NOT included:**
- Badges, shields, or CI/CD status icons
- Contributing guide
- License section
- Code of Conduct
- Changelog (goes in CHANGELOG.md)
- Screenshots (the QA artifacts cover this)

Tone: direct, technical, brief. The audience is a developer who knows
their way around code and just needs to know THIS project's specifics.

### 2. CHANGELOG.md

Write `output/CHANGELOG.md` documenting what was built in this pipeline run.
Format:

```markdown
# Changelog

## [Unreleased] — {today's date}

### Added
- [feature description]: what the user can now do
- [feature description]: what the user can now do

### Fixed (if bug fixes were applied)
- [bug description]: what was broken and is now fixed

### Architecture
- [key decision]: why this approach was chosen
```

Read the implementation log from `{PHASE_ARTIFACTS}/phase-09-implement.md`
(or `phase-03-implement.md` if this is a v1 run) for the list of files
created. Read the bug fix logs for the list of fixes applied.

### 3. Inline Code Comments

Read each source file in `output/`. For any logic that is non-obvious,
add a brief inline comment explaining WHY (not WHAT — the code itself
shows what; the comment explains the reasoning).

Apply this checklist per function/method:
- [ ] Is the function name self-explanatory? If not, rename it.
- [ ] Is there complex logic (bit ops, regex, >3 conditions in a chain)?
  → Add a single-line comment explaining the intent.
- [ ] Does it handle an edge case that isn't obvious from the spec?
  → Add a comment referencing the edge case.
- [ ] Does it make an assumption about input format or state?
  → Add a comment stating the assumption.

DO NOT add comments to:
- Simple getters/setters
- Standard library calls whose semantics are obvious
- Code that already reads like English

### 4. Public API / Function Documentation

For any public functions or modules intended to be called by other code
(exports, route handlers, class methods), add JSDoc/docstring-style
documentation if not already present:

**JavaScript:**
```js
/**
 * Fetches the latest prices for the given asset symbols.
 * Returns an empty array if the external API is unreachable.
 *
 * @param {string[]} symbols - Asset symbols, e.g. ['BTC', 'ETH']
 * @returns {Promise<{symbol: string, price: number}[]>}
 */
```

**Python:**
```python
def fetch_prices(symbols: list[str]) -> list[dict]:
    """
    Fetches the latest prices for the given asset symbols.
    Returns an empty list if the external API is unreachable.

    Args:
        symbols: Asset symbols, e.g. ['BTC', 'ETH']

    Returns:
        List of dicts with 'symbol' and 'price' keys.
    """
```

Only document functions with non-obvious behavior, complex parameters,
or important return value semantics. Skip trivial functions.

### 5. .env.example

If the project uses environment variables, ensure `output/.env.example`
exists with every required variable listed, with placeholder values and
one-line comments explaining each:

```bash
# Your API key from https://example.com/settings/api
ODDS_API_KEY=your_key_here

# SMTP host for email delivery. Use smtp.gmail.com for Gmail.
SMTP_HOST=smtp.gmail.com
```

Do NOT include real values. If `.env.example` already exists, audit it
against the actual variables used in the code — add any missing ones.

### 6. Commit Documentation

Stage and commit the documentation:
```bash
git add output/
git commit -m "docs({RUN_ID}): add README, CHANGELOG, and inline comments"
```

## Output Format

Write to `{PHASE_ARTIFACTS}/phase-12-document.md`:

```markdown
# Documentation Manifest — Run {RUN_ID}

## README.md
- Written: YES / UPDATED
- Sections: What, Quick start, Configuration, Tests, Architecture
- Env vars documented: [N] variables

## CHANGELOG.md
- Written: YES / UPDATED
- Features documented: [N]
- Fixes documented: [N]

## Inline Comments Added
- [file]: [N] comments added — [brief description of what was commented]

## JSDoc / Docstrings Added
- [file]: [N] functions documented

## .env.example
- Status: PRESENT / CREATED / UPDATED
- Variables: [N] total

## Commit
- Hash: [short hash]
- Message: [commit message]

## Gaps / Skipped
- [anything skipped and why]
```
