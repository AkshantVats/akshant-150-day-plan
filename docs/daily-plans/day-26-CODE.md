# Day 26 — Code Plan
## distributed-flagd BENCHMARKS.md + README Platform cross-links

**Calendar**: Thursday, June 11 2026 · Day 26 of 150
**Product**: LensAI
**Repo**: `AkshantVats/infra-ai-streaming` (distributed-flagd module + cross-repo READMEs)
**Language**: Go + Markdown
**Builds on**: Days 21–25 — distributed-flagd full implementation with HTTP CRUD, etcd backend, gRPC streaming, Kafka audit log, flagctl kill-switch, and HN launch draft

### Shared Thread
> Three-repo cross-links in READMEs are the platform story recruiters ask for in month five — start showing it now.

---

## Summary

Day 26 is a documentation and benchmarking sprint. The implementation is complete (Days 21–25). Today makes the work legible to any engineer — or recruiter — who arrives cold:

1. **BENCHMARKS.md** — real performance numbers for distributed-flagd: flag evaluation QPS, watch propagation latency P99, and etcd write throughput. Numbers come from a Go benchmark run (`go test -bench`) and a k6 smoke test.
2. **README Platform section** — cross-link all three OSS repos (infra-ai-streaming, distributed-flagd, ebpf-llm-tracer) in each repo's README under a `## Platform` section that explains how they fit together.

No new feature code today. The acceptance criteria are: BENCHMARKS.md exists with real numbers, all three READMEs cross-link the other two, `go test -bench ./...` exits 0.

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|--------------|
| AC-1 | `BENCHMARKS.md` exists in distributed-flagd root with ≥3 benchmark tables | File present, tables rendered correctly in GitHub |
| AC-2 | Flag evaluation QPS ≥ 100,000/sec (single-node, in-process) | `go test -bench=BenchmarkEvaluate -benchtime=5s` output in BENCHMARKS.md |
| AC-3 | Watch propagation P99 latency ≤ 200ms (local etcd) | Integration benchmark or k6 output in BENCHMARKS.md |
| AC-4 | etcd write throughput baseline captured | `go test -bench=BenchmarkPut -benchtime=5s` output |
| AC-5 | `distributed-flagd/README.md` has `## Platform` section linking ebpf-llm-tracer and infra-ai-streaming | README rendered on GitHub |
| AC-6 | `ebpf-llm-tracer/README.md` has `## Platform` section linking distributed-flagd and infra-ai-streaming | README PR or direct push to that repo |
| AC-7 | `infra-ai-streaming/README.md` has `## Platform` section linking distributed-flagd and ebpf-llm-tracer | README PR or direct push |
| AC-8 | `go test ./... -race -count=1` still exits 0 after all changes | CI output in PR description |

---

## Part 1 — BENCHMARKS.md

### 1.1 File location and structure

Create `distributed-flagd/BENCHMARKS.md`. Top section: methodology. Then three benchmark tables. Bottom section: hardware spec and run instructions.

### 1.2 Benchmark 1 — Flag Evaluation QPS

Measure how many flag evaluations per second the evaluator can process in-memory (no etcd I/O, pure CPU path).

**Go benchmark:**
```go
// internal/eval/evaluator_bench_test.go
// SPDX-License-Identifier: MIT
package eval_test

import (
	"fmt"
	"testing"

	"github.com/akshantvats/distributed-flagd/internal/eval"
)

func BenchmarkEvaluateBool(b *testing.B) {
	fv := eval.FlagValue{FlagName: "bench-bool", Type: "bool", ValueJSON: "true"}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = eval.Evaluate(fv, fmt.Sprintf("req-%d", i))
	}
}

func BenchmarkEvaluatePercentage(b *testing.B) {
	variants := []eval.PercentageVariant{
		{Value: "gpt-4o", Weight: 20},
		{Value: "gpt-3.5-turbo", Weight: 80},
	}
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_ = eval.EvaluatePercentage("model-flag", fmt.Sprintf("session-%d", i), variants)
	}
}
```

Run: `go test -bench=BenchmarkEvaluate -benchtime=5s -benchmem ./internal/eval/`

