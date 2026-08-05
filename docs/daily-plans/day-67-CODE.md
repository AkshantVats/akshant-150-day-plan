# Day 67 — Code Plan

**Repo:** `infra-ai-streaming`, component `cost-budget-enforcer/` (continuing Day 65/66)
**Product:** RouteIQ
**Ticket:** Admin API `PATCH /tenants/{id}/budget` — live budget changes without restart. Audit log to Kafka.

## Goal

Day 66 implemented enforcement (`pkg/store`, `pkg/enforcer`, `pkg/middleware`) against a
`config.Config` loaded once from a file at process start. Changing a tenant's budget meant a
file edit and a restart. Day 67 adds the operational path around that: a `PATCH` endpoint that
changes one tenant's budget in a running process, with every change durably audited.

## Scope

1. `pkg/config/live.go` — `LiveStore`, a mutex-guarded wrapper around `Config` with `Patch`
   (partial update via `TenantConfigPatch`, validated before commit) and `Set` (outright
   overwrite, used to roll a patch back).
2. `pkg/config/config.go` — `TenantConfig.Validate()`: positive budget, positive window,
   `0 < alert < soft < hard`, shared by both the config-file path and the new Admin API.
3. `pkg/audit/` — `BudgetChangeEvent`, the `Publisher` interface, and `KafkaPublisher` (topic
   `cost_budget_audit_log`, keyed by tenant ID, `RequiredAcks: RequireAll`).
4. `pkg/admin/admin.go` — `Handler` serving `PATCH /tenants/{id}/budget`: decode partial patch,
   apply + validate via `LiveStore.Patch`, publish the audit event, and — the key design
   decision — roll back and `503` if the audit publish fails, the opposite of `middleware.go`'s
   fail-open choice on a Redis error.
5. `README.md` / `DESIGN.md` — document the Admin API and the fail-closed-vs-fail-open contrast.

## Out of scope

- No live Kafka broker in this sandbox (no Docker daemon, same constraint Day 65/66 logged for
  Redis) — `KafkaPublisher` is tested against an unreachable address for its error path only.
- No authentication on the Admin API itself — `X-Admin-Actor` is trusted as supplied; a
  network-boundary auth layer is assumed, same assumption this repo's other internal endpoints make.
- No consumer for `cost_budget_audit_log` — this day ships the producer side only.

## Tests

36/36 unit tests (100%), `-race` clean, `golangci-lint` clean. New: `LiveStore.Patch`
partial-merge + validation-rejection + concurrent-patch race tests; `admin.Handler` table of
success/reject/rollback cases; `KafkaPublisher` error-path test; `BudgetChangeEvent` JSON
round-trip test.
