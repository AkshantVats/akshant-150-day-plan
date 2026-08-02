# Day 55 — Experience Blog Plan

**Title**: Two Products, One Tenant Bill
**Subtitle**: Wayfair · unified metrics · finance
**Employer context**: `docs/context/pricing-system-architecture.md` (ScheduledReader Total
Cost Engine + Cost Aggregation Layer) + `docs/context/resume-extracted.md` (role scope).
Relevant facts only:
- Wayfair, Bengaluru, Nov 2024 – Mar 2026, Sr. Software Engineer III — led PAS (Price
  Adjustment System) and Pricing, Promotions & Discounts teams simultaneously, owning
  end-to-end delivery across both product areas.
- Architecture doc, Cost Aggregation Layer (section 1): three independent cost sources —
  UCMS/SPCS (supplier net cost), Hydros/EdenReader (ML + logistics cost estimates), PAS
  Cost Adjustments (manual corrections/subsidies) — all feed into **ScheduledReader**, the
  "Total Cost Engine," before a single Total Cost figure ever reaches Delphi (the retail
  price calculator). Delphi never reads from the three sources directly.
- Do NOT invent specific dollar figures or team headcounts beyond what's in these two
  files. Do not claim the ScheduledReader join key or implementation details beyond what
  the architecture doc states (three sources in, one Total Cost out).

**Format**: `feature` (per `docs/BLOG-FORMAT-MIX.md`: "we turned DESIGN into `/ingest`" —
today's code is a new capability shipped end to end, not a tradeoff essay about one already
-decided schema). Last-10 Experience posts lean `design`/`patterns` (Day 51 design, Day 52
design, Day 53 patterns, Day 54 design) with no `feature`-framed post recently, so `feature`
varies the mix while still being the honest shape of today's work.

**Bridge**: One `tenant_id` to rule cost — design the join on Day 1. Today's code in
`agent-benchmark-runner` (`pkg/lensai/writer.go`) dual-writes a benchmark batch's
completion onto LensAI's shared `/ingest` pipeline, the same envelope
`tool-call-analyzer/pkg/lensai` already uses for tool-call cost — so a benchmark run and an
inference call for the same tenant land in the same query face instead of two disconnected
dashboards.

## Angle

At Wayfair, leading PAS and Pricing/Promotions simultaneously meant sitting across two
product areas that both needed one number neither could produce alone: the Total Cost of a
SKU. Three independent systems each know a piece of it — UCMS knows the supplier's net
cost, Hydros knows the ML-estimated logistics cost, PAS knows manual corrections and
subsidies — and none of them is authoritative on its own. Wayfair's answer isn't asking
Delphi (the pricing calculator) to query all three separately; it's ScheduledReader, a
Total Cost Engine that every source feeds into, so Delphi reads one number instead of
reconciling three.

The naive alternative — Delphi calling UCMS, Hydros, and PAS Cost Adjustments directly on
every price calculation — sounds simpler until a fourth cost source shows up, or one of the
three goes down mid-calculation, or two sources disagree on the same SKU at the same
moment. A single aggregation point means Delphi's contract stays "read one Total Cost," not
"know how to reconcile three sources and their failure modes." The join happens once,
upstream, instead of being re-derived by every consumer.

TraceForge is two products for the same reason PAS and Promotions are two teams under one
lead: LensAI tracks inference cost per tenant, and `agent-benchmark-runner` tracks how well
an agent performs per tenant — and a finance view that only sees one of those two numbers
isn't a bill, it's half a bill. Today's code doesn't build a ScheduledReader; it does the
smaller, prerequisite thing ScheduledReader depends on even existing: making sure both cost
sources speak the same envelope, keyed by the same `tenant_id`, so a future aggregation
point has something to join in the first place.

## Section Outline

1. **The two-team seat** — what it actually meant to own PAS and Promotions
   simultaneously: two product areas, two roadmaps, one Wayfair org chart. Ground this in
   the resume line, not invented anecdotes.
2. **Why ScheduledReader exists** — three cost sources (UCMS/SPCS, Hydros, PAS Cost
   Adjustments), one Total Cost Engine, Delphi never touches the sources directly. Diagram
   the aggregation-layer shape from the architecture doc (source count and names only, no
   invented QPS/latency figures beyond what's documented).
3. **The same shape, one layer earlier, in TraceForge** — LensAI (inference cost) and
   agent-benchmark-runner (benchmark outcome) are the two sources; today's code doesn't
   write the aggregator, it makes both sources speak `/ingest`'s envelope so a real
   aggregation point (a future day) has a join key to work from.
4. **What "one bill" actually requires** — a shared tenant identifier and a shared
   envelope are necessary but not sufficient; ScheduledReader is real infrastructure, not
   just a schema convention. Honest gap: today's code is the join-key prerequisite, not the
   aggregation engine itself.

## Diagram

One Mermaid diagram: three labeled boxes (UCMS/SPCS, Hydros, PAS Cost Adj) feeding into
ScheduledReader, ScheduledReader feeding Delphi — max 8 nodes, labels ≤6 words, required
init block from CLAUDE.md §4.5.
