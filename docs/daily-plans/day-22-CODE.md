# Day 22 — Code Plan
## distributed-flagd core in Go: HTTP CRUD for flags, etcd backend with watch, gRPC streaming push to clients

**Calendar**: Wednesday, June 10 2026 · Day 22 of 150
**Product**: LensAI
**Repo**: `AkshantVats/distributed-flagd` (implementing stubs from Day 21)
**Language**: Go
**Builds on**: Day 21 scaffold — DESIGN.md, proto/flagd.proto, evaluator.go (implemented), and stubs for etcd client, gRPC server, audit log, HTTP layer

### Shared Thread
> `resolved_model_id` on ingest events closes the loop between flagd policy and ClickHouse cost attribution.

---

## Summary

Day 22 turns the Day 21 scaffold into a working server. Every stub from Day 21 gets a complete implementation. The three-part deliverable:

1. **HTTP CRUD layer** — `internal/http/handler.go`: REST endpoints for flag create/read/update/delete. Accepts JSON, validates flag types, delegates writes to etcd client. New file — not present in Day 21.
2. **etcd backend with watch** — `internal/etcd/client.go`: full implementation of `Get`, `Put`, `Watch` prefix, `Txn`, `Close`. Replaces the Day 21 stub entirely.
3. **gRPC streaming server** — `internal/server/server.go`: full implementation of `GetFlag`, `SetFlag`, `ListFlags`, `EvaluateStream` with fan-out to all connected clients. Replaces the Day 21 stub.

What is **new** versus Day 21:
- `internal/http/handler.go` — does not exist yet, created today
- `internal/http/routes.go` — does not exist yet, created today
- `internal/server/fanout.go` — does not exist yet; fan-out logic extracted to keep server.go readable
- All four stub files receive full implementations, not stubs
- `internal/audit/audit.go` — full atomic write implementation
- Tests: `internal/eval/evaluator_test.go`, `internal/etcd/client_integration_test.go`

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|--------------|
| AC-1 | `POST /flags` creates a flag in etcd; `GET /flags/{name}` returns it | `curl` sequence in smoke test exits 0 with correct JSON |
| AC-2 | `DELETE /flags/{name}` removes a flag; subsequent `GET` returns 404 | `curl` smoke test |
| AC-3 | gRPC `EvaluateStream` sends a SNAPSHOT on connect, then a DELTA within 200ms of any flag mutation | Integration test using `grpc_testing` or real gRPC client goroutine |
| AC-4 | etcd `Watch` fires for all key mutations under `/flags/` prefix; server fan-out propagates to all open streams | Integration test: connect 3 streams, mutate 1 flag, assert all 3 receive DELTA |
| AC-5 | Percentage rollout flag with 50/50 split distributes ±2% at 10,000 evaluations | Unit test in `evaluator_test.go` |
| AC-6 | Audit entry written atomically with flag mutation; if flag write fails, audit entry is absent | Txn test using embedded etcd or testcontainers |
| AC-7 | `docker compose up` brings etcd + flagd; HTTP and gRPC ports reachable; seed flag visible | `make smoke` target exits 0 |
| AC-8 | `go build ./...` and `go test ./... -race` both exit 0 | CI output in PR description |

---

## Part 1 — HTTP CRUD Layer

### 1.1 Routes

The HTTP server runs on `:8080`. All handlers live in `internal/http/`. Routes are registered in `routes.go` using the standard `net/http` multiplexer (no external router dependency — keep the module lean).

```
POST   /flags           Create or overwrite a flag
GET    /flags           List all flags
GET    /flags/{name}    Get one flag by name
PUT    /flags/{name}    Update flag value (full replacement)
DELETE /flags/{name}    Delete a flag
GET    /healthz         Liveness probe — returns 200 OK
```

### 1.2 Request/Response shapes

**Flag JSON (used in POST body, GET response, PUT body)**:
```json
{
  "flag_name":   "llm_model_version",
  "type":        "percentage_rollout",
  "value_json":  "[{\"value\":\"gpt-4o\",\"weight\":10},{\"value\":\"gpt-3.5-turbo\",\"weight\":90}]",
  "changed_by":  "akshant@inferix.dev",
  "reason":      "gradient rollout day 1"
}
```

