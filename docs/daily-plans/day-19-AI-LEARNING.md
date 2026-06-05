# Day 19 AI Learning Blog

**Title:** Day 19 — Agent Infrastructure — Tools, Memory, Loops
**Subtitle:** Production agents need queues, idempotency, and traces
**File:** `Profile/blog/series/ai-learning/day-19-agent-infrastructure-tools-memory-loops.html`
**Live:** https://akshantvats.github.io/Profile/blog/series/ai-learning/day-19-agent-infrastructure-tools-memory-loops.html
**Format:** deep-dive
**Hook:** Tool calling is RPC with hallucination risk — your streaming stack already handles worse RPC fan-out.

## Summary

Tool calling as RPC (map-reduce analogy, hallucination as schema validation failure).
Agent memory as tiered cache (in-context hot, retrieval warm, persistent cold).
Context eviction as Redis force-evict analogy. Agent loops with WAL for durable execution.
Observability: step count, token/step, tool error rate. eBPF sidecar for zero-SDK agent tracing.
