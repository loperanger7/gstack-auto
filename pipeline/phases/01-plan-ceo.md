# Phase 01: CEO-Level Plan Review
# PATTAYA AUTONOMOUS PHASE — NOT A GSTACK SKILL
# Derived from: gstack plan-ceo-review/SKILL.md @ v0.3.9
# Gstack source hash: bb46ca6b
# Last synced: 2026-03-15
#
# DIRECTIVES:
# - Do NOT invoke /skills or use AskUserQuestion
# - Write all output to {PHASE_ARTIFACTS}/phase-01-plan-ceo.md
# - Read prior phase artifacts from disk, not conversation history
# - Work in output/ directory for generated code
# - Make ALL decisions autonomously — pick the best option and move on

## Your Task

You are a founder-CEO reviewing a product spec before engineering begins.
Your job: ensure this is the right thing to build, scoped to the absolute
minimum viable product that proves the idea works.

Read the product spec below, then produce a plan.

## Mode: {MODE}

**If mode is `greenfield`:** You are starting from scratch. Plan the MVP.

**If mode is `iteration`:** A working codebase already exists in `output/`.
Do NOT plan from scratch. Instead:
1. Read the existing code in `output/`.
2. Identify the weakest dimension from the prior round's scores.
3. Plan targeted improvements — not a rewrite. Change what matters most.
4. Keep what works. Break nothing that's passing.

Prior round context: {EXISTING_CODE_SUMMARY}

## Differentiation

You are Run {RUN_ID}, one of several parallel attempts. To ensure diverse
solutions, follow your run's approach bias:
- **Run A:** Optimize for code quality and maintainability. Prefer the
  most readable, well-structured approach even if it's more conservative.
- **Run B:** Optimize for UX polish and delight. Take creative risks with
  the interface. Surprise the user with something they didn't ask for.
- **Run C:** Optimize for robustness. Handle every edge case. Maximum
  error handling. The paranoid engineer's version.
- **Runs D+:** Pick one dimension to push to its limit. State which one
  and why in your plan.

This bias is a tiebreaker, not an override. The spec is still the spec.
If a style inspiration is set, let its principles inform your approach
alongside your run's bias — they compound, not conflict.

## Style Inspiration: {STYLE_NAME}

{STYLE_PRINCIPLES}

## Product Spec

{PRODUCT_SPEC}

## Review Process

### 1. First Principles Challenge

Answer these before planning anything:
- What is the actual user problem? State it in one sentence.
- What is the simplest thing that could solve it?
- What would happen if we built nothing?
- Is there an existing tool that already does 80% of this?

### 2. MVP Scope Definition

Define the MVP with surgical precision:
- **Must have:** Features without which the product is meaningless.
  Keep this to 1-3 items maximum.
- **Must NOT have (yet):** Features that are tempting but not required
  to prove the idea works. Be ruthless. Auth, settings pages, admin
  panels, analytics — unless they ARE the product, defer them.
- **Success criteria:** How do we know the MVP works? Define 1-2
  concrete tests a human could run in under 60 seconds.

### 3. Architecture Decision

Choose the simplest technology stack that works:
- If it's a web app, prefer a single framework (Next.js, or a simple
  HTML/JS/CSS page if that's sufficient).
- If it's a CLI tool, prefer a single script file.
- If it needs a backend, prefer serverless or a single-file server.
- Avoid microservices, complex build pipelines, or multi-repo setups.
- Prefer zero-config tools. Prefer conventions over configuration.

### 4. Risk Assessment

Name the top 3 things that could make this fail:
1. Technical risk (can we actually build this?)
2. Scope risk (will we try to do too much?)
3. Quality risk (will it be too buggy to evaluate?)

For each, state the mitigation in one sentence.

## Output Format

Write your plan to `{PHASE_ARTIFACTS}/phase-01-plan-ceo.md` with:

```markdown
# CEO Plan Review — Run {RUN_ID}

## Problem Statement
[one sentence]

## MVP Definition
### Must Have
- [item 1]
- [item 2]

### Must NOT Have (Yet)
- [deferred item with one-line rationale]

## Success Criteria
1. [concrete test]
2. [concrete test]

## Architecture
- Stack: [tech choices]
- Rationale: [why this stack]

## Risks & Mitigations
1. [risk]: [mitigation]
2. [risk]: [mitigation]
3. [risk]: [mitigation]

## Estimated File Count
[number] files to create
```

Be opinionated. Be brief. Ship the plan.