For boolean flags: `"type": "bool"`, `"value_json": "true"`
For string flags: `"type": "string"`, `"value_json": "\"v2\""` (JSON-encoded string)

**List response**:
```json
{
  "flags": [ { ...FlagValue... }, ... ],
  "count": 3
}
```

**Error response** (all 4xx/5xx):
```json
{ "error": "flag not found", "code": 404 }
```

### 1.3 internal/http/handler.go — full implementation

```go
// SPDX-License-Identifier: MIT
package httpapi

import (
	"encoding/json"
	"errors"
	"net/http"
	"strings"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
)

// Handler holds dependencies for all HTTP handlers.
type Handler struct {
	store *etcd.Client
}

// New returns a Handler wired to the etcd client.
func New(store *etcd.Client) *Handler {
	return &Handler{store: store}
}

// flagRequest is the JSON body accepted by POST /flags and PUT /flags/{name}.
type flagRequest struct {
	FlagName  string `json:"flag_name"`
	Type      string `json:"type"`
	ValueJSON string `json:"value_json"`
	ChangedBy string `json:"changed_by"`
	Reason    string `json:"reason"`
}

func (h *Handler) CreateFlag(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req flagRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, "invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}
	if err := validateFlagRequest(req); err != nil {
		writeError(w, err.Error(), http.StatusBadRequest)
		return
	}
	fv := etcd.FlagValue{
		FlagName:  req.FlagName,
		Type:      req.Type,
		ValueJSON: req.ValueJSON,
	}
	if err := h.store.Put(r.Context(), fv, req.ChangedBy, req.Reason); err != nil {
		writeError(w, "etcd write failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(fv)
}

func (h *Handler) GetFlag(w http.ResponseWriter, r *http.Request) {
	name := flagNameFromPath(r.URL.Path)
	if name == "" {
		writeError(w, "flag name required", http.StatusBadRequest)
		return
	}
	fv, err := h.store.Get(r.Context(), name)
	if errors.Is(err, etcd.ErrNotFound) {
		writeError(w, "flag not found", http.StatusNotFound)
		return
	}
	if err != nil {
		writeError(w, "etcd read failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(fv)
}

func (h *Handler) ListFlags(w http.ResponseWriter, r *http.Request) {
	flags, err := h.store.List(r.Context())
	if err != nil {
		writeError(w, "etcd list failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"flags": flags,
		"count": len(flags),
	})
}

func (h *Handler) UpdateFlag(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		writeError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	name := flagNameFromPath(r.URL.Path)
	if name == "" {
		writeError(w, "flag name required", http.StatusBadRequest)
		return
	}
	var req flagRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, "invalid JSON: "+err.Error(), http.StatusBadRequest)
		return
	}
	req.FlagName = name
	if err := validateFlagRequest(req); err != nil {
		writeError(w, err.Error(), http.StatusBadRequest)
		return
	}
	fv := etcd.FlagValue{
		FlagName:  req.FlagName,
		Type:      req.Type,
		ValueJSON: req.ValueJSON,
	}
	if err := h.store.Put(r.Context(), fv, req.ChangedBy, req.Reason); err != nil {
		writeError(w, "etcd write failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(fv)
}

func (h *Handler) DeleteFlag(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		writeError(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	name := flagNameFromPath(r.URL.Path)
	if name == "" {
		writeError(w, "flag name required", http.StatusBadRequest)
		return
	}
	if err := h.store.Delete(r.Context(), name); err != nil {
		if errors.Is(err, etcd.ErrNotFound) {
			writeError(w, "flag not found", http.StatusNotFound)
			return
		}
		writeError(w, "etcd delete failed: "+err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (h *Handler) Healthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

func flagNameFromPath(path string) string {
	parts := strings.Split(strings.Trim(path, "/"), "/")
	if len(parts) >= 2 {
		return parts[1]
	}
	return ""
}

func validateFlagRequest(req flagRequest) error {
	if req.FlagName == "" {
		return errors.New("flag_name is required")
	}
	switch req.Type {
	case "bool", "string", "percentage_rollout":
		// valid
	default:
		return errors.New("type must be one of: bool, string, percentage_rollout")
	}
	if req.ValueJSON == "" {
		return errors.New("value_json is required")
	}
	return nil
}

func writeError(w http.ResponseWriter, msg string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(map[string]interface{}{
		"error": msg,
		"code":  code,
	})
}
```

