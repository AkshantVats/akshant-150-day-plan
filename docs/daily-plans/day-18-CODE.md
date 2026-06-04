# Day 18 — Code Plan
## Ticket G-10 Pattern on Ingestion Path: WAL + Rate Limiting in ebpf-llm-tracer

**Calendar**: Saturday, June 4 2026 · Day 18 of 150
**Product**: LensAI
**Repo**: `AkshantVats/ebpf-llm-tracer`
**Language**: Go (consumer), Rust (ingestion path reference)
**Builds on**: Day 16 (HTTP event parsing), Day 17 (Prometheus metrics, streaming reassembly)

### Shared Thread
> `wal_replay_events_total` and probe drop counters belong in the same Grafana board — both are durability under overload.

---

## Summary

Day 18 hardens the Go consumer in two orthogonal directions:

1. **WAL (Write-Ahead Log)** — before any `kafka.Produce()` call, append the HTTPEvent to an append-only segment file on disk. On startup, replay any segments that were never ack'd. This is the G-10 pattern: never lose a write because a downstream broker was temporarily unavailable.

2. **Rate limiting + drop policy** — when Kafka backpressures (ring buffer full, produce latency > threshold), the consumer enters a shedding mode. New events are evaluated against a per-origin token bucket; events that exceed the bucket are dropped and counted. This prevents unbounded queue growth from cascading into OOM.

