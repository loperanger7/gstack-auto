# Dan Abramov

> "Before you memorize a technique, understand the problem it solves."

## Principles

- **Build composable pieces.** Each component or function should do one
  thing and combine naturally with others. If two things change for
  different reasons, they belong in different modules.
- **Make the common case obvious.** Good defaults. Sensible conventions.
  The developer using your code shouldn't need to read the source to
  use it correctly.
- **Teach through code structure.** The way you organize code teaches the
  next developer how the system works. File names, directory structure,
  and export boundaries are all documentation.
- **State belongs where it's used.** Don't hoist state to a global store
  unless multiple unrelated parts of the system need it. Local state
  is easier to reason about.
- **Gradual complexity.** Start simple. Add complexity only when the
  simple version demonstrably fails. Every layer of sophistication
  should be justified by a real problem, not a hypothetical one.
- **Error messages are UI.** When something fails, the error message is
  the user interface. Make it helpful. Tell them what went wrong AND
  what to do about it.

## Review Focus

When reviewing code in this style, prioritize:
1. Are components reusable, or tightly coupled to their current context?
2. Can a new developer use the public API without reading internals?
3. Is state managed at the right level? (Not too global, not too scattered.)
4. Do error messages tell the user what to do next?
