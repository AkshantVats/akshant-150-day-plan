# Day 58 — Code Plan

**Repo:** `infra-ai-streaming`, component `agent-benchmark-runner`
**Product:** TraceForge
**Ticket:** Launch rehearsal + integration test; draft product essay for Day 59.

## Goal

`agent-benchmark-runner` has an orchestrator, report/landing generation, and a `run` CLI,
but no test that exercises the full CLI path end-to-end the way a real launch rehearsal
would: two fake agent executables, a task YAML, and an assertion that the CLI produces a
correct pass-rate summary plus all three report artifacts (`.md`, `.json`, `.html`
landing page) with the expected divergence between the two agents.

## Scope

1. Add an integration test (build-tag gated like the existing `pkg/store/integration_test.go`
   pattern, or a plain `_test.go` under `cmd/traceforge/` if it doesn't need external
   services) that:
   - Builds/uses two tiny stub "agent" scripts (or in-process stand-ins) with a known,
     different pass rate against `testdata/checkout-happy-path.yaml`.
   - Runs the same code path `cmd/traceforge run` uses (call the orchestrator directly,
     not by shelling out to `go run`, to keep it fast and hermetic).
   - Asserts the pass-rate summary matches the fixed pass rates, and that report
     generation produces non-empty markdown, valid JSON, and an HTML landing page
     containing both agent names.
2. If a bug or rough edge surfaces while wiring the rehearsal (e.g. summary rounding,
   landing page missing a field), fix it — that's the point of a rehearsal.
3. Update `agent-benchmark-runner/README.md` "Quickstart" or "CLI" section with one line
   noting the rehearsal/integration test if it changes how contributors run tests.

## Out of scope

- No new CLI flags.
- No product essay content lives in this repo — the essay itself is drafted separately
  for Day 59 in `akshant-150-day-plan` (product_blog field), not committed here.

## Tests

Full existing suite (`go test ./...`) plus the new rehearsal test must pass.
