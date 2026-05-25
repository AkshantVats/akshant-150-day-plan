# Y Combinator Application — Master Draft

> **Purpose:** Copy-paste source for [ycombinator.com/apply](https://www.ycombinator.com/apply). Tone: staff-engineer credible, honest about shipped vs planned.  
> **Last aligned to:** Summer 2026 batch fields (company, founders, idea, progress, market, competition, video). Update dates before submit.

---

## Quick reference (fill before submit)

| Field | Draft value | Status |
|-------|-------------|--------|
| **Company name** | [Legal entity name — e.g. LensAI Inc.] | **TBD** |
| **Company URL** | https://github.com/AkshantVats/infra-ai-streaming | Live (OSS) |
| **Product name** | LensAI (wedge); platform codename: 150-day stack | — |
| **One-liner (≤50 chars)** | `AI ops data plane: observe→route→retrain` | 44 chars |
| **Describe in one sentence** | See § Company one-sentence | — |
| **Batch** | [Summer 2026 / Fall 2026 / Early Decision] | **TBD** |
| **Incorporated** | [Yes/No — country, date] | **TBD** |
| **Investment taken** | [None / amount / SAFE] | **TBD** |
| **Revenue** | $0 | Honest |
| **Users / customers** | 0 paying; OSS repo public | Honest |

---

## Company

### Company name

**[Legal company name]** — recommend incorporating as a Delaware C-Corp or Indian Pvt Ltd before interview if accepted. Product brand for wedge: **LensAI** (`infra-ai-streaming` repo).

### What does your company do? (one sentence — plain English)

We build an open-source data plane for production LLM inference—ingest, stream, and query per-tenant cost and latency at the cardinality where Prometheus and trace-first tools break—then extend it into agent tracing, routing, drift detection, and fine-tuning in one closed loop.

### 50-character description (YC short field)

`AI ops data plane: observe→route→retrain`

### What is your company going to make?

**Today (shipped in open source):** **LensAI** — a Kafka-backed, ClickHouse-native inference observability stack:

- Rust HTTP ingestion (`POST /ingest`) with WAL-before-Kafka, per-tenant Redis rate limits, channel backpressure
- Go consumer: batch writer (1000 events / 500ms), circuit breaker, Redis overflow, DLQ
- Local + k3d deploy: Redpanda, ClickHouse, Prometheus, Grafana (product SLO + ops dashboards)
- Event schema built for inference: `tenant_id`, `model_id`, `latency_ms`, prompt/completion tokens, `cost_usd`

Repo: [github.com/AkshantVats/infra-ai-streaming](https://github.com/AkshantVats/infra-ai-streaming). Honest status doc: `docs/PROJECT-STATUS.md`. Milestones G-01–G-06 delivered on `main`; G-07 (Helm + HPA on Kafka lag) on feature branch / PR #5.

**Next 150 days (planned, not shipped):** Five-product platform on one telemetry bus:

| Product | Days | Status | Role |
|---------|------|--------|------|
| **LensAI** | 0–29 | **In build** (week 1 done) | Inference observability — **wedge** |
| **TraceForge** | 30–59 | Planned | Agent execution traces (OTel → ClickHouse) |
| **RouteIQ** | 60–89 | Planned | Multi-model router (cost/latency/SLO-aware) |
| **DriftWatch** | 90–119 | Planned | Drift + quality on production traffic |
| **FineForge** | 120–149 | Planned | Fine-tuning pipeline triggered by drift |

**Day 149 closed loop:** LensAI telemetry → DriftWatch evals → FineForge retrain → RouteIQ registers weights → TraceForge validates agents on shadow traffic.

We are **not** claiming TraceForge, RouteIQ, DriftWatch, or FineForge exist as products yet. The application thesis is: (1) the data-plane wedge is real code with staff-level design docs; (2) the founder has already operated at this scale (1.5T events/day TSDB); (3) the roadmap is sequenced, not a slide-deck fantasy.

### Where do you live now, and where would the company be based after YC?

- **Founder location:** Bengaluru, India — **[confirm]**
- **Post-YC:** San Francisco for batch duration (YC in-person); company can remain India-incorporated with US subsidiary **TBD** with counsel

### How far along are you?

**Honest snapshot (plan day ~8 of 150):**

- **Code:** Open-source MIT repo; CI on Rust ingestion tests; local E2E documented (`scripts/smoke-e2e.sh`, `docs/E2E-PROOF-K3D.md`)
- **Not yet:** Hosted SaaS, paying customers, sales motion, anomaly detection (backlog), full `tenant_id:model_id` Kafka partition key (design doc only)
- **Traction:** 0 revenue, 0 production tenants. Progress signal = **execution velocity + design quality**, not ARR:
  - Days 0–6: README → DESIGN.md → ingestion → compose stack → ClickHouse writer → dual Grafana dashboards
  - Public build log: 150-day plan site + daily experience/AI learning blogs (credibility for hiring/partners, not user count)

**Demo:** Local/docker/k3d — `curl /ingest` → Kafka → ClickHouse → Grafana panels (throughput, P99 by model, cost/hour, consumer lag). **[Record 2-min screen capture for application URL field]**

### How long have the founders known each other, and how did you meet?

**[TBD — solo founder: state "solo, recruiting co-founder" OR fill co-founder story]**

Suggested solo answer: *Solo technical founder. Actively recruiting a GTM/product co-founder with B2B infra SaaS experience; not applying with a stranger met at a hackathon.*

### Are people using your product?

**No** — not a hosted product yet. The repo is public for evaluation and contribution. **[If any design partners / friends testing locally, name count here]**

### Do you have revenue?

**No.** $0 MRR. Plan: open-core → managed cloud (per-tenant ingest + retention) → enterprise (SSO, VPC, SLA).

### If you applied before with the same idea, what changed?

**[N/A or describe pivot from prior application]**

---

## Idea

### Why did you pick this idea to work on?

At Agoda I worked on WhiteFalcon, a TSDB ingesting **~1.5 trillion events/day**. Prometheus-style cardinality limits and "buy observability" failed at that scale—we built custom ingestion, partitioning, and quantile merge paths.

Every team shipping LLM inference now hits the same shape: `model_id × tenant_id × deployment` explodes series count; finance needs **per-tenant `cost_usd`**; SRE needs **prefill vs decode** latency, not one blended number. Trace-first LLM tools optimize prompt UX, not a replayable bus with sub-100ms ingest SLOs.

I'm building what I already operated—an **AP-oriented inference data plane**—as open source first, then the agent/route/drift/retrain loop on top.

### Why now?

1. **LLM inference is production infrastructure**, not experiments—multi-tenant cost attribution is a board-level question.
2. **Agent systems** multiply failure modes (tool calls, loops); trace-only APM misses cost-per-step economics.
3. **Open stack maturity:** Redpanda, ClickHouse, Rust/Go ops patterns make a credible OSS data plane buildable by a small team in weeks, not years.
4. **Regulatory + efficiency pressure** (EU AI Act, FinOps) pushes continuous eval + retrain—our Day 149 loop targets that workflow.

### Who desperately needs this?

- **Platform / infra teams** running vLLM/Triton (or API gateways) with 10+ models and real multi-tenancy
- **FinOps + ML platform** leaders who cannot answer "which customer spent what on which model yesterday?"
- **Agent product teams** who need cost-per-tool-call before TraceForge ships (LensAI schema already carries tokens + cost)

Initial ICP: Series B–D companies with **self-hosted inference** or high API spend—not hobbyists.

### How do you know people need this?

**Primary evidence (founder-market fit, not surveys yet):**

- Operated the pain at Agoda (1.5T/day), Delivery Hero (5k geo-events/s), Walmart (7M IoT sensors), Wayfair (250k+ SKU pricing pipelines)—all high-cardinality streaming problems
- **[TBD: 10–20 customer discovery calls]** — document quotes before submit
- **Competitive gap:** Langfuse/Helicone excel at traces and prompts; Datadog LLM Observability is bundled APM pricing; none open-source a **Kafka + ClickHouse + per-tenant cost** inference bus you can self-host on day one

**Secondary:** GitHub stars/forks, Discord/issues engagement after launch post — **[fill metrics]**

### What do you understand about your business that competitors don't?

**Insight:** LLM observability at scale is a **data-plane problem**, not a dashboard problem. Winners need:

1. **Ingest AP semantics** — accept fast, WAL + Kafka, never block the GPU path (429 + Retry-After, not silent drop)
2. **Cardinality discipline** — `model_id` and `tenant_id` as first-class partition keys; RoaringBitmap-style thinking from TSDB days
3. **Closed loop** — observe → detect drift → retrain → route traffic → validate agents (competitors sell point tools; we sequence one bus)

Selling trace UI without owning the event bus caps margin and locks customers into vendor retention pricing. We open-source the bus, monetize hosted ops + enterprise controls.

### How do you make money?

| Phase | Model | Pricing sketch |
|-------|--------|----------------|
| **0–12 mo** | Open-core (MIT) + **managed cloud** | Per 1M events ingested + retention tier; free tier for single tenant dev |
| **12–24 mo** | **Enterprise** | VPC deploy, SSO, audit logs, HA support, custom SLO reviews |
| **24+ mo** | **Platform modules** | TraceForge / RouteIQ / DriftWatch as add-ons on same tenant graph |

India angle: global SaaS pricing in USD; India-based eng cost structure improves gross margin vs purely US-founded competitors.

**Current revenue:** $0. **Target first dollar:** **[TBD — pilot LOI or design partner]**

### How will you get users?

1. **Open source** — `infra-ai-streaming` as the flagship; technical blogs (Agoda cardinality, DH routing, vLLM batching parallels)
2. **Integrations** — vLLM / Triton sidecar ingest; OTel exporter (planned)
3. **Community** — CNCF-adjacent, Kafka/ClickHouse meetups, `[TBD: conference talks]`
4. **B2B outbound** — ML platform leads at companies running self-hosted inference **[TBD pipeline]**

---

## Founders

> Replace placeholders. Primary draft uses public profile data for Akshant; add co-founder blocks if applicable.

### Founder 1

| Field | Value |
|-------|--------|
| **Name** | Akshant Sharma |
| **Email** | Akshant3@gmail.com |
| **Phone** | +91 9592948889 |
| **Title** | Founder / CEO (technical) |
| **LinkedIn** | [linkedin.com/in/akshant-sharma](https://www.linkedin.com/in/akshant-sharma) — **[verify URL]** |
| **GitHub** | [github.com/AkshantVats](https://github.com/AkshantVats) |
| **Age** | **[TBD]** |
| **Full-time on startup?** | **[Yes/No — e.g. left job DATE or nights/weekends]** |
| **Equity %** | **[TBD]%** |

**Please tell us about something impressive each founder has built or achieved:**

Akshant contributed to Agoda's WhiteFalcon TSDB (**~1.5T events/day**, Rust + Kafka + Ceph). Led two engineering teams at Wayfair shipping a real-time global pricing engine across **250k+ SKUs per supplier**. Built IoT-scale pipelines at Walmart (**7M sensors**). At Delivery Hero, worked on high-throughput geo/routing streams (**5k events/s**). Now shipping LensAI in public with daily design docs + working ingest pipeline (days 0–6 of 150-day plan).

**[Add 2–3 bullets with metrics — avoid generic "hard worker" language per PG's howtoapply]**

### Founder 2

**[Co-founder name]** — **[Role]** — **[Impressive achievement with numbers]** — Equity: **[TBD]%**

### Founder relationship

**[How long known, prior project together, or "solo founder"]**

### Are you technical?

**Yes** — primary founder writes Rust/Go, designs data planes, operates Kubernetes. **[Co-founder technical? TBD]**

### Who writes code, or does other technical work on your company?

Akshant — 100% of current codebase (Rust ingestion, Go consumer, Helm, compose). **[Update if co-founder joins]**

### Equity breakdown

| Holder | % |
|--------|---|
| Founder 1 (Akshant) | **[TBD]** |
| Founder 2 | **[TBD]** |
| Option pool | **[TBD]** |
| Other investors | **[TBD / none]** |

---

## Progress & metrics

### What is your weekly growth rate?

**N/A** (no users). **Eng build velocity:** ~1 major milestone/day in week 1 (G-01..G-05). **[Track GitHub stars weekly for submit]**

### Key metrics (honest)

| Metric | Value |
|--------|-------|
| Paying customers | 0 |
| MRR | $0 |
| Events ingested (prod) | 0 |
| GitHub stars | **[TBD at submit]** |
| CI | Green on `main` (Rust tests) |
| Design partners | **[TBD]** |

### What tools / tech stack?

- **Ingestion:** Rust (Axum), rdkafka, WAL segments, Redis token buckets
- **Stream processing:** Go (franz-go), batch ClickHouse writer, circuit breaker, DLQ
- **Storage / analytics:** ClickHouse MergeTree; Redis overflow
- **Messaging:** Kafka / Redpanda
- **Ops:** Docker Compose, Helm, k3d, Prometheus, Grafana, HPA on `kafka_consumer_lag_sum`
- **Future:** OTel collector (TraceForge), Python eval jobs (DriftWatch), GPU training jobs (FineForge)

### Moat (defensibility)

1. **Operational know-how encoded in DESIGN.md** — partition strategy, backpressure, CHAOS runbooks (hard to copy without living at 1T+/day scale)
2. **Schema + bus ownership** — once tenants store cost/latency history in our ClickHouse model, switching cost is high
3. **Platform loop** — single tenant graph powers observe → route → drift → retrain (module upsell)
4. **Open-source community** — contributors on ingestion/consumer before proprietary UI

Not claiming patents. **Honest risk:** Datadog/Langfuse can narrow gap; we compete on self-host, cost transparency, and data-plane depth.

---

## Market & competition

### Market size

- **TAM:** ~$30B+ observability + ML ops software (Datadog, Dynatrace, ML experiment tracking, LLM ops tools — rough aggregate)
- **SAM:** Teams running self-hosted LLM inference or $50k+/mo API spend needing FinOps-grade telemetry — **[estimate $2–5B]**
- **SOM (3 yr):** 200 enterprise tenants × $50k ACV = **$10M ARR** target narrative

### Competitors

| Competitor | Strength | Our difference |
|------------|----------|----------------|
| **Langfuse / Helicone** | Trace UX, prompt management | We own Kafka+CH bus; sub-100ms ingest SLO; self-host |
| **Datadog LLM Observability** | Distribution, APM bundle | Cardinality cost; not open; no retrain loop |
| **Arize / WhyLabs** | ML drift monitoring | DriftWatch not built yet; we start inference bus first |
| **Prometheus + Grafana** | Free, familiar | Breaks on LLM label cardinality |
| **Cloud provider native** | Integrated billing | Lock-in; weak cross-model agent economics |

### What's your unfair advantage?

- **7.5 years** building exactly this class of system (TSDB, IoT, geo streams, pricing engines)
- **Staff-level public build** — DESIGN.md before code; daily verifiable commits
- **India-based** — can run lean engineering vs SF-only burn **[if relevant to narrative]**

---

## Legal & other YC fields

| Question | Answer |
|----------|--------|
| **Incorporation** | **[TBD — recommend before accept]** |
| **Prior funding** | **[TBD]** |
| **Bank balance / runway** | **[TBD — months of runway]** |
| **Visa / can you move to SF for batch?** | **[TBD — B1/B2 / O-1 / YC visa support]** |
| **AI safety disclosure (if shown)** | Fine-tune on customer telemetry only with contract; no user PII in shared models; VPC deploy option |
| **Climate tag (optional)** | Dynamic routing + quantization path reduces wasted GPU spend **[quantify when RouteIQ exists]** |
| **Referral / alumni code** | **[TBD]** |
| **Other ideas considered** | WhatsApp doc vault (separate venture — do not mix unless same applicant company) |

### Please tell us about a time you hacked a non-computer system

**[TBD — personal story. Example prompts: visa process, supplier negotiation, internal process change at Wayfair/Agoda with measurable outcome]**

### Please tell us something surprising or impressive about one of the founders

**[TBD — pick one concrete story: e.g. quantile merge across hot/cold tiers, 7M sensor rollout, pricing engine 10× load]**

---

## 1-minute video script outline

> YC wants unpolished, founder-facing camera, ~60 seconds. No marketing music.

| Sec | Time | Script |
|-----|------|--------|
| Hook | 0–10s | "I'm Akshant. I built telemetry at 1.5 trillion events a day at Agoda. LLM teams now hit the same wall—so I'm open-sourcing the inference data plane." |
| Demo | 10–35s | Screen: `curl /ingest` → show Grafana panel (P99 by model, cost/hour). "This is LensAI week one—Rust ingest, Kafka, ClickHouse. Shipped, not slideware." |
| Vision | 35–50s | "Next: agent traces, smart routing, drift detection, retrain—one loop on one bus. TraceForge and RouteIQ are on the roadmap, not live yet." |
| Ask | 50–60s | "We're pre-revenue, post-design-doc. YC would accelerate hosted SaaS and our first ten design partners." |

**Upload:** Unlisted YouTube/Vimeo — **[URL TBD]**

---

## Anything else we should know?

- Building in public: [150-day plan](https://github.com/AkshantVats/akshant-150-day-plan) with daily code + blogs — accountability, not vanity metrics.
- **Honesty policy:** `PROJECT-STATUS.md` lists gaps (no anomaly detection in CI, partition key TODO). We would rather lose on honesty than win on hype.
- **Solo risk acknowledged:** Recruiting co-founder with B2B SaaS GTM; technical risk is low for wedge.

---

## Application copy-paste blocks (concise)

**What is your company going to make? (short)**

Open-source LensAI: Kafka + ClickHouse inference telemetry with per-tenant cost and latency at high cardinality. Roadmap: TraceForge (agents), RouteIQ (router), DriftWatch (drift), FineForge (retrain)—only LensAI is shipped today.

**How far along are you? (short)**

Week 1 of 150-day plan complete: Rust/Go pipeline, compose + Grafana, CI green. No paying users. G-07 Helm on PR #5. TraceForge+ not started.

**Why will you win? (short)**

Founder built 1.5T/day TSDB; competitors sell dashboards—we ship the bus first, then the closed loop.

---

*Sources: `data/plan.json`, `platform.html`, `infra-ai-streaming/docs/PROJECT-STATUS.md`, Profile `index.html`, [YC howtoapply](https://www.ycombinator.com/howtoapply).*
