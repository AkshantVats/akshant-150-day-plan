# Plan B — AI Learning blog (Day 4 of N · calendar day 5)

**Status:** Revised 2026-05-17. Plan mode only — no HTML until `implement AI blog`.

---

## Metadata

| Field | Value |
|-------|--------|
| **H1** | Day 4 of Learning LLM Inference — Tensor Parallelism Meets Kafka Partitions |
| **Subtitle** | Model serving scale-out as a sharding problem |
| **Series index** | **Day 4 of N** (`ai.day_index: 4`) |
| **Hook** | Triton's model repository is just a partition assignment table with GPUs instead of brokers. |
| **Word target** | **1,000–1,400** |
| **Mermaid** | **2 diagrams** (optionally 3rd sequence for CH flush — match Day 2/3 depth if needed) |

## Paths & OG

| Item | Value |
|------|--------|
| **target_html** | `Profile/blog/series/ai-learning/day-4-tensor-parallelism-kafka-partitions.html` |
| **Canonical** | `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-4-tensor-parallelism-kafka-partitions.html` |
| **og:image** | `https://akshantvats.github.io/Profile/blog/assets/og/day-4-tensor-parallelism-kafka-partitions.png` |
| **Cover badge** | `AI LEARNING SERIES` only |

## Experience cross-links (updated paths)

Replace any stale `agoda/` URLs:

| Sibling | Canonical URL |
|---------|----------------|
| **Experience 4 (DH geo)** | `https://akshantvats.github.io/Profile/blog/series/experience/five-thousand-geo-events-per-second.html` |
| Experience 3 (IoT) | `.../experience/seven-million-iot-sensors-failure-modes.html` |
| Day 3 (cost) | `.../ai-learning/day-3-token-budgets-cost-structure.html` |
| Day 2 (batching) | `.../ai-learning/day-2-continuous-batching-vllm.html` |

**§8 experience-link:** One developed paragraph — DH SQS/order partitioning and `tenant_id:model_id` Kafka keys are the same assignment problem; link to Experience post **after** it is live (no `TBD` in merged HTML).

## Outline (unchanged structure, path/OG fixes)

1. Cold open + Daily Thread (verbatim from `plan.json`)
2. `tp-pp` — Tensor vs pipeline parallelism
3. `triton-hook` — Model repository as routing table
4. `kafka` — Partitions and ordering
5. `ds-analogy` — **Required** extended analogy table
6. `batching-serving` — Cross-partition vs in-GPU batching (link Day 2)
7. `clickhouse-rollups` — G-03: 1000 events / 500ms, breaker, Redis, DLQ×3
8. `observability` — OBSERVABILITY.md metrics; thread tie-in
9. `experience-link` — DH geo stream (canonical experience URL)
10. `takeaway` + Day 6 Grafana tease

## Mermaid (2 core + optional 3rd)

1. **TP scale-out** — request router → GPU groups → all-reduce  
2. **Kafka → ClickHouse** — consumer batch, breaker → Redis, DLQ  
3. *(Optional)* **sequenceDiagram** — flush timer vs batch size (mirrors Day 3 ingest validation)

## Schema refs (freeze post-code)

- Topic `ai_inference_events`; `InferenceEvent` fields; CH `ORDER BY (tenant_id, model_id, timestamp)`
- Example rollup: `sum(cost_usd)` by tenant/hour
- Link Day 3 `cost_usd` validation

## OG note

Same gates as all posts: generate 1200×630 PNG, absolute `og:image`/`twitter:image`, on-page `post-cover`, LinkedIn Post Inspector after deploy. Parent agent auditing all legacy posts.
