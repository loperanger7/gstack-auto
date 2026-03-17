# Pattaya Scoring Rubric

Score each dimension 0-10. Be honest. A 7 is good. A 9 is exceptional.
A 10 means you wouldn't change a single line.

## Weight Tables

Two weight configurations depending on whether design review ran:

**With design_quality (6 dimensions):**

| Dimension      | Weight |
|----------------|--------|
| Functionality  | 30%    |
| Code Quality   | 20%    |
| Test Coverage  | 15%    |
| UX Polish      | 10%    |
| Spec Adherence | 15%    |
| Design Quality | 10%    |

**Without design_quality (5 dimensions):**

| Dimension      | Weight |
|----------------|--------|
| Functionality  | 30%    |
| Code Quality   | 20%    |
| Test Coverage  | 15%    |
| UX Polish      | 15%    |
| Spec Adherence | 20%    |

## Functionality

| Score | Meaning |
|-------|---------|
| 0-2   | Doesn't run or crashes immediately |
| 3-4   | Runs but core features are broken |
| 5-6   | Core features work with notable bugs |
| 7-8   | All success criteria pass, minor issues |
| 9-10  | Everything works, handles edge cases gracefully |

## Code Quality

| Score | Meaning |
|-------|---------|
| 0-2   | Unreadable, no structure, copy-pasted from tutorials |
| 3-4   | Works but messy — long functions, bad names, no error handling |
| 5-6   | Reasonable structure, some rough edges |
| 7-8   | Clean, well-organized, good naming, proper error handling |
| 9-10  | Elegant — a new engineer could understand it in 10 minutes |

## Test Coverage

| Score | Meaning |
|-------|---------|
| 0-2   | No tests or tests that don't test anything meaningful |
| 3-4   | A few tests covering happy paths only |
| 5-6   | Tests for main features, missing edge cases |
| 7-8   | Good coverage of happy paths and common failure modes |
| 9-10  | Comprehensive — happy paths, edge cases, error conditions |

## UX Polish

| Score | Meaning |
|-------|---------|
| 0-2   | Unusable — broken layout, confusing interface |
| 3-4   | Functional but ugly or confusing |
| 5-6   | Works, looks acceptable, some rough edges |
| 7-8   | Clean, intuitive, handles loading/error states |
| 9-10  | Delightful — feels like a real product |

## Spec Adherence

| Score | Meaning |
|-------|---------|
| 0-2   | Built something completely different from the spec |
| 3-4   | Partially addresses the spec, missing key requirements |
| 5-6   | Covers the spec but with significant gaps |
| 7-8   | Faithfully implements the spec, minor omissions |
| 9-10  | Nails the spec exactly — nothing missing, nothing extra |

## Design Quality

Only scored when design review phases (12-13) ran. The numeric score
comes directly from `design-scores.json` produced by Phase 12.

| Score | Meaning |
|-------|---------|
| 0-2   | AI slop — purple gradients, 3-column grids, generic everything |
| 3-4   | Looks AI-generated — default fonts, no design point of view |
| 5-6   | Functional but generic — no design thinking, just default |
| 7-8   | Intentional design — good typography, coherent palette, rhythm |
| 9-10  | Polished — would pass review at a respected design studio |

## Penalties

- Bugs remaining after fix cycles: -1.0 per bug (max -3.0)
- Exhausted fix budget (3 cycles): -2.0
- Floor: 0.0, Ceiling: 10.0