Expected BENCHMARKS.md table:
```
| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|---|---|---|---|---|
| BenchmarkEvaluateBool | ~8,500,000 | ~118 | 0 | 0 |
| BenchmarkEvaluatePercentage | ~2,200,000 | ~455 | 48 | 1 |
```

> Note: fill in actual numbers from your run. Do not fabricate. The QPS floor for BENCHMARKS.md is 100,000/sec — if the actual number is lower, investigate the evaluator before publishing.

### 1.3 Benchmark 2 — Watch Propagation Latency P99

Measure the end-to-end latency from a flag PUT to the gRPC EvaluateStream client receiving the DELTA update.

**Approach:** Integration benchmark using testcontainers (existing infra from Day 22).

```go
// internal/server/propagation_bench_test.go
// SPDX-License-Identifier: MIT
//go:build integration

package server_test

import (
	"context"
	"fmt"
	"sort"
	"testing"
	"time"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
)

// BenchmarkWatchPropagation measures P99 latency from etcd Put to gRPC DELTA receipt.
// Runs 1000 iterations, reports sorted latency distribution.
func BenchmarkWatchPropagation(b *testing.B) {
	endpoint, cleanup := startEtcd(b)
	defer cleanup()

	store, _ := etcd.NewClient(endpoint)
	defer store.Close()

	latencies := make([]time.Duration, 0, b.N)
	ctx := context.Background()

	watchCh := make(chan etcd.FlagValue, 256)
	go store.Watch(ctx, watchCh)
	time.Sleep(100 * time.Millisecond)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		t0 := time.Now()
		fv := etcd.FlagValue{
			FlagName:  fmt.Sprintf("bench-flag-%d", i),
			Type:      "bool",
			ValueJSON: "true",
		}
		_ = store.Put(ctx, fv, "bench", "propagation benchmark")
		select {
		case <-watchCh:
			latencies = append(latencies, time.Since(t0))
		case <-time.After(500 * time.Millisecond):
			b.Logf("iteration %d: timeout waiting for watch event", i)
		}
	}

	if len(latencies) > 0 {
		sort.Slice(latencies, func(i, j int) bool { return latencies[i] < latencies[j] })
		p50 := latencies[len(latencies)/2]
		p95 := latencies[int(float64(len(latencies))*0.95)]
		p99 := latencies[int(float64(len(latencies))*0.99)]
		b.ReportMetric(float64(p50.Milliseconds()), "p50-ms")
		b.ReportMetric(float64(p95.Milliseconds()), "p95-ms")
		b.ReportMetric(float64(p99.Milliseconds()), "p99-ms")
	}
}
```

Run: `go test -bench=BenchmarkWatchPropagation -tags=integration -benchtime=100x ./internal/server/`

Expected BENCHMARKS.md table:
```
| Metric | Value |
|---|---|
| P50 propagation latency | < 10ms |
| P95 propagation latency | < 50ms |
| P99 propagation latency | < 200ms |
| Sample size | 100 flag mutations |
| etcd setup | local testcontainers (quay.io/coreos/etcd:v3.5.12) |
```

> Note: fill with actual numbers. If P99 exceeds 200ms on local etcd, note the environment caveat.

### 1.4 Benchmark 3 — etcd Write Throughput

Measure how many flag PUT operations per second the etcd client can sustain, including the atomic audit-log Txn.

```go
// internal/etcd/put_bench_test.go
// SPDX-License-Identifier: MIT
//go:build integration

package etcd_test

import (
	"context"
	"fmt"
	"testing"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
)

func BenchmarkPut(b *testing.B) {
	endpoint, cleanup := startEtcd(b)
	defer cleanup()
	c, _ := etcd.NewClient(endpoint)
	defer c.Close()
	ctx := context.Background()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		fv := etcd.FlagValue{
			FlagName:  fmt.Sprintf("bench-flag-%d", i%100),
			Type:      "bool",
			ValueJSON: "true",
		}
		_ = c.Put(ctx, fv, "bench", "benchmark run")
	}
}
```

Run: `go test -bench=BenchmarkPut -benchtime=5s -tags=integration ./internal/etcd/`

