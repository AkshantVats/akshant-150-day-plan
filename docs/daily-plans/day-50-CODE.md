# Day 50 — Code Plan
## agent-replay-engine: CI Smoke Test Against a Sample Bundle + On-Call Runbook

**Calendar**: Thursday, Day 50 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.25
**Builds on**: `cmd/traceforge` (Day 44 onward) — every subcommand shipped so far (`replay`,
`--stop-at-step` Day 46, `diff` Day 47, `--inject-timeout` Day 48, streaming Day 49) gets
exercised together for the first time today, against one shared fixture.

### Shared Thread
> `replay-engine CI with sample bundle; README 'debug step 7' runbook.` Every package's unit
> tests run against in-memory fixtures built by hand in Go — none of them run the actual
> compiled `traceforge` binary the way an on-call engineer types it. Today closes that gap with
> a checked-in sample event log and a CI step that runs the real CLI against it, then ties every
> debugging capability built since Day 44 into one seven-step runbook.

---

## Summary

1. **`testdata/sample_run.jsonl`** — a small, checked-in two-trace bundle
   (`trace-checkout-1001` / `trace-checkout-1002`) sharing an identical `check_inventory` call
   and diverging at `charge_payment`, built specifically to exercise every CLI path: full
   replay, `--stop-at-step`, `diff`, and `--inject-timeout`.
2. **`scripts/smoke_test.sh`** — builds the real `traceforge` binary with `go build` and runs
   all four CLI paths against the sample bundle, asserting on actual stdout/stderr and exit
   codes rather than in-process function calls.
3. **CI wiring** — `.github/workflows/ci.yml`'s `go` job gets a new step, "Smoke test —
   traceforge CLI against sample bundle (agent-replay-engine)", additive to the existing
   `go test -race` step, not a replacement.
4. **README on-call runbook** — a numbered, copy-paste seven-step section ("On-Call Runbook —
   Debugging a Bad Agent Run") that orders the CLI's existing capabilities into the sequence an
   on-call engineer actually needs: pull the trace, reproduce, isolate the step, diff against a
   known-good trace, force the failure mode on demand, stop before the blast radius (the Day 46
   lesson), and confirm the fix against the same sample bundle CI checks before shipping.
5. **DESIGN.md** — new "CI Smoke Test and the On-Call Runbook" section explaining why unit
   tests alone don't catch CLI wiring regressions, and why the runbook's step 7 deliberately
   reuses the same script CI runs.

No new packages, no new CLI flags — Day 50 is entirely about tying together what's already
built, not adding new replay mechanics.

Target: `go build ./...`, `go vet ./...`, `gofmt -l .` empty, `go test -race ./...` exits 0,
`bash scripts/smoke_test.sh` exits 0.

---

## Acceptance Criteria

```bash
go build ./...              # exits 0
go vet ./...                 # exits 0
gofmt -l .                    # empty
go test -race ./...           # exits 0, all packages pass
bash scripts/smoke_test.sh    # exits 0, all 5 smoke checks pass
```

## Series Navigation

Previous: Day 49 — agent-replay-engine: Streaming Replay — `eventlog.Scanner` + `RunFromReader`
Next: Day 51 — TBD
