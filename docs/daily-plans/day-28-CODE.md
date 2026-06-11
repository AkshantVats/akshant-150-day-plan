# Day 28 — Code Plan
## lensai-integration Day 1 — Unified Docker Compose Quickstart + Org Setup

**Calendar**: Friday, June 12 2026 · Day 28 of 150
**Product**: LensAI
**Repo**: `AkshantVats/lensai-integration` (new repo — Day 28 creates it)
**Language**: Shell, YAML (docker-compose), SQL, Grafana JSON
**Builds on**: Days 21–27 — infra-ai-streaming (Rust ingest + ClickHouse), distributed-flagd (Go feature flags + etcd + Kafka audit), ebpf-llm-tracer (eBPF kernel probes)

### Shared Thread
> Landing page demo GIF must show eBPF → ingest → flagd → Grafana or it's marketing, not engineering.

---

## Summary

Day 28 is the integration day. Three repos — infra-ai-streaming, distributed-flagd, ebpf-llm-tracer — have been built independently over 27 days. Today they run together for the first time.

Two parallel tracks:

1. **GitHub org setup (manual steps)** — Create `lensai-dev` GitHub org, transfer the three repos under it. These steps require GitHub UI actions; the plan documents exact steps in `docs/ORG-SETUP.md`.

2. **Unified docker-compose quickstart** — A `lensai-integration` repo (initially under `AkshantVats`, transferred to `lensai-dev` after org creation) with a `quickstart/` directory containing: docker-compose.yml with all services, Grafana dashboard provisioning, and `scripts/smoke.sh` that exits 0 when events flow end-to-end.

Acceptance criterion: `bash scripts/smoke.sh` exits 0 on a clean Linux machine with Docker installed. No other dependencies.

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|---------------|
| AC-1 | `lensai-integration` repo exists with `quickstart/docker-compose.yml` | GitHub URL accessible |
| AC-2 | `docker-compose up -d` completes without error in `quickstart/` | Command output in PR description |
| AC-3 | Grafana pre-provisioned: datasource + LensAI overview dashboard on first startup | Screenshot or curl output |
| AC-4 | `scripts/smoke.sh` exits 0 when all services healthy and events flow ingest → ClickHouse | Script output in PR description |
| AC-5 | `scripts/smoke.sh` exits 1 with clear message if any service unhealthy | Tested by stopping one service |
| AC-6 | `quickstart/README.md` has one-command quickstart: `git clone ... && cd quickstart && bash scripts/smoke.sh` | README rendered on GitHub |
| AC-7 | `docs/ORG-SETUP.md` documents the manual GitHub org steps | File present |

---

## Part 1 — GitHub Org Setup (Manual Steps for Akshant)

The agent creates `docs/ORG-SETUP.md` with these steps. Akshant executes them manually.

### 1.1 Create lensai-dev org

1. Visit https://github.com/organizations/new
2. Organization name: `lensai-dev`
3. Plan: Free
4. Add Akshant as owner

### 1.2 Transfer repos

For each repo, go to Settings → Danger Zone → Transfer ownership:
- `AkshantVats/infra-ai-streaming` → `lensai-dev/infra-ai-streaming`
- `AkshantVats/ebpf-llm-tracer` → `lensai-dev/ebpf-llm-tracer`

(distributed-flagd lives inside infra-ai-streaming as a module — no separate transfer.)

### 1.3 Create lensai-integration under lensai-dev

1. Visit https://github.com/organizations/lensai-dev/repositories/new
2. Repo name: `lensai-integration`
3. Visibility: Public
4. Do not initialize with README (agent pushes one)

### 1.4 Update remote URLs after transfer

```bash
source akshant-agent/.agent/credentials.env
git remote set-url origin https://${GITHUB_PAT}@github.com/lensai-dev/lensai-integration.git
```

---

## Part 2 — docker-compose Quickstart

### 2.1 Directory structure

