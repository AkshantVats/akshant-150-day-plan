# Day 65 — Code Plan

**Repo:** `infra-ai-streaming`, component `cost-budget-enforcer/` (new subdirectory module,
continuing the Day 60 `semantic-cache-engine/` precedent — not a separate GitHub repo)
**Product:** RouteIQ
**Ticket:** cost-budget-enforcer — DESIGN.md: sliding window token budgets in Redis, hard vs
soft limits, graceful degradation route to cheaper model, webhook alerts at 80% budget.

## Goal

Day 60 opened the RouteIQ arc with `semantic-cache-engine`, a response cache. Day 65 opens
the arc's second module: a per-tenant spend guardrail that caps LLM token usage inside a
rolling window. Like Day 60, this is a design-doc-only day — the four decisions needed before
any runtime code exists: the sliding-window budget mechanism, the hard-vs-soft limit split,
the graceful-degradation routing policy, and the webhook alert contract.

## Scope

1. `cost-budget-enforcer/DESIGN.md` — §1 sliding-window token budget in Redis (weighted
   two-bucket counter, Lua-atomic check-and-increment); §2 hard vs soft limits (80% alert /
   100% soft limit routes to a cheaper model / 120% hard limit rejects with 429); §3 why the
   soft-limit route mirrors the Wayfair pricing API's fail-open circuit breaker philosophy,
   applied to a cost axis instead of an availability axis; §4 debounced webhook alert at 80%
   of budget (SETNX-gated, one fire per window); out-of-scope section noting no live Redis run
   in this sandbox (no Docker daemon) and no change to `ingestion`'s existing request-rate
   limiter, which stays a separate mechanism in a separate Redis keyspace.
2. `README.md` — adds `cost-budget-enforcer/` as a sixth row in the TraceForge/RouteIQ
   component table, marked design-only, mirroring how `semantic-cache-engine` was added on
   Day 60.

## Out of scope

- No runtime code, migrations, or Kafka topics — same shape as Day 60's DESIGN.md-first day.
- No live Redis instance exercised (no Docker daemon in this sandbox) — the Lua script in the
  design doc is validated by reading, not by running.
- No change to `ingestion`'s existing per-tenant rate limiter — token spend and request rate
  are deliberately kept as separate guardrails with separate Redis keyspaces.

## Tests

None — design-doc-only day, no runtime code to test. Same as Day 60's `semantic-cache-engine`
DESIGN.md commit.
