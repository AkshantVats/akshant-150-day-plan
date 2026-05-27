# Work Day 12 — Code / Infra (G-09)

**Status:** Plan mode only — no implementation until user says `approve code`.

**Calendar day:** 12 of N · **Sunday** · **LensAI** · repo: `infra-ai-streaming`

**Shared Daily Thread:** The anomalies topic is where exact rules end — semantic cache false positives will land in the same operational queue.

---

## 1. Ticket + scope

**G-09** (from `data/plan.json` day 12 `code`):

> Anomaly detection in Go consumer: z-score on inference latency per `model_id` (sliding window 100 points, flag if >3σ). On anomaly: Kafka topic `ai_anomalies`, Prometheus `anomalies_detected_total`, Grafana alert rule.

**Interpretation for today:**

| In scope | Out of scope (today) |
|----------|----------------------|
| Z-score detector on **`latency_ms`** with sliding window **100**, threshold **3.0σ** | Separate anomaly-detector **binary** or second consumer group (inline in existing consumer per `docs/7-day-plan.md`) |
| Window key **`tenant_id:model_id`** (per-tenant isolation; satisfies “per model_id” in plan) | Cost / budget burn-rate anomalies (README backlog item) |
| Publish JSON anomaly events to **`ai_anomalies`** Kafka topic | ClickHouse table for anomalies (topic-only is enough for G-09) |
| Counter **`anomalies_detected_total{tenant_id, model_id}`** on `:9091` | EWMA / CUSUM (DriftWatch days 104+) |
| **Grafana unified alert rule** (file-provisioned) firing on anomaly counter | PagerDuty/Slack notification adapters |
| Unit tests for window math + detector + publisher mock | `go test` in GitHub Actions (still local-only CI gap) |
| Topic init + `deploy/.env.example` + docs (`DESIGN.md`, `OBSERVABILITY.md`, `PROJECT-STATUS.md`, `ARCHITECTURE-AND-FLOWS.md`) | Partition key `hash(tenant_id:model_id)` on Rust producer (separate ticket) |
| Optional: one panel on **Product SLOs** or **Local E2E** dashboard showing anomaly rate | Week-2 README polish (calendar **day 13**) |
| Manual / script proof: inject spike latencies → topic + metric + alert state | Re-run full `scripts/run_chaos.sh` as deliverable |

**Design anchor:** `docs/7-day-plan.md` pseudocode (`consumer/internal/anomaly/detector.go`, lines ~1058–1072) and `OBSERVABILITY.md` metric catalog (`anomalies_detected_total`). `DESIGN.md` §3 notes separate consumer groups for anomaly detection long-term; **today** ships the detector **in-process** beside the ClickHouse writer (same poll loop) to close G-09 without a second deployable.

**Detector parameters (defaults, env-overridable):**

| Param | Default | Env var (proposed) |
|-------|---------|----------------------|
| Window size | 100 | `ANOMALY_WINDOW_SIZE` |
| Z threshold | 3.0 | `ANOMALY_Z_THRESHOLD` |
| Min samples before evaluate | 20 | `ANOMALY_MIN_SAMPLES` |
| Anomalies topic | `ai_anomalies` | `KAFKA_ANOMALIES_TOPIC` |

**Anomaly Kafka payload (v0):**

```json
{
  "tenant_id": "demo",
  "model_id": "gpt-4o",
  "latency_ms": 8500,
  "z_score": 4.12,
  "mean_ms": 340.5,
  "stddev_ms": 45.2,
  "window_size": 100,
  "threshold": 3.0,
  "detected_at_unix_ms": 1716800000123,
  "request_id": "optional-from-event"
}
```

---

## 2. Prerequisites

### Infra repo (`infra-ai-streaming`)