### 1.4 internal/http/routes.go — full implementation

```go
// SPDX-License-Identifier: MIT
package httpapi

import "net/http"

// RegisterRoutes wires all HTTP handlers onto mux.
func RegisterRoutes(mux *http.ServeMux, h *Handler) {
	mux.HandleFunc("/flags", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			h.CreateFlag(w, r)
		case http.MethodGet:
			h.ListFlags(w, r)
		default:
			writeError(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/flags/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			h.GetFlag(w, r)
		case http.MethodPut:
			h.UpdateFlag(w, r)
		case http.MethodDelete:
			h.DeleteFlag(w, r)
		default:
			writeError(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	})

	mux.HandleFunc("/healthz", h.Healthz)
}
```

---

## Part 2 — etcd Backend with Watch

### 2.1 FlagValue struct (shared type)

The etcd client package owns the canonical `FlagValue` struct so both the HTTP layer and gRPC server import it without a circular dependency.

```go
// FlagValue is the canonical in-memory representation of a feature flag.
type FlagValue struct {
	FlagName  string `json:"flag_name"`
	Type      string `json:"type"`
	ValueJSON string `json:"value_json"`
	Version   int64  `json:"version"`
}

var ErrNotFound = errors.New("flag not found")
```

### 2.2 internal/etcd/client.go — full implementation