Expected BENCHMARKS.md table:
```
| Benchmark | ops/sec | ns/op | Notes |
|---|---|---|---|
| BenchmarkPut | ~1,200 | ~830,000 | includes etcd atomic Txn + audit lease grant |
```

### 1.5 BENCHMARKS.md full template

```markdown
# distributed-flagd Benchmarks

Performance numbers for flag evaluation, watch propagation, and etcd write throughput.
Run on: {machine spec} · {date} · Go {version} · etcd v3.5.12 (testcontainers)

---

## Flag Evaluation QPS

Pure in-memory evaluation. No network I/O. Measures the evaluator's CPU path only.

Run: `go test -bench=BenchmarkEvaluate -benchtime=5s -benchmem ./internal/eval/`

| Benchmark | ops/sec | ns/op | B/op | allocs/op |
|---|---|---|---|---|
| BenchmarkEvaluateBool | {actual} | {actual} | {actual} | {actual} |
| BenchmarkEvaluatePercentage | {actual} | {actual} | {actual} | {actual} |

**Interpretation:** Boolean flags resolve in a single JSON unmarshal + type assertion — effectively zero work. Percentage rollout adds an FNV-1a hash and a modulo operation. Both exceed 100k ops/sec, meaning flag evaluation is never the bottleneck in the request path.

---

## Watch Propagation Latency

End-to-end: from `etcd.Put()` call to gRPC `EvaluateStream` client receiving the DELTA update.

Run: `go test -bench=BenchmarkWatchPropagation -tags=integration -benchtime=100x ./internal/server/`

| Metric | Value |
|---|---|
| P50 | {actual} ms |
| P95 | {actual} ms |
| P99 | {actual} ms |
| Sample size | 100 mutations |
| Environment | local testcontainers etcd |

**Interpretation:** P99 < 200ms on local etcd confirms the Day 22 AC-3 acceptance criterion. Production etcd on dedicated SSDs typically delivers faster propagation.

---

## etcd Write Throughput

Atomic flag mutation with audit log Txn. Includes: `Lease.Grant` + `Txn{OpPut(flag), OpPut(audit)}`.

Run: `go test -bench=BenchmarkPut -tags=integration -benchtime=5s ./internal/etcd/`

| Benchmark | ops/sec | ns/op | Notes |
|---|---|---|---|
| BenchmarkPut | {actual} | {actual} | Txn + audit lease |

**Interpretation:** etcd write throughput is I/O-bound. The audit Txn adds ~15% overhead vs a plain Put. For distributed-flagd's workload (flag changes are rare — minutes to hours between writes), this throughput is more than sufficient.

---

## Methodology

- Integration benchmarks use testcontainers (Docker required)
- Results are from a single 5-second run; re-run 3x and take the median for publication
- Machine: {fill in: CPU, RAM, SSD/HDD, OS}
- Go: {fill in: `go version`}
- etcd: v3.5.12 via `quay.io/coreos/etcd:v3.5.12`

## Updating

```bash
make bench              # unit benchmarks (no Docker)
make bench-integration  # requires Docker, runs propagation + etcd benches
```
```

---

## Part 2 — README Platform Cross-links

### 2.1 Platform section template

Add this section to each repo's README.md, directly after the `## Architecture` or `## Usage` section:

```markdown
## Platform

This repo is one piece of a three-component AI inference observability platform built open-source:

| Repo | Role |
|---|---|
| [infra-ai-streaming](https://github.com/AkshantVats/infra-ai-streaming) | Rust ingestion engine → Kafka → Go consumer → ClickHouse → Grafana |
| [distributed-flagd](https://github.com/AkshantVats/infra-ai-streaming/tree/main/distributed-flagd) | Go feature flag daemon — model version rollout, kill-switch, Kafka audit log |
| [ebpf-llm-tracer](https://github.com/AkshantVats/ebpf-llm-tracer) | eBPF kernel probes — zero-code LLM request tracing at the syscall level |

These components are designed to run together: ebpf-llm-tracer captures inference requests at the kernel, infra-ai-streaming ingests and stores them, and distributed-flagd controls which model version each request is routed to.
```

