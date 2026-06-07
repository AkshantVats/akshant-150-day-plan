# Day 21 — Code Plan
## distributed-flagd: Repo Scaffold + DESIGN.md + Initial Go Skeleton

**Calendar**: Tuesday, June 9 2026 · Day 21 of 150
**Product**: LensAI
**Repo**: `AkshantVats/distributed-flagd` (new repo — create today)
**Language**: Go (primary), Protocol Buffers (gRPC service definition)
**Builds on**: Day 20 (LensAI consumer infrastructure) — flagd is the control plane that governs model version traffic in the Day 20 pipeline

### Shared Thread
> Percentage rollout flags are how the AI Learning routing patterns (provider failover, fallback model selection) become the change-management story ops teams trust — a flag is the audit trail between "we changed models" and "we know exactly who saw each model."

---

## Summary

Day 21 creates `AkshantVats/distributed-flagd` — a self-hosted feature flag control plane designed specifically for AI model version rollouts. The deliverable is not a fully working server; it is a complete DESIGN.md that can be executed by any engineer, plus the Go module scaffold with gRPC service definitions and an etcd client stub.

The three-part deliverable:

1. **DESIGN.md** — problem, architecture, data model, etcd consensus design, gRPC streaming protocol, audit log schema, AI rollout semantics
2. **Go scaffold** — module init, directory layout, `proto/flagd.proto`, `cmd/flagd/main.go`, `internal/etcd/client.go`, `internal/server/server.go` stubs
3. **README.md** — problem statement, quickstart (single `docker compose up`), architecture diagram, "why not LaunchDarkly" paragraph

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | DESIGN.md covers all five plan.json components: problem, etcd consensus, gRPC streaming, AI rollout flags, audit log | Section headers present; no section is a stub |
| AC-2 | `proto/flagd.proto` compiles with `protoc --go_out=. --go-grpc_out=.` | `make proto` exits 0 |
| AC-3 | `go build ./...` exits 0 from repo root | Makefile `build` target passes |
| AC-4 | README has Mermaid architecture diagram (≤8 nodes, ≤6-word labels, correct init block) | Renders on GitHub |
| AC-5 | README quickstart: `docker compose up` brings etcd + flagd server + a demo client | `docker-compose.yml` present |
| AC-6 | DESIGN.md audit log schema specifies: flag_name, old_value, new_value, changed_by, changed_at, evaluation_count_snapshot | All six fields present |
| AC-7 | AI rollout section in DESIGN.md: percentage-based traffic split between model versions, deterministic hash on request_id | Present with example: 10% to `gpt-4o`, 90% to `gpt-3.5-turbo` |
| AC-8 | Repo created, initial commit pushed, PR opened | PR URL captured in DAILY_PROGRESS.md |

---

## Part 1 — DESIGN.md

### 1.1 Problem Statement

LaunchDarkly's pricing at scale is punitive. The list price is per-seat for developers plus per-monthly-active-context (MAC) for production evaluations. A service evaluating feature flags on every request at 1k RPS = 2.6B MACs/month. At their enterprise tier, that is not a research budget item — it is a line item that gets cut, and when it gets cut, teams start hardcoding flags or disabling evaluation.

For AI inference services specifically, the problem is worse. Model version rollouts are not binary (on/off) — they are percentage-based traffic splits across multiple models simultaneously, with per-request determinism (the same `user_id` must see the same model in a session), and they require an audit trail (for cost attribution and compliance). LaunchDarkly's targeting rules can approximate this, but the audit export format is designed for marketing attribution, not infra cost attribution.

The three forces driving distributed-flagd:
1. **Cost**: evaluation is on the critical path for every LLM request — must be sub-millisecond with no external network call
2. **Semantics**: AI rollout flags need percentage splits with request-level determinism (consistent hashing), not just boolean targeting
3. **Audit**: every flag change must record the evaluation_count_snapshot at change time — so you can attribute cost deltas to flag changes

