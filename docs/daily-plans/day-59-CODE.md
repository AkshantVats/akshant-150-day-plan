# Day 59 — Code Plan

**Repo:** `infra-ai-streaming`, cross-cutting (`ingestion`, `consumer`, `agent-benchmark-runner` dashboards)
**Product:** TraceForge
**Ticket:** TraceForge v1 launch HN + publish product essay + LensAI+TraceForge Grafana proof.

## Goal

`agent-benchmark-runner/pkg/lensai` already dual-writes benchmark-batch-completion
events onto LensAI's ingest pipeline with `TraceID` and `Source: "benchmark_run"` set
on the wire (see `pkg/lensai/writer.go`'s doc comment: "a single Grafana board can join
inference cost and benchmark outcome per tenant"). That claim doesn't hold today: the
Rust `InferenceEvent` struct ingestion accepts doesn't have `trace_id`/`source` fields
at all, so both are silently dropped at the ingest handler before they ever reach Kafka,
the consumer, or ClickHouse. The "Grafana proof" this ticket asks for can't be built
until that gap is closed.

## Scope

1. Add `trace_id: Option<String>` and `source: Option<String>` to
   `ingestion/src/handlers/event.rs::InferenceEvent`, additive and
   `skip_serializing_if` like `resolved_model_id`. `normalize_events` in `validate.rs`
   defaults `source` to `"inference"` when a producer omits it, the same way it already
   defaults `status` to `"success"`.
2. Add the matching fields to `consumer/internal/model/event.go::InferenceEvent` and
   thread them through `consumer/internal/clickhouse/row.go::RowFromEvent` (with the
   same `"inference"` default at the mapping layer) and `writer.go`'s INSERT statement.
3. Add `trace_id Nullable(String)` and `source LowCardinality(String) DEFAULT 'inference'`
   columns to `infra_ai.inference_events` in both `deploy/clickhouse/init.sql` and
   `deploy/helm/lensai/files/clickhouse-init.sql` (kept identical, per existing
   convention).
4. Add `dashboards/traceforge-lensai-cross-product.json` (mirrored into
   `deploy/grafana/provisioning/dashboards/`): events-by-source, cost-by-source
   (documenting that `benchmark_run` cost is deliberately always 0), P99 latency by
   source, and a table of recent benchmark batches. This is the actual "Grafana proof."
5. Draft `docs/hn-launch-traceforge.md` in `infra-ai-streaming` (Show HN launch post for
   the TraceForge suite), mirroring the existing `docs/hn-launch-lensai.md` format.
6. Document the new columns + dashboard in `OBSERVABILITY.md`.

## Out of scope

- No changes to `agent-benchmark-runner`'s CLI or orchestrator — the dual-write already
  sets the right values; this PR only makes the ingest/consumer/schema path stop
  dropping them.
- No live Grafana verification (no Grafana server available in this build's sandbox) —
  the dashboard JSON is validated for well-formed JSON and correct field references
  against the actual wire format, not screenshotted against live data.

## Tests

Full existing suites (`cargo test -p ingestion`, `go test ./...` in `consumer/` and
`agent-benchmark-runner/`) plus new coverage: Rust `normalize_preserves_explicit_source_and_trace_id`,
Go `TestRowFromEventSourceDefaultsToInference` and
`TestRowFromEventPreservesExplicitSourceAndTraceID`.
