# Pattaya Scoring Rubric

Score each dimension 0-10. Be honest. A 7 is good. A 9 is exceptional.
A 10 means you wouldn't change a single line.

## Functionality (weight: 30%)

| Score | Meaning |
|-------|---------|
| 0-2   | Doesn't run or crashes immediately |
| 3-4   | Runs but core features are broken |
| 5-6   | Core features work with notable bugs |
| 7-8   | All success criteria pass, minor issues |
| 9-10  | Everything works, handles edge cases gracefully |

## Code Quality (weight: 20%)

| Score | Meaning |
|-------|---------|
| 0-2   | Unreadable, no structure, copy-pasted from tutorials |
| 3-4   | Works but messy — long functions, bad names, no error handling |
| 5-6   | Reasonable structure, some rough edges |
| 7-8   | Clean, well-organized, good naming, proper error handling |
| 9-10  | Elegant — a new engineer could understand it in 10 minutes |

## Test Coverage (weight: 15%)

| Score | Meaning |
|-------|---------|
| 0-2   | No tests or tests that don't test anything meaningful |
| 3-4   | A few tests covering happy paths only |
| 5-6   | Tests for main features, missing edge cases |
| 7-8   | Good coverage of happy paths and common failure modes |
| 9-10  | Comprehensive — happy paths, edge cases, error conditions |

## UX Polish (weight: 15%)

| Score | Meaning |
|-------|---------|
| 0-2   | Unusable — broken layout, confusing interface |
| 3-4   | Functional but ugly or confusing |
| 5-6   | Works, looks acceptable, some rough edges |
| 7-8   | Clean, intuitive, handles loading/error states |
| 9-10  | Delightful — feels like a real product |

## Spec Adherence (weight: 20%)

| Score | Meaning |
|-------|---------|
| 0-2   | Built something completely different from the spec |
| 3-4   | Partially addresses the spec, missing key requirements |
| 5-6   | Covers the spec but with significant gaps |
| 7-8   | Faithfully implements the spec, minor omissions |
| 9-10  | Nails the spec exactly — nothing missing, nothing extra |

## Penalties

- Bugs remaining after fix cycles: -1.0 per bug (max -3.0)
- Exhausted fix budget (3 cycles): -2.0
- Floor: 0.0, Ceiling: 10.0