Both features report into the shared durability Grafana board alongside the existing eBPF probe drop counters from Day 17.

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | WAL segments written to disk before every `Produce()` call | Unit test: kill process mid-produce, confirm segment file exists |
| AC-2 | On startup, un-acked segments are replayed in order before accepting new events | Integration test: write 100 events, crash before ack, restart, verify 100 events produced |
| AC-3 | Segments older than `wal_retention_seconds` are pruned on startup | Unit test: inject old segment, confirm pruned |
| AC-4 | `wal_segments_pending` gauge reflects actual count of unacknowledged segment files | Prometheus scrape test |
| AC-5 | `wal_replay_events_total` counter increments for every replayed event | Integration test |
| AC-6 | Token bucket rate limiter created per unique origin (host:port of traced process) | Unit test: two origins, each gets independent bucket |
| AC-7 | Events dropped when bucket exhausted; `probe_events_dropped_total` incremented | Unit test |
| AC-8 | Drop policy is `tail-drop` (newest event dropped, WAL'd events never dropped) | Confirmed by code review + test |
| AC-9 | When Kafka produce latency falls below threshold, rate limiter resets | Integration test with mock Kafka |
| AC-10 | All new metrics visible in `GET /metrics` Prometheus endpoint | Scrape + parse test |

---

## Architecture

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart TD
    subgraph kernel ["eBPF Kernel Space"]
        P["kprobe: SSL_write/read"]
        RB["Perf Ring Buffer"]
    end
    subgraph consumer ["Go Consumer (Day 18 focus)"]
        RD["Ring Buffer Reader"]
        RL["Rate Limiter\n(per-origin token bucket)"]
        WAL["WAL Writer\n(append segment)"]
        KP["Kafka Producer"]
        ACK["Ack Handler\n(delete segment)"]
        REP["WAL Replay\n(startup only)"]
    end
    subgraph storage ["Disk"]
        SEG["WAL Segments\n/var/lib/lensai/wal/"]
    end
    subgraph kafka ["Kafka"]
        TOP["llm-http-events topic"]
    end

    P --> RB
    RB --> RD
    RD -->|"backpressure\ncheck"| RL
    RL -->|"token available"| WAL
    RL -->|"bucket empty"| DROP["Drop + count"]
    WAL --> SEG
    WAL --> KP
    KP --> TOP
    TOP --> ACK
    ACK -->|"delete segment"| SEG
    SEG -->|"on startup"| REP
    REP --> KP
```

---

## Implementation Plan

### Part 1 — WAL (Write-Ahead Log)

#### 1.1 Directory Structure

```
ebpf-llm-tracer/
  consumer/
    wal/
      wal.go          ← WAL manager: open, append, list, replay, prune
      segment.go      ← segment file: header + framing
      wal_test.go
    ratelimit/
      token_bucket.go ← per-origin token bucket
      ratelimit_test.go
    consumer.go       ← wires WAL + rate limiter into existing event loop
```

#### 1.2 WAL Segment File Format

Each WAL segment is a single file. One file = one HTTPEvent (or a configurable micro-batch of up to N events — start with 1 for simplicity; batching is a follow-up).

**File naming convention:**

```
/var/lib/lensai/wal/{unix_nano}_{uuid4}.wal
```

- `unix_nano`: nanosecond timestamp at write time — ensures natural ordering on replay
- `uuid4`: collision avoidance across goroutines
- `.wal` extension: distinguishes from other files in the directory

**File binary layout:**

```
Offset  Len   Field
──────────────────────────────────────────────────────
0       4     Magic: 0x4C454E53 ("LENS") — integrity check
4       2     Version: uint16 LE, currently 0x0001
6       8     WriteTimestamp: unix nano, int64 LE
14      4     PayloadLength: uint32 LE
18      1     Encoding: 0x01 = protobuf, 0x02 = JSON (use protobuf)
19      4     CRC32: IEEE checksum of bytes [0..18] + payload
23      N     Payload: serialized HTTPEvent proto
```

Why magic + CRC: if a process crashes mid-write, we may have a partial segment. On replay, magic check fails → segment is skipped and logged, not crashed on. CRC catches bit rot or truncation.

#### 1.3 WAL Manager — Go stubs

```go
// consumer/wal/wal.go

package wal

import (
    "os"
    "path/filepath"
    "sort"
    "sync"
    "time"

    "github.com/akshantvats/ebpf-llm-tracer/proto"
    "github.com/prometheus/client_golang/prometheus"
)

const (
    Magic   uint32 = 0x4C454E53
    Version uint16 = 1
    WalExt         = ".wal"
)

type Config struct {
    Dir              string
    RetentionSeconds int64 // segments older than this are pruned even if un-acked
}

type WAL struct {
    cfg     Config
    mu      sync.Mutex
    pending map[string]struct{} // segment path → in-flight

    // Prometheus
    segmentsPending prometheus.Gauge
    replayTotal     prometheus.Counter
}

func New(cfg Config, reg prometheus.Registerer) (*WAL, error) {
    if err := os.MkdirAll(cfg.Dir, 0o755); err != nil {
        return nil, err
    }
    w := &WAL{
        cfg:     cfg,
        pending: make(map[string]struct{}),
        segmentsPending: prometheus.NewGauge(prometheus.GaugeOpts{
            Namespace: "lensai",
            Name:      "wal_segments_pending",
            Help:      "Number of WAL segment files not yet acked by Kafka",
        }),
        replayTotal: prometheus.NewCounter(prometheus.CounterOpts{
            Namespace: "lensai",
            Name:      "wal_replay_events_total",
            Help:      "Total HTTPEvents replayed from WAL on startup",
        }),
    }
    reg.MustRegister(w.segmentsPending, w.replayTotal)
    return w, nil
}

// Append writes the event to a new segment file and returns the segment path.
// Must be called BEFORE kafka.Produce().
func (w *WAL) Append(ev *proto.HTTPEvent) (segPath string, err error) {
    payload, err := marshalEvent(ev)
    if err != nil {
        return "", err
    }
    path, err := writeSegment(w.cfg.Dir, payload)
    if err != nil {
        return "", err
    }
    w.mu.Lock()
    w.pending[path] = struct{}{}
    w.segmentsPending.Set(float64(len(w.pending)))
    w.mu.Unlock()
    return path, nil
}

// Ack deletes the segment after Kafka confirms delivery.
func (w *WAL) Ack(segPath string) error {
    if err := os.Remove(segPath); err != nil && !os.IsNotExist(err) {
        return err
    }
    w.mu.Lock()
    delete(w.pending, segPath)
    w.segmentsPending.Set(float64(len(w.pending)))
    w.mu.Unlock()
    return nil
}

// ReplayPending reads all existing segment files in timestamp order,
// calls produce() for each, then calls Ack on success.
// Must be called once on startup before the main event loop begins.
func (w *WAL) ReplayPending(produce func(*proto.HTTPEvent) error) error {
    segments, err := listSegments(w.cfg.Dir)
    if err != nil {
        return err
    }
    pruneThreshold := time.Now().UnixNano() - w.cfg.RetentionSeconds*int64(time.Second)
    for _, seg := range segments {
        ts, payload, err := readSegment(seg)
        if err != nil {
            logCorrupt(seg, err)
            _ = os.Remove(seg)
            continue
        }
        if ts < pruneThreshold {
            _ = os.Remove(seg)
            continue
        }
        ev, err := unmarshalEvent(payload)
        if err != nil {
            logCorrupt(seg, err)
            _ = os.Remove(seg)
            continue
        }
        if err := produce(ev); err != nil {
            return err
        }
        w.replayTotal.Inc()
        _ = w.Ack(seg)
    }
    return nil
}

// listSegments returns segment paths sorted by embedded timestamp (filename).
func listSegments(dir string) ([]string, error) {
    entries, err := os.ReadDir(dir)
    if err != nil {
        return nil, err
    }
    var paths []string
    for _, e := range entries {
        if filepath.Ext(e.Name()) == WalExt {
            paths = append(paths, filepath.Join(dir, e.Name()))
        }
    }
    sort.Strings(paths)
    return paths, nil
}
```

```go
// consumer/wal/segment.go

package wal

import (
    "encoding/binary"
    "fmt"
    "hash/crc32"
    "os"
    "path/filepath"
    "time"

    "github.com/google/uuid"
)

func writeSegment(dir string, payload []byte) (string, error) {
    now := time.Now().UnixNano()
    fname := fmt.Sprintf("%d_%s%s", now, uuid.NewString(), WalExt)
    path := filepath.Join(dir, fname)

    f, err := os.OpenFile(path, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0o644)
    if err != nil {
        return "", err
    }
    defer f.Close()

    header := make([]byte, 23)
    binary.LittleEndian.PutUint32(header[0:4], Magic)
    binary.LittleEndian.PutUint16(header[4:6], Version)
    binary.LittleEndian.PutUint64(header[6:14], uint64(now))
    binary.LittleEndian.PutUint32(header[14:18], uint32(len(payload)))
    header[18] = 0x01

    crc := crc32.ChecksumIEEE(append(header[:19], payload...))
    binary.LittleEndian.PutUint32(header[19:23], crc)

    if _, err := f.Write(header); err != nil {
        return "", err
    }
    if _, err := f.Write(payload); err != nil {
        return "", err
    }
    return path, f.Sync()
}

func readSegment(path string) (ts int64, payload []byte, err error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return 0, nil, err
    }
    if len(data) < 23 {
        return 0, nil, fmt.Errorf("segment too short: %d bytes", len(data))
    }
    if binary.LittleEndian.Uint32(data[0:4]) != Magic {
        return 0, nil, fmt.Errorf("bad magic in %s", path)
    }
    payLen := binary.LittleEndian.Uint32(data[14:18])
    if int(payLen) != len(data)-23 {
        return 0, nil, fmt.Errorf("payload length mismatch in %s", path)
    }
    storedCRC := binary.LittleEndian.Uint32(data[19:23])
    computedCRC := crc32.ChecksumIEEE(append(data[:19], data[23:]...))
    if storedCRC != computedCRC {
        return 0, nil, fmt.Errorf("CRC mismatch in %s: stored=%08x computed=%08x", path, storedCRC, computedCRC)
    }
    ts = int64(binary.LittleEndian.Uint64(data[6:14]))
    return ts, data[23:], nil
}
```

---

### Part 2 — Rate Limiting + Drop Policy

#### 2.1 Design Decisions

- **Algorithm**: token bucket (not leaky bucket). Token bucket allows short bursts — appropriate for tracing workloads where HTTP events come in clusters (a single LLM inference is a burst of request + streaming chunks). Leaky bucket smooths at the cost of dropping legitimate bursts.
- **Granularity**: per-origin, where origin = `(pid, comm)` tuple from the eBPF probe. Different processes traced on the same host each get their own bucket.
- **Backpressure signal**: Kafka produce latency > `kafka_backpressure_threshold_ms` (default 500ms) OR ring buffer overflow counter increments. Either signal activates rate limiting.
- **Drop policy**: tail-drop (newest event dropped when bucket empty). WAL'd events are never subject to the rate limiter — they've already been persisted and are being replayed in order.
- **Recovery**: when Kafka produce latency drops below `kafka_recovery_threshold_ms` (default 100ms) for 3 consecutive measurements, buckets are refilled to capacity.

#### 2.2 Token Bucket Parameters

| Parameter | Default | Rationale |
|-----------|---------|----------|
| `bucket_capacity` | 1000 tokens | ~1000 events before shedding kicks in |
| `refill_rate` | 200 tokens/sec | Matches expected steady-state ~200 events/sec per origin |
| `refill_interval` | 100ms | Granularity; refills 20 tokens every 100ms |
| `backpressure_threshold_ms` | 500 | Kafka produce p99 above this = backpressure |
| `recovery_threshold_ms` | 100 | Kafka produce p99 below this = recovered |
| `recovery_confirmations` | 3 | Consecutive measurements below threshold before refill |

#### 2.3 Rate Limiter — Go stubs

```go
// consumer/ratelimit/token_bucket.go

