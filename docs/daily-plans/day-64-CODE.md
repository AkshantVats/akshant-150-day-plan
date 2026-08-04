# Day 64 — Code Plan

**Repo:** `infra-ai-streaming`, component `semantic-cache-engine/` (subdirectory module,
continuing the Day 44+ / Day 60–63 precedent — not a separate GitHub repo)
**Product:** RouteIQ
**Ticket:** semantic-cache-engine README + docker-compose with postgres/pgvector. Load test
1k QPS lookups — p99 latency under 15ms on M1 Max baseline.

## Goal

Days 60–63 built the cache end to end (DESIGN.md → embedding worker → lookup path → cache
analytics) but every one of those days ran against `pkg/localsim`/in-memory fakes or pure unit
tests — nothing in this module has ever been exercised against a real Postgres+pgvector
instance, and nothing has measured the lookup path's actual latency distribution under
concurrent load. Day 64 closes both gaps: a `docker-compose.yml` that boots a real
pgvector-enabled Postgres with `schema/001_semantic_cache_entries.sql` applied on first start,
and a load-test harness that drives `cachestore.Reader` (the same interface
`cmd/cachelookup` uses) at a target QPS and reports p50/p95/p99 latency.

## Scope

1. `semantic-cache-engine/docker-compose.yml` — single `postgres` service on
   `pgvector/pgvector:pg16`, schema SQL mounted as a `docker-entrypoint-initdb.d` init script,
   healthcheck via `pg_isready`, host port `5433` (repo's other compose files don't use 5432,
   but 5433 avoids clobbering any host-level Postgres). No app services — this module's CLIs
   already run outside Docker via `go run`.
2. `pkg/loadtest` — a `Run(ctx, Config, cachestore.Reader)` harness: a closed-loop ticker at
   `Config.QPS`, dispatching onto a bounded worker pool of `Config.Concurrency`, timing each
   `FindNearest` call (the ANN/hnsw index path — the one whose latency actually depends on
   index size and tuning, unlike `FindExact`'s primary-key lookup), and reporting
   p50/p95/p99 plus achieved throughput. Also exports `MemStore`, an in-memory
   `cachestore.Reader` with a configurable simulated round-trip latency, so the harness (and
   `cmd/loadtest`'s default mode) runs without a live Postgres — same "fake stands in for an
   unavailable live dependency, documented as such" shape `pkg/localsim` established for
   `cmd/threshold-sweep` on Day 63.
3. `cmd/loadtest` — CLI wiring flags (`--qps`, `--duration`, `--concurrency`, `--dsn`,
   `--sim-latency`) to `pkg/loadtest.Run`. `--dsn` (or `PGVECTOR_DSN`) unset → seeds and runs
   against `MemStore`; set → connects via `cachestore.NewPostgresWriter` (which also implements
   `Reader`), seeds one synthetic entry per tenant, and drives real `FindNearest` calls against
   the live pgvector index.
4. `README.md` — new "Load test (Day 64)" section: `docker compose up -d`, then
   `PGVECTOR_DSN=... go run ./cmd/loadtest --dsn "$PGVECTOR_DSN"`; update the Status line.
5. `DESIGN.md` — §10, documenting the load-test harness's design (why `FindNearest` not the
   full `Lookup()` embed+lookup path — embedding-API latency is a separate SLA from the
   index's own query latency, and conflating them would blame the index for OpenAI's response
   time) and the sandbox constraint below.
6. `BENCHMARKS.md` — a "Day 64 — Load test" section with real numbers from this sandbox run
   against `MemStore` (no Docker daemon available here — `docker ps` fails with
   `dial unix /var/run/docker.sock: connect: no such file or directory`, the same constraint
   Day 56 logged), stated plainly as a simulated-latency proxy for the DB round trip, not a
   live pgvector measurement, alongside the exact commands to reproduce against a real instance
   once Docker is available.

## Out of scope

- No live Postgres/pgvector run in this sandbox (no Docker daemon) — `docker-compose.yml` is
  validated with `docker compose config` only, matching Day 56's documented gap for its
  unified compose file.
- No change to `pkg/lookup`, `pkg/cachestore`, or the lookup/threshold logic itself — Day 64
  measures the existing Day 62 path, it does not change it.
- No k6/HTTP load test — this module's lookup path is a library (`pkg/lookup`) driven by a
  batch CLI (`cmd/cachelookup`), not a running HTTP service, so the harness drives the
  `cachestore.Reader` interface directly in-process rather than introducing an HTTP server
  whose latency would then include request-framing overhead nothing in production has.

## Tests

Unit tests for `pkg/loadtest`: percentile computation (`computePercentiles`) against a known
fixed slice of durations, `MemStore.FindExact`/`FindNearest` correctness (hit/miss, per-tenant
isolation), and `Run` end-to-end against `MemStore` with a small QPS/duration (asserting
request count, zero errors, and p50 <= p95 <= p99 ordering). `cmd/loadtest` tests mirror
`cmd/embedworker/main_test.go`'s shape (`run(args, stdout, stderr) int`, captured output).
Target 100% pass on the unit suite.
