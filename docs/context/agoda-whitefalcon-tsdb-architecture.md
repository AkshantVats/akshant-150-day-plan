# Agoda WhiteFalcon TSDB — Architecture & Context

Source of truth for Experience-series blog posts referencing Agoda's WhiteFalcon system.
Read this before writing any Agoda post. Do not invent system names or scale numbers.

---

## Attribution boundary (MANDATORY)

Akshant contributed to WhiteFalcon as a **Senior Engineer for ~5 months**.
He did NOT design the core system. Always distinguish:

- **"Agoda team built"** → RoaringBitmap engine, Kafka pipeline, Rust consumers, Scala query engine, Ceph/S3 tiering, Hadoop cold storage
- **"Akshant contributed"** → cross-tier query engine extension, new cardinality dimension (k8s tags), 2-3 new Grafana query types

Agoda published their own engineering blog posts on WhiteFalcon. Reference them honestly.

---

## Scale

| Metric | Value | Source |
|--------|-------|--------|
| Events per day | 1.5T (resume) / 1.8T (Kafka forwarder) | Resume + cardinality post |
| Tenure | ~5 months, Senior Engineer | Resume |
| Hot tier retention | Last 3–7 days at per-hour granularity | Building TSDB post |
| Compaction cadence | Hourly → 3-hour → daily | Building TSDB post |

---

## System overview

WhiteFalcon is Agoda's in-house time-series database, inspired by Apache Druid. The Agoda team published detailed write-ups on their engineering blog.

**Lineage:** Kafka → Rust ingest → storage tiers → Scala query engine → Grafana

```
Kafka (1.5T events/day)
   │
   ▼
Rust consumers
   │
   ├──► Redis (hot tier, time-windowed buckets, last 3–7 days)
   │
   └──► Compaction jobs
            │
            ▼
         Ceph (storage layer between pods and S3)
            │
            ▼
         S3 / Parquet (cold tier, datetime-partitioned)
            │
            ▼
         Hadoop (long-term audit/archival)
```

---

## Storage layers

### Hot tier — Redis
- Bucketed in time windows
- Window closes → background flush to Ceph/S3 as Parquet
- Per-hour granularity for last 3–7 days (peak query load)
- After retention window, data is accessible only from cold tier

### Cold tier — Ceph → S3 (Parquet)
- Ceph sits as the storage layer between pods and S3
- Local NVMe used by Ceph OSDs for performance
- Parquet files partitioned by datetime
- Compaction merges: hourly → 3-hour → daily files
- Coarser granularity for data older than the hot window

### Long-term — Hadoop
- Audit/archival data
- Not part of the real-time query path

---

## Query engine (Scala)

Grafana → Scala query engine → fetches from Redis (hot) or Parquet/S3 (cold)

**Key design:** Aggregations stored as **histogram bucket counts**, not pre-computed percentiles.
This is what makes cross-tier quantile merge mathematically correct.

### Cross-tier quantile merge (Akshant's contribution)
Before: queries hit one tier only. Time ranges crossing hot/cold boundary required two manual queries.

After: single request spans both tiers with correct merge logic.

**Why it matters — the wrong vs right approach:**
```
WRONG: P95(Redis, last 3h) + P95(S3, hours 3-30) = 30h P95
       ↳ mathematically incorrect, quantiles are not additive

CORRECT:
  1. Fetch histogram bucket counts from Redis (raw distribution, last 3h)
  2. Fetch histogram bucket counts from S3 (raw distribution, hours 3-30)
  3. Add corresponding bucket counts (merge distributions)
  4. Compute P95 once on the merged histogram
```

Storing histograms (not quantiles) is the design decision that makes this possible.

---

## Indexing — RoaringBitmap inverted index (Agoda team's design)

**Structure:** One bitmap per tag value → maps to the set of series IDs carrying that value.

**Query execution:** Set operations
- Filter by `model=X` → fetch bitmap for model=X
- Filter by `cluster=Y` → fetch bitmap for cluster=Y
- Intersect both → series IDs matching both conditions
- Subtract exclusions if needed