package ratelimit

import (
    "sync"
    "time"

    "github.com/prometheus/client_golang/prometheus"
)

type Config struct {
    Capacity              float64
    RefillRate            float64
    RefillInterval        time.Duration
    BackpressureThreshold time.Duration
    RecoveryThreshold     time.Duration
    RecoveryConfirmations int
}

func DefaultConfig() Config {
    return Config{
        Capacity:              1000,
        RefillRate:            200,
        RefillInterval:        100 * time.Millisecond,
        BackpressureThreshold: 500 * time.Millisecond,
        RecoveryThreshold:     100 * time.Millisecond,
        RecoveryConfirmations: 3,
    }
}

type bucket struct {
    tokens    float64
    lastRefil time.Time
    mu        sync.Mutex
}

func (b *bucket) consume(cfg Config) bool {
    b.mu.Lock()
    defer b.mu.Unlock()
    now := time.Now()
    elapsed := now.Sub(b.lastRefil).Seconds()
    b.tokens += elapsed * cfg.RefillRate
    if b.tokens > cfg.Capacity {
        b.tokens = cfg.Capacity
    }
    b.lastRefil = now
    if b.tokens >= 1.0 {
        b.tokens -= 1.0
        return true
    }
    return false
}

type Manager struct {
    cfg    Config
    mu     sync.RWMutex
    buckets map[string]*bucket

    backpressureActive bool
    recoveryCount      int

    droppedTotal      prometheus.Counter
    backpressureGauge prometheus.Gauge
}

