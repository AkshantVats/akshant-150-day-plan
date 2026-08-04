# Day 65 — Experience Post Plan

**Title:** Token Budgets — Finance Meets Gateway
**Subtitle:** Wayfair · spend caps
**Format:** `design` (per `docs/BLOG-FORMAT-MIX.md` — DESIGN.md code day maps to `design`)
**Bridge:** Budget enforcer is supplier spend caps for tokens. Today's cost-budget-enforcer
work makes that concrete.

## Employer context used

`docs/context/resume-extracted.md` — Wayfair, Nov 2024–Mar 2026, Sr. SWE III, led PAS and
Pricing, Promotions & Discounts teams; architected the GCP event-driven Global Pricing &
Promotion Engine (hours→sub-seconds propagation, 20k+ suppliers); built the high-throughput
bulk cost-change framework (99.99% availability) with distributed rate limiting and circuit
breakers.

`docs/context/pricing-system-architecture.md` — UCMS (Unified Cost Management System) supplier
cost tables, specifically `tbl_lo_base_cost_violations` (cost violations) and
`tbl_lo_base_cost_changelog` (cost change log), used as the grounded real-system analog for a
guardrail that flags a cost change past a threshold rather than hard-blocking it.

## Structure (design format: options table → decision → rejected alternatives → consequences)

1. The two easy answers to a runaway-number guardrail (hard reject-only vs. silent no-op) and
   why both are wrong.
2. Wayfair's UCMS base-cost violation flow as the real-system precedent — flags a submission,
   doesn't block it, because a legitimate cost change still has to be able to land.
3. Three-threshold table mapping cost-budget-enforcer's Redis design (80% alert / 100% soft /
   120% hard) against the UCMS analog, explicit about the one place the analogy breaks (UCMS
   has no true hard-block state; a token budget does, because a rejected token has no
   information value a rejected cost figure would).
4. What transferred (the three-way split) vs. what had to be rebuilt (a synchronous cheaper-
   model route instead of an asynchronous human-review queue).

Gold reference read: `blog/series/experience/supplier-apis-and-token-buckets-wayfair-circuit-breaker.html`
(direct precedent — Wayfair per-supplier request-rate token bucket + fail-open circuit
breaker).

## Format diversity check

Last 10 Experience posts (days 55–64) are not incident-heavy — day 60 `design`, day 61/62
`feature`/`design`, day 63/64 `deep-dive`. `design` for Day 65 keeps the mix balanced and
matches the DESIGN.md-day signal directly.