```
lensai-integration/
├── quickstart/
│   ├── docker-compose.yml
│   ├── clickhouse/
│   │   └── init/
│   │       └── 00_schema.sql
│   ├── grafana/
│   │   └── provisioning/
│   │       ├── datasources/
│   │       │   └── clickhouse.yaml
│   │       └── dashboards/
│   │           ├── dashboards.yaml
│   │           └── lensai-overview.json
│   └── README.md
├── scripts/
│   └── smoke.sh
└── docs/
    └── ORG-SETUP.md
```

### 2.2 docker-compose.yml

```yaml
version: "3.9"

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
    healthcheck:
      test: ["CMD", "bash", "-c", "echo ruok | nc localhost 2181"]
      interval: 10s
      timeout: 5s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      zookeeper:
        condition: service_healthy
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    healthcheck:
      test: ["CMD", "kafka-topics", "--bootstrap-server", "localhost:9092", "--list"]
      interval: 15s
      timeout: 10s
      retries: 5

  clickhouse:
    image: clickhouse/clickhouse-server:24.1
    ports:
      - "8123:8123"
    volumes:
      - ./clickhouse/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  etcd:
    image: quay.io/coreos/etcd:v3.5.12
    command:
      - etcd
      - --advertise-client-urls=http://etcd:2379
      - --listen-client-urls=http://0.0.0.0:2379
    healthcheck:
      test: ["CMD", "etcdctl", "--endpoints=http://localhost:2379", "endpoint", "health"]
      interval: 10s
      timeout: 5s
      retries: 5

  flagd:
    image: ghcr.io/akshantvats/infra-ai-streaming/flagd:latest
    depends_on:
      etcd:
        condition: service_healthy
      kafka:
        condition: service_healthy
    environment:
      ETCD_ENDPOINTS: etcd:2379
      KAFKA_BROKERS: kafka:9092
      HTTP_PORT: "8080"
      GRPC_PORT: "9090"
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  ingest:
    image: ghcr.io/akshantvats/infra-ai-streaming/ingest:latest
    depends_on:
      kafka:
        condition: service_healthy
      clickhouse:
        condition: service_healthy
    environment:
      KAFKA_BROKERS: kafka:9092
      CLICKHOUSE_URL: clickhouse:9000
      KAFKA_TOPIC: lensai-inference-events
    ports:
      - "4000:4000"

  ebpf-tracer:
    image: ghcr.io/akshantvats/ebpf-llm-tracer/tracer:latest
    profiles: ["ebpf"]
    privileged: true
    pid: host
    volumes:
      - /sys/kernel/debug:/sys/kernel/debug:ro
      - /sys/fs/bpf:/sys/fs/bpf
    environment:
      KAFKA_BROKERS: kafka:9092
      KAFKA_TOPIC: lensai-inference-events
    depends_on:
      kafka:
        condition: service_healthy

  grafana:
    image: grafana/grafana:10.3.0
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: lensai
      GF_INSTALL_PLUGINS: grafana-clickhouse-datasource 4.0.0
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      clickhouse:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:3000/api/health"]
      interval: 15s
      timeout: 10s
      retries: 5
```

**Note on eBPF:** The `ebpf-tracer` service uses `profiles: ["ebpf"]` so it does not start by default (`docker-compose up -d`). Start it explicitly with `docker-compose --profile ebpf up -d` on a Linux host with kernel debug access. The smoke test skips the eBPF check unless `LENSAI_SMOKE_EBPF=1` is set.

### 2.3 ClickHouse schema init

`quickstart/clickhouse/init/00_schema.sql`:
```sql
CREATE DATABASE IF NOT EXISTS lensai;

CREATE TABLE IF NOT EXISTS lensai.inference_events
(
    request_id        String,
    model             String,
    resolved_model_id String DEFAULT model,
    prompt_tokens     UInt32,
    completion_tokens UInt32,
    duration_ms       UInt32,
    status_code       UInt16,
    total_cost_usd    Float64 DEFAULT 0.0,
    ingested_at       DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (ingested_at, model)
PARTITION BY toYYYYMM(ingested_at);
```

