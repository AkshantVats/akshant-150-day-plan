# Day 23 — Code Plan

## Repo: distributed-flagd (in infra-ai-streaming)
## Branch: feat/distributed-flagd-day23-evaluator

## Task
Model rollout evaluator: given tenant_id + user_id hash, resolve active model version from percentage flag.
Integration hook: infra-ai-streaming ingestion adds resolved_model_id label from flagd sidecar.
Tests for sticky assignment and 50/50 split stability.

## Files to create/modify

### New: distributed-flagd/internal/eval/model_evaluator.go
- `ModelEvaluator` struct wrapping the flag evaluation engine
- `ResolveModelVersion(ctx, tenantID, userID string) (string, error)` — hashes `tenantID:userID` with FNV-1a, looks up active percentage flag for that tenant
- Returns fully qualified model version string (e.g. `gpt-4-turbo-2024-04-09`)

### New: distributed-flagd/internal/eval/model_evaluator_test.go
- `TestStickyAssignment` — same tenant+user always returns same model version across 1000 calls
- `TestSplitStability` — at 50/50 weight, across 10k random user IDs, verify distribution is within ±2% of 50%

### Modify: distributed-flagd/internal/http/handler.go
- Add `POST /evaluate` endpoint: body `{tenant_id, user_id}`, response `{resolved_model_id, variant, flag_key}`
- Used by infra-ai-streaming sidecar to resolve model version at ingest time

### New: infra-ai-streaming/internal/ingest/model_resolver.go
- `ModelResolver` that calls flagd HTTP `/evaluate` endpoint
- `ResolveModelID(ctx, tenantID, userID string) (string, error)` with 50ms timeout and fallback to `default`
- Circuit breaker: if flagd is unavailable for 3 consecutive calls, return `default` model ID

### New: infra-ai-streaming/internal/ingest/model_resolver_test.go
- Test timeout fallback
- Test circuit breaker open state
