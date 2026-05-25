# Executive One-Pager — [Company Name] / LensAI Platform

**Contact:** [Founder name] · [email] · [phone] · [GitHub]  
**Date:** [Submit date] · **Stage:** Pre-seed / OSS · **Ask:** YC standard ($500k) · **Location:** Bengaluru → SF (batch)

---

## One sentence

Open-source **inference data plane** (LensAI) for per-tenant LLM cost and latency at million-events-per-minute scale—extending into agent trace, routing, drift, and retrain on one telemetry bus.

## Problem

Production LLM teams cannot answer: *Which tenant spent how much on which model yesterday, and was P99 decode or prefill?* Prometheus-style metrics explode on `model_id × tenant_id`. Trace-first tools lack a durable, queryable bus with FinOps-grade `cost_usd`. At **1.5T events/day** (Agoda TSDB), buying observability failed—the same pattern now hits every inference platform.

## Solution

| Layer | Product | Status |
|-------|---------|--------|
| **Wedge (shipped OSS)** | **LensAI** — Rust ingest → Kafka → Go → ClickHouse; Grafana SLOs; Helm/k3d | **Week 1 built** ([repo](https://github.com/AkshantVats/infra-ai-streaming)) |
| Agent ops | TraceForge (OTel → CH) | Days 30–59 · planned |
| Routing | RouteIQ (cost/SLO router) | Days 60–89 · planned |
| Quality | DriftWatch | Days 90–119 · planned |
| Retrain | FineForge | Days 120–149 · planned |

**Closed loop (target):** observe → detect drift → retrain → route → validate agents on shadow traffic.

## Traction (honest)

- **Revenue / customers:** $0 · 0 production tenants  
- **Product:** G-01–G-06 on `main`; G-07 Helm+HPA on PR #5; CI green; documented E2E  
- **Signal:** Staff-level public build (150-day plan, daily blogs), founder operated equivalent systems at Agoda, Wayfair, Walmart, Delivery Hero  

## Market

- **ICP:** ML platform / infra teams with self-hosted inference or large API spend  
- **Model:** MIT open-core → managed cloud (per-event + retention) → enterprise (VPC, SSO, SLA)  
- **Geo:** Global SaaS; engineering based in India for capital efficiency  

## Competition & insight

Langfuse/Helicone (trace UX), Datadog (bundled APM, cardinality cost), Arize (drift, no ingest bus). **Insight:** Winners own the **data plane** (ingest AP, WAL, partition discipline, per-tenant economics)—not another dashboard.

## Team

**[Founder name]** — Staff engineer, 7.5y distributed systems + AI infra (1.5T/day TSDB, 7M IoT sensors, 250k+ SKU pricing, 5k geo-events/s). Building LensAI in public. **[Co-founder: TBD]**

## Use of YC

1. Hosted SaaS MVP + first 10 design partners  
2. GTM co-founder or first solutions hire  
3. SF batch focus for US enterprise intros  

## Links

- Code: https://github.com/AkshantVats/infra-ai-streaming  
- Plan: [akshant-150-day-plan](https://github.com/AkshantVats/akshant-150-day-plan)  
- Demo video: **[TBD]**  
- Profile: **[TBD URL]**

---

*One printed page · ~450 words · no hype claims for unshipped products.*
