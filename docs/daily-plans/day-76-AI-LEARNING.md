# Day 76 — AI Learning Post Plan

**Title:** Day 76 of Learning LLM Inference — Exact-Match vs Semantic Cache — Two-Tier Memory
Hierarchy
**Subtitle:** L1 exact / L2 embedding, like CPU cache levels
**Day index:** 76
**Hook:** The router checks the fingerprint table before it ever pays for a pgvector round-trip.
**Format:** `deep-dive` (one mechanism — why a two-tier cache with two genuinely different lookup
costs beats either tier alone — taught with a CPU-cache-hierarchy DS analogy), per
`docs/BLOG-FORMAT-MIX.md`.

## Mechanism taught

Why `Stack.Get`'s ordering (L1 exact-match first, L2 semantic second, backfill on an L2 hit) isn't
an arbitrary implementation choice — it's the same shape a CPU memory hierarchy uses, and for the
same underlying reason: cheap-and-narrow in front of expensive-and-broad, with the expensive tier
doing strictly more work (an embedding call plus a similarity search versus one Redis `GET`) in
exchange for catching cases the cheap tier structurally cannot.

## Structure

1. The two questions a cache tier can answer, and they're not the same question. L1 (fingerprint)
   answers "have I seen this *exact* prompt before" — a yes/no on byte-identical input after
   normalization. L2 (semantic) answers "have I seen something *similar enough* to this prompt
   before" — a fuzzier, strictly harder question that needs an embedding model and a similarity
   search to even ask.
2. DS analogy (attr-box, team): a CPU's L1/L2 cache hierarchy. L1 is small, sits right next to the
   core, and answers in a couple of cycles — but it only holds what's been touched most recently
   and can only ever answer "is this exact address cached." L2 is larger and slower (tens of
   cycles instead of a handful) and catches what L1 missed. Neither tier is "the cache" on its
   own — the hierarchy's whole value is that most lookups get answered by the fast, narrow tier,
   and only the ones that need it pay the slower, broader tier's cost. `prompt-fingerprinter`'s L1
   (Redis, exact match) in front of `semantic-cache-engine`'s L2 (embedding + pgvector) is the
   identical shape at a different latency scale — microseconds versus milliseconds instead of
   cycles versus tens of cycles, but the same "narrow-cheap-first" reasoning.
3. Why L1 can't just be a smaller version of L2: an exact-match cache is a lookup, one Redis `GET`
   on a key that's either present or not — no ranking, no threshold, no model call. A semantic
   cache is a search — it has to convert the prompt into an embedding, then compare that embedding
   against every candidate within a similarity threshold. That extra work is precisely what buys
   L2 its broader hit criterion (catching a *rephrased* duplicate, not just a byte-identical one) —
   the cost and the capability are the same tradeoff, not two independent design choices.
4. Today's code, concretely: the admin `PUT /tenants/{id}/fingerprint-rules` endpoint lets a tenant
   configure `strip_punctuation`/`lowercase`/`max_prompt_bytes` — widening what L1 treats as "the
   same prompt" without touching L2 at all. `TestIntegration_AdminRulesExpandDuplicateDetection`
   proves the concrete payoff: two prompts differing only in case and punctuation, which would have
   split across a miss-then-hit under Day 70's default rules, now both resolve at L1 once a tenant
   opts in — one fewer trip to the (simulated) embedding API, the exact cost L2 exists to gate.
5. Closing the observability loop: `cache_hit_type=exact` (DESIGN.md §4's `cache_hit_exact` source
   value, reserved on Day 70) now actually reaches LensAI via the same `/ingest` envelope
   `cost-budget-enforcer`'s writer already established — the point where "how much traffic is a
   literal duplicate" becomes a real, queryable number instead of a documented intent.
6. So-what: a two-tier cache isn't two independent caches bolted together — it's one hierarchy
   where the cheap tier's entire justification is catching enough traffic that the expensive tier's
   real cost gets paid only when the cheap tier's narrower question genuinely can't answer it. The
   same reasoning governs a CPU deciding what lives in L1 versus L2 and a request router deciding
   what gets an exact-match check before an embedding call.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus Day 75's AI Learning post for recent-post register match
and to avoid re-explaining `Normalize()` (already covered there) — today's post assumes it and
builds the tier-ordering argument on top.

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links to
the companion Experience post (Day 76) and to Days 70, 75.
