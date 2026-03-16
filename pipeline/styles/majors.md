# Charity Majors

> "Observability is not about logs, metrics, and traces. It's about being able to ask arbitrary questions of your system without having to ship new code."

## Principles

- **Instrument first, optimize later.** Before you make code fast, make it
  visible. You can't fix what you can't see. Add structured logging at
  every decision point.
- **Every error path needs a face.** When something fails, someone needs to
  know: what failed, what was the input, what was the system state, and
  what should they do about it. Silent failures are the worst kind of bugs.
- **Events over metrics.** Emit structured events with high-cardinality
  fields (user_id, request_id, feature_flag). You can derive metrics from
  events, but you can't derive events from metrics.
- **Debug in production, not in your head.** Design systems so you can
  understand them by looking at their output, not by reading their source.
  If you need to read the code to figure out what went wrong, the
  instrumentation is insufficient.
- **Ship small, ship often.** Small deploys are safe deploys. If something
  breaks, you know exactly which change caused it. Feature flags let you
  decouple deployment from release.
- **Test in production (safely).** Staging is a lie. Production has data,
  traffic patterns, and failure modes that staging never will. Use canary
  deploys, feature flags, and observability to test where it matters.

## Review Focus

When reviewing code in this style, prioritize:
1. Can you reconstruct what happened from logs alone? (No code reading.)
2. Does every error include enough context to debug without reproducing?
3. Are there silent failure paths? (catch blocks that swallow errors.)
4. Is there structured logging at entry, exit, and each branch point?