```go
// SPDX-License-Identifier: MIT
package etcd

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/akshantvats/distributed-flagd/internal/audit"
	clientv3 "go.etcd.io/etcd/client/v3"
)

const (
	flagPrefix  = "/flags/"
	auditPrefix = "/audit/"
	auditTTL    = 7776000
)

type Client struct {
	kv      clientv3.KV
	watcher clientv3.Watcher
	leaser  clientv3.Lease
	raw     *clientv3.Client
}

func NewClient(endpoint string) (*Client, error) {
	cli, err := clientv3.New(clientv3.Config{
		Endpoints:   []string{endpoint},
		DialTimeout: 5 * time.Second,
	})
	if err != nil {
		return nil, fmt.Errorf("etcd dial %s: %w", endpoint, err)
	}
	return &Client{
		kv:      clientv3.NewKV(cli),
		watcher: clientv3.NewWatcher(cli),
		leaser:  clientv3.NewLease(cli),
		raw:     cli,
	}, nil
}

func (c *Client) Close() error { return c.raw.Close() }

func (c *Client) Get(ctx context.Context, flagName string) (FlagValue, error) {
	resp, err := c.kv.Get(ctx, flagKey(flagName))
	if err != nil {
		return FlagValue{}, fmt.Errorf("etcd get %s: %w", flagName, err)
	}
	if len(resp.Kvs) == 0 {
		return FlagValue{}, ErrNotFound
	}
	var fv FlagValue
	if err := json.Unmarshal(resp.Kvs[0].Value, &fv); err != nil {
		return FlagValue{}, fmt.Errorf("unmarshal flag %s: %w", flagName, err)
	}
	fv.Version = resp.Kvs[0].ModRevision
	return fv, nil
}

func (c *Client) List(ctx context.Context) ([]FlagValue, error) {
	resp, err := c.kv.Get(ctx, flagPrefix, clientv3.WithPrefix())
	if err != nil {
		return nil, fmt.Errorf("etcd list flags: %w", err)
	}
	flags := make([]FlagValue, 0, len(resp.Kvs))
	for _, kv := range resp.Kvs {
		var fv FlagValue
		if err := json.Unmarshal(kv.Value, &fv); err != nil {
			continue
		}
		fv.Version = kv.ModRevision
		flags = append(flags, fv)
	}
	return flags, nil
}

func (c *Client) Put(ctx context.Context, fv FlagValue, changedBy, reason string) error {
	old, err := c.Get(ctx, fv.FlagName)
	var oldJSON json.RawMessage
	if err == nil {
		oldJSON, _ = json.Marshal(old)
	} else if !errors.Is(err, ErrNotFound) {
		return fmt.Errorf("pre-read for audit: %w", err)
	}

	newBytes, err := json.Marshal(fv)
	if err != nil {
		return fmt.Errorf("marshal flag: %w", err)
	}

	entry := audit.Entry{
		FlagName:  fv.FlagName,
		OldValue:  oldJSON,
		NewValue:  json.RawMessage(newBytes),
		ChangedBy: changedBy,
		ChangedAt: time.Now().UTC(),
		Reason:    reason,
	}
	auditBytes, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("marshal audit: %w", err)
	}

	leaseResp, err := c.leaser.Grant(ctx, auditTTL)
	if err != nil {
		return fmt.Errorf("lease grant for audit: %w", err)
	}

	auditKey := fmt.Sprintf("%s%s/%d", auditPrefix, fv.FlagName, time.Now().UnixNano())

	_, err = c.kv.Txn(ctx).
		Then(
			clientv3.OpPut(flagKey(fv.FlagName), string(newBytes)),
			clientv3.OpPut(auditKey, string(auditBytes), clientv3.WithLease(leaseResp.ID)),
		).
		Commit()
	if err != nil {
		return fmt.Errorf("etcd txn put %s: %w", fv.FlagName, err)
	}
	return nil
}

func (c *Client) Delete(ctx context.Context, flagName string) error {
	old, err := c.Get(ctx, flagName)
	if errors.Is(err, ErrNotFound) {
		return ErrNotFound
	}
	if err != nil {
		return err
	}

	oldBytes, _ := json.Marshal(old)
	entry := audit.Entry{
		FlagName:  flagName,
		OldValue:  json.RawMessage(oldBytes),
		NewValue:  json.RawMessage("null"),
		ChangedBy: "system",
		ChangedAt: time.Now().UTC(),
		Reason:    "deleted",
	}
	auditBytes, _ := json.Marshal(entry)

	leaseResp, err := c.leaser.Grant(ctx, auditTTL)
	if err != nil {
		return fmt.Errorf("lease grant for audit: %w", err)
	}
	auditKey := fmt.Sprintf("%s%s/%d", auditPrefix, flagName, time.Now().UnixNano())

	_, err = c.kv.Txn(ctx).
		Then(
			clientv3.OpDelete(flagKey(flagName)),
			clientv3.OpPut(auditKey, string(auditBytes), clientv3.WithLease(leaseResp.ID)),
		).
		Commit()
	if err != nil {
		return fmt.Errorf("etcd txn delete %s: %w", flagName, err)
	}
	return nil
}

func (c *Client) Watch(ctx context.Context, ch chan<- FlagValue) {
	watchCh := c.watcher.Watch(ctx, flagPrefix, clientv3.WithPrefix())
	for resp := range watchCh {
		for _, ev := range resp.Events {
			if ev.Type == clientv3.EventTypeDelete {
				ch <- FlagValue{FlagName: flagNameFromKey(string(ev.Kv.Key)), Version: -1}
				continue
			}
			var fv FlagValue
			if err := json.Unmarshal(ev.Kv.Value, &fv); err != nil {
				continue
			}
			fv.Version = ev.Kv.ModRevision
			ch <- fv
		}
	}
}

func flagKey(name string) string        { return flagPrefix + name }
func flagNameFromKey(key string) string { return key[len(flagPrefix):] }
```

---

## Part 3 — gRPC Streaming Server

### 3.1 internal/server/fanout.go — full implementation

```go
// SPDX-License-Identifier: MIT
package server

import (
	"sync"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
)

type registry struct {
	mu      sync.RWMutex
	streams map[string]chan etcd.FlagValue
}

func newRegistry() *registry {
	return &registry{streams: make(map[string]chan etcd.FlagValue)}
}

func (r *registry) subscribe(id string) chan etcd.FlagValue {
	ch := make(chan etcd.FlagValue, 64)
	r.mu.Lock()
	r.streams[id] = ch
	r.mu.Unlock()
	return ch
}

func (r *registry) unsubscribe(id string) {
	r.mu.Lock()
	if ch, ok := r.streams[id]; ok {
		close(ch)
		delete(r.streams, id)
	}
	r.mu.Unlock()
}

// broadcast sends fv to all subscribers; drops for slow clients (non-blocking).
func (r *registry) broadcast(fv etcd.FlagValue) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	for _, ch := range r.streams {
		select {
		case ch <- fv:
		default:
		}
	}
}
```