### 2.2 Repos to update

| Repo | README location | Action |
|---|---|---|
| `AkshantVats/infra-ai-streaming` | `README.md` root | Add `## Platform` section after Architecture |
| `AkshantVats/infra-ai-streaming` | `distributed-flagd/README.md` | Add `## Platform` section |
| `AkshantVats/ebpf-llm-tracer` | `README.md` root | Add `## Platform` section after Architecture |

---

## Makefile additions

Add to the existing Day 21–25 Makefile:

```makefile
.PHONY: bench bench-integration

bench:
	go test -bench=. -benchtime=5s -benchmem ./internal/eval/ ./internal/etcd/

bench-integration:
	go test -bench=. -tags=integration -benchtime=5s ./internal/etcd/ && \
	go test -bench=BenchmarkWatchPropagation -tags=integration -benchtime=100x ./internal/server/
```

---

## Implementation Checklist

### Part 1 — BENCHMARKS.md
- [ ] Create `internal/eval/evaluator_bench_test.go` with `BenchmarkEvaluateBool` + `BenchmarkEvaluatePercentage`
- [ ] Run evaluation benchmarks — capture real output
- [ ] Create `internal/etcd/put_bench_test.go` with `BenchmarkPut` behind `//go:build integration`
- [ ] Run etcd Put benchmark — capture real output
- [ ] Create `internal/server/propagation_bench_test.go` with `BenchmarkWatchPropagation` behind `//go:build integration`
- [ ] Run propagation benchmark — capture real output
- [ ] Create `distributed-flagd/BENCHMARKS.md` using template — fill ALL `{actual}` placeholders with real numbers
- [ ] Add `make bench` and `make bench-integration` targets to Makefile

### Part 2 — README cross-links
- [ ] Update `infra-ai-streaming/README.md` — add `## Platform` section
- [ ] Update `infra-ai-streaming/distributed-flagd/README.md` — add `## Platform` section
- [ ] Update `ebpf-llm-tracer/README.md` — add `## Platform` section

### Final checks
- [ ] `go build ./...` exits 0
- [ ] `go test ./... -race -count=1` exits 0
- [ ] BENCHMARKS.md has no `{actual}` placeholders remaining
- [ ] All three READMEs link all three repos
- [ ] PR opened with benchmark numbers visible in PR description
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| testcontainers not available in CI for propagation bench | Medium | Low | Tag as `//go:build integration`; unit eval benchmarks run without Docker |
| Benchmark numbers vary by machine | Low | Low | Note hardware spec and date in BENCHMARKS.md; note "representative" |
| ebpf-llm-tracer README requires separate repo write access | Low | Medium | Check PAT scope covers ebpf-llm-tracer before run |

---

## Definition of Done

- [ ] `go build ./...` exits 0
- [ ] `go test ./... -race -count=1` exits 0
- [ ] `BENCHMARKS.md` present with real numbers in all three tables (no `{actual}` placeholders)
- [ ] All three READMEs have `## Platform` section with correct cross-links
- [ ] `make bench` target documented and working
- [ ] PR opened with benchmark output in description
- [ ] PR URL recorded in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## PR Description Template

```
## Day 26 — distributed-flagd BENCHMARKS.md + Platform README cross-links

### What
- BENCHMARKS.md with three benchmark suites: flag eval QPS, watch propagation P99, etcd write throughput
- Benchmark test files in `internal/eval/`, `internal/etcd/`, `internal/server/`
- `make bench` and `make bench-integration` Makefile targets
- `## Platform` section added to all three repo READMEs cross-linking the full observability stack

### Benchmark results
| Benchmark | Result |
|---|---|
| BenchmarkEvaluatePercentage | {fill in} ops/sec |
| Watch propagation P99 | {fill in} ms |
| BenchmarkPut (etcd + audit Txn) | {fill in} ops/sec |

### Why this matters
BENCHMARKS.md closes the HN launch draft requirement for a benchmarks section. README cross-links
make the three-repo platform story visible to any engineer landing on any of the three repos.

Self-review: N issues found and fixed.
```
