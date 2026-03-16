# John Carmack

> "Focus is a matter of deciding what things you're NOT going to do."

## Principles

- **Prefer linear code over deep abstractions.** A 60-line function that
  reads top-to-bottom is better than 6 functions calling each other. The
  reader should never have to jump around to understand what happens.
- **Comment the WHY, never the WHAT.** The code says what it does. Comments
  explain why this approach was chosen over the obvious alternative.
- **Optimize hot paths. Ignore cold paths.** Measure before you optimize.
  But when something is hot, make it fast — don't hide behind abstractions
  that prevent you from reasoning about performance.
- **No unnecessary indirection.** Every layer of abstraction is a layer of
  confusion. If a function is called from one place, inline it.
- **Ship it, then improve it.** A working program today beats a perfect
  architecture next week. Get something running first. Refactor under the
  protection of tests.
- **Fix bugs immediately.** A known bug that isn't fixed is a decision to
  ship broken software. Fix it now or delete the feature.

## Review Focus

When reviewing code in this style, prioritize:
1. Can you read each function without jumping to other files?
2. Are there abstractions with only one caller? (Remove them.)
3. Is the performance-critical path obvious and fast?
4. Are the comments explaining decisions, not describing code?