### 3.2 internal/server/server.go — full implementation

```go
// SPDX-License-Identifier: MIT
package server

import (
	"context"
	"fmt"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
	pb "github.com/akshantvats/distributed-flagd/proto/flagd/v1"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type Server struct {
	pb.UnimplementedFlagServiceServer
	store    *etcd.Client
	registry *registry
}

func New(ctx context.Context, store *etcd.Client) *Server {
	s := &Server{store: store, registry: newRegistry()}
	go s.watchLoop(ctx)
	return s
}

func (s *Server) watchLoop(ctx context.Context) {
	ch := make(chan etcd.FlagValue, 256)
	go s.store.Watch(ctx, ch)
	for {
		select {
		case <-ctx.Done():
			return
		case fv, ok := <-ch:
			if !ok {
				return
			}
			s.registry.broadcast(fv)
		}
	}
}

func (s *Server) GetFlag(ctx context.Context, req *pb.GetFlagRequest) (*pb.FlagValue, error) {
	if req.FlagName == "" {
		return nil, status.Error(codes.InvalidArgument, "flag_name is required")
	}
	fv, err := s.store.Get(ctx, req.FlagName)
	if err != nil {
		if err == etcd.ErrNotFound {
			return nil, status.Errorf(codes.NotFound, "flag %q not found", req.FlagName)
		}
		return nil, status.Errorf(codes.Internal, "etcd get: %v", err)
	}
	return toProto(fv), nil
}

func (s *Server) SetFlag(ctx context.Context, req *pb.SetFlagRequest) (*pb.SetFlagResponse, error) {
	if req.FlagName == "" {
		return &pb.SetFlagResponse{Success: false, ErrorMsg: "flag_name is required"}, nil
	}
	fv := etcd.FlagValue{FlagName: req.FlagName, ValueJSON: req.ValueJson}
	if err := s.store.Put(ctx, fv, req.ChangedBy, req.Reason); err != nil {
		return &pb.SetFlagResponse{Success: false, ErrorMsg: err.Error()}, nil
	}
	updated, err := s.store.Get(ctx, req.FlagName)
	if err != nil {
		return &pb.SetFlagResponse{Success: true, Revision: 0}, nil
	}
	return &pb.SetFlagResponse{Success: true, Revision: updated.Version}, nil
}

func (s *Server) ListFlags(ctx context.Context, _ *pb.ListFlagsRequest) (*pb.FlagList, error) {
	flags, err := s.store.List(ctx)
	if err != nil {
		return nil, status.Errorf(codes.Internal, "etcd list: %v", err)
	}
	pbFlags := make([]*pb.FlagValue, 0, len(flags))
	for _, fv := range flags {
		pbFlags = append(pbFlags, toProto(fv))
	}
	return &pb.FlagList{Flags: pbFlags}, nil
}

func (s *Server) EvaluateStream(req *pb.EvaluateStreamRequest, stream pb.FlagService_EvaluateStreamServer) error {
	ctx := stream.Context()

	flags, err := s.store.List(ctx)
	if err != nil {
		return status.Errorf(codes.Internal, "snapshot fetch: %v", err)
	}
	pbFlags := make([]*pb.FlagValue, 0, len(flags))
	for _, fv := range flags {
		pbFlags = append(pbFlags, toProto(fv))
	}
	if err := stream.Send(&pb.FlagUpdate{
		UpdateType: pb.FlagUpdate_SNAPSHOT,
		Flags:      pbFlags,
	}); err != nil {
		return err
	}

	streamID := fmt.Sprintf("%s/%s", req.ServiceName, req.InstanceId)
	ch := s.registry.subscribe(streamID)
	defer s.registry.unsubscribe(streamID)

	for {
		select {
		case <-ctx.Done():
			return nil
		case fv, ok := <-ch:
			if !ok {
				return nil
			}
			if err := stream.Send(&pb.FlagUpdate{
				UpdateType: pb.FlagUpdate_DELTA,
				Flags:      []*pb.FlagValue{toProto(fv)},
			}); err != nil {
				return err
			}
		}
	}
}

func toProto(fv etcd.FlagValue) *pb.FlagValue {
	return &pb.FlagValue{
		FlagName:  fv.FlagName,
		Type:      fv.Type,
		ValueJson: fv.ValueJSON,
		Version:   fv.Version,
	}
}
```

