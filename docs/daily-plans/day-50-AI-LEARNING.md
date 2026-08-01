# Day 50 — AI Learning Blog Plan

**Title**: Day 50 — Operability — CLI as API
**Subtitle**: replay, diff subcommands
**Hook**: If it's not scriptable, on-call won't run it at 3am.
**day_index**: 50

## Angle

Clone the GOLD post's depth (`day-2-continuous-batching-vllm.html`) and the most recent AI
Learning post's structure (Day 49). Reader already knows a CLI as "the thing you type instead
of clicking a UI"; new concept is a CLI *as an API* — a contract other scripts, CI jobs, and
tired humans can call the same way every time, with stable flags and parseable exit codes,
instead of a grab-bag of commands that only make sense read top to bottom by a human.

Cover, in order:

1. **Hook**: "If it's not scriptable, on-call won't run it at 3am," then the concrete failure
   mode: a debugging tool with five undocumented ways to combine its flags is a tool nobody
   trusts enough to run under pressure.
2. **DS analogy (attr-box team)**: a well-labeled circuit breaker panel vs. a junction box with
   unlabeled wires — both technically let you cut power, but only one is safe to use by someone
   who didn't wire it.
3. **`replay` and `diff` as a contract, not a grab-bag**: both subcommands take the same shape
   of input (`--log`, one or two `--trace-*` ids), return the same shape of output (stdout for
   the result, nonzero exit for failure), and compose the same way whether a human types them or
   a CI script calls them. Mermaid diagram: Runbook Step → CLI Flag → Exit Code → Next Action.
4. **The smoke test as a contract test**: `scripts/smoke_test.sh` isn't testing replay logic
   (the unit suite already does that) — it's testing that the CLI's *interface* still behaves
   the way the README promises, which is a different and just as necessary kind of correctness.
5. **Where "CLI as API" earns its keep**: the same `traceforge replay --inject-timeout N`
   invocation a human runs by hand in the runbook is exactly what CI runs unattended — no
   separate "automation-friendly mode" needed, because the interface was designed scriptable
   from the start.
6. **Closer**: a debugging tool's operability is a design decision made at the flag-parsing
   layer, not a feature bolted on after the mechanism is built.

Required: mermaid init block (CLAUDE.md section 4.5), labels ≤6 words, attr-box DS analogy,
ai.hook opening line, `<strong>So what:</strong>` inline matching Day 49 AI Learning's
convention.
