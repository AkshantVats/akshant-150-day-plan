# Day 51 — Code Plan
## agent-benchmark-runner: DESIGN.md — Task YAML, Compare Two Agents, Success Criteria

**Calendar**: Thursday, Day 51 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-benchmark-runner/` (new component, first commit)
**Language**: Go 1.25
**Builds on**: agent-replay-engine's event-log-driven design pattern (Day 44 onward) — a
sibling component under the same monorepo, kept self-contained rather than importing
agent-replay-engine's packages directly.

### Shared Thread
> `agent-benchmark-runner DESIGN.md — task YAML, compare two agents, success criteria.`
> "Agent A feels better than agent B" is not a benchmark result — it's an opinion formed
> from whichever transcripts someone happened to read. Fixing the scenario as data (a task
> YAML) and the pass bar as data (typed success criteria) turns that opinion into a
> function of two recorded run outcomes and one task file.

---

## Summary

1. **`DESIGN.md`** — problem statement, why the seed lives on the task not the run,
   the success-criteria design decision (options table: free-form scripts vs. LLM-judge
   vs. closed typed set — closed set chosen), and the two-agent comparison contract.
2. **`pkg/task/task.go`** — `Task`, `Criterion`, `LoadYAML`/`LoadFile`, `Validate()`.
3. **`pkg/task/task_test.go`** — 7 tests: valid load, missing task_id, missing criteria,
   zero timeout, unknown criterion type, per-type field validation, missing file.
4. **`pkg/criteria/criteria.go`** — `RunOutcome`, `Result`, `Evaluate`/`EvaluateAll`/`AllPassed`.
5. **`pkg/criteria/criteria_test.go`** — 9 tests covering all four criterion types plus
   unknown-type fail-closed behavior.
6. **`pkg/compare/compare.go`** — `AgentRun`, `Divergence`, `Compare()` — grades both
   agents independently and finds the first tool-call-sequence divergence.
7. **`pkg/compare/compare_test.go`** — 6 tests: both pass, one passes one fails, mismatched
   step, shorter sequence, identical sequences, result field carry-through.
8. **`testdata/checkout-happy-path.yaml`** — sample task exercising all three criterion types.
9. **`README.md`** — quickstart, architecture diagram, package table.
10. **CI wiring** — `.github/workflows/ci.yml`'s `go` job gets gofmt/vet/test steps for
    `agent-benchmark-runner`, additive to the existing consumer and agent-replay-engine steps.

Target: `go test -race ./...` exits 0 (22 tests), `go vet ./...` exits 0, `gofmt -l .` empty.

---

## Key Design Decisions

- **Seed lives on the Task, not on either agent's run** — otherwise a tool-call-sequence
  divergence between agent A and agent B would be ambiguous (different behavior vs.
  different random draw).
- **Closed set of typed criteria, no interpreted code in task files** — rejects free-form
  assertion scripts (unsafe, undiffable) and LLM-judge grading (non-deterministic, defeats
  the point of a repeatable benchmark).
- **Divergence reported separately from pass/fail** — two agents can both pass while
  taking different paths, or both fail for unrelated reasons; conflating "did it pass"
  with "where did behavior differ" loses information a benchmark report needs.
- **No live agent invocation yet** — `RunOutcome` is caller-supplied. A runner CLI wiring
  actual agent processes to task YAML files is explicitly out of scope for Day 51.

---

## Acceptance Criteria

```bash
gofmt -l .           # empty
go vet ./...         # exits 0
go test -race ./...  # exits 0, 22 tests pass
```

## Series Navigation

Previous: Day 50 — agent-replay-engine: CI Smoke Test Against a Sample Bundle + On-Call Runbook
Next: Day 52 — TBD
