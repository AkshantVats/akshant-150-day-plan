# Day 79 — AI Learning Post Plan

**Title:** Day 79 of Learning LLM Inference — Score Normalization — Why 0–1 Beats Raw Likert
**Subtitle:** Comparable units across models like z-scored metrics
**Day index:** 79
**Hook:** Store both raw and normalized in `quality_scores`.
**Format:** `deep-dive` (one mechanism — why a 0–1 normalized unit is the comparable one across
rubrics with different criteria counts and weight distributions — taught with a z-score DS
analogy), per `docs/BLOG-FORMAT-MIX.md`'s "mechanism in title" signal.

## Mechanism taught

Why storing `normalized_score` alongside the raw `score` isn't a cosmetic rename of "0–100" to
"0–1" — it's the same move as z-scoring a metric before comparing it across populations with
different scales: the raw number encodes information (how many criteria, what the weights were)
that has nothing to do with the actual question a rollup needs to answer, which is "how good was
this response, in a unit that means the same thing regardless of which rubric produced it."

## Structure

1. The concrete problem: two `task_type`s can have rubrics with a different number of criteria and
   different weight distributions (Day 77's `JudgeRubric` schema makes this legal by design — one
   rubric per `task_type`, criteria and weights chosen per task). `WeightedScore` already outputs
   0–100 regardless, so on the surface this looks solved — but 0–100 for a 2-criterion rubric and
   0–100 for a 5-criterion rubric were produced by structurally different weighted sums, and a
   rollup that averages `model_id=X`'s scores across both `task_type`s is quietly averaging two
   different measurement processes as if they were the same ruler.
2. DS analogy (attr-box, mine): z-scoring. A raw exam score of 78 means something different on a
   test with a mean of 50 and a spread of 10 than on a test with a mean of 75 and a spread of 20 —
   comparing the two raw numbers directly is comparing them on each test's own arbitrary scale. A
   z-score (`(x - mean) / stddev`) puts both onto the same unit — "how many standard deviations from
   this population's own center" — so a 78 on one test and a 62 on another become comparable the
   moment they're expressed the same way. `normalize.Score` doesn't z-score (the rubric's `[0,100]`
   range is already fixed and bounded, not an open-ended population), but it does the same job at a
   smaller scale: collapsing `WeightedScore`'s output onto one interpretable unit (`[0,1]`, "fraction
   of the rubric's maximum") so a rollup comparing `model_id=A` on `summarization` against
   `model_id=A` on `extraction` is comparing two numbers on the same footing, not two numbers that
   happen to share a range by coincidence.
3. Why store both raw and normalized, not just normalized: `score` (0–100) is what the judge
   actually computed and what a debugging session reading `rationale` alongside it wants to see —
   throwing it away the moment it's written would make the stored row less legible for the exact
   audit use case DESIGN.md §6 already designed `rationale` for. `normalized_score` is a derived,
   always-recomputable-from-`score` convenience column for the one thing raw scores are bad at:
   being averaged across a boundary (`model_id×task_type`) that mixes different rubrics.
4. Today's rollup code, concretely: `pkg/rollup.Query(Window1h)` and `Query(Window24h)` return the
   `toStartOfHour`/`toStartOfDay(scored_at)`-grouped SQL that averages `normalized_score` (never
   raw `score`) per `model_id, task_type` bucket — the query-time aggregation DESIGN.md §6 already
   committed model-quality-scorer to, extended to operate on the comparable unit instead of the raw
   one.
5. The statistical noise floor: `pkg/rollup.MinSamplesForConfidence = 30` and `StandardError`
   (`stddev / sqrt(n)`) are the other half of "comparable" — a bucket's average is not trustworthy
   on its own; it needs its sample count considered too. A 1h bucket with 4 samples and a 1h bucket
   with 400 samples can report the identical average and mean very different things, the same way a
   z-score computed from a 4-person sample and one computed from a 400-person sample carry very
   different confidence even at an identical value.
6. Today's Experience post, same shape: Walmart's Azure Stream Analytics windowed HVAC telemetry
   dropped events a bounded window couldn't hold; the fix was Kafka's durable, replayable log —
   never discarding the underlying facts a later computation might need to redo. `quality_scores`
   keeping every raw sample (never collapsing to a running average at write time) is the identical
   discipline: the comparable, normalized rollup is always recomputable from retained raw facts,
   the same way a replayable log is always recoverable from a committed offset.
7. So-what: a "0–100 vs 0–1" choice looks cosmetic until you have to average across a boundary the
   raw scale was never designed to cross — the same lesson a z-score teaches about comparing two
   populations, applied one level down, to comparing two rubrics.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus `day-78-async-evaluation-pipelines-throughput-over-latency.html`
(most recent AI Learning post, for register match and because it's this post's direct predecessor —
Day 78's own "What Comes Next" section already previews this exact scope).

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links to the
companion Experience post (Day 79) and to Days 77, 78.
