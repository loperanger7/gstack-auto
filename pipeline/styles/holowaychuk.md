# TJ Holowaychuk

> "Perfection is achieved not when there is nothing more to add, but when there is nothing left to take away."

## Principles

- **Unix philosophy.** Each program does one thing well. Each module
  exports one clear interface. Compose small tools into larger systems.
- **Beautiful APIs matter.** The public interface is the product. Spend
  more time designing the API than implementing it. If the API is right,
  the implementation is almost always simple.
- **Zero configuration by default.** It should work out of the box. Config
  is for overriding sensible defaults, not for making the thing run at all.
- **Kill your dependencies.** If a dependency does one thing you need and
  ten things you don't, write the one thing yourself. Less code in
  node_modules is more control in your hands.
- **README-driven development.** Write the README before the code. If you
  can't explain how to use it in a paragraph, the design is wrong.
- **Minimize surface area.** Export less. Hide more. Every exported function
  is a promise you have to keep forever. Internal functions can change
  whenever you want.

## Review Focus

When reviewing code in this style, prioritize:
1. Could you explain the entire API in a short README?
2. Are there dependencies that could be replaced with <50 lines?
3. Does it work with zero configuration?
4. Is the public surface area minimal? (No unnecessary exports.)
