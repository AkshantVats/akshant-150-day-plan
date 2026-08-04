# Day 65 — AI Learning Post Plan

**Title:** Day 65 — Token Budgets as Rate Limits
**Subtitle:** Sliding windows in Redis
**Day index:** 65
**Hook:** Lua atomicity again — budgets race like rate limits.
**Format:** `deep-dive` (one mechanism: sliding-window counter vs. token bucket, taught with a
DS analogy), per `docs/BLOG-FORMAT-MIX.md`'s "cost / routing economics → design or deep-dive"
guidance.

## Mechanism taught

Why `ingestion`'s existing per-tenant rate limiter (`ingestion/src/rate_limit/token_bucket.rs`
— a continuously-refilling Redis token bucket) is the wrong algorithm for a token-spend
*budget*, and why `cost-budget-enforcer`'s design uses a weighted two-bucket sliding-window
counter instead. A token bucket answers "how fast"; a budget answers "how much, total, this
window" — refilling capacity as time passes is correct for the first question and wrong for
the second.

## Structure

1. Token bucket vs. budget — why continuous refill defeats the point of a hard total.
2. DS analogy (attr-box, team): a water meter (cumulative draw against a billing period) vs. a
   leaking tank (bucket that tops back up) — grounded in an everyday object per CLAUDE.md 4.3.
3. The weighted two-bucket sliding-window-counter algorithm — O(1) memory, approximate,
   closes the fixed-window boundary-gaming gap.
4. Same Lua-atomicity requirement as the existing token bucket, shown side by side in a
   comparison table (token bucket / fixed window / sliding window counter / sliding window
   log — memory, exactness, what each answers).
5. What this doesn't prove yet — no live Redis run in this sandbox, approximation error is a
   documented property, not a measured one.

Gold reference read: `blog/series/ai-learning/day-2-continuous-batching-vllm.html` (series
gold-standard mechanism deep-dive) plus Day 64's AI Learning post for recent-post register
match.

Required mermaid init block used (per CLAUDE.md §4.5). Diagram labels ≤ 6 words. Cross-links
to the companion Experience post (Day 65) and to Day 64.
