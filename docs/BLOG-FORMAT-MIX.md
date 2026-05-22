# Blog format mix — editorial policy (150-day plan)

**Applies to:** Experience (`blog/series/experience/`) and AI Learning (`blog/series/ai-learning/`) posts drafted from `data/plan.json`.

**Does not change:** Public titles in `plan.json` / `experience.title` / `ai.title` — those stay as topic anchors. This doc governs **how** each post is written (structure, hook, framing), not the headline on the calendar.

---

## Why not incident-only

A 150-day public series that reads like “another outage every day” trains the wrong expectation:

- **Credibility:** Not every calendar day had a production incident worth a postmortem. Forcing that frame invites invented drama or repetitive “we were paging at 2am” templates.
- **Signal:** Staff-level writing includes **how you shipped**, **why you chose B over A**, and **one mechanism explained deeply** — not only scars.
- **Interview fit:** Hiring panels want design judgment and delivery narrative, not 150 war stories.
- **Reader fatigue:** Incident-first every day blurs together; mixed formats make the archive browsable.

**Incident / postmortem is one strong mode — not the default.** Use it when the plan day’s topic is genuinely about failure, recovery, or operational surprise.

---

## Format types (when to use each)

| Format | ID | Use when… | Experience voice | AI Learning voice |
|--------|-----|-----------|------------------|-------------------|
| **Incident / postmortem** | `incident` | Outage, near-miss, chaos test with customer impact, “what broke and how we fixed it” | Timeline → blast radius → root cause → fix → guardrails. Honest scope (team vs mine). | Rare; e.g. when tying a production lesson to today’s inference concept (OOM storm, cache stampede). |
| **Feature / how we shipped** | `feature` | New capability, launch, repo milestone, “we turned DESIGN into `/ingest`” | Problem → constraints → build phases → verification → what we’d do next. | “How this lands in infra” — wiring a feature (routing, cache headers) to observable outcomes. |
| **Design decision / tradeoff essay** | `design` | DESIGN.md day, CAP/partition choice, rate-limit policy, schema that prevents cardinality | Options table → decision → rejected alternatives → consequences. | Algorithm vs systems tradeoffs; prefill/decode, sampling policy, quantization choice. |
| **Deep dive (one mechanism)** | `deep-dive` | One subsystem named in title (quantile merge, RoaringBitmap, OSRM stream shape, KV cache) | Teach the mechanism with one employer anchor; diagrams required. | Core curriculum posts — one concept developed with DS analogy. |
| **Rollout / migration lesson** | `rollout` | Cutover, dual-write, backfill, “at-least-once is a feature”, propagation to 250k SKUs | Before/after topology, rollback plan, metrics that proved success. | Pipeline stages (RAG, multi-model routing) as rollout problems. |
| **Lessons / patterns essay** | `patterns` | EKS/HPA patterns, OSS reading, README as hiring artifact, leading teams | Synthesized patterns from multiple incidents — **not** a single fake outage. | Framework comparison, “queue model before benchmark score”. |
| **Meta / positioning** | `meta` | Day 0 launch, “why I’m building in public”, portfolio site | Short; tie to arc, not faux-incident. | Day 0 roadmap only (sparingly). |

**Soft quota (150 days, both series combined):** aim for **≤ ~40%** `incident` across Experience + AI Learning. Track loosely in draft phase; rebalance upcoming days via [`data/blog-format-hints.json`](../data/blog-format-hints.json) when adding hints.

---

## Picking format from plan metadata

Use **in order**: (1) explicit hint in sidecar, (2) rules below, (3) ask user if ambiguous.

### From `experience.title` / subtitle / employer

| Signal in title or subtitle | Suggested format |
|-----------------------------|------------------|
| “Killed”, “chaos”, “outage”, “wall we hit”, “failure modes”, “silent killer” | `incident` or `deep-dive` (if mechanism is the hero, prefer `deep-dive`) |
| “Sub-second”, “propagation”, “event-driven”, “shipped”, “README”, “Week N” | `feature` or `rollout` |
| “Design doc”, “CAP”, “tradeoff”, “token bucket”, “schema”, “cardinality” (as design) | `design` |
| “P95/P99”, “RoaringBitmap”, “OSRM”, “stream shape”, “quantile”, “KV cache” (mechanism in title) | `deep-dive` |
| “EKS”, “HPA”, “patterns”, “concurrent requests”, “PDB” | `patterns` or `rollout` (if cutover story) — **avoid third generic peak-incident post**; see PLAN-REALIGNMENT days 8/20/82 |
| “Decoupling”, “migration”, “OTA”, “at-least-once”, “SQS →” | `rollout` |
| “Why I'm building”, “150 days”, portfolio / positioning | `meta` or `feature` |

### From `code` ticket prefix / keywords

