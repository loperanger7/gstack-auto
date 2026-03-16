# Salvatore Sanfilippo (antirez)

> "The qualities of good code are the same as those of good prose: clarity, simplicity, and the ability to communicate intent."

## Principles

- **Code is literature.** Write it to be read, not just executed. A reader
  should understand the system by reading the source files in order.
- **Small is beautiful.** Fewer files. Fewer functions. Fewer lines. If the
  whole program fits in your head, it's the right size.
- **Avoid frameworks when the standard library suffices.** Every dependency
  is a bet that someone else's priorities will match yours forever.
- **Data structures first, algorithms second.** Get the data representation
  right and the code almost writes itself.
- **Name things precisely.** A variable called `remaining` is better than
  `r`. A function called `expire_stale_sessions` is better than `cleanup`.
  Invest the time. Names are the cheapest documentation.
- **Simplicity requires courage.** It's easy to add complexity. It takes
  courage to say "we don't need this" and delete code that works but isn't
  necessary.

## Review Focus

When reviewing code in this style, prioritize:
1. Could a competent programmer understand this file in one sitting?
2. Are there dependencies that could be replaced with 20 lines of code?
3. Is every abstraction earning its keep, or just adding indirection?
4. Does the naming tell you what things ARE, not how they're implemented?
