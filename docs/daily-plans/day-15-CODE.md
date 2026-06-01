# Work Day 15 — Code / Infra (eBPF connect probe)

**Calendar day:** 15 of N · **Wednesday** · **LensAI** · repo: `ebpf-llm-tracer`

**Plan source:** `data/plan.json` day 15 code:

> eBPF program v0 — trace socket syscalls for outbound HTTPS to api.openai.com / api.anthropic.com. BPF maps for connection → PID correlation. Userspace loader in Go using cilium/ebpf. Log raw connect events; no parsing yet.

**DESIGN.md milestone:** Day 15 — BPF connect probe (fd → dst_ip map)

---

## 1. Ticket summary + acceptance criteria

### Ticket summary

**BPF connect probe v0** — implement the `sys_enter/exit_connect` tracepoint pair that populates the `active_conns` BPF hash map and emits `ConnectEvent` records to a ring buffer. This is the foundational data-collection layer: every subsequent probe (SSL_write uprobe, HTTP body parsing) depends on having a `(pid, tid, fd) → dst_ip` mapping established at connect time.

Scope: port-443 filter only; emit for all HTTPS connections, mark LLM targets via `llm_ip_allowlist`; no body parsing yet.

| In scope | Out of scope |
|----------|--------------|
| `bpf/connect.bpf.c` — enter/exit tracepoints | SSL_write uprobe (Day 16) |
| `active_conns` map: (pid,tid,fd) → (ip,port,target,ts) | HTTP body parsing (Day 16+) |
| `llm_ip_allowlist` map populated from DNS at startup | IPv6 support |
| Ring buffer `connect_events` → Go consumer | Bedrock pattern-match (needs hostname, not IP) |
| Go loader using `cilium/ebpf` + `ebpf.LoadCollectionSpec` | Kafka producer (Day 18) |
| `go test ./probe/...` passes without BPF toolchain | Integration test against live kernel |
| Makefile: `bpf`, `build-go`, `test`, `docker-build` targets | |

### Acceptance criteria

| # | Criterion | Proof |
|---|-----------|-------|
| 1 | `bpf/connect.bpf.c` compiles via `make bpf` (clang + libbpf) | `bpf/connect_bpf.o` exists |
| 2 | Enter probe populates `active_conns` on port-443 connects only | BPF source review + code structure |
| 3 | Exit probe removes failed connections (retval != 0 && != -EINPROGRESS) | Code review |
| 4 | Ring buffer emits `connect_event` with pid, tid, fd, dst_ip, dst_port, is_llm_target | Struct layout matches BPF |
| 5 | `llm_ip_allowlist` populated from `ResolveAllowlist()` at startup | `probe/allowlist.go` unit test |
| 6 | `go vet ./...` clean | CI |
| 7 | `go test ./probe/... -count=1` passes without kernel | CI unit-test job |
| 8 | `make bpf` succeeds in Docker with `ubuntu:22.04 + clang + libbpf-dev` | CI bpf-compile job |

---

## 2. BPF map design

| Map | Type | Key | Value | Max entries |
|-----|------|-----|-------|-------------|
| `llm_ip_allowlist` | HASH | `__u32` (dst_ip, host order) | `__u8` | 64 |
| `pending_fds` | HASH | `__u32` (tid) | `__u64` (fd) | 4096 |
| `active_conns` | HASH | `conn_key{pid,tid,fd}` | `conn_info{ip,port,target,ts}` | 4096 |
| `connect_events` | RINGBUF | — | `connect_event` (48 bytes) | 1 MB |

---

## 3. ConnectEvent struct layout (BPF ↔ Go)

```
offset  size  field
0       4     pid          __u32 / uint32
4       4     tid          __u32 / uint32
8       8     fd           __u64 / uint64
16      4     dst_ip       __u32 / uint32  (host byte order)
20      2     dst_port     __u16 / uint16
22      1     is_llm_target __u8 / uint8
23      1     _pad         __u8 / uint8
24      8     ts_ns        __u64 / uint64
32      16    comm         __u8[16] / [16]byte
total   48 bytes
```

Go `binary.Read(bytes.NewReader(rec.RawSample), binary.LittleEndian, &ev)` maps these fields correctly on x86_64.

---

## 4. Implementation checklist

**Branch (ebpf-llm-tracer):** `feat/ebpf-connect-probe`

- [x] `bpf/vmlinux.h` — minimal type definitions for connect tracepoints
- [x] `bpf/connect.bpf.c` — enter/exit probes, map population, ring buffer emit
- [x] `probe/types.go` — `ConnectEvent` Go struct + `DstIPString()`, `ProcessName()`
- [x] `probe/allowlist.go` — `LLMHosts` slice, `ResolveAllowlist()` DNS resolution
- [x] `probe/probe.go` — `Load()`, `Close()`, ring buffer reader goroutine
- [x] `probe/probe_test.go` — IP encoding, ProcessName, LLMHosts unit tests
- [x] `cmd/tracer/main.go` — CLI with `--bpf` flag, zap logger
- [x] `go.mod` — module + cilium/ebpf + zap dependencies
- [x] `Makefile` — bpf, build-go, test, lint, docker-build
- [x] `.github/workflows/ci.yml` — go-test job + bpf-compile job

---

## 5. LLM hosts tracked (Day 15 scope)

```
api.openai.com
api.anthropic.com
generativelanguage.googleapis.com
api.cohere.ai
```

Bedrock (`bedrock-runtime.<region>.amazonaws.com`) deferred to Day 16 — requires hostname-based matching in the SSL layer, not IP allowlist.

---

## 6. Day 16 handoff

The `active_conns` map established here is the prerequisite for Day 16:

- `SSL_write` uprobe: look up `(pid, tid, fd)` in `active_conns` to confirm this is an LLM connection, then read pre-encryption HTTP bytes (extract `model_id` from JSON fragment)
- `SSL_read` uprobe: capture response for token count extraction from `usage.prompt_tokens` / `usage.completion_tokens`

Neither uprobe can function without the fd→dst_ip mapping from this probe.

---

## 7. Time estimate

| Item | Estimate |
|------|----------|
| BPF C source | 1h |
| Go probe package | 1.5h |
| CLI + go.mod | 0.5h |
| Makefile + CI | 0.5h |
| **Total** | **3.5h** |