| Check | Status / action |
|-------|-----------------|
| **Day 10 chaos PR #5** | **MERGED** on `origin/main` (`064c234`). |
| **Day 11 OSS pointer** | **MERGED** on `main` (`88ba20a` — links Vector PR #25496). |
| Local `main` | **Pull before branch:** `git fetch origin && git checkout main && git pull origin main`. Confirm HEAD ≥ `88ba20a`. |
| Day 11 OSS work | **Done** — Vector [PR #25496](https://github.com/vectordotdev/vector/pull/25496) (open upstream; not blocking G-09). |
| Existing consumer | No `consumer/internal/anomaly/` tree yet — greenfield on current reader/sink path. |
| Compose stack | `ai_anomalies` topic **not** created by `deploy/redpanda/init-topics.sh` today — Day 12 must add it. |

### Profile repo

| Check | Status / action |
|-------|-----------------|
| **Profile PR #8** (Day 11 blogs) | **MERGED** — no merge gate for code workstream. |
| Experience / AI HTML for day 12 | **Separate approvals** — code agent does not block on blogs. |

**Blog numbering note (not blocking code):** `plan.json` sets `ai.day_index: 12` for calendar day 12; [CHECKLIST.md](../../CHECKLIST.md) rule is **Day (N−1) of N** → kicker should be **Day 11** when shipping AI post on calendar day 12. Fix in blog plan / `plan.json` during Experience/AI workstreams, not in this PR.

### Plan repo (`akshant-150-day-plan`)

- [ ] Set `data/current-day.json` → `12` when starting the workday (local only; **do not push** plan repo).
- [ ] Mark day 11 `status: done` in `plan.json` if not already (day 11 OSS complete).
- [ ] Phase 2: user approves **this file** before implementation.

### Toolchain

- Go 1.22+ (consumer module), Docker Compose, `rpk` via compose exec.
- Grafana 11.3 (compose image) — unified alerting provisioning format.

---

## 3. Numbered implementation checklist

### Phase A — Branch + config (15 min)

1. [ ] `cd /Users/akshant/Desktop/github/infra-ai-streaming && git checkout main && git pull origin main`
2. [ ] Create branch `feat/consumer-anomaly-zscore-detection` from updated `main`.
3. [ ] Extend `consumer/internal/config/config.go`: `KafkaAnomaliesTopic`, anomaly window/threshold/min-samples env vars (see §1 table).
4. [ ] Add to `deploy/.env.example`: `KAFKA_ANOMALIES_TOPIC=ai_anomalies`, anomaly tunables with comments.

### Phase B — Sliding window + z-score (1–1.5 h)

5. [ ] Create `consumer/internal/anomaly/window.go` — ring buffer `SlidingWindow` with `Add`, `Count`, `Mean`, `StdDev` (Welford or two-pass; handle `count < 2` → no anomaly).
6. [ ] Create `consumer/internal/anomaly/window_test.go` — fixed sequence, known mean/stddev; edge cases: constant values (stddev 0 → skip), window wrap at 100.
7. [ ] Create `consumer/internal/anomaly/detector.go` — `Detector` with `map[string]*SlidingWindow` keyed by `tenant_id + ":" + model_id`, `sync.RWMutex`, `Observe(event)` returning optional anomaly struct.
8. [ ] Create `consumer/internal/anomaly/detector_test.go` — feed 25 normal latencies (~300 ms), then one 5000 ms → expect z > 3; verify no fire before `minSamples`.

### Phase C — Kafka publish + metrics (45 min)

9. [ ] Create `consumer/internal/kafka/anomalies.go` — `AnomalyPublisher` mirroring `dlq.go` (`ProduceSync` to `KAFKA_ANOMALIES_TOPIC`).
10. [ ] Add `AnomaliesDetected *prometheus.CounterVec` to `consumer/internal/metrics/metrics.go` — name **`anomalies_detected_total`**, labels `tenant_id`, `model_id`.
11. [ ] Wire publisher + detector in `consumer/cmd/consumer/main.go` (init after metrics, before reader).

### Phase D — Reader integration (30 min)

12. [ ] Extend `kafka.Reader` (or inject `AnomalyObserver` interface) so each deserialized event calls `detector.Observe` **after** successful sink handoff (same record commit boundary — anomaly side effect must not block CH write; publish errors → log, do not fail offset commit).
13. [ ] Update `consumer/internal/kafka/reader_test.go` if sink mock needs anomaly hook.

### Phase E — Infra / topics (20 min)

14. [ ] Update `deploy/redpanda/init-topics.sh` and `deploy/helm/lensai/files/redpanda-init-topics.sh` — add `KAFKA_ANOMALIES_TOPIC` / `ai_anomalies` to topic loop.
15. [ ] Update `scripts/smoke-e2e.sh` — `grep -q ai_anomalies` in topic list check.

### Phase F — Grafana alert + observability docs (45 min)

16. [ ] Create `deploy/grafana/provisioning/alerting/anomaly-latency.yaml` — unified alert group **AI Inference**:
    - **Title:** `Inference latency anomaly detected`
    - **Condition:** `increase(anomalies_detected_total[5m]) > 0` (or equivalent on consumer scrape job)
    - **Labels:** `severity=warning`, `component=consumer`
    - **For:** 0m (immediate on first spike in window) or 1m if flapping during dev
17. [ ] Optional: add timeseries panel to `deploy/grafana/provisioning/dashboards/ai-inference-product.json` — `sum(rate(anomalies_detected_total[5m])) by (model_id)`.
18. [ ] Update `OBSERVABILITY.md` — document metric, PromQL alert suggestion, anomaly topic schema.
19. [ ] Update `docs/PROJECT-STATUS.md` — move anomaly line from gaps to **production-grade**.
20. [ ] Update `docs/ARCHITECTURE-AND-FLOWS.md` G-09 row → **Done**; add one lifecycle bullet (event → detector → `ai_anomalies`).
21. [ ] Update `DESIGN.md` implementation status — anomaly detector **in tree** (inline v0); note future split to dedicated consumer group.

### Phase G — Commits + showcase (30 min)

22. [ ] Commits (Conventional, small logical chunks):
    - `feat(consumer): z-score latency anomaly detector`
    - `feat(deploy): ai_anomalies topic and Grafana alert rule`
    - `docs: G-09 anomaly detection observability`
23. [ ] Run test/proof commands (§8); paste output for user showcase ([CHECKLIST.md](../../CHECKLIST.md) Phase 3.5).
24. [ ] **Do not push** until user sign-off (`approved — push and open PR`).

---

## 4. Acceptance criteria

| # | Criterion | Proof |
|---|-----------|--------|
| 1 | Z-score detector with window **100**, threshold **3σ**, min samples **20** | `go test ./consumer/internal/anomaly/...` green; test names document math |
| 2 | Anomaly fires on **`tenant_id:model_id`** latency stream | Unit test: baseline ~300 ms × 25, spike 5000 ms → publish |
| 3 | **`ai_anomalies` topic** receives JSON payload | `rpk topic consume ai_anomalies` shows record after spike script |
| 4 | **`anomalies_detected_total{tenant_id,model_id}`** increments | `curl -s localhost:9091/metrics \| grep anomalies_detected_total` |
| 5 | **Grafana alert rule** provisioned | UI → Alerting → rules → “Inference latency anomaly detected”; state **Normal** at rest, **Firing** after spike (or alert history entry) |
| 6 | Topic created on compose up | `rpk topic list` includes `ai_anomalies` |
| 7 | Existing pipeline unchanged | `./scripts/smoke-e2e.sh` passes; ingest → CH still works |
| 8 | Docs honest | `PROJECT-STATUS.md` + `ARCHITECTURE-AND-FLOWS.md` reflect G-09 shipped |
| 9 | No scope creep | No README week-2 polish, no Helm HPA changes, no Profile HTML |

---

## 5. Files to create / modify

### Create

| Path | Purpose |
|------|---------|
| `consumer/internal/anomaly/window.go` | Ring buffer + mean/stddev |
| `consumer/internal/anomaly/window_test.go` | Window math tests |
| `consumer/internal/anomaly/detector.go` | Per-key z-score detector |
| `consumer/internal/anomaly/detector_test.go` | Spike detection tests |
| `consumer/internal/kafka/anomalies.go` | Anomaly topic publisher |
| `deploy/grafana/provisioning/alerting/anomaly-latency.yaml` | Unified alert rule |

### Modify

| Path | Change |
|------|--------|
| `consumer/internal/config/config.go` | Anomaly + anomalies topic env |
| `consumer/internal/metrics/metrics.go` | `anomalies_detected_total` CounterVec |
| `consumer/internal/kafka/reader.go` | Call detector per event |
| `consumer/cmd/consumer/main.go` | Wire detector + publisher |
| `consumer/internal/kafka/reader_test.go` | Adjust if needed |
| `deploy/redpanda/init-topics.sh` | Create `ai_anomalies` |
| `deploy/helm/lensai/files/redpanda-init-topics.sh` | Same |
| `deploy/.env.example` | New env vars |
| `scripts/smoke-e2e.sh` | Topic grep |
| `deploy/grafana/provisioning/dashboards/ai-inference-product.json` | Optional anomaly panel |
| `OBSERVABILITY.md` | Metric + alert docs |
| `docs/PROJECT-STATUS.md` | G-09 done |
| `docs/ARCHITECTURE-AND-FLOWS.md` | G-09 status |
| `DESIGN.md` | Implementation status paragraph |

### Plan repo (this file)

| Path | Action |
|------|--------|
| `docs/daily-plans/day-12-CODE.md` | This plan (committed locally) |

---

## 6. Branch naming

Per [CHECKLIST.md](../../CHECKLIST.md) — **no** `day-012-*` or sprint names.

| Repo | Branch |
|------|--------|
| `infra-ai-streaming` | **`feat/consumer-anomaly-zscore-detection`** |

Optional split (only if diff is large):

| Branch | Scope |
|--------|--------|
| `feat/consumer-anomaly-zscore-detection` | Go detector + metrics + reader |
| `feat/deploy-anomaly-topic-grafana-alert` | Topic init + Grafana YAML |

Default: **one PR** on `feat/consumer-anomaly-zscore-detection`.

**Commit body example:**

```
feat(consumer): z-score latency anomaly detection (G-09)

Sliding window per tenant:model, publish ai_anomalies, expose
anomalies_detected_total for Grafana alerting.

Refs: 12 of N — infra-ai-streaming — The anomalies topic is where exact rules end.
```

---

## 7. Test / proof commands

### Unit tests

```bash
cd /Users/akshant/Desktop/github/infra-ai-streaming/consumer
go test ./internal/anomaly/... -v
go test ./...
```

### Stack + pipeline

```bash
cd /Users/akshant/Desktop/github/infra-ai-streaming
cp deploy/.env.example deploy/.env   # if missing
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d

# Terminal A
cd consumer && set -a && source ../deploy/.env && set +a && go run ./cmd/consumer

# Terminal B
set -a && source deploy/.env && set +a && cargo run -p ingestion
```

### Baseline traffic (warm windows)

```bash
for i in $(seq 1 30); do
  ts=$(python3 -c 'import time; print(int(time.time()*1000))')
  curl -sS -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/ingest \
    -H 'Content-Type: application/json' -H 'X-Tenant-ID: demo' \
    -d "{\"events\":[{\"tenant_id\":\"demo\",\"model_id\":\"gpt-4o\",\"timestamp_unix_ms\":${ts},\"latency_ms\":320,\"prompt_tokens\":10,\"completion_tokens\":5,\"cost_usd\":0.001,\"status\":\"success\"}]}"
done
```

### Spike (should fire anomaly)

```bash
ts=$(python3 -c 'import time; print(int(time.time()*1000))')
curl -sS -X POST http://localhost:8080/ingest \
  -H 'Content-Type: application/json' -H 'X-Tenant-ID: demo' \
  -d "{\"events\":[{\"tenant_id\":\"demo\",\"model_id\":\"gpt-4o\",\"timestamp_unix_ms\":${ts},\"latency_ms\":9000,\"prompt_tokens\":10,\"completion_tokens\":5,\"cost_usd\":0.001,\"status\":\"success\"}]}"
```

### Proof artifacts

```bash
# Metric
curl -s http://localhost:9091/metrics | grep anomalies_detected_total

# Topic (compose exec)
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T redpanda \
  rpk topic consume ai_anomalies -n 1 -o start

# Topics exist
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec -T redpanda rpk topic list

# Smoke regression
./scripts/smoke-e2e.sh
```

### Grafana

- Open http://localhost:3000 (`admin`/`admin`)
- **Product SLOs** `/d/ai-inference-product` — optional anomaly panel
- **Alerting → Alert rules** — confirm rule loaded; after spike, check **Firing** or history

### Showcase block for user (Phase 3.5)

Paste: commands above + expected lines (`anomalies_detected_total{tenant_id="demo",model_id="gpt-4o"} 1`, one JSON record on `ai_anomalies`, alert state change).

---

## 8. Time estimate + risks

| Item | Estimate |
|------|----------|
| Config + topic init | 0.5 h |
| Window + detector + tests | 1.5–2 h |
| Kafka publisher + reader wire | 1 h |
| Grafana alert + dashboard touch | 0.5–1 h |
| Docs + smoke proof | 0.5–1 h |
| **Total** | **4–6 h** (Sunday box) |

| Risk | Mitigation |
|------|------------|
| **Stddev = 0** (flat latency) | Skip z-score when stddev < epsilon |
| **Unbounded `windows` map** (many model_ids) | Document v0 limit; optional max-keys eviction follow-up |
| **Grafana 11 alert YAML schema** | Start from [Grafana provisioning docs](https://grafana.com/docs/grafana/latest/alerting/set-up/provision-alerting-resources/file-provisioning/); validate via compose restart + UI |
| **Alert flapping** on single spike | Accept for demo; add `For: 5m` or rate-based condition if noisy |
| **Anomaly publish fails** | Log error; do not fail CH path or offset commit |
| **Scope creep into day 13 README** | Defer polish to day 13 plan |
| **plan.json `ai.day_index` drift** | Blog agents fix to 11 when shipping day 12 posts |

---

## 9. Definition of done

User can mark Day 12 code workstream complete when:

- [ ] This plan reviewed; user said **`approve code`** (edits applied here if any).
- [ ] Branch `feat/consumer-anomaly-zscore-detection` implements G-09 per §4 acceptance table.
- [ ] `go test ./...` in `consumer/` passes; `./scripts/smoke-e2e.sh` passes.
- [ ] Manual spike proof: metric + `ai_anomalies` record + Grafana alert rule visible.
- [ ] Docs updated (`OBSERVABILITY.md`, `PROJECT-STATUS.md`, `ARCHITECTURE-AND-FLOWS.md`, `DESIGN.md` status).
- [ ] Showcase pasted in chat (commands + pass criteria).
- [ ] User sign-off recorded before **`git push`** / PR ([CHECKLIST.md](../../CHECKLIST.md) Phase 3.5).

**After approval → implementation:** Re-read this file; execute §3 checklist; do not rely on chat summary alone ([WORKFLOW.md](../../WORKFLOW.md)).

---

## 10. Out of scope

- **OSS-01 / Vector PR #25496** — day 11 complete; no upstream work required.
- **Chaos re-proof** — `scripts/run_chaos.sh` not a day 12 deliverable.
- **Week-2 README** — calendar day 13.
- **Profile blogs** — Experience “OTA at Scale…” and AI “Semantic Caching…” are separate approvals.
- **Separate anomaly consumer group / deployment** — future hardening; inline detector closes G-09.
- **ClickHouse `anomalies` table** — topic + metrics sufficient for v0.
- **Plan repo push** — local only.

---

## Cross-workstream dependencies

| Consumer | Needs from G-09 code |
|----------|----------------------|
| **Experience blog** | z-score as “edge filtering upstream”; `ai_anomalies` topic name; one metric name |
| **AI blog** | Threshold / false-positive analogy; optional PromQL snippet |
| **Day 13 README** | Screenshot of Grafana alert or anomaly panel if user wants it in week-2 polish |

**Freeze before Experience/AI HTML:** final commit SHA; exact metric name `anomalies_detected_total`; anomaly JSON field list; Grafana alert title.