func NewManager(cfg Config, reg prometheus.Registerer) *Manager {
    m := &Manager{
        cfg:     cfg,
        buckets: make(map[string]*bucket),
        droppedTotal: prometheus.NewCounter(prometheus.CounterOpts{
            Namespace: "lensai",
            Name:      "probe_events_dropped_total",
            Help:      "Total HTTPEvents dropped due to rate limiting under Kafka backpressure",
        }),
        backpressureGauge: prometheus.NewGauge(prometheus.GaugeOpts{
            Namespace: "lensai",
            Name:      "kafka_backpressure_active",
            Help:      "1 if Kafka backpressure is active and rate limiting is enforced",
        }),
    }
    reg.MustRegister(m.droppedTotal, m.backpressureGauge)
    return m
}

func (m *Manager) Allow(origin string) bool {
    m.mu.RLock()
    active := m.backpressureActive
    m.mu.RUnlock()

    if !active {
        return true
    }

    m.mu.Lock()
    b, ok := m.buckets[origin]
    if !ok {
        b = &bucket{tokens: m.cfg.Capacity, lastRefil: time.Now()}
        m.buckets[origin] = b
    }
    m.mu.Unlock()

    allowed := b.consume(m.cfg)
    if !allowed {
        m.droppedTotal.Inc()
    }
    return allowed
}

