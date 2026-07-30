# Day 45 — Code Plan
## agent-replay-engine: Trace Export to Object Storage — zstd, Checksums, Retention

**Calendar**: Friday, Day 45 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-replay-engine/`
**Language**: Go 1.22+
**Builds on**: `pkg/eventlog` (Day 44) — the `EventLog` type this exports.

### Shared Thread
> JSONL on MinIO is Ceph for traces — cheap bytes, replayable history. Today's code in
> agent-replay-engine implements that lesson: event logs recorded by `pkg/eventlog` are
> exported to an S3-compatible object store (MinIO), compressed with zstd, checksummed,
> and aged out under a two-tier retention policy (30 days hot / 90 days cold).

---

## Summary

Day 45 adds an export path that takes a recorded `eventlog.EventLog` and writes it to
object storage as a compressed, checksummed, retention-tagged object. The deliverable:

1. **`pkg/objectstore/store.go`** — `ObjectStore` interface (`Put`, `Get`, `Delete`, `List`)
   kept storage-backend-agnostic so tests never need a live service.
2. **`pkg/objectstore/memory.go`** — in-memory fake implementing `ObjectStore`, used by all
   tests and by any caller running without a MinIO endpoint configured.
3. **`pkg/objectstore/minio.go`** — real implementation backed by `github.com/minio/minio-go/v7`,
   used only when a MinIO endpoint is configured. Not exercised by unit tests (no live
   service in CI); build-tagged so `go vet`/`go build` still cover it.
4. **`pkg/export/export.go`** — `Exporter`: serializes an `EventLog` to JSONL, compresses
   with zstd (`github.com/klauspost/compress/zstd`), computes a SHA-256 checksum of the
   *compressed* bytes, and calls `ObjectStore.Put` with a deterministic key.
5. **`pkg/export/retention.go`** — `RetentionPolicy`: given an object's age, returns whether
   it is in the hot tier (0–30 days), cold tier (30–90 days), or expired (>90 days). Pure
   function over `time.Time`, no I/O, fully unit-testable.
6. **`pkg/export/export_test.go`** + **`pkg/export/retention_test.go`** — ≥12 tests total:
   round-trip export/checksum verification, corrupted-object detection, retention tier
   boundaries (29/30/31 days, 89/90/91 days), key naming, compression ratio sanity check.

Target: `go test ./...` exits 0, `go vet ./...` exits 0, `gofmt -l .` empty.

---

## Object Key Layout

```
traces/{trace_id}/{seq_num_range}.jsonl.zst
traces/{trace_id}/{seq_num_range}.jsonl.zst.sha256
```

Example: `traces/9f2a.../000001-000047.jsonl.zst`

**Why a companion `.sha256` file, not object metadata**: MinIO/S3 metadata is easy to lose
across copy/replication operations depending on backend config; a sibling object is
portable across any S3-compatible store and human-inspectable with `aws s3 cp` + `sha256sum`.

---

## ObjectStore Interface

```go
// SPDX-License-Identifier: MIT
package objectstore

import (
	"context"
	"io"
	"time"
)

type ObjectMeta struct {
	Key          string
	Size         int64
	LastModified time.Time
}

// ObjectStore is the minimal S3-compatible surface the exporter needs.
// A MinIO-backed implementation and an in-memory fake both satisfy it —
// tests run against the fake, production runs against MinIO.
type ObjectStore interface {
	Put(ctx context.Context, key string, body io.Reader, size int64) error
	Get(ctx context.Context, key string) (io.ReadCloser, error)
	Delete(ctx context.Context, key string) error
	List(ctx context.Context, prefix string) ([]ObjectMeta, error)
}
```

## Exporter

```go
package export

// Exporter compresses an EventLog with zstd and writes it plus a checksum
// sidecar to an ObjectStore under a deterministic trace-scoped key.
type Exporter struct {
	Store ObjectStore
}

// Export writes log as {prefix}/{trace_id}/{first_seq}-{last_seq}.jsonl.zst
// and a sibling .sha256 file containing the hex SHA-256 of the compressed bytes.
// Returns the object key written.
func (e *Exporter) Export(ctx context.Context, log eventlog.EventLog) (string, error)

// Verify re-downloads the object and its checksum sidecar and confirms
// SHA-256(object bytes) == sidecar contents. Returns an error naming the
// mismatch if corrupted.
func (e *Exporter) Verify(ctx context.Context, key string) error
```

## RetentionPolicy

```go
package export

type Tier string

const (
	TierHot     Tier = "hot"     // 0-30 days: fast path, uncompressed listing expected
	TierCold    Tier = "cold"    // 30-90 days: compressed, infrequent access
	TierExpired Tier = "expired" // >90 days: eligible for deletion
)

// Classify returns the retention tier for an object given its age.
// Boundaries are inclusive on the lower bound: exactly 30 days is cold, exactly 90 is expired.
func Classify(age time.Duration) Tier

// Sweep scans an ObjectStore under prefix and returns the keys classified
// TierExpired as of now. Callers decide whether to delete them (Day 45 does
// not auto-delete — this returns candidates only, per the "no silent data
// loss" rule for a debug-oriented system).
func Sweep(ctx context.Context, store ObjectStore, prefix string, now time.Time) ([]string, error)
```

---

## Test Specification Summary

| File | Tests | Type |
|---|---|---|
| `pkg/objectstore/memory_test.go` | ≥4 | unit (Put/Get/Delete/List round trip, not-found error) |
| `pkg/export/export_test.go` | ≥5 | unit (export round trip, checksum verify, corruption detection, key format) |
| `pkg/export/retention_test.go` | ≥6 | unit (tier boundaries at 29/30/31/89/90/91 days, Sweep filters correctly) |

Total new tests: ≥15.

## Dependencies

Two new external modules, both pure-Go, no cgo, no live service required to build or test:
- `github.com/klauspost/compress/zstd` — zstd encode/decode
- `github.com/minio/minio-go/v7` — only imported by `pkg/objectstore/minio.go`, not exercised
  by unit tests since no MinIO service runs in CI. `go build ./...` and `go vet ./...` still
  compile it, catching type errors.

## Acceptance Criteria

```bash
go build ./...     # exits 0
go vet ./...        # exits 0
gofmt -l .           # empty
go test ./...        # exits 0, ≥15 new tests pass, memory-backed ObjectStore only
```

---

## Series Navigation

Previous: Day 44 — agent-replay-engine: Event Sourcing, Mock Tools, Determinism Rules
Next: Day 46 — agent-replay-engine: Replay Runner + Model Client Interface