---

## Part 4 — Audit Log

### 4.1 internal/audit/audit.go — full implementation

```go
// SPDX-License-Identifier: MIT
package audit

import (
	"encoding/json"
	"time"
)

// Entry is the audit log record written atomically with every flag mutation.
// All six fields required by DESIGN.md Section 1.6 are present.
type Entry struct {
	FlagName                string          `json:"flag_name"`
	OldValue                json.RawMessage `json:"old_value"`
	NewValue                json.RawMessage `json:"new_value"`
	ChangedBy               string          `json:"changed_by"`
	ChangedAt               time.Time       `json:"changed_at"`
	EvaluationCountSnapshot int64           `json:"evaluation_count_snapshot"` // populated by Day 23
	Reason                  string          `json:"reason,omitempty"`
}
```

`EvaluationCountSnapshot` is always `0` on Day 22. Day 23 wires in the evaluator integration that fills this field.

---

## Part 5 — cmd/flagd/main.go — final wiring

```go
// SPDX-License-Identifier: MIT
package main

import (
	"context"
	"flag"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"

	etcdclient "github.com/akshantvats/distributed-flagd/internal/etcd"
	httpapi "github.com/akshantvats/distributed-flagd/internal/http"
	"github.com/akshantvats/distributed-flagd/internal/server"
	pb "github.com/akshantvats/distributed-flagd/proto/flagd/v1"
	"google.golang.org/grpc"
)

func main() {
	etcdAddr := flag.String("etcd", "localhost:2379", "etcd endpoint")
	grpcAddr := flag.String("grpc", ":50051", "gRPC listen address")
	httpAddr := flag.String("http", ":8080", "HTTP listen address")
	flag.Parse()

	store, err := etcdclient.NewClient(*etcdAddr)
	if err != nil {
		log.Fatalf("etcd connect: %v", err)
	}
	defer store.Close()

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	flagServer := server.New(ctx, store)
	grpcServer := grpc.NewServer()
	pb.RegisterFlagServiceServer(grpcServer, flagServer)
	grpcLis, err := net.Listen("tcp", *grpcAddr)
	if err != nil {
		log.Fatalf("grpc listen: %v", err)
	}
	go func() {
		log.Printf("gRPC listening on %s", *grpcAddr)
		if err := grpcServer.Serve(grpcLis); err != nil {
			log.Fatalf("grpc serve: %v", err)
		}
	}()

	handler := httpapi.New(store)
	mux := http.NewServeMux()
	httpapi.RegisterRoutes(mux, handler)
	httpServer := &http.Server{Addr: *httpAddr, Handler: mux}
	go func() {
		log.Printf("HTTP listening on %s", *httpAddr)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("http serve: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("shutting down...")
	cancel()
	grpcServer.GracefulStop()
	_ = httpServer.Shutdown(context.Background())
}
```

---

## Part 6 — Docker Compose + Makefile

The `docker-compose.yml` from Day 21 is already correct. Add these targets to the Day 21 `Makefile`:

```makefile
.PHONY: build proto test lint docker smoke

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

smoke:
	docker compose up -d
	sleep 3
	curl -sf -X POST http://localhost:8080/flags \
	  -H "Content-Type: application/json" \
	  -d '{"flag_name":"smoke_test","type":"bool","value_json":"true","changed_by":"ci"}' \
	  | grep smoke_test
	curl -sf http://localhost:8080/flags/smoke_test | grep smoke_test
	docker compose down
```

---

## Part 7 — Tests

### 7.1 internal/eval/evaluator_test.go

