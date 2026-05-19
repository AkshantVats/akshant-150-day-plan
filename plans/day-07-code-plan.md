# Plan A — Code (Day 7 · Ticket G-06)

**Status:** Plan mode only — no implementation until `approve code`.

---

## Metadata

| Field | Value |
|-------|--------|
| **Calendar day** | 7 of N |
| **Ticket** | G-06 |
| **Repo** | `akshantvats/infra-ai-streaming` |
| **Branch** | `feat/per-tenant-rate-limits-chaos` |
| **Depends on** | G-05 merged on `main` (PR #2 — product SLO dashboard + `kafka_consumer_lag_events`) |

## What ships (single observable outcome)

**Per-tenant rate-limit configuration** (not one global `RATE_LIMIT_DEFAULT_RPS` for everyone) plus a committed **`CHAOS.md`** runbook for five failure scenarios — with ingest still returning **429 + `Retry-After`** when a tenant exceeds quota, and **documented fail-open** when Redis is unavailable.

## Why today (platform narrative)

Day 6 proved the schema in Grafana. Day 7 proves **noisy-neighbor containment**: a tenant on a pricing-style burst cannot starve others. The thread ties Redis loss to fairness — without a shared bucket store you either block everyone or admit everyone; fail-open is an explicit product choice, not an accident.

## Baseline on `main` (do not re-build)

Already shipped in G-01:

- `ingestion/src/rate_limit/token_bucket.rs` — Redis Lua token bucket, key `ratelimit:{tenant_id}`
- `ingestion/src/handlers/ingest.rs` — **429** + `Retry-After` on deny; metric `rate_limited_requests_total{tenant_id}`
- **Fail-open** on Redis connection/script errors (DESIGN.md §5 row 3)
- `./scripts/demo-flows.sh rate-limit` + e2e panel for rate limits

**G-06 delta:** configurable limits per tenant + formal chaos doc + tests/docs — not a second bucket implementation.

---

## Architecture impact

| Area | Change |
|------|--------|
| **Config** | Per-tenant `max_events_per_sec` + `burst_multiplier` (file and/or Redis hash) |
| **Rate limiter** | Lua or Rust lookup: resolve limits for `tenant_id`, fall back to global defaults |
| **Observability** | Optional label `limit_source=default|tenant` on deny metric (only if cardinality-safe — prefer logs) |
| **Docs** | New root `CHAOS.md`; cross-link from `DESIGN.md` §5, `README.md`, `END-TO-END-FLOWS.md` |
| **Compose** | Example tenant limits in `deploy/tenant-limits.example.json` or env doc |

---

## Design choices (recommend one path)

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **A. JSON file** mounted in compose | Simple, git-reviewed, no extra Redis schema | Requires reload/restart for limit changes | **v1 ship** |
| **B. Redis hash `tenant_limits:{id}`** | Hot reload, multi-replica consistent | Ops complexity, needs seed script | **v1.1** or hybrid: file seeds Redis on startup |
| **C. Fail-closed when Redis down** | Strict fairness | Availability hit; contradicts current DESIGN | **Out of scope** — document only |

**Recommendation:** **A + optional B seed** — load `TENANT_LIMITS_PATH` at startup into in-memory map; Lua receives per-tenant `rps`/`burst` as ARGV (extend script, keep atomicity).

---

## Files to touch

| Path | Action |
|------|--------|
| `ingestion/src/config.rs` | `tenant_limits_path`, parse limits file |
| `ingestion/src/rate_limit/mod.rs` | Export tenant limit resolver |
| `ingestion/src/rate_limit/token_bucket.rs` | Per-tenant ARGV; unit tests with mock Redis |
| `ingestion/src/rate_limit/tenant_limits.rs` | **New** — parse/validate JSON schema |
| `ingestion/src/handlers/ingest.rs` | Wire resolver; ensure `Retry-After` uses tenant-specific retry_ms |
| `deploy/tenant-limits.example.json` | **New** — 2–3 tenants + default |
| `deploy/.env.example` | `TENANT_LIMITS_PATH=...` |
| `CHAOS.md` | **New** — 5 scenarios (below) |
| `DESIGN.md` | Link to CHAOS.md; note per-tenant limits |
| `README.md` | Quickstart: set low limit for demo tenant |
| `docs/END-TO-END-FLOWS.md` | Per-tenant limit demo steps |
| `OBSERVABILITY.md` | Rate-limit panel + fail-open metric/log guidance |
| `ingestion/src/rate_limit/token_bucket.rs` (tests) | Deny/allow edge cases |

**Not in scope today:** `chaos/run_chaos.sh` (calendar day 10), Helm (G-07), fail-closed mode, k6 in CI.

---

## CHAOS.md — five scenarios (content contract)

Mirror DESIGN.md §5; each section: **trigger · expected behavior · recovery · data-loss / fairness note · how to demo locally**.

1. **Kafka broker dies mid-ingest** — WAL holds; producer retries; no silent drop of fsynced WAL entries.
2. **ClickHouse timeout** — consumer breaker opens; Redis overflow LIST; lag grows; offsets not committed past policy.
3. **Redis lost (rate limit path)** — **fail-open**: ingest accepts; `rate_limited_requests_total` quiet; log/metric `redis_rate_limit_degraded` (add if missing); CHAOS explains "decorated DoS" if you had fail-closed.
4. **Ingestion OOM** — pod kill; WAL replay on restart; at-least-once duplicates possible.
5. **Network partition (consumer ↔ ClickHouse)** — insert failures; breaker; no forward commit until heal.

Each scenario links to `./scripts/demo-flows.sh` subcommand where one exists, or a one-line `docker compose pause` instruction.

---

## Tests

| Test | Type | Assert |
|------|------|--------|
| Tenant A limit 10 rps, Tenant B 1000 rps | Unit + Redis integration (feature-gated) | A gets 429 before B under hammer |
| Denied response | Unit (handler) | Status 429, body `rate_limit_exceeded`, `Retry-After` ≥ 1 |
| Unknown tenant | Unit | Uses global default from env |
| Malformed limits file | Unit | Startup error or safe default (pick one, document) |
| Redis down | Unit/mock | `Allowed` (fail-open) + warn log |
| Limits file reload | Optional | Out of scope unless hot-reload chosen |

Run: `cargo test -p ingestion` · existing `go test ./...` unchanged unless consumer touched.

---

## Demo story — how you'll experience the feature locally

This isn't a command list. This is what happens when you sit down, run the stack, and break things on purpose.

**Scene 1 — The happy path feels invisible.** You `docker compose up -d` and run `demo-flows.sh happy-path`. Events flow. Grafana shows green. Nothing is interesting yet — because rate limiting only matters when someone pushes too hard.

**Scene 2 — Tenant "demo-greedy" hits the wall.** You've set `tenant-demo` to 5 rps in `tenant-limits.example.json`. Now you `curl` 20 requests in a second. The first 5 return `202 Accepted`. Request 6 comes back `429 Too Many Requests` with a `Retry-After: 1` header. In Grafana's "Errors & rejections" panel, `rate_limited_requests_total{tenant_id="tenant-demo"}` spikes. Meanwhile `tenant-b` (configured at 1000 rps) is unbothered — its events still land in ClickHouse. That's the noisy-neighbor story: one tenant's burst doesn't steal another's throughput.

**Scene 3 — Redis disappears, and ingest keeps going.** You run `docker compose stop redis`. Then you `curl` another batch as `tenant-demo`. This time every request returns `202` — the rate limiter has no state store, so it **fails open**. The logs show `redis_rate_limit_degraded`. The 429 counter goes silent. This is the moment you feel the tradeoff: availability won, but fairness lost. `CHAOS.md` scenario 3 documents exactly this — because if you don't know your fail mode, your fail mode chooses you.

**Scene 4 — Redis comes back, limits resume.** `docker compose start redis`. Next burst from `tenant-demo` is rate-limited again. The `Retry-After` header returns. The system didn't need a restart, a config push, or a prayer — the Lua script picks up the existing key `ratelimit:tenant-demo` and enforces.

**The punch line you want in a demo:** "When Redis is up, noisy tenants get 429. When Redis is down, everyone gets through. That's a product decision, not a bug — and CHAOS.md proves it."

---

## Demo commands (reference)

```bash
cd infra-ai-streaming/deploy && docker compose up -d
# Set TENANT_LIMITS_PATH to example with tenant-demo=5 rps
./scripts/demo-flows.sh happy-path
./scripts/demo-flows.sh rate-limit   # with RATE_LIMIT_DEFAULT_RPS=10 or low tenant-demo cap
```

**Verify in Grafana:**

- `ai-inference-e2e-local` → Errors & rejections → `rate_limited_requests_total` by `tenant_id`
- `curl -i` showing `HTTP/1.1 429` and `Retry-After: N`
- `CHAOS.md` scenario 3: stop Redis (`docker compose stop redis`), POST still 202, log line fail-open

---

## Definition of done

- [ ] Per-tenant limits enforced in ingest path (at least JSON file)
- [ ] `CHAOS.md` committed with all 5 scenarios + local repro steps
- [ ] Tests green; README quickstart updated
- [ ] No regression to G-05 dashboards on `main`
- [ ] Local showcase commands pasted in chat; user sign-off before push/PR

## Out of scope

- Automated chaos runner (`run_chaos.sh`)
- Changing fail-open to fail-closed
- Per-tenant limits in Helm ConfigMap (G-07)
- BENCHMARKS.md load numbers
- Resume/LinkedIn updates (day 6 carryover — optional chore commit)

---

## Commit outline (after implementation)

1. `feat(ingestion): per-tenant rate limit config via tenant-limits file`
2. `docs: add CHAOS.md failure runbook for five scenarios`
3. `docs: README and E2E flows for tenant rate limit demo`

Body footer: `Refs: 7 of N — infra-ai-streaming — <Daily Thread one-liner>`

---

## Cross-workstream dependencies

| Consumer | Needs from code |
|----------|-----------------|
| **Experience blog** | Example 429 response, Wayfair burst story alignment, link to `CHAOS.md` §3 |
| **AI blog** | Quantization analogy only — optional mention of INT8 storage vs Snappy on disk (no code coupling) |

**Freeze before HTML:** final `tenant-limits.example.json` shape; one real `curl -i` 429 capture; commit SHA.
