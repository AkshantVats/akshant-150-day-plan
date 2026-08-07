# Day 73 — Code Plan

**Repo:** `infra-ai-streaming`, component `prompt-fingerprinter/pkg/stack` (continuing Day 70's
DESIGN.md, Day 71's `pkg/fingerprint`, Day 72's `pkg/stack`)
**Product:** RouteIQ
**Ticket:** Prompt fingerprint collision drill — intentional hash clash test, verify TTL
isolation.

## Goal

A SHA-256 fingerprint collision is cryptographically implausible (DESIGN.md §2), but "implausible"
is not "impossible," and DESIGN.md §2 is explicit about the failure mode if one ever happened:
serving one tenant's cached response for a different prompt. Day 73 does not try to prove a
collision can't happen — no test can prove that — it exercises what the stack does to *contain*
one when it does, and closes a real gap Day 72 left open: `pkg/stack.RedisClient.Set` had no TTL,
so an L1 entry (corrupted or not) lived forever. DESIGN.md §3 already commits to "the same TTL
semantic-cache-engine's freshness-decay policy already configures, rather than inventing an
independent expiry" — that policy's hard ceiling (`semantic-cache-engine/DESIGN.md` §6) is 30
days, so Day 73 wires that exact number in as `stack.HardTTL`, not a new one.

## Scope

1. `pkg/stack/clock.go` (new) — a `Clock` interface (`Now() time.Time`) with a `RealClock`
   default and a `FakeClock` for tests, so the TTL drill can advance 30 days without a real
   30-day sleep.
2. `pkg/stack/stack.go` — `RedisClient.Set` gains a `ttl time.Duration` parameter (mirrors a real
   Redis client's `SETEX`). `Stack.Get`'s backfill now calls `Set(ctx, key, response, HardTTL)`.
   New `HardTTL = 30 * 24 * time.Hour` constant, sourced from `semantic-cache-engine/DESIGN.md`
   §6, with a comment explaining why L1 has no decay-curve analog (it's an exact-match key, not
   a similarity search — nothing for a decaying threshold to act on).
3. `pkg/stack/memstore.go` — `MemRedis` now tracks per-key expiry against an injected `Clock`.
   `Get` (and `Contains`) treat an expired key as absent, the same way a real Redis instance
   would have already evicted it via its own TTL. `NewMemRedis()` keeps its old real-clock
   default; `NewMemRedisWithClock(clock)` is new, for tests that need to control time.
4. `pkg/stack/collision_test.go` (new) — the drill itself, three tests:
   - `TestCollisionDrill_SharedKeyServesWrongResponse` — seeds `MemRedis` directly at the key a
     collision would produce (can't force real SHA-256 to collide, so the drill simulates the
     resulting *state* instead) and confirms the raw failure mode: L1 has no way to detect it's
     serving the wrong prompt's answer.
   - `TestCollisionDrill_TenantScopingContainsBlastRadius` — same corrupted key under
     `tenant-a`; confirms `tenant-b` asking the identical prompt is unaffected, because
     `RedisKey` folds `tenant_id` into the key itself.
   - `TestCollisionDrill_TTLBoundsBlastRadius` — a `FakeClock` advances to one second before
     `HardTTL` (still corrupted — the bound is exact, not approximate) and then past it (expired,
     self-heals via a fresh L2 lookup, no operator intervention).
5. `pkg/stack/stack_test.go` — one existing direct `redis.Set` call updated to the new
   four-argument signature (`Set(ctx, key, value, HardTTL)`); no behavioral change to the six
   Day 72 tests.
6. `README.md` — new paragraph under "Cache stack" documenting `HardTTL`'s provenance and what
   the collision drill does and does not prove.

## Out of scope

- No real SHA-256 collision is manufactured (not possible in a test) — the drill simulates the
  *post-collision state* directly, which exercises the same code path a real collision would.
- No live Redis instance (no Docker daemon, same constraint every prior day here has logged) —
  `MemRedis`'s own expiry tracking is what stands in for Redis's native `EXPIRE`.
- No change to the decay-curve half of semantic-cache-engine's §6 policy — that curve is a
  similarity-threshold mechanism with no L1 analog, as noted in `stack.HardTTL`'s doc comment.

## Tests

Table/scenario tests for the collision drill plus one updated call site in the existing Day 72
suite. Target ≥90% pass rate per the build-slot threshold; ran locally at 16/16 (100%),
`gofmt`/`go vet`/`golangci-lint` clean, race-clean (`-race`).
