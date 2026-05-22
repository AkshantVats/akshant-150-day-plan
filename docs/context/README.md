# Context artifacts — 150-day plan & Experience blogs

Canonical files for **this chat window** and future agent runs. Read before inventing employer architecture or scale claims.

## Rule (mandatory)

**Before generating or drafting any Experience-series blog:**

1. Read this index.
2. Read [`../delivery-hero-rider-tracking-system.md`](../delivery-hero-rider-tracking-system.md) for Delivery Hero posts.
3. For Wayfair / pricing / supplier / PAS / promotions posts, read [`pricing-system-architecture.md`](pricing-system-architecture.md).
4. For employer dates, scope, and metrics labeling, read [`resume-extracted.md`](resume-extracted.md).
5. If the post blends personal narrative (applications, goals), optionally read [`cover-letter-extracted.md`](cover-letter-extracted.md).

**If context is ambiguous** → ask the user OR cite only what appears in these files. Do not substitute Kinesis-only pipelines, generic “stealth startup” stories, or vendor-scale numbers without a source.

---

## Artifacts

| File | When to use |
|------|-------------|
| [`pricing-system-architecture.md`](pricing-system-architecture.md) | Wayfair Global Pricing & Promotion Engine: Delphi, Aletheia, Barter, PAS, UCMS, gst-acc-promotions, Pilgrim, GKE, Bigtable, CloudSQL, Kafka `pricing_refresh`, supplier token buckets, 250k+ SKU propagation. **Company: Wayfair (2024–2026).** |
| [`resume.pdf`](resume.pdf) / [`resume-extracted.md`](resume-extracted.md) | Employers, tenure, headline metrics (1.5T/day Agoda, 5k geo/sec DH, 7M sensors Walmart, 250k SKU Wayfair). Label team vs personal scope in prose. |
| [`cover-letter.pdf`](cover-letter.pdf) / [`cover-letter-extracted.md`](cover-letter-extracted.md) | Narrative tone, Staff/AI-infra positioning — not system topology. |
| [`../assets/delivery-hero-rider-tracking-architecture.png`](../assets/delivery-hero-rider-tracking-architecture.png) | Whiteboard topology (2026-05-22). Pair with rider-tracking doc. |
| [`../delivery-hero-rider-tracking-system.md`](../delivery-hero-rider-tracking-system.md) | **Source of truth** for DH: Order Service, Order SQS, Route Service (EKS), Route Consumers, OSRM, Route `{ }` object, Revisit Order System, GBQ. |

---

## Employer → primary context file

| Employer | Primary doc | Secondary |
|----------|-------------|-----------|
| Delivery Hero | `delivery-hero-rider-tracking-system.md` | Resume (SQS+Kinesis decoupling for notifications, not map hot path) |
| Wayfair | `pricing-system-architecture.md` | Resume (team lead, 250k SKU, sub-second propagation) |
| Agoda | Resume + plan days 0–6 shipped posts | WhiteFalcon / cardinality / cross-tier quantiles |
| Walmart Labs | Resume | IoT / Azure Hub / stream analytics |
| BrowserStack | Resume | Device instrumentation, CI flakiness (sparse in plan) |
| LensAI / infra-ai-streaming | `data/plan.json` code threads | Agoda cardinality bridge in DESIGN.md |

---

## Maintenance

- Replace `resume.pdf` when resume changes; re-run extraction into `resume-extracted.md`.
- Pricing doc is a point-in-time export (2026-03-01 Datadog/GCP); do not invent new service names.
- Rider PNG: overwrite `docs/assets/delivery-hero-rider-tracking-architecture.png` when user supplies a newer whiteboard.