### 2.4 Grafana datasource provisioning

`quickstart/grafana/provisioning/datasources/clickhouse.yaml`:
```yaml
apiVersion: 1
datasources:
  - name: ClickHouse
    type: grafana-clickhouse-datasource
    isDefault: true
    jsonData:
      host: clickhouse
      port: 8123
      username: default
      defaultDatabase: lensai
    secureJsonData:
      password: ""
```

`quickstart/grafana/provisioning/dashboards/dashboards.yaml`:
```yaml
apiVersion: 1
providers:
  - name: LensAI
    orgId: 1
    folder: LensAI
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

### 2.5 LensAI overview dashboard panels

`quickstart/grafana/provisioning/dashboards/lensai-overview.json` — four panels:

**Panel 1 — Inference Rate (time series):**
```sql
SELECT toStartOfMinute(ingested_at) as t, count() as reqs
FROM lensai.inference_events
WHERE ingested_at > now() - INTERVAL 10 MINUTE
GROUP BY t ORDER BY t
```

**Panel 2 — P99 Latency (time series):**
```sql
SELECT toStartOfMinute(ingested_at) as t,
  quantile(0.99)(duration_ms) as p99
FROM lensai.inference_events
WHERE ingested_at > now() - INTERVAL 10 MINUTE
GROUP BY t ORDER BY t
```

**Panel 3 — Cost by model (bar chart, resolved_model_id):**
```sql
SELECT resolved_model_id, sum(total_cost_usd) as cost
FROM lensai.inference_events
WHERE toDate(ingested_at) = today()
GROUP BY resolved_model_id ORDER BY cost DESC
```

**Panel 4 — Error rate (time series):**
```sql
SELECT toStartOfMinute(ingested_at) as t,
  countIf(status_code >= 500) / count() as error_rate
FROM lensai.inference_events
WHERE ingested_at > now() - INTERVAL 10 MINUTE
GROUP BY t ORDER BY t
```

Generate the full Grafana JSON by copying the dashboard JSON structure from an existing panel template. Use `"type": "timeseries"` for panels 1, 2, 4 and `"type": "barchart"` for panel 3.

### 2.6 smoke.sh

```bash
#!/usr/bin/env bash
# scripts/smoke.sh
# SPDX-License-Identifier: MIT
# Smoke test: verify events flow ingest → ClickHouse, Grafana provisioned.
# Usage: bash scripts/smoke.sh
# Set LENSAI_SMOKE_EBPF=1 to also verify eBPF tracer container.
# Exit 0: all checks pass. Exit 1: failure with diagnostic message.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUICKSTART_DIR="${SCRIPT_DIR}/../quickstart"
CLICKHOUSE_URL="http://localhost:8123"
GRAFANA_URL="http://localhost:3000"
INGEST_URL="http://localhost:4000"
MAX_WAIT=120
CHECK_INTERVAL=5

log() { echo "[smoke] $*" >&2; }
fail() { echo "[FAIL] $*" >&2; exit 1; }

# Step 1: Start services
log "Starting services..."
cd "${QUICKSTART_DIR}"
docker-compose up -d

# Step 2: Wait for Grafana
log "Waiting for Grafana (max ${MAX_WAIT}s)..."
elapsed=0
until curl -sf "${GRAFANA_URL}/api/health" > /dev/null; do
  sleep ${CHECK_INTERVAL}
  elapsed=$((elapsed + CHECK_INTERVAL))
  [ ${elapsed} -ge ${MAX_WAIT} ] && fail "Grafana did not become healthy within ${MAX_WAIT}s"
done
log "Grafana healthy"

# Step 3: Wait for ClickHouse
log "Waiting for ClickHouse (max ${MAX_WAIT}s)..."
elapsed=0
until curl -sf "${CLICKHOUSE_URL}/ping" > /dev/null; do
  sleep ${CHECK_INTERVAL}
  elapsed=$((elapsed + CHECK_INTERVAL))
  [ ${elapsed} -ge ${MAX_WAIT} ] && fail "ClickHouse did not become healthy within ${MAX_WAIT}s"
