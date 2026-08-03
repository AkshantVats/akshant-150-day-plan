# Day 60 — Experience Post Plan

**Title:** Semantic Cache — Wayfair Pricing Deja Vu
**Subtitle:** Wayfair · Aletheia cache · price-change Kafka · near-duplicate SKU updates
**Employer:** Wayfair — read `docs/context/pricing-system-architecture.md` and
`docs/context/resume-extracted.md` before writing.
**Format:** `design` (tradeoff essay, per `docs/BLOG-FORMAT-MIX.md`) — today's code is a
DESIGN.md day (`semantic-cache-engine`), not a shipped feature or an incident.

## Bridge

Near-duplicate prompts need the same tolerance pricing had for "almost same" supplier feeds.
Today's `semantic-cache-engine` DESIGN.md work makes that concrete: an LLM cache keyed by
embedding similarity has to decide, the same way Wayfair's pricing stack decides for near-
duplicate SKU cost updates, when "close enough" is actually close enough to reuse a cached
result versus recompute.

## Content anchors — must come only from `pricing-system-architecture.md`

- **Aletheia** (`storefront-svc`, ASP.NET Core, Team: Price Output Systems) is the price
  cache + GraphQL API in front of the storefront: ~20,590 RPS avg / ~24,822 peak, 2.1s avg
  latency, backed by Bigtable + in-memory, serving retail price reads to `Storefront` and
  `BasketService`.
- **PRICE CHANGE KAFKA**: Aletheia publishes price-change events onto `pricing_refresh`
  (40 partitions) and `sku_pricing_refresh` (3 partitions) — an event-sourcing pattern that
  invalidates/refreshes cached prices when the underlying calculation changes upstream.
- The angle: Aletheia's cache is not exact-match on every possible query — it's a price
  cache that has to stay coherent as upstream systems (Delphi retail calculator, supplier
  cost feeds) emit near-continuous updates for "almost the same" SKU, not identical SKUs.
  That's the same shape of problem semantic cache faces with near-duplicate prompts: when
  does a new input differ enough from a cached one to require recomputation, and how do you
  invalidate on an upstream signal (a price-change event; a source/context change) rather
  than only on TTL.
- Do NOT claim ownership of Aletheia or the price-change Kafka pipeline — frame this as the
  operational pattern observed while leading PAS & Pricing/Promotions teams (per
  `resume-extracted.md`: Sr. SWE III, Wayfair, Nov 2024–Mar 2026, led PAS and Pricing,
  Promotions & Discounts teams, architected a GCP event-driven Global Pricing system). Keep
  scope to "the pattern I watched Aletheia handle" — not a claim of having built Aletheia
  itself.

## Angle

- Open on the moment a "near-duplicate" SKU price update (same product, trivially different
  cost input) forced a decision: serve the cached retail price or recompute through Delphi.
- Bring in the `pricing_refresh` / `sku_pricing_refresh` Kafka split as the concrete
  event-sourcing anchor for "cache invalidation driven by an upstream signal, not just TTL."
- Land on: `semantic-cache-engine`'s per-tenant similarity threshold and TTL/decay policy
  (today's DESIGN.md) are the same knob Aletheia's price-change events tune for — how much
  drift is tolerable before a cached answer is wrong enough to matter.
- So what: a false cache hit in Aletheia is a stale price shown to a customer; a false cache
  hit in `semantic-cache-engine` is a wrong LLM answer served with high confidence — same
  failure shape, different blast radius, same reason the threshold has to be a tunable,
  per-tenant decision rather than a global constant.
