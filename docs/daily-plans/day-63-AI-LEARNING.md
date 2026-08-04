# Day 63 — AI Learning Blog Plan

**Title:** Day 63 — Cache Quality Metrics
**Subtitle:** Hit rate, precision proxy, TTL
**day_index:** 63
**Hook:** Track thumbs-down rate on cache hits if you can.
**Format:** `deep-dive` (per `docs/BLOG-FORMAT-MIX.md`) — one mechanism (why a hit-rate metric
alone can't validate a similarity threshold, and what a precision proxy adds) developed with a
DS analogy, continuing the RouteIQ arc Day 60–62 opened.

## Required reading before writing

- `day-2-continuous-batching-vllm.html` (GOLD post) for depth/structure.
- Most recent AI Learning post (Day 62 — "ANN Search at QPS") for register and to make the arc
  continuation explicit: Day 62 covered how the lookup finds a candidate; Day 63 covers how you
  know whether the threshold that decided "close enough" was actually right.
- Today's `semantic-cache-engine` code (Day 63: `pkg/analytics`, `pkg/feedback`,
  `cmd/threshold-sweep`) for the concrete technical anchor.

## Angle

- Open on or build to the hook: track thumbs-down rate on cache hits if you can — a hit rate
  alone tells you how often the cache fired, never whether it fired correctly. A classifier
  that always predicts "yes" gets a great hit rate and a useless accuracy; a similarity
  threshold that's too loose gets the same shape of lie.
- Core mechanism: precision vs. recall applied to a similarity threshold. Raise the threshold
  (require closer matches) and precision goes up (fewer wrong hits) but recall goes down
  (fewer prompts qualify as duplicates at all, more cache misses, more real inference calls).
  Lower it and the reverse. `DESIGN.md §3`'s per-tenant threshold and `§8`'s shipped `0.92`
  default are both single points on that curve — a threshold sweep (`cmd/threshold-sweep`,
  today's code) is what makes the curve visible instead of assumed.
- DS analogy (attr-box required): a smoke detector tuned to never miss a real fire will also
  scream at burnt toast — high recall, low precision. Tune it to only alarm on unmistakable
  fire and it'll stay quiet through some real fires that look ambiguous early on — high
  precision, lower recall. There's no dial setting that maximizes both at once; the shipped
  default is a choice about which failure mode you'd rather have. The cache's similarity
  threshold is the same dial: too loose, and "close enough" prompts get treated as duplicates
  they aren't (false hits, DESIGN.md §4's correctness failure); too tight, and the cache stops
  firing on prompts that really were near-duplicates (needless inference cost, but at least not
  wrong).
- Precision proxy without ground truth: DESIGN.md §4 designed for a "sampled human/LLM-judge
  review pass" to compute a real false-positive rate; today's `pkg/feedback` thumbs-down
  webhook is the minimal real signal available without that full pipeline — a lower bound on
  the true false-positive rate (only users who noticed and bothered to flag), not the number
  itself, and the post should say so plainly rather than presenting it as ground truth.
- Land on: a hit-rate dashboard with no accompanying precision signal isn't lying, but it's
  answering a different question than the one that matters — "did the cache fire" instead of
  "was firing the right call" — and a threshold sweep is how you find out where on that curve a
  single fixed default (0.92) actually sits before trusting it in production.

## Diagram requirement

Standard mermaid init block (CLAUDE.md §4.5). One flowchart or simple chart-shaped diagram
showing the threshold sweep: prompt pair → cosine similarity score → compare against sweep
thresholds (0.88…0.96) → classify hit/miss at each → aggregate into precision/recall/FPR per
threshold. Labels ≤6 words, ≤8 nodes.

## Constraints

- Kicker: `Day 63 of 150`.
- ai.hook opening line, attr-box DS analogy present.
- No claim that the thumbs-down proxy or the local bag-of-words similarity sweep (documented
  in today's `BENCHMARKS.md` — real `OPENAI_API_KEY` is at its billing quota limit in this
  sandbox, confirmed by a live probe) is the same signal a live pgvector + OpenAI embedding run
  would produce. Frame both as honest proxies with a stated limitation, not a measured
  production result.