func (m *Manager) ObserveProduceLatency(latency time.Duration) {
    m.mu.Lock()
    defer m.mu.Unlock()

    if !m.backpressureActive {
        if latency > m.cfg.BackpressureThreshold {
            m.backpressureActive = true
            m.recoveryCount = 0
            m.backpressureGauge.Set(1)
        }
        return
    }

    if latency < m.cfg.RecoveryThreshold {
        m.recoveryCount++
        if m.recoveryCount >= m.cfg.RecoveryConfirmations {
            m.backpressureActive = false
            m.backpressureGauge.Set(0)
            m.refillAllBuckets()
        }
    } else {
        m.recoveryCount = 0
    }
}

func (m *Manager) refillAllBuckets() {
    for _, b := range m.buckets {
        b.mu.Lock()
        b.tokens = m.cfg.Capacity
        b.mu.Unlock()
    }
}
```

---

### Part 3 — Wiring into consumer.go

```go
func (c *Consumer) processEvent(ev *proto.HTTPEvent) error {
    origin := fmt.Sprintf("%d:%s", ev.Pid, ev.Comm)

    if !c.rateLimiter.Allow(origin) {
        return nil
    }

    segPath, err := c.wal.Append(ev)
    if err != nil {
        return fmt.Errorf("wal append: %w", err)
    }

    start := time.Now()
    if err := c.producer.Produce(ev); err != nil {
        c.rateLimiter.ObserveProduceLatency(time.Since(start))
        return fmt.Errorf("kafka produce: %w", err)
    }
    c.rateLimiter.ObserveProduceLatency(time.Since(start))

    return c.wal.Ack(segPath)
}

func (c *Consumer) Start(ctx context.Context) error {
    if err := c.wal.ReplayPending(func(ev *proto.HTTPEvent) error {
        return c.producer.Produce(ev)
    }); err != nil {
        return fmt.Errorf("wal replay: %w", err)
    }
    return c.runEventLoop(ctx)
}
```

---

## Metrics Definitions

| Metric name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `lensai_wal_segments_pending` | Gauge | — | Number of WAL segment files on disk awaiting Kafka ack |
| `lensai_wal_replay_events_total` | Counter | — | Cumulative events replayed from WAL since process start |
| `lensai_probe_events_dropped_total` | Counter | `comm` | Events dropped by rate limiter under backpressure (label by comm, not pid — cardinality bound) |
| `lensai_kafka_backpressure_active` | Gauge | — | 1 when backpressure state machine is active, 0 when recovered |
| `lensai_kafka_produce_latency_seconds` | Histogram | — | Latency of kafka.Produce() calls; p99 drives backpressure signal |

**Cardinality note**: `probe_events_dropped_total` labels by `comm` (process name, ~10 values) not `pid` (unbounded). Document in metric Help string.

---

## Grafana Board: "LensAI Durability Under Overload"

Shared board with probe drop counters from Day 17. Day 18 adds:

- Panel 1: `lensai_wal_segments_pending` — gauge, alert at > 1000
- Panel 2: `rate(lensai_wal_replay_events_total[5m])` — should be 0 in steady state; spike = recent crash
- Panel 3: `lensai_kafka_backpressure_active` — state timeline (0/1)
- Panel 4: `sum(rate(lensai_probe_events_dropped_total[1m]))` — drop rate
- Panel 5: `histogram_quantile(0.99, lensai_kafka_produce_latency_seconds_bucket)` — the backpressure signal

---

## WAL Segment Lifecycle Diagram

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
stateDiagram-v2
    [*] --> Written: wal.Append()
    Written --> Producing: kafka.Produce() called
    Producing --> Acked: delivery confirmed
    Producing --> Written: produce error (segment stays)
    Acked --> [*]: wal.Ack() deletes file
    Written --> Replayed: startup replay
    Replayed --> Acked: produce + ack
    Written --> Pruned: age > retention
    Pruned --> [*]
```

---

## Implementation Checklist

### Setup
- [ ] Create `consumer/wal/` directory
- [ ] Create `consumer/ratelimit/` directory
- [ ] Add `github.com/google/uuid` to `go.mod`
- [ ] Verify protobuf dependency for `marshalEvent` / `unmarshalEvent`

