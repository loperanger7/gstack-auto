# Phase 03: Implementation
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: (original to Pattaya — no gstack source)
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-03-implement.md
# - Read prior phase artifacts from disk, not conversation history
# - ALL generated code goes in output/ directory
# - Make ALL decisions autonomously — pick the best option and move on

## Your Task

Build the MVP defined in the engineering plan. Write code that is simple,
correct, and immediately runnable. No scaffolding. No boilerplate for
boilerplate's sake. Every file earns its place.

Read the engineering plan at `{PHASE_ARTIFACTS}/phase-02-plan-eng.md`.

## Mode: {MODE}

**If mode is `iteration`:** You are modifying existing code in `output/`,
not writing from scratch. Read the existing files first. Make surgical
changes per the engineering plan. Run existing tests before AND after your
changes — break nothing that was passing.

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Implementation Style

Write code as if the best engineer you know will read it tomorrow:

- **Clarity over cleverness.** If a reader needs to pause to understand
  a line, rewrite it.
- **Small functions that do one thing.** If a function needs a comment
  explaining what it does, its name is wrong.
- **Handle errors at the boundary.** Validate inputs where they enter
  the system. Trust data inside the system.
- **No dead code.** No commented-out blocks. No "just in case" imports.
- **No premature abstraction.** Three similar blocks of code is fine.
  An abstraction with one caller is wrong.
- **Tests are not optional.** For every feature, write at least one
  test that proves it works and one that proves it fails gracefully.

## Process

1. Read the file plan from Phase 02.
2. Create files in the implementation order specified.
3. For each file:
   a. Write the implementation.
   b. Write its tests (in a tests/ or __tests__/ directory).
   c. Verify it works by running the tests.
4. After all files are written:
   a. Run the full test suite.
   b. If any test fails, fix the code (not the test) unless the test
      is wrong.
   c. Run the application and verify the success criteria from Phase 01.

## Output Directory Structure

All code goes in `output/`:
```
output/
├── [project files per engineering plan]
├── tests/
│   └── [test files]
├── package.json (if applicable)
└── README.md (one paragraph: what it is, how to run it)
```

The README.md should contain:
- One sentence: what this is.
- How to install dependencies (if any).
- How to run it.
- How to run tests.

Nothing else. No badges, no contributing guide, no license section.

## Completion Log

Write a brief log to `{PHASE_ARTIFACTS}/phase-03-implement.md`:

```markdown
# Implementation Log — Run {RUN_ID}

## Files Created
- output/[file]: [what it does]

## Tests Written
- output/tests/[file]: [what it tests]

## Test Results
[paste test output]

## Success Criteria Check
1. [criterion from Phase 01]: PASS/FAIL
2. [criterion from Phase 01]: PASS/FAIL

## Decisions Made
- [any deviation from the plan, with rationale]
```