| Code signal | Suggested format |
|-------------|------------------|
| `Ticket G-*` (greenfield build in infra-ai-streaming) | `feature` (first time) → `design` (DESIGN.md) → `deep-dive` (observability mechanism) |
| `DESIGN.md`, `CHAOS.md`, architecture-only | `design` |
| `chaos/`, `run_chaos`, kill broker mid-ingest | `incident` (evidence-based; attach metrics/screenshots) |
| `Helm`, `HPA`, `PDB`, `deploy/` | `rollout` or `patterns` — not default `incident` |
| `OSS-*`, reading upstream source | `patterns` or `deep-dive` |
| `Portfolio site`, `README polish` | `feature` |
| `eBPF`, new repo + DESIGN.md | `design` (day 14) → `feature` (day 15+ code) |
| Peak / lunch rush / OSRM saturation | `rollout` or `patterns` unless a **specific** outage is documented |

### AI Learning (`ai.title` / `day_index`)

| Signal | Suggested format |
|--------|------------------|
| “Day N of Learning LLM Inference — &lt;Mechanism&gt;” | Usually `deep-dive` |
| Roadmap / scope (Day 0) | `meta` |
| Comparison across frameworks | `patterns` |
| Cost / routing / cache economics | `design` or `deep-dive` |

---

## Voice (unchanged core, new default frame)

- **Staff engineer:** precise, mechanism-first, earned numbers, humble scope labels.
- **Problem-first opening** stays — but the “problem” can be “we needed sub-second SKU visibility”, not only “the dashboard was red”.
- **Do not** open every post with pager duty unless the format is `incident`.
- **Do not** put Daily Thread, ticket IDs, or `plans/drafts` paths in published HTML (see [`CHECKLIST.md`](../CHECKLIST.md)).
- **Context before fiction:** Experience posts still require [`docs/context/README.md`](context/README.md) for employer topology.

---

## Gold reference posts (Profile repo)

Canonical base: `https://akshantvats.github.io/Profile/blog/series/`

Paths below are relative to the **Profile** repository root.

### Experience

| Format | Example slug | Path |
|--------|--------------|------|
| `deep-dive` | When percentiles lie | `blog/series/experience/when-percentiles-lie-cross-tier-queries.html` |
| `deep-dive` | Geo stream shape | `blog/series/experience/five-thousand-geo-events-per-second.html` |
| `deep-dive` / `incident` | Cardinality / RoaringBitmap | `blog/series/experience/cardinality-is-the-silent-killer-roaringbitmap-lessons.html` |
| `incident` / failure modes | IoT at scale | `blog/series/experience/seven-million-iot-sensors-failure-modes.html` |
| `feature` / arc | TSDB observability buy vs build | `blog/series/experience/building-tsdb-at-agoda.html` |
| `design` | Token buckets / supplier boundary | `blog/series/experience/supplier-apis-and-token-buckets-wayfair-circuit-breaker.html` |
| `patterns` / `rollout` | EKS under peak load | `blog/series/experience/ten-thousand-concurrent-requests-eks-patterns-delivery-hero.html` |

### AI Learning

| Format | Example slug | Path |
|--------|--------------|------|
| `meta` | Series roadmap | `blog/series/ai-learning/day-0-series-roadmap.html` |
| `deep-dive` | Continuous batching | `blog/series/ai-learning/day-2-continuous-batching-vllm.html` |
| `deep-dive` | Token/cost structure | `blog/series/ai-learning/day-3-token-budgets-cost-structure.html` |
| `design` / `deep-dive` | Prompt caching infra | `blog/series/ai-learning/day-7-prompt-caching-infrastructure-layer.html` |

When drafting, read **one gold post of the chosen format** in the same series before outlining.

---

## Sidecar hints (`data/blog-format-hints.json`)

Optional per calendar day:

```json
{
  "9": { "experience": "rollout", "ai": "deep-dive" }
}
```

- Keys are **calendar day** strings (`"0"` … `"149"`).
- Values: `incident` | `feature` | `design` | `deep-dive` | `rollout` | `patterns` | `meta`.
- Generator does **not** consume this file; agents and checklist do.

---

## Agent workflow (before blog days)

1. Read this file + [`CHECKLIST.md`](../CHECKLIST.md) § Experience & AI blogs.
2. Load hint for calendar day **N** from `data/blog-format-hints.json` if present.
3. If no hint, derive format from tables above (`experience.title`, `code`, `ai.title`).
4. State chosen format in **Phase 1** blog plan (`A2` / `A3`): format ID + why + which gold post to emulate.
5. Draft to format structure (not default incident narrative).
6. Cross-check rolling mix: if last 3 Experience posts were `incident`, prefer `design` / `feature` / `deep-dive` for today unless topic demands otherwise.

---

## Related docs

- [`CHECKLIST.md`](../CHECKLIST.md) — daily gates, voice, numbering
- [`docs/context/README.md`](context/README.md) — employer source of truth
- [`docs/PLAN-REALIGNMENT-RECOMMENDATIONS.md`](PLAN-REALIGNMENT-RECOMMENDATIONS.md) — title/topic fixes (appendix: format diversity)
- [Profile `blog/NEW-POST-CHECKLIST.md`](https://github.com/akshantvats/Profile/blob/main/blog/NEW-POST-CHECKLIST.md) — publish mechanics