```go
// SPDX-License-Identifier: MIT
package eval_test

import (
	"fmt"
	"testing"

	"github.com/akshantvats/distributed-flagd/internal/eval"
)

func TestEvaluatePercentage_Deterministic(t *testing.T) {
	variants := []eval.PercentageVariant{
		{Value: "gpt-4o", Weight: 10},
		{Value: "gpt-3.5-turbo", Weight: 90},
	}
	first := eval.EvaluatePercentage("llm_model", "req-abc-123", variants)
	for i := 0; i < 1000; i++ {
		got := eval.EvaluatePercentage("llm_model", "req-abc-123", variants)
		if got != first {
			t.Fatalf("iteration %d: got %q, want %q", i, got, first)
		}
	}
}

func TestEvaluatePercentage_Distribution(t *testing.T) {
	variants := []eval.PercentageVariant{
		{Value: "a", Weight: 50},
		{Value: "b", Weight: 50},
	}
	counts := map[string]int{}
	for i := 0; i < 10000; i++ {
		key := fmt.Sprintf("req-%d", i)
		v := eval.EvaluatePercentage("flag", key, variants)
		counts[v]++
	}
	for _, v := range []string{"a", "b"} {
		pct := float64(counts[v]) / 10000 * 100
		if pct < 48 || pct > 52 {
			t.Errorf("variant %q: %.1f%% (want 48-52%%)", v, pct)
		}
	}
}

func TestEvaluatePercentage_EmptyVariants(t *testing.T) {
	got := eval.EvaluatePercentage("flag", "key", nil)
	if got != "" {
		t.Errorf("empty variants: got %q, want empty string", got)
	}
}
```

### 7.2 Integration test (internal/etcd/client_integration_test.go)

```go
// SPDX-License-Identifier: MIT
//go:build integration

package etcd_test

import (
	"context"
	"testing"
	"time"

	"github.com/akshantvats/distributed-flagd/internal/etcd"
	tc "github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"
)

func startEtcd(t *testing.T) (string, func()) {
	t.Helper()
	ctx := context.Background()
	req := tc.ContainerRequest{
		Image:        "quay.io/coreos/etcd:v3.5.12",
		ExposedPorts: []string{"2379/tcp"},
		Cmd: []string{
			"etcd",
			"--advertise-client-urls=http://0.0.0.0:2379",
			"--listen-client-urls=http://0.0.0.0:2379",
		},
		WaitingFor: wait.ForListeningPort("2379/tcp").WithStartupTimeout(30 * time.Second),
	}
	container, err := tc.GenericContainer(ctx, tc.GenericContainerRequest{ContainerRequest: req, Started: true})
	if err != nil {
		t.Fatalf("start etcd: %v", err)
	}
	host, _ := container.Host(ctx)
	port, _ := container.MappedPort(ctx, "2379")
	return host + ":" + port.Port(), func() { _ = container.Terminate(ctx) }
}

func TestClientPutGet(t *testing.T) {
	endpoint, cleanup := startEtcd(t)
	defer cleanup()
	c, err := etcd.NewClient(endpoint)
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	defer c.Close()
	ctx := context.Background()
	fv := etcd.FlagValue{FlagName: "test-flag", Type: "bool", ValueJSON: "true"}
	if err := c.Put(ctx, fv, "test", "unit test"); err != nil {
		t.Fatalf("Put: %v", err)
	}
	got, err := c.Get(ctx, "test-flag")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if got.ValueJSON != "true" {
		t.Errorf("got ValueJSON=%q, want true", got.ValueJSON)
	}
}

func TestClientWatch(t *testing.T) {
	endpoint, cleanup := startEtcd(t)
	defer cleanup()
	c, err := etcd.NewClient(endpoint)
	if err != nil {
		t.Fatalf("NewClient: %v", err)
	}
	defer c.Close()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	ch := make(chan etcd.FlagValue, 8)
	go c.Watch(ctx, ch)
	time.Sleep(100 * time.Millisecond)
	fv := etcd.FlagValue{FlagName: "watch-flag", Type: "string", ValueJSON: `"v1"`}
	if err := c.Put(ctx, fv, "test", "watch test"); err != nil {
		t.Fatalf("Put: %v", err)
	}
	select {
	case got := <-ch:
		if got.FlagName != "watch-flag" {
			t.Errorf("got %q, want watch-flag", got.FlagName)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("timeout waiting for watch event")
	}
}
```

Run with: `go test -tags=integration ./internal/etcd/... -v`

---

## Implementation Checklist

### Part 1 — HTTP CRUD
- [ ] Create `internal/http/handler.go` with `Handler` struct and all five methods
- [ ] Create `internal/http/routes.go` with `RegisterRoutes`
- [ ] `POST /flags` creates a flag, returns 201 with flag JSON
- [ ] `GET /flags` returns all flags with count
- [ ] `GET /flags/{name}` returns single flag or 404
- [ ] `PUT /flags/{name}` updates flag, returns 200
- [ ] `DELETE /flags/{name}` deletes flag, returns 204 or 404
- [ ] `GET /healthz` returns `{"status":"ok"}`