done
log "ClickHouse healthy"

# Step 4: Wait for ingest service
log "Waiting for ingest service (max ${MAX_WAIT}s)..."
elapsed=0
until curl -sf "${INGEST_URL}/health" > /dev/null; do
  sleep ${CHECK_INTERVAL}
  elapsed=$((elapsed + CHECK_INTERVAL))
  [ ${elapsed} -ge ${MAX_WAIT} ] && fail "Ingest service did not become healthy within ${MAX_WAIT}s"
done
log "Ingest service healthy"

# Step 5: Inject a synthetic inference event
log "Injecting synthetic inference event..."
curl -sf -X POST "${INGEST_URL}/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "smoke-test-001",
    "model": "gpt-4o",
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "duration_ms": 450,
    "status_code": 200
  }' || fail "Ingest endpoint not responding on POST /ingest"
log "Event injected"

# Step 6: Wait for event in ClickHouse (up to 30s)
log "Waiting for event in ClickHouse..."
elapsed=0
until [ "$(curl -sf "${CLICKHOUSE_URL}/?query=SELECT+count()+FROM+lensai.inference_events+WHERE+request_id%3D'smoke-test-001'+FORMAT+TabSeparated" 2>/dev/null)" = "1" ]; do
  sleep ${CHECK_INTERVAL}
  elapsed=$((elapsed + CHECK_INTERVAL))
  [ ${elapsed} -ge 30 ] && fail "Event 'smoke-test-001' did not appear in ClickHouse within 30s"
done
log "Event found in ClickHouse"

