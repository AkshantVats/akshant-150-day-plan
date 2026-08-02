# Day 55 — AI Learning Blog Plan

**Title**: Day 55 — Cross-Product Metrics — LensAI × TraceForge
**Subtitle**: Join keys and dashboard contracts
**Hook**: One tenant_id to rule cost — design the join on Day 1.
**day_index**: 55

**Format**: `design` (per `docs/BLOG-FORMAT-MIX.md`) — the post is a tradeoff essay about
*which field is the join key and why the envelope stays additive-only*, following the GOLD
post's mechanism-first structure but centered on a design decision rather than a pure
mechanism deep-dive, to vary from Day 51-54's `deep-dive`/hybrid run.

**Bridge**: today's code (`pkg/lensai/writer.go` in `agent-benchmark-runner`) dual-writes
benchmark-batch completion onto LensAI's `/ingest` pipeline using the same envelope
`tool-call-analyzer/pkg/lensai` (Day 42) already uses for tool-call cost, with a new
`source: "benchmark_run"` discriminator. The post explains why two unrelated products
(an inference-cost pipeline and a benchmark-grading pipeline) can share one wire format at
all, and what has to stay true about that format for a future join to work.

## Angle

A distributed system rarely gets to choose its dashboard's join key after the fact. By the
time two pipelines both have data flowing and a stakeholder asks "show me cost and quality
for this tenant on one screen," retrofitting a shared key means backfilling history that
was never tagged with it — or living with two screens forever. The cheaper move is
deciding the join key on day one of the *second* pipeline, before it has any data to
migrate: LensAI's `/ingest` envelope already had `tenant_id`; the only question Day 55
had to answer was whether `agent-benchmark-runner` would reuse it or invent its own.

The systems-engineering parallel is a wide event / structured-log join key: a request ID
threaded through every service a request touches isn't free — every service has to accept
carrying a field it doesn't otherwise need — but the alternative (correlating logs after
the fact by timestamp and hope) fails exactly when it matters most, under load, with clock
skew. `tenant_id` on a benchmark-completion event is the same trade: `orchestrator.Summary`
doesn't need a tenant concept to grade a batch correctly, but the event built from it does,
because the event's only job is to be joinable later.

The other design question the post covers: LensAI's `InferenceEvent` struct has a fixed
set of fields, and Day 42 already proved that struct silently drops fields it doesn't
recognize (Rust's serde ignores unknown JSON keys without `deny_unknown_fields`). That's
what makes it safe for `agent-benchmark-runner` to reuse the *same* envelope with a
different `source` value instead of standing up a second endpoint — the schema is
additive-safe by construction, not by convention. The honest gap: additive-safe today
doesn't mean additive-safe forever; the day LensAI's ingest handler adds strict field
validation, both dual-writers break at once, silently, until someone notices a metric went
to zero.

Sections: the join-key-first design principle (why `tenant_id` had to be decided before
data existed to migrate) | the wide-event/structured-log systems parallel | why serde's
default unknown-field behavior is what makes the shared envelope safe to extend, and the
"additive-safe today ≠ additive-safe forever" honest gap | what a real aggregation point
(next to today's ScheduledReader-shaped bridge post) would still need beyond a shared key.

## Attr-box DS analogy

A phone system's country-code prefix: every number needs one whether or not a given call
ever crosses a border, because retrofitting a prefix onto an existing numbering scheme
after adoption is far more expensive than reserving the field before any numbers exist.

## Diagram

One Mermaid diagram: two source boxes (LensAI inference event, benchmark-run event) both
labeled with `tenant_id`, converging on one `/ingest` envelope box, diverging again to two
labeled `source` values (`tool_call`/`inference`, `benchmark_run`) inside one ClickHouse
table box. Max 8 nodes, labels ≤6 words, required init block from CLAUDE.md §4.5.