### Part 2 — etcd Client
- [ ] Add `FlagValue` struct and `ErrNotFound` to `internal/etcd/client.go`
- [ ] Implement `NewClient` with 5s dial timeout
- [ ] Implement `Get`, `List`, `Put` (atomic Txn), `Delete` (atomic Txn), `Watch`

### Part 3 — gRPC Server
- [ ] Create `internal/server/fanout.go` with `registry`, `subscribe`, `unsubscribe`, `broadcast`
- [ ] Implement `server.New` — starts `watchLoop` goroutine
- [ ] Implement all four proto RPCs with correct interface signatures
- [ ] `EvaluateStream` sends SNAPSHOT on connect, DELTA on each flag change

### Part 4 — Audit Log
- [ ] `audit.Entry` struct with all 6 required fields
- [ ] `EvaluationCountSnapshot` field present (0 on Day 22)

### Part 5 — main.go
- [ ] Wire HTTP server on `:8080` and gRPC server on `:50051`
- [ ] Graceful shutdown on SIGINT/SIGTERM

### Part 6 — Docker Compose + Makefile
- [ ] `make docker` brings up etcd + flagd
- [ ] `make smoke` exits 0
- [ ] `make build` and `make test` exit 0

### Part 7 — Tests
- [ ] Unit tests: determinism, 50/50 distribution, empty variants
- [ ] Integration tests behind `//go:build integration` tag
- [ ] `go test ./... -race -count=1` exits 0

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| etcd Txn atomicity: audit lease grant fails before Txn | Low | Medium | Grant lease before building Txn ops; if grant fails, return error before any write |
| gRPC fan-out goroutine leak on client disconnect | Medium | Medium | `defer s.registry.unsubscribe(streamID)` ensures cleanup even on `Send` error |
| Watch channel backpressure: slow consumer blocks fan-out | Low | High | Buffer of 256 on internal watch channel; non-blocking send in `broadcast` drops for slow clients |
| testcontainers not available in CI | Medium | Low | Integration tests behind `//go:build integration` tag; unit tests run without docker |
| proto-generated code out of sync | Low | High | `make proto` is idempotent; run in CI before `go build`; generated files committed |

---

## Definition of Done

- [ ] `go build ./...` exits 0
- [ ] `go test ./... -race -count=1` exits 0 (unit tests)
- [ ] `make smoke` exits 0 end-to-end
- [ ] gRPC EvaluateStream receives SNAPSHOT then DELTA within 200ms of a flag PUT
- [ ] Audit entry exists in etcd under `/audit/smoke_test/` after a PUT
- [ ] PR opened with build and test output in description
- [ ] PR URL captured in `DAILY_PROGRESS.md`
- [ ] `Self-review: N issues found and fixed.` in commit message

---

## PR Description Template

```
## Day 22 — distributed-flagd: Core Implementation

### What
- HTTP CRUD layer: POST/GET/PUT/DELETE /flags, GET /healthz
- etcd backend: Get, List, Put (atomic Txn + audit), Delete, Watch prefix
- gRPC server: GetFlag, SetFlag, ListFlags, EvaluateStream with fan-out registry
- Audit log: atomic write with flag mutation, 90-day lease, all 6 required fields
- Graceful shutdown: SIGINT/SIGTERM drains gRPC streams and HTTP connections

### Build output
```
$ go build ./...
(no errors)
$ go test ./... -race -count=1
ok  github.com/akshantvats/distributed-flagd/internal/eval   0.012s
$ make smoke
{"flag_name":"smoke_test","type":"bool","value_json":"true","version":2}
```

### Key design decisions
1. Fan-out via buffered channels — slow clients get drops, re-sync via SNAPSHOT on reconnect
2. Atomic Txn for audit — flag write and audit entry are a single etcd Txn
3. FlagValue owned by etcd package — HTTP and gRPC import from etcd, no circular deps

### What Day 23 adds
- resolved_model_id label injection into infra-ai-streaming ingest events
- Sticky assignment tests at 50k evaluations

Self-review: N issues found and fixed.
```