# Step 7: Verify Grafana dashboard provisioned
log "Verifying Grafana dashboard provisioned..."
DASHBOARD_COUNT=$(curl -sf "http://admin:lensai@localhost:3000/api/search?type=dash-db" \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
if [ "${DASHBOARD_COUNT}" -lt 1 ]; then
  fail "No dashboards found in Grafana — provisioning failed"
fi
log "Grafana has ${DASHBOARD_COUNT} dashboard(s)"

# Optional: eBPF tracer check
if [ "${LENSAI_SMOKE_EBPF:-0}" = "1" ]; then
  log "Checking eBPF tracer container..."
  docker-compose --profile ebpf ps | grep -q "ebpf-tracer" || \
    fail "eBPF tracer container not running (start with: docker-compose --profile ebpf up -d)"
  log "eBPF tracer running"
fi

log ""
log "✓ All smoke checks passed"
log "  ClickHouse: ${CLICKHOUSE_URL}"
log "  Grafana:    ${GRAFANA_URL} (admin / lensai)"
log "  Ingest:     ${INGEST_URL}"
exit 0
```

---

## Implementation Checklist

### Setup
- [ ] Create `lensai-integration` repo (under `AkshantVats` initially)
- [ ] Initialize repo with `README.md` and `LICENSE` (MIT)
- [ ] Create `docs/ORG-SETUP.md` with manual org setup instructions

### docker-compose infrastructure
- [ ] Create `quickstart/docker-compose.yml` with 8 services (zookeeper, kafka, clickhouse, etcd, flagd, ingest, ebpf-tracer [profile], grafana)
- [ ] Add `healthcheck` to all services
- [ ] Create `quickstart/clickhouse/init/00_schema.sql` — lensai database + inference_events table
- [ ] Create `quickstart/grafana/provisioning/datasources/clickhouse.yaml`
- [ ] Create `quickstart/grafana/provisioning/dashboards/dashboards.yaml`
- [ ] Create `quickstart/grafana/provisioning/dashboards/lensai-overview.json` (4 panels)
- [ ] Create `quickstart/README.md` with one-command quickstart

### Smoke test
- [ ] Create `scripts/smoke.sh` with 7 checks
- [ ] `chmod +x scripts/smoke.sh`
- [ ] Run `bash scripts/smoke.sh` — verify exit 0 and capture output
- [ ] Test failure: stop ClickHouse, verify exit 1 with clear message

### Validation
- [ ] `docker-compose up -d` exits 0 in `quickstart/`
- [ ] `bash scripts/smoke.sh` exits 0 (output captured for PR description)
- [ ] Grafana dashboard visible at http://localhost:3000 (admin/lensai)
- [ ] All four panels present (data after synthetic event injection)
- [ ] PR opened with full smoke.sh output in description
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Container images not yet published to ghcr.io | High | High | Use `build:` directives pointing to cloned repos for Day 28; ghcr.io publishing is Day 29 |
| eBPF tracer requires privileged Docker — not in CI | High | Medium | `profiles: ["ebpf"]` — excluded from default `docker-compose up`; smoke.sh skips unless `LENSAI_SMOKE_EBPF=1` |
| Grafana ClickHouse plugin version mismatch | Low | Medium | Pin to `grafana-clickhouse-datasource 4.0.0` tested with Grafana 10.3.0 |
| ClickHouse schema not initialized on first run | Medium | High | `clickhouse/init/00_schema.sql` mounted at `/docker-entrypoint-initdb.d` — runs on first container start |

### Build directives for Day 28 (before ghcr.io images exist)

Until container images are published, use local builds:
```yaml
  ingest:
    build:
      context: ../../infra-ai-streaming
      dockerfile: Dockerfile.ingest
    # ... rest of service config

  flagd:
    build:
      context: ../../infra-ai-streaming/distributed-flagd
      dockerfile: Dockerfile
    # ...
```

Clone the sibling repos at the same directory level as `lensai-integration` before running `docker-compose up`.

---

## Definition of Done

- [ ] `docker-compose up -d` exits 0
- [ ] `bash scripts/smoke.sh` exits 0 with all 7 checks passing
- [ ] Grafana dashboard visible at http://localhost:3000
- [ ] `docs/ORG-SETUP.md` present with complete manual org setup steps
- [ ] PR opened with smoke.sh output in description
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## PR Description Template

```
## Day 28 — lensai-integration Day 1: Unified Docker Compose Quickstart

### What
- New repo: `lensai-integration`
- Unified `quickstart/docker-compose.yml`: Kafka, ClickHouse, etcd, distributed-flagd,
  infra-ai-streaming ingest, ebpf-llm-tracer (profile), Grafana
- ClickHouse schema init: `lensai.inference_events` table with resolved_model_id + cost fields
- Grafana pre-provisioned: ClickHouse datasource + LensAI overview dashboard (4 panels)
- `scripts/smoke.sh`: 7-step smoke test, exits 0 when events flow end-to-end
- `docs/ORG-SETUP.md`: manual steps for creating `lensai-dev` GitHub org + repo transfers

### Smoke test output
```
[smoke] Starting services...
[smoke] Waiting for Grafana (max 120s)...
[smoke] Grafana healthy
[smoke] Waiting for ClickHouse (max 120s)...
[smoke] ClickHouse healthy
[smoke] Waiting for ingest service (max 120s)...
[smoke] Ingest service healthy
[smoke] Injecting synthetic inference event...
[smoke] Event injected
[smoke] Waiting for event in ClickHouse...
[smoke] Event found in ClickHouse
[smoke] Verifying Grafana dashboard provisioned...
[smoke] Grafana has 1 dashboard(s)
[smoke]
[smoke] ✓ All smoke checks passed
[smoke]   ClickHouse: http://localhost:8123
[smoke]   Grafana:    http://localhost:3000 (admin / lensai)
[smoke]   Ingest:     http://localhost:4000
```

### Next steps (Day 29)
- Publish container images to `ghcr.io/lensai-dev/...`
- CI workflow running smoke.sh without eBPF (safe for GH Actions)
- Landing page demo GIF recording

Self-review: N issues found and fixed.
```
