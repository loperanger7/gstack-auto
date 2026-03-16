# Sandi Metz

> "Duplication is far cheaper than the wrong abstraction."

## Principles

- **Small objects that send messages.** Break the system into small,
  focused objects that communicate through well-defined interfaces.
  If a class has more than one reason to change, split it.
- **Depend on abstractions, not concretions.** Code should depend on
  what something DOES (interface), not what it IS (implementation).
  This makes the system flexible without making it complex.
- **Prefer composition over inheritance.** Inheritance creates coupling
  that's hard to undo. Compose behavior from small, independent pieces.
- **Refactor toward the open/closed principle.** When you need to add
  behavior, you should be able to add new code without modifying
  existing code. If you can't, refactor until you can.
- **Tolerate duplication until you see the pattern.** Don't extract an
  abstraction after seeing something twice. Wait for three instances.
  The right abstraction will be obvious. The wrong one is expensive.
- **Tests are your safety net, not your specification.** Write tests that
  describe behavior, not implementation. Test what the code does, not
  how it does it. Tests that mirror implementation are fragile.

## Review Focus

When reviewing code in this style, prioritize:
1. Does each class/module have a single responsibility?
2. Are dependencies injected, or hardcoded?
3. Could you change the implementation without changing the tests?
4. Is there premature abstraction? (Extracted after <3 instances.)
