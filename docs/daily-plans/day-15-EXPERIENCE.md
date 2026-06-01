# Experience Day 15 — Order SQS → Route Consumers

**Status:** DONE — blog published to main branch.

**URL:** https://akshantvats.github.io/Profile/blog/series/experience/order-sqs-route-consumers-delivery-hero.html

**File:** `blog/series/experience/order-sqs-route-consumers-delivery-hero.html`

---

## Summary

**Title:** Order SQS → Route Consumers: Decoupling Map-Match from Status

**Subtitle:** Delivery Hero · How separating OSRM route calculation from order status updates via distinct SQS consumer groups eliminated head-of-line blocking during dinner rush.

**Context:** Global Logistics Platform, Delivery Hero Berlin, 2022–2023. 1M+ daily orders, 5k route updates/sec on AWS EKS.

---

## Key themes covered

1. **Head-of-line blocking pattern** — OSRM's CPU-heavy graph traversal (300–800ms) staving fast status consumers (50ms) sharing the same SQS consumer group
2. **Fix: consumer group isolation** — split into Status Consumer (fast path, vis timeout 30s) and Route Consumer (OSRM path, vis timeout 120s)
3. **Autoscaling decoupled** — Status Consumers scale on message age; Route Consumers scale on lag count
4. **AI inference analogy** — streaming requests vs batch jobs need the same queue-isolation treatment
5. **Connection to LensAI** — real-time telemetry events cannot share queue with batch cost aggregation jobs

---

## Employer context used

- `docs/delivery-hero-rider-tracking-system.md` — canonical Order SQS topology
- `docs/context/resume-extracted.md` — Delivery Hero logistics scale figures
- Related experience posts: five-thousand-geo-events-per-second.html, ten-thousand-concurrent-requests-eks-patterns-delivery-hero.html

---

## Bridge note (per plan.json)

> Async notifications use SQS+Kinesis elsewhere — this post is Order SQS into Route Consumers, not a Kinesis-only map-match story.

This was correctly respected: the post focuses on `active_conns` → Route Consumers consumer group split, not on Kinesis.