### 1.2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Control Plane                           │
│  flagd CLI / web UI  ──→  flagd server  ──→  etcd cluster   │
│                              ↕                               │
│                         audit log                            │
│                       (etcd + emit)                          │
└──────────────────────────────┬──────────────────────────────┘
                               │  gRPC streaming
                ┌──────────────┼──────────────┐
                ↓              ↓              ↓
           edge client    edge client    edge client
          (LensAI ingest) (LensAI router) (any service)
```

**Data path — flag evaluation (hot path)**:
1. Service starts → connects to flagd server over gRPC streaming (`EvaluateStream`)
2. flagd server pushes full flag snapshot to client on connect
3. Client stores snapshot in-process (Go map, read-only, atomically swapped)
4. Flag evaluation = local memory read (~100ns, no network)
5. When a flag changes: etcd watch fires → flagd server pushes delta to all connected clients → clients atomically swap map

**Data path — flag mutation (control path)**:
1. Operator calls `flagd set-flag` via CLI or HTTP API
2. flagd server writes new value to etcd with a CAS (compare-and-swap) using the current revision
3. etcd persists; etcd watch fires on all flagd server replicas
4. Each replica pushes the delta to its connected edge clients
5. Audit log entry written to etcd with snapshot of evaluation_count at change time

### 1.3 etcd Consensus Design

etcd provides the consistency guarantee: at any point in time, all flagd server replicas agree on the current flag state. The key schema:

```
/flags/{flag_name}                → current flag value (JSON)
/flags/{flag_name}/meta           → metadata (created_at, updated_by, description)
/audit/{flag_name}/{revision}     → audit entry (see 1.5)
/locks/{flag_name}                → distributed lock (TTL: 10s) for write operations
```

**Watch propagation**: flagd server opens an etcd `Watch` on prefix `/flags/`. Any write to any flag key triggers a watch event. The server fan-outs the change to all connected gRPC streams within one event loop tick. Target latency: flag change to edge client propagation < 50ms on same-region LAN.

**Consistency mode**: flagd uses etcd's serializable reads for the hot-path snapshot fetch on startup (avoid linearizable read overhead). For writes, all mutations go through `Txn` with a `Version` precondition to prevent lost-update races between flagd replicas.

**Split-brain behavior**: if etcd loses quorum, flagd servers continue serving reads from their last-known snapshot. Writes are rejected. This is a safe degradation — serving stale flags is better than serving no flags.

### 1.4 gRPC Streaming Protocol

**Proto service**:
```protobuf
service FlagService {
  rpc GetFlag(GetFlagRequest) returns (FlagValue);
  rpc SetFlag(SetFlagRequest) returns (SetFlagResponse);
  rpc EvaluateStream(EvaluateStreamRequest) returns (stream FlagUpdate);
  rpc ListFlags(ListFlagsRequest) returns (FlagList);
}
```

**EvaluateStream semantics**:
- Client sends `EvaluateStreamRequest` with its service identity (`service_name`, `instance_id`)
- Server immediately sends `FlagUpdate { type: SNAPSHOT, flags: {all current flags} }`
- On each subsequent flag change, server sends `FlagUpdate { type: DELTA, flag_name: ..., new_value: ... }`
- Client maintains local map; SNAPSHOT replaces; DELTA patches
- Server-side: each connected stream is a goroutine with a channel; flag changes are fan-out to all channels

**Reconnection**: client implements exponential backoff (2s, 4s, 8s, 16s, 32s cap). On reconnect, client gets a fresh SNAPSHOT. No state is lost on the server side (flag state is in etcd, not in-memory).

### 1.5 AI Model Rollout Flags

Standard boolean and string flags are table stakes. The AI-specific addition is the **percentage rollout flag type**.

**Data model**:
```json
{
  "flag_name": "llm_model_version",
  "type": "percentage_rollout",
  "variants": [
    {"value": "gpt-4o", "weight": 10},
    {"value": "gpt-3.5-turbo", "weight": 90}
  ],
  "hash_key": "request_id",
  "sticky": true
}
```

**Evaluation algorithm**:
1. Extract `hash_key` field from evaluation context (e.g., `request_id`)
2. Compute `hash = FNV-1a(flag_name + ":" + context[hash_key]) % 10000`
3. Walk variants in order; assign to bucket based on cumulative weight × 100
4. Return the matching variant's value

`sticky: true` means the same `hash_key` value always maps to the same variant — deterministic, session-consistent rollout.

**Why FNV-1a**: Fast (single-pass, no allocations), uniform distribution across 10k buckets, sufficient for percentage accuracy to ±0.1% at reasonable flag evaluation volumes.

**Gradient rollout**: variants support dynamic weight updates. Set `gpt-4o` to 10% → evaluate for 24h → set to 25% → 50% → 100%. The audit log captures evaluation_count_snapshot at each weight change so cost increase is attributable to specific flag mutations.

### 1.6 Audit Log Design

Every flag mutation writes an audit entry to etcd under `/audit/{flag_name}/{unix_ns}`:

```json
{
  "flag_name": "llm_model_version",
  "old_value": {"gpt-4o": 10, "gpt-3.5-turbo": 90},
  "new_value": {"gpt-4o": 25, "gpt-3.5-turbo": 75},
  "changed_by": "akshant@inferix.dev",
  "changed_at": "2026-06-09T08:15:00Z",
  "evaluation_count_snapshot": 847293,
  "reason": "gradient rollout: day 1 stable, increasing gpt-4o to 25%"
}
```

**evaluation_count_snapshot**: the total number of evaluations for this flag since creation, captured at change time. Used to compute evaluation delta between changes — the audit trail for cost attribution.

Audit entries are written atomically with the flag value mutation in a single etcd `Txn`. If the flag write fails, the audit entry is not written. If the audit write fails, the flag write is rolled back (atomic pair).

**Retention**: audit entries are kept for 90 days. An etcd lease TTL of 7,776,000 seconds (90 days) is attached to each audit key on write.

---

## Part 2 — Go Scaffold

### 2.1 Directory Layout

```
distributed-flagd/
├── cmd/
│   └── flagd/
│       └── main.go          # server entrypoint: parse flags, init etcd, start gRPC server
├── internal/
│   ├── etcd/
│   │   └── client.go        # etcd client wrapper: Get, Put, Watch, Txn
│   ├── server/
│   │   └── server.go        # gRPC server: implements FlagService
│   ├── eval/
│   │   └── evaluator.go     # percentage rollout evaluation: FNV-1a hashing
│   └── audit/
│       └── audit.go         # audit log writer: Txn with flag mutation
├── proto/
│   └── flagd.proto          # gRPC service + message definitions
├── Makefile                 # targets: build, proto, test, docker, lint
├── docker-compose.yml       # etcd + flagd server
├── DESIGN.md                # complete design document (Section 1 above)
├── README.md                # problem statement + quickstart + architecture diagram
└── go.mod                   # module: github.com/akshantvats/distributed-flagd
```

### 2.2 proto/flagd.proto

```protobuf
syntax = "proto3";
package flagd.v1;
option go_package = "github.com/akshantvats/distributed-flagd/proto/flagd/v1";