### WAL
- [ ] Implement `segment.go`: `writeSegment`, `readSegment` with magic + CRC
- [ ] Implement `wal.go`: `New`, `Append`, `Ack`, `ReplayPending`, `listSegments`
- [ ] Wire Prometheus metrics in `New()`
- [ ] Unit test: `TestWALAppendAck` — append, ack, confirm file deleted
- [ ] Unit test: `TestWALReplay` — append 50 events without ack, call ReplayPending, verify all produced
- [ ] Unit test: `TestWALCorruptSegment` — inject truncated segment, verify replay skips without panic
- [ ] Unit test: `TestWALPruning` — inject old timestamp segment, verify pruned

### Rate Limiter
- [ ] Implement `token_bucket.go`: `bucket`, `Manager`, `Allow`, `ObserveProduceLatency`
- [ ] Unit test: `TestAllowedWhenNoBackpressure`
- [ ] Unit test: `TestDropWhenBucketEmpty`
- [ ] Unit test: `TestRecovery` — N consecutive fast produces, backpressure deactivated
- [ ] Unit test: `TestPerOriginIsolation` — two origins, exhaust one, verify other unaffected

### Integration
- [ ] Update `consumer.go`: wrap produce call with WAL + rate limiter
- [ ] Update `Start()`: call `ReplayPending` before event loop
- [ ] Add CLI flags: `--wal-dir`, `--wal-retention-seconds`, `--rl-capacity`, `--rl-refill-rate`
- [ ] Integration test: crash mid-produce, restart, verify events not lost

### Metrics + Grafana
- [ ] Register all 5 new metrics
- [ ] Export `kafka_produce_latency_seconds` histogram
- [ ] Add `lensai_wal_segments_pending` alert rule: > 1000 for 2 min → warning
- [ ] Update Grafana dashboard JSON with 5 new panels

### Code Quality
- [ ] `golangci-lint run ./consumer/wal/... ./consumer/ratelimit/...`
- [ ] All exported symbols have doc comments
- [ ] `go test -race ./consumer/...` — no data races

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Disk full from WAL growth | Low | High | Enforce retention; alert on `wal_segments_pending > 1000`; default retention 1h |
| fsync latency on hot path | Medium | Medium | Option to fsync async with bounded channel; document tradeoff |
| CRC collision | Very Low | Low | IEEE CRC32 1-in-4B; acceptable for tracer use case |
| Per-origin bucket map unbounded | Low | Medium | Evict origins not seen in 5 min; add `lensai_ratelimit_buckets_active` gauge |
| WAL replay ordering on clock skew | Low | Low | Filename timestamp is monotonic; NTP jump is only risk; document assumption |

---

## Definition of Done

- [ ] All 15 unit tests pass: `go test ./consumer/wal/... ./consumer/ratelimit/...`
- [ ] Integration test passes: 100 events, crash, restart, all 100 replayed
- [ ] `go test -race ./consumer/...` clean
- [ ] `golangci-lint run` exits 0
- [ ] All 5 metrics visible at `/metrics`
- [ ] PR description includes: test output, WAL segment format spec, token vs leaky bucket rationale
- [ ] `Self-review: N issues found and fixed.` in commit message body

---

## PR Description Template

```
## Day 18 — WAL + Rate Limiting in ebpf-llm-tracer

### What
- WAL: append-only segment files before every kafka.Produce()
- Replay un-acked segments on startup
- Per-origin token bucket rate limiter under Kafka backpressure
- 5 new Prometheus metrics; Grafana durability board updated

### Why
Events were silently lost when Kafka was unavailable. The WAL provides at-least-once delivery.
Rate limiting prevents the consumer from OOM-ing when Kafka is slow — new events are shed
rather than buffered indefinitely in memory.

### Test output
{paste go test -v output here}

### Metrics added
- lensai_wal_segments_pending
- lensai_wal_replay_events_total
- lensai_probe_events_dropped_total
- lensai_kafka_backpressure_active
- lensai_kafka_produce_latency_seconds

Self-review: N issues found and fixed.
```
