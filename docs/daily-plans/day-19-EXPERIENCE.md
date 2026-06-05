# Day 19 Experience Blog

**Title:** Kafka + Redis Tiering — Query Latency by Temperature
**Subtitle:** Agoda · decoupling hot reads from cold storage
**File:** `Profile/blog/series/experience/day-19-kafka-redis-tiering-query-latency.html`
**Live:** https://akshantvats.github.io/Profile/blog/series/experience/day-19-kafka-redis-tiering-query-latency.html
**Format:** deep-dive
**Employer:** Agoda / WhiteFalcon

## Summary

Why SLOs that average across storage temperatures lie. WhiteFalcon's Kafka → Rust consumer
→ Redis hot tier → Ceph/S3 cold tier pipeline. Separate hot/cross/cold p99 metrics that
revealed 800ms cold-tier latency hidden by 10ms Redis reads. Kafka consumer lag as
freshness SLI. Force eviction as data loss path.

## Attribution
- Tier storage design (Redis, Ceph, Kafka pipeline): Agoda team
- Cross-tier query engine + tier labeling: Akshant contribution