message FlagValue {
  string flag_name = 1;
  string type = 2;          // "bool" | "string" | "percentage_rollout"
  string value_json = 3;    // JSON-encoded current value or rollout config
  int64  version = 4;       // etcd revision at last write
}

message GetFlagRequest { string flag_name = 1; }

message SetFlagRequest {
  string flag_name   = 1;
  string value_json  = 2;
  string changed_by  = 3;
  string reason      = 4;
}

message SetFlagResponse {
  bool   success    = 1;
  string error_msg  = 2;
  int64  revision   = 3;
}

message EvaluateStreamRequest {
  string service_name = 1;
  string instance_id  = 2;
}

message FlagUpdate {
  enum UpdateType { SNAPSHOT = 0; DELTA = 1; }
  UpdateType update_type = 1;
  repeated FlagValue flags = 2;  // all flags on SNAPSHOT; one flag on DELTA
}

message ListFlagsRequest {}
message FlagList { repeated FlagValue flags = 1; }

service FlagService {
  rpc GetFlag(GetFlagRequest) returns (FlagValue);
  rpc SetFlag(SetFlagRequest) returns (SetFlagResponse);
  rpc EvaluateStream(EvaluateStreamRequest) returns (stream FlagUpdate);
  rpc ListFlags(ListFlagsRequest) returns (FlagList);
}
```

### 2.3 cmd/flagd/main.go (stub)

```go
// SPDX-License-Identifier: MIT
package main

