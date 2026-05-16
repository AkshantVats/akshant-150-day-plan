# Day 4 — Implementation Agent 1 (Code)

**You are the Code implementation agent (A1) for calendar day 4 of N.**  
**User has approved the code workstream** (`approve code` or `approve all`). If you were launched without that approval, **stop** and tell the user to approve via [day-04-APPROVAL-GATE.md](day-04-APPROVAL-GATE.md).

---

## Mandatory reads (session start)

Read **in full** before writing any code:

1. `plans/day-04-code-plan.md` — **primary contract** (file-by-file scope, branches, validation, commits)
2. [CHECKLIST.md](../CHECKLIST.md) — §C Code Development, § Branching & Git Standards
3. [WORKFLOW.md](../WORKFLOW.md) — md wins over chat

Optional context: `data/plan.json` day 4 (`repo`, `thread`, ticket G-02).

**Do not** rely on chat summaries alone. If anything in this IMPLEMENT file conflicts with `day-04-code-plan.md`, **the code plan wins**.

---

## Workspace

| Item | Path |
|------|------|
| **Code repo** | `/Users/akshant/Desktop/github/infra-ai-streaming` |
| **Plan repo** (read-only) | `/Users/akshant/Desktop/github/akshant-150-day-plan` |
| **Remote** | `akshantvats/infra-ai-streaming` |

---

## Observable outcome (G-02)

After implementation and validation:

- `docker compose up` brings up Redis, Redpanda, ClickHouse, Prometheus, Grafana (+ init jobs)
- `cargo run -p ingestion` + `go run ./consumer/cmd/consumer` + one `curl /ingest` → event appears in Go consumer **stdout**
- ClickHouse **DDL expanded** in `init.sql`; **no** ClickHouse writes from Go (Day 5)

---

## Branch strategy (OSS — no `day-004-*`)

Per code plan §1b — choose **one**:

| Mode | Branch(es) |
|------|------------|
| **A — Single branch** | `feat/local-dev-go-consumer-stdout` |
| **B — Split (preferred)** | `chore/deploy-prometheus-grafana-redpanda-init`, `feat/deploy-clickhouse-inference-events-schema`, `feat/consumer-kafka-stdout-skeleton`, `docs/readme-e2e-smoke-quickstart` |

**Rules:**

- Branch off **updated `main`**
- Conventional Commits; Daily Thread in commit **body** only (`Refs: 4 of N — infra-ai-streaming — …`)
- **No push** until user explicitly says push

---

## Implementation scope (execute code plan §2–§12)

Implement exactly what `day-04-code-plan.md` lists. Summary:

### Deploy (`deploy/`)

- Extend `docker-compose.yml`: `redpanda-init`, Prometheus, Grafana, health chains
- Create `deploy/redpanda/init-topics.sh`, `deploy/prometheus/prometheus.yml`, Grafana datasource provisioning
- Expand `deploy/clickhouse/init.sql` to full `InferenceEvent` schema
- Update `deploy/.env.example`, `deploy/README.md`

### Go consumer (`consumer/`)

- Module `github.com/akshantvats/infra-ai-streaming/consumer`, Go 1.22+
- franz-go reader; deserialize `{"events":[...]}` batch wrapper
- Structured stdout log per event (format per code plan §7)
- Unit test for JSON deserialize
- **Do not** add ClickHouse writer, circuit breaker, Redis overflow, DLQ consumer logic (Day 5)

### Docs & scripts

- Update `README.md`, `DESIGN.md` (Day 4 appendix), `docs/PROJECT-STATUS.md`, `CONTRIBUTING.md`
- Create `scripts/smoke-e2e.sh` (recommended)
- Optional: `go test` in CI — only if fast; otherwise document manual E2E

### Out of scope (do not touch)

- Rust ingestion logic (unless E2E bug)
- Grafana dashboard JSON, Helm, `BENCHMARKS.md` / `CHAOS.md`
- Profile blog HTML (A2/A3 agents)

---

## Implementation order

Follow code plan § “Implementation order (after approval)”:

1. Branch per §1b
2. `deploy/` (redpanda-init → prometheus → grafana → init.sql → `.env.example`)
3. `consumer/` (model → kafka reader → main → tests)
4. `scripts/smoke-e2e.sh`
5. Docs pass
6. Manual E2E (code plan §8)
7. Local commits per §10

---

## Validation (required before reporting done)

Run code plan §8 commands. Success criteria:

| # | Criterion |
|---|-----------|
| 1 | Compose services healthy (~2 min) |
| 2 | Topics `ai_inference_events`, `ai_inference_dlq` exist |
| 3 | `curl /ingest` → **202** with `batch_id` |
| 4 | Go consumer logs line with `demo`, `gpt-4o`, `cost_usd=0.00423` |
| 5 | `cargo test -p ingestion` and `go test ./consumer/...` pass |
| 6 | Prometheus scrape ingestion on **8080** `/metrics` (not 9090) |
| 7 | No secrets in logs or committed `.env` |

Light failure-path: stop consumer → ingest → restart (at-least-once acceptable).

---

## Commits

Use Conventional Commits from code plan §10 (4 commits or squash per user preference). Every commit body includes:

```
Refs: 4 of N — infra-ai-streaming — Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance asks.
```

**Self-review:** code plan §11 checklist before each commit.

---

## Handoff to blog agents (before they finalize HTML)

Post to user (and parent if applicable):

1. **Commit SHA(s)** on implementation branch(es)
2. **Frozen test JSON** (code plan §7)
3. **Consumer stdout sample** (exact log line)
4. **Final compose service list** + ports (Grafana/Prometheus included?)
5. **Blockers** from code plan §12 if any user decision needed (module path, full compose RAM, Go in CI)

Experience and AI agents need this for accurate snippets and footnotes.

---

## Git policy

| Action | Allowed |
|--------|---------|
| `git add`, `git commit` on feature branch(es) | ✅ |
| `git push` | ❌ unless user explicitly says push |
| Commit `deploy/.env` | ❌ |
| Push plan repo | ❌ |

If user approves push: push branch, open PR if applicable, return PR URL.

---

## Report back

When done, return:

- Branch name(s) and commit SHAs
- E2E pass/fail summary (§8 table)
- Deviations from plan (if any) and why
- Items deferred to Day 5
- Blog handoff block (JSON, stdout, compose list)

---

*Implementation agent A1 — Day 4 · infra-ai-streaming · G-02*