**Why RoaringBitmap:** Handles sparse integer distributions efficiently. Series IDs are integers; most tags have sparse coverage (most series don't have a given value). Roaring uses arrays for sparse ranges, bitsets for dense ranges — optimal for this use case.

**Cardinality constraint:** Bitmaps grow with distinct values × series count. High-cardinality tags on high-traffic metrics cause bitmaps to balloon overnight, increasing index memory and scan cost.

```
Label explosion example from production:
  model_id (200) × tenant_id (500) × status (3) = 300,000 series for one metric
  Add pod (50) × zone (4) → 60M combinations possible
```

---

## The cardinality incident (basis for Experience posts)

Prometheus scrape duration crept up while request rate was flat. Root cause: `pod` label added to a fleet metric. Each new pod multiplied existing series. No alert fired until scrape targets started failing. The alert designed to detect stack degradation was the first to go dark.

**Key lesson:** Cardinality does not grow linearly. It grows as the product of every distinct value across every dimension. One bad label multiplies everything before it.

**Schema discipline enforced after the incident:**
- Cross-product analysis required before any new tag
- 10k max label budget per metric (hard cap)
- High-cardinality labels (pod, experiment_id) must justify combinatorial cost

---

## Akshant's three contribution areas

### 1. Cross-tier query engine
- Extended Scala query engine to support time ranges spanning Redis + S3 in a single request
- Correct quantile merge: histogram bucket merge → compute quantiles on merged result
- Added 2-3 new query types accessible via Grafana (wildcard tag matching, combined range queries)

### 2. New cardinality dimension
- Added Kubernetes infrastructure tags (pod and service-level labels) to the indexing layer
- Required cross-product modeling before merge to avoid cardinality explosion
- Learned the RoaringBitmap engine's limits firsthand by proposing the wrong approach initially

### 3. (Additional context from resume)
- Contributed to Kafka pipeline components (exact scope: resume only, do not over-claim)
- Participated in compaction job design discussions

---

## Technology stack

| Component | Technology | Notes |
|-----------|-----------|-------|
| Event ingest | Kafka | 1.5T events/day |
| Consumers | Rust | Read from Kafka, write to Redis |
| Hot tier | Redis | Time-windowed buckets |
| Storage layer | Ceph | Between pods and S3, NVMe backing |
| Cold tier | S3 (Parquet) | Via Ceph |
| Long-term | Hadoop | Audit/archival |
| Query engine | Scala | Cross-tier, histogram-based quantiles |
| Index | RoaringBitmap | Per-tag-value inverted index |
| Visualization | Grafana | Connected to Scala query API |

---

## What NOT to write

- Do not claim Akshant designed the RoaringBitmap engine — that was the Agoda team
- Do not claim Kafka pipeline ownership — contributing engineer, not designer
- Do not use scale numbers outside the ranges above (1.5T–1.8T/day)
- Do not name Agoda team members
- Do not reference Agoda business logic (hotel pricing, search ranking) — this was pure infra
- Do not invent a "WhiteFalcon v2" or future roadmap — only document what was running

---

## Blog posts already published referencing WhiteFalcon

| Post | Key angle | File |
|------|-----------|------|
| Building a TSDB at Agoda | Full system tour, 3 contribution areas | `building-tsdb-at-agoda.html` |
| When Percentiles Lie — Cross-Tier Queries | Quantile merge problem, histogram design | `when-percentiles-lie-cross-tier-queries.html` |
| Cardinality Is the Silent Killer | RoaringBitmap, label explosion, 10k budget | `cardinality-is-the-silent-killer-roaringbitmap-lessons.html` |

---

## Public references (link when appropriate)

- Agoda engineering blog has published WhiteFalcon posts — search "Agoda WhiteFalcon engineering blog"
- Apache Druid documentation (architecture inspiration)
- RoaringBitmap paper: Lemire et al. (2016)