import (
	"context"
	"flag"
	"log"
	"net"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
	"github.com/akshantvats/distributed-flagd/internal/server"
	pb "github.com/akshantvats/distributed-flagd/proto/flagd/v1"
	"google.golang.org/grpc"
)

func main() {
	etcdAddr := flag.String("etcd", "localhost:2379", "etcd endpoint")
	listenAddr := flag.String("listen", ":50051", "gRPC listen address")
	flag.Parse()

	etcdClient, err := etcd.NewClient(*etcdAddr)
	if err != nil {
		log.Fatalf("etcd connect: %v", err)
	}
	defer etcdClient.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	flagServer := server.New(ctx, etcdClient)
	grpcServer := grpc.NewServer()
	pb.RegisterFlagServiceServer(grpcServer, flagServer)

	lis, err := net.Listen("tcp", *listenAddr)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	log.Printf("flagd listening on %s", *listenAddr)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
```

### 2.4 internal/eval/evaluator.go (percentage rollout)

```go
// SPDX-License-Identifier: MIT
package eval

import (
	"encoding/json"
	"hash/fnv"
)

type PercentageVariant struct {
	Value  string `json:"value"`
	Weight int    `json:"weight"` // out of 100
}

// EvaluatePercentage returns the variant for the given hashKey using FNV-1a.
// Deterministic: same flagName + hashKey always returns the same variant.
func EvaluatePercentage(flagName, hashKey string, variants []PercentageVariant) string {
	h := fnv.New32a()
	h.Write([]byte(flagName + ":" + hashKey))
	bucket := int(h.Sum32() % 10000) // 0..9999

	cumulative := 0
	for _, v := range variants {
		cumulative += v.Weight * 100 // weight is 0..100, bucket is 0..9999
		if bucket < cumulative {
			return v.Value
		}
	}
	// Fallback to last variant (handles rounding)
	if len(variants) > 0 {
		return variants[len(variants)-1].Value
	}
	return ""
}

// ParseVariants decodes JSON-encoded variant config.
func ParseVariants(valueJSON string) ([]PercentageVariant, error) {
	var v []PercentageVariant
	return v, json.Unmarshal([]byte(valueJSON), &v)
}
```

### 2.5 docker-compose.yml

```yaml
version: "3.9"
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.12
    command:
      - etcd
      - --advertise-client-urls=http://0.0.0.0:2379
      - --listen-client-urls=http://0.0.0.0:2379
    ports:
      - "2379:2379"

  flagd:
    build: .
    command: ["/flagd", "--etcd=etcd:2379", "--listen=:50051"]
    ports:
      - "50051:50051"
    depends_on:
      - etcd
```

### 2.6 Makefile

```makefile
.PHONY: build proto test lint docker

build:
	go build -o bin/flagd ./cmd/flagd

proto:
	protoc --go_out=. --go-grpc_out=. proto/flagd.proto

test:
	go test ./... -race -count=1

lint:
	golangci-lint run ./...

docker:
	docker compose up --build
```

---

## Implementation Checklist

### DESIGN.md
- [ ] Section 1.1: problem statement (LaunchDarkly cost, MAC pricing, AI-specific gaps)
- [ ] Section 1.2: architecture overview diagram (ASCII or Mermaid in DESIGN.md)
- [ ] Section 1.3: etcd key schema, watch propagation, consistency mode, split-brain behavior
- [ ] Section 1.4: gRPC streaming protocol, EvaluateStream semantics, reconnection
- [ ] Section 1.5: percentage rollout data model, FNV-1a algorithm, sticky semantics
- [ ] Section 1.6: audit log schema (all 6 fields), atomicity guarantee, retention

### Go Scaffold
- [ ] `go mod init github.com/akshantvats/distributed-flagd`
- [ ] Add dependencies: `go.etcd.io/etcd/client/v3`, `google.golang.org/grpc`, `google.golang.org/protobuf`
- [ ] Write `proto/flagd.proto` (all 4 RPC methods, all message types)
- [ ] `make proto` — exits 0
- [ ] Write `cmd/flagd/main.go` stub (compiles)
- [ ] Write `internal/eval/evaluator.go` (FNV-1a percentage evaluator)
- [ ] Write `internal/etcd/client.go` stub (NewClient, Close, Get, Put, Watch, Txn)
- [ ] Write `internal/server/server.go` stub (implements FlagServiceServer interface)
- [ ] Write `internal/audit/audit.go` stub (AuditEntry struct, Write method)
- [ ] `go build ./...` — exits 0

### README
- [ ] Problem statement: 2 paragraphs ("why not LaunchDarkly")
- [ ] Architecture Mermaid diagram (≤8 nodes, correct init block)
- [ ] Quickstart: `docker compose up` + demo seed flag command
- [ ] Link to DESIGN.md

### Repo & PR
- [ ] Create `AkshantVats/distributed-flagd` on GitHub (public, MIT license)
- [ ] Initial commit: all scaffold files
- [ ] Open PR with test output (`go build ./...` and `make proto` output)
- [ ] Capture PR URL in DAILY_PROGRESS.md

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `protoc` not installed in build environment | Medium | Medium | Add `protoc` install step to Makefile; document in README |
| etcd v3 Go client import path changed | Low | Medium | Pin exact version in go.mod: `go.etcd.io/etcd/client/v3 v3.5.12` |
| gRPC stream fan-out goroutine leak on client disconnect | Medium | Low | Use `context.WithCancel` per stream; cancel on `Send` error |
| FNV-1a distribution not uniform enough for < 5% weights | Low | Medium | Document minimum weight of 5% in DESIGN.md; add unit test |

---

## Definition of Done

- [ ] `go build ./...` exits 0
- [ ] `make proto` exits 0
- [ ] README Mermaid diagram renders on GitHub
- [ ] DESIGN.md has all 6 sections, no stubs, all 6 audit fields present
- [ ] PR opened with build output in description
- [ ] PR URL in DAILY_PROGRESS.md
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## PR Description Template

```
## Day 21 — distributed-flagd: Scaffold + DESIGN.md

### What
- New repo: distributed-flagd — self-hosted feature flag control plane for AI model rollouts
- Complete DESIGN.md: problem, etcd consensus, gRPC streaming, percentage rollout, audit log
- Go scaffold: proto, evaluator, stubs for etcd client + gRPC server
- docker-compose.yml: etcd + flagd server

### Build output
```
$ go build ./...
(no errors)
$ make proto
(generated proto/flagd/v1/flagd.pb.go, proto/flagd/v1/flagd_grpc.pb.go)
```

### Key design decision
Evaluation is local-memory read (~100ns) — no network call on hot path. etcd is only
consulted for writes and initial snapshot fetch. gRPC streaming pushes deltas to all
edge clients within 50ms of a flag change.

Self-review: N issues found and fixed.
```
