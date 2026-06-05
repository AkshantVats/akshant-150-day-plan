# Day 19 Code — Demo Harness

**Repo:** `ebpf-llm-tracer`
**Branch:** `feat/demo-harness-day19`
**PR:** https://github.com/AkshantVats/ebpf-llm-tracer/pull/7

## Task

ebpf-llm-tracer demo harness: docker-compose sidecar deployment, capture live calls to
mock LLM server with zero app SDK changes. BENCHMARKS.md for probe overhead (CPU %,
P99 latency delta). Document required kernel ≥5.10 and CAP_BPF.

## What was built

- `demo/docker-compose.yml` — three-service stack: app + mock-llm + tracer sidecar sharing PID namespace
- `demo/app/main.go` — demo client cycling 4 model IDs every 5s via plain `net/http`
- `demo/mock-llm/main.go` — standalone OpenAI-compatible server for compose stack
- `demo/tracer/Dockerfile` — tracer image; documents CAP_BPF + CAP_PERFMON requirements
- `demo/integration_test.go` — end-to-end pipeline test (4 models) + throughput benchmark
- `BENCHMARKS.md` — probe overhead section: ~12µs/op parse+map, kernel ≥5.10 table

## Test results

```
ok  github.com/AkshantVats/ebpf-llm-tracer/demo        parse+map ~12µs/op @ 1000 iter
ok  github.com/AkshantVats/ebpf-llm-tracer/consumer/ratelimit
ok  github.com/AkshantVats/ebpf-llm-tracer/consumer/wal
ok  github.com/AkshantVats/ebpf-llm-tracer/http
ok  github.com/AkshantVats/ebpf-llm-tracer/mapper
ok  github.com/AkshantVats/ebpf-llm-tracer/mock
ok  github.com/AkshantVats/ebpf-llm-tracer/probe

go test ./... -race → clean (no data races)
```
