# Day 56 — Code Plan

## agent-benchmark-runner: First CLI + Unified `docker-compose.yml` (All Four TraceForge Components)

**Calendar**: Tuesday, Day 56 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` — root `docker-compose.yml`, plus new
`Dockerfile`s in `agent-replay-engine/`, `agent-benchmark-runner/`, and
`tool-call-analyzer/` (`traceforge/Dockerfile` already existed from Day 44).
**Language**: Go 1.25 (agent-benchmark-runner's first `cmd/`)
**Builds on**: Days 51–55's agent-benchmark-runner packages (`task`, `criteria`,
`compare`, `orchestrator`, `report`, `lensai`) — all library-only until today.

### Shared Thread
> Org Boundaries meets Monorepo vs Multi-Repo — Platform Packaging in today's
> agent-benchmark-runner commit.
> Buyers install `docker compose up`, not four `git clone`s and four READMEs' worth of
> manual wiring. Today's code gives agent-benchmark-runner its first CLI (needed to put it
> in a container at all) and ties all four TraceForge components — `traceforge` (ingest
> service), `agent-replay-engine`, `agent-benchmark-runner`, `tool-call-analyzer` — into one
> root `docker-compose.yml`.

---

## Summary

1. **`pkg/subprocess/subprocess.go`** — implements `orchestrator.AgentFunc` by invoking
   the agent under test as an external command: task+seed marshaled as JSON on stdin, a
   `criteria.RunOutcome` decoded as JSON from stdout. Runs the command in its own process
   group (`Setpgid: true`) and kills the whole group on timeout/cancellation (not just the
   `sh` PID), with `cmd.WaitDelay` as a backstop — closes a real hang: a non-exec-optimized
   shell forking a grandchild that outlives a killed `sh` and keeps stdout/stderr pipes
   open.
2. **`pkg/subprocess/subprocess_test.go`** — 5 tests: decode success, non-zero exit,
   undecodable stdout, timeout is actually enforced (bounded elapsed time), stdin payload
   contains the expected task_id/seed.
3. **`pkg/criteria/criteria.go`, `pkg/task/task.go`** — additive `json` struct tags
   alongside the existing `yaml` tags on `RunOutcome`, `Task`, and `Criterion`, so they have
   a defined JSON wire shape for the new subprocess contract. No behavior change to
   existing YAML loading or in-process callers.
4. **`cmd/traceforge/main.go`** — agent-benchmark-runner's first CLI, mirroring
   `agent-replay-engine`'s `run(args, stdout, stderr) int` testable-entrypoint pattern. One
   subcommand, `run`: loads a task YAML, runs it N times against one or two agent shell
   commands via `pkg/subprocess`, prints a pass-rate summary (`orchestrator.Summarize`) per
   agent, and — with two agents — builds a `compare.Result` from each agent's first
   completed repetition and writes a markdown + JSON divergence report
   (`pkg/report.Build`/`RenderMarkdown`/`RenderJSON`). Optional `--lensai-url`/`--tenant-id`
   dual-writes the batch completion via `pkg/lensai`, unchanged from Day 55.
5. **`cmd/traceforge/main_test.go`** — 4 tests: single agent all-pass, missing required
   flags exits 2, two-agent run writes a divergence report to disk and asserts its content,
   unknown subcommand prints usage and exits 2.
6. **`agent-replay-engine/Dockerfile`, `agent-benchmark-runner/Dockerfile`,
   `tool-call-analyzer/Dockerfile`** — new multi-stage builds (Go builder → `alpine:3.19`
   runtime), matching `traceforge/Dockerfile`'s existing pattern exactly: build context is
   the repo root, `ENTRYPOINT` is the component's `traceforge` binary.
7. **`docker-compose.yml` (repo root, NEW)** — unifies all four components: `redpanda`
   (Kafka-compatible broker) and `clickhouse` (reusing `traceforge/clickhouse/schema.sql` +
   `trace_cost_rollup.sql`) as shared infra; `otel-collector` wired to both the existing
   `deploy/otel-collector/config.yaml` (LensAI) and `deploy/otel/traceforge-config.yaml`
   (TraceForge span pipeline); `collector` (the `traceforge` ingest HTTP service) as the
   always-on core service; `replay`, `benchmark`, `analyzer` under a `tools` compose
   profile since they're one-shot CLIs, not long-running services — invoked with
   `docker compose --profile tools run --rm <service> <args>`.
8. **CI wiring** — new `compose` job in `.github/workflows/ci.yml`: `docker compose -f
   docker-compose.yml config` (parses/validates the compose file — no image build or pull)
   plus a check that all four referenced `Dockerfile`s exist. No Docker daemon was
   available in the environment this was authored in, so image builds and
   `docker compose up` were not run end-to-end locally — see the honest gap below.
9. **`README.md` (repo root)** — new "TraceForge platform (unified stack)" section: a
   table of the four components and their interface (HTTP service vs. CLI), plus the
   `docker compose up` / `docker compose --profile tools run` quickstart.
10. **`agent-benchmark-runner/README.md`** — new "CLI" section documenting the `run`
    subcommand's flags and the stdin/stdout JSON contract, plus a `pkg/subprocess` row in
    the packages table.
11. **`agent-benchmark-runner/DESIGN.md`** — new "The First CLI, and the Subprocess
    Contract (Day 56)" section: why a subprocess boundary instead of an in-process
    interface, the process-group-kill bug and fix, and the honest gap (no contract
    versioning; no state reuse across repetitions).

### Honest Gap

No Docker daemon was available in the sandbox this was built in, so `docker compose
config` validated the file's syntax and structure, but none of the four images were
actually built or run together. The `compose` CI job only validates config; a real
end-to-end `docker compose up` smoke test (all four services healthy, one CLI tool
successfully invoked against the running stack) is not yet automated anywhere and is the
natural next OSS-polish item for this stack.

### Tests

```bash
cd agent-benchmark-runner
gofmt -l .           # empty
go vet ./...         # exits 0
go test -race ./...  # all packages pass, including new pkg/subprocess and cmd/traceforge
```
