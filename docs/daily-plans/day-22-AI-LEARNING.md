# Day 22 — Feature Flags for Model Rollouts
## Blog Outline — AI Learning Series

---

## Header Block

| Field | Value |
|---|---|
| Series | AI Learning · Day 22 of 150 |
| Day | 22 |
| Topic | Feature Flags for Model Rollouts |
| Subtitle | Canary models with audit trails |
| Hook | "A model rollout without audit log is a production incident waiting for a postmortem." |
| DS Analogy | Feature flags for model versions are like traffic routing at a load balancer — except the "server" is a model version and the health metric is quality score, not latency. You don't switch all traffic to the new model at once; you canary it. |
| Target URL | `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-22-feature-flags-model-rollouts.html` |
| Thread Connection | `resolved_model_id` on ingest events closes the loop between flagd policy and ClickHouse cost attribution. |

---

## HTML File Target Block

All of the following must use "Day 22" — never an episode ordinal.

| HTML Location | Required Text |
|---|---|
| `<title>` | `Day 22 — Feature Flags for Model Rollouts \| AI Learning Series` |
| Accent chip | `AI Learning · Day 22 of 150` |
| `<h1 class="post-title">` | `Day 22 — Feature Flags for Model Rollouts` |
| Meta line | `AI Learning · Day 22 of 150` |
| Series footer | `Day 22 of 150 — Feature Flags for Model Rollouts` |

---

## Voice Reminders

- Write in first person throughout: "I hit this wall when...", "Here's what surprised me...", "What I didn't expect was..."
- Maximum 3 sentences per paragraph. If a paragraph hits 4 sentences, split it.
- One concrete analogy per major concept — grounded in physical or everyday objects, never another software concept.
- Every section ends with a "so what" sentence that lands the practical takeaway.
- No bullet lists as a substitute for prose. Lists only for ordered steps where prose is genuinely harder to follow.

---

## Opening Hook

**Purpose:** Pull the reader into the core tension — model rollouts look like code deploys but they aren't, and the audit trail is what separates a controlled experiment from a blind swap.

### Paragraph 1 (The incident frame)
Open with the hook verbatim: "A model rollout without audit log is a production incident waiting for a postmortem." Then expand: three weeks into building this system, I merged a model version bump on a Friday afternoon the same way I'd merge any dependency upgrade — bump the version string, ship it, watch metrics. By Monday morning I had a cost spike I couldn't explain because I had no record of which requests had hit the new model, at what percentage, and when the weight changed. The audit trail wasn't a nice-to-have. It was the only thing that would have let me answer the question "did the new model cause this?"

### Paragraph 2 (What the rest of this post covers)
This post walks through the mechanics I built: a percentage rollout flag backed by FNV-1a hashing for deterministic session assignment, an audit log that snapshots evaluation counts at every weight change, and a `resolved_model_id` field that gets written on every inference event so ClickHouse can tell me the exact cost diff between flag versions. By the end, the loop is closed — every dollar of inference cost is traceable back to a flag state.

### Concrete Non-Software Analogy
A pharmaceutical trial uses the same logic. You don't give the new drug to every patient on day one. You start with 5% of the cohort, measure outcomes, hold that percentage for a defined observation window, and only advance if the data clears the bar. The audit trail isn't bureaucracy — it's what lets you say "the effect appeared when we crossed 20% on day 3" rather than "something changed and we're not sure what."

### Core Frame
The core frame for this entire post: feature flags for models are a rollout instrument, not a configuration switch. The difference is that a configuration switch takes effect immediately and is reversible with a revert. A rollout instrument has state — it records who got what, when, and at what cost. Everything in this post builds toward that distinction.

---

## Section 1 — Why Code Deploys and Model Rollouts Are Different

**Purpose:** Establish the fundamental mismatch between the mental model most engineers bring from code deployments and the actual constraints of model rollouts.

### Key Points

**Point 1 — Multi-turn context breaks stateless swap logic.**
A code deploy is stateless with respect to users. If I roll back a service, the next request hits the old binary and the user gets a valid response. A model rollout is not stateless for multi-turn conversations. If a user is three turns into a conversation that was started under model v2 and I swap them to v3 mid-session, the new model receives a context window it was never calibrated on. The quality regression isn't in any single response — it's in the coherence of the turn sequence. I hit this wall when I tried to use a simple percentage flag without a stickiness constraint and got complaint reports that conversations felt "forgetful."

**Point 2 — Quality regression is not detectable in one request.**
A latency regression in a code deploy shows up in P99 within minutes of rollout. A quality regression in a model shows up in downstream metrics — user satisfaction scores, re-query rates, escalation rates — that have lag measured in hours. This means you can't use the same rollout velocity for models that you use for code. The observation window has to be longer.

**Point 3 — Cost is a step function, not a gradient.**
When you swap from GPT-3.5 to GPT-4, cost doesn't increase gradually with the percentage rollout. Every request that hits the new model costs at the new tier's rate. At 5% rollout on a high-traffic system, that's a meaningful absolute cost increase even if the percentage sounds small. Without an audit log that records which requests hit which model, you can't separate "the new model is expensive" from "we routed more traffic to it than we intended."

**Point 4 — Rollback is not the same as revert.**
In code, a rollback restores the previous binary. In a model rollout, a rollback means changing the flag weight back to 0% — but any multi-turn sessions that started under the new model still have that model's context window. A true rollback requires either session termination or a per-session model ID that persists across turns.

### "What I didn't expect" insight
What I didn't expect was that the hardest part wasn't the flag mechanics — it was defining what "ready to advance to the next percentage" actually meant. For code, it's "error rate below threshold after N minutes." For models, I had to instrument a quality proxy metric before I could even write the advance condition.

### Concrete Non-Software Analogy
A bridge load test uses the same incremental approach. Engineers don't drive a fully loaded convoy across a new bridge on day one. They start with a single vehicle, instrument the stress sensors, hold at that load level, read the deflection data, and only increase when the measurements clear safety margins. The percentage rollout is the load increment. The audit log is the sensor data.

### "So what" sentence
If you carry code-deploy intuitions into a model rollout, you will get burned — not by a crash, but by a cost anomaly or a quality regression that you can't explain because you never recorded the state.

---

## Section 2 — The Percentage Rollout Flag: Mechanics and Semantics

**Purpose:** Explain how the flagd percentage rollout flag is structured, what "percentage" actually means at evaluation time, and what the flag schema looks like.

### Key Points

**Point 1 — The flag schema.**
The flag lives in a JSON configuration that flagd evaluates at request time. The relevant fields are the variant names (e.g., `"model-v1"` and `"model-v2"`), the defaultVariant, and a `fractionalEvaluation` rule that maps a hash of the targeting key to a bucket. The percentage is not a probability — it's a deterministic bucket assignment. If 20% of hash space maps to `model-v2`, then exactly 20% of distinct targeting keys will consistently resolve to `model-v2`.

**Point 2 — The targeting key is the unit of consistency.**
The targeting key is what you hash. If you hash `request_id`, you get request-level randomization with no stickiness. If you hash `session_id`, you get session-level stickiness — same session always hits same model. If you hash `user_id`, you get user-level stickiness across sessions. The choice is a product decision disguised as a configuration detail. For multi-turn chat, `session_id` is the right key.

**Point 3 — Weight changes take effect immediately.**
When I change the flag weight from 20% to 50%, the change takes effect on the next evaluation for every new session. Existing sessions that were sticky to `model-v1` stay on `model-v1` for the duration of that session. New sessions are re-evaluated against the new weight. This means weight changes are not instantaneous across the fleet — the rollout advances as new sessions start.

**Point 4 — The flag is not a circuit breaker.**
A common mistake is to treat the flag as a circuit breaker — "if quality drops, set weight to 0%." But a circuit breaker has automatic trigger logic. A flag requires a human (or an automated policy) to explicitly change the weight. The flag mechanics don't know anything about quality. That coupling — between quality signals and flag state — has to be built separately.

### "What I didn't expect" insight
What I didn't expect was how much the semantics of "percentage" matter. I initially thought of it as "20% of requests go to the new model." The correct framing is "20% of the hash space resolves to the new model." Those are the same thing over a uniform distribution of targeting keys, but they diverge when your traffic is bursty or when your session IDs are not uniformly distributed.

### Concrete Non-Software Analogy
Think of a paint mixing machine at a hardware store. When you dial in a color formula, the machine dispenses precise fractions of each pigment by weight, not by probability. The result is deterministic — the same formula always produces the same color. The percentage rollout is the formula. The hash is the dispensing mechanism. You're not rolling dice; you're following a recipe.

### "So what" sentence
Understanding that percentage rollout is deterministic bucket assignment — not probabilistic sampling — is the foundation for everything that comes next, including the stickiness guarantee and the audit log's cost attribution math.

---

## Section 3 — Deterministic Hashing for Session Consistency

**Purpose:** Explain FNV-1a hashing, why it produces deterministic bucket assignments, and why this matters specifically for multi-turn conversations.

### Key Points

**Point 1 — FNV-1a: fast, non-cryptographic, uniform.**
FNV-1a (Fowler–Noll–Vo) is a non-cryptographic hash function that produces a 32-bit or 64-bit output from an arbitrary byte input. It's fast (single-pass, no state accumulation), has good avalanche properties (a 1-bit input change produces ~50% output bit changes), and produces a reasonably uniform distribution over its output space. For bucket assignment, you take the hash output modulo 10000 to get a bucket number between 0 and 9999, then compare it against the cumulative weight thresholds.

**Point 2 — The sticky assignment guarantee.**
Given the same `session_id` string and the same flag weight configuration, FNV-1a always produces the same bucket number. This is the sticky assignment guarantee. It means that once a session is assigned to `model-v2`, every subsequent evaluation of the flag for that session will resolve to `model-v2` — not because there's a database entry recording the assignment, but because the hash is deterministic. The assignment is implicit in the session ID and the current weight configuration.

**Point 3 — Why this matters for multi-turn conversations.**
A multi-turn conversation accumulates context across turns. Turn 1 establishes the user's intent. Turn 2 references it. Turn 3 builds on the reference. If a different model processes Turn 3 than processed Turns 1 and 2, the context window is being interpreted by a model that wasn't calibrated on the history of this session. Sticky assignment prevents this. Every turn in a session hits the same model variant for the lifetime of the session.

**Point 4 — The edge case: weight changes during an active session.**
If the flag weight changes from 20% to 50% while a session is active, a session whose bucket number was in the v1 range at 20% might flip to v2 at 50% — because its bucket number is now within the enlarged v2 range. This is the subtle breakage: weight changes can re-assign active sessions. The fix is to snapshot the assignment at session creation and store it, or to enforce a policy that weight changes only take effect for new sessions.

### "What I didn't expect" insight
What I didn't expect was that "deterministic" and "sticky" are not the same property. Deterministic means the same input always produces the same output given the same configuration. Sticky means the assignment doesn't change across the lifetime of a session even if the configuration changes. You need both, and they require different implementation choices.

### Concrete Non-Software Analogy
Think of a postal sorting office that routes packages by zip code. The routing rule is deterministic — zip code 10001 always goes to the Manhattan facility. But if the routing rules change mid-day (new facility opens, zone boundaries shift), packages that are already in transit don't get re-routed. They follow the rule that was in effect when they entered the system. Session stickiness works the same way: the assignment rule at session creation is the one that counts.

### "So what" sentence
FNV-1a gives you deterministic assignment for free, but stickiness across flag weight changes requires you to either snapshot the assignment at session start or enforce a policy that weight changes only take effect for new sessions.

---

## Section 4 — The Audit Log: Cost Attribution, Not Just Change Tracking

**Purpose:** Reframe the audit log from a compliance artifact into a cost attribution instrument, and explain the `evaluation_count_snapshot` field that makes this possible.

### Key Points

**Point 1 — The audit log records state transitions, not just who-changed-what.**
Most audit logs record: timestamp, actor, field, old value, new value. That's a change log. A cost attribution audit log needs one more field: the cumulative evaluation count at the moment of each weight change. This is `evaluation_count_snapshot`. It's the number of flag evaluations that have happened against this flag, globally, up to the point of the weight change. With this field, you can compute the exact number of evaluations (and therefore requests) that occurred at each weight level.

**Point 2 — Computing cost diff between flag versions.**
If the audit log shows: weight changed from 20% to 50% at evaluation count 847,000 — and the current evaluation count is 1,200,000 — then 353,000 evaluations happened at the 50% weight level. At 50% routing to model-v2, that's approximately 176,500 requests that hit model-v2 at the higher cost tier. Multiply by the token cost delta between v1 and v2, and you have an attribution number. This is not an estimate — it's a calculation from recorded state.

**Point 3 — The audit log is append-only.**
The audit log must be append-only. Weight changes append a new record; they never modify existing records. This is not just a compliance property — it's what makes the cost attribution math reliable. If records can be modified, the evaluation count snapshots become untrustworthy.

**Point 4 — What the audit log schema looks like.**
Fields: `flag_key`, `changed_at` (ISO 8601 with timezone), `changed_by`, `old_weight`, `new_weight`, `evaluation_count_snapshot`, `reason` (required free text). The `reason` field is not optional — it forces the actor making the change to record why. "Advancing canary to 50% — quality score 0.87 over 24h" is a reason. "bump" is not.

### "What I didn't expect" insight
What I didn't expect was how useful the audit log became for debugging unrelated issues. Three weeks in, a cost anomaly appeared on a Tuesday. The audit log showed a weight change at 2:14 AM — an automated canary advance triggered by a quality score threshold crossing. The anomaly wasn't a bug. It was the expected cost increase of moving from 20% to 50% on a higher-cost model. Without the audit log, I would have filed an incident. With it, I closed the investigation in four minutes.

### Concrete Non-Software Analogy
A utility meter reading log works the same way. The meter records cumulative kilowatt-hours at each billing period boundary. The difference between two readings gives you the consumption for that period. The meter doesn't care why you used that electricity — it just records the snapshot. The `evaluation_count_snapshot` is the meter reading at the moment of each flag state change.

### "So what" sentence
The audit log with `evaluation_count_snapshot` turns "why did our inference bill go up?" from a mystery into a five-minute query — and that's worth more in production than any individual feature of the flagging system.

---

## Section 5 — resolved_model_id: Closing the Loop to ClickHouse

**Purpose:** Explain the `resolved_model_id` field, where it's written, how it flows into ClickHouse, and why it's the final piece that closes the cost attribution loop.

**Thread connection:** `resolved_model_id` on ingest events closes the loop between flagd policy and ClickHouse cost attribution.

### Key Points

**Point 1 — The field and where it lives.**
`resolved_model_id` is a field written on every inference event by the flagd sidecar at evaluation time. When a request comes in, the sidecar evaluates the flag, resolves to a model variant (e.g., `gpt-4-turbo-2024-04-09`), and writes the exact model ID — not the variant name, but the fully qualified model identifier — into the inference event before it hits the router. This field is carried through the entire request lifecycle: inference event → Kafka topic → ClickHouse `inference_events` table.

**Point 2 — Why the fully qualified model ID, not the variant name.**
The variant name is `model-v2`. The fully qualified model ID is `gpt-4-turbo-2024-04-09`. These are not interchangeable. If you log the variant name, your ClickHouse query can tell you how many requests hit the `model-v2` variant. But it can't tell you the per-token cost, because different model versions under the same variant name might have different pricing. The fully qualified model ID is what you join against the pricing table.

**Point 3 — The ClickHouse query that closes the loop.**
With `resolved_model_id` in the `inference_events` table, the cost attribution query is:
```sql
SELECT
  resolved_model_id,
  count() AS request_count,
  sum(total_tokens) AS total_tokens,
  sum(total_tokens * price_per_token) AS total_cost
FROM inference_events
JOIN model_pricing ON inference_events.resolved_model_id = model_pricing.model_id
WHERE toDate(ingested_at) = today()
GROUP BY resolved_model_id
```
This gives you cost by model version for today. Add a join against the `flag_audit` table on timestamp ranges and you have cost by flag state.

**Point 4 — The loop is now closed.**
The audit log records when the flag weight changed and how many evaluations had accumulated. The `resolved_model_id` field records which model each individual request hit. The ClickHouse query joins them. The loop: flagd policy → evaluation → inference event → Kafka → ClickHouse → cost report → flag change decision → flagd policy.

### "What I didn't expect" insight
What I didn't expect was that `resolved_model_id` would be more useful than the flag's own metrics for debugging. The flag system tracks evaluation counts per variant. But it doesn't track token usage, latency distribution, or error rates by variant. `resolved_model_id` in ClickHouse does all of that, because it's just a column in the same table where all inference metrics already live.

### Concrete Non-Software Analogy
Think of a warehouse inventory system that records the exact supplier lot number on every outgoing package. If a product recall happens, the lot number is what lets you trace which customers received affected stock — not the product name, not the SKU, but the specific manufacturing batch. `resolved_model_id` is the lot number for inference requests. It's the traceability field that makes every other analysis possible.

### "So what" sentence
`resolved_model_id` is a single field written once at evaluation time, but it's what makes the entire cost attribution system work — without it, the audit log gives you when the flag changed, but ClickHouse can't tell you what each change actually cost.

---

## Section 6 — What a Real Canary Rollout Looks Like

**Purpose:** Walk through the concrete four-step canary sequence (5% → 20% → 50% → 100%), what you measure at each step, and what the advance conditions look like.

### Key Points

**Step 1 — 5% (smoke test, not a real sample).**
The 5% step is not statistically significant. You're not trying to measure quality at 5% — you're trying to catch catastrophic failures: model API errors, timeout rates, malformed response formats, and cost anomalies. The observation window is 1–2 hours. The advance condition is: error rate on model-v2 requests < 0.5%, P99 latency within 20% of model-v1 baseline, no cost anomaly flag triggered.

**Step 2 — 20% (first quality signal).**
At 20%, you have enough volume for a preliminary quality signal if your traffic is moderate-to-high. This is where you start reading the quality proxy metric. The observation window is 4–8 hours or 10,000 requests, whichever comes first. The advance condition adds: quality score for model-v2 requests ≥ quality score for model-v1 requests within a ±3% tolerance band.

**Step 3 — 50% (A/B parity check).**
At 50%, you have a true A/B split. Every metric — quality, cost, latency, error rate — is now comparable with statistical significance. The observation window is 12–24 hours. The advance condition: quality parity confirmed, cost delta understood and accepted (a business decision, not a technical one), no regression in any monitored metric.

**Step 4 — 100% (full rollout and observation window).**
The advance to 100% does not end the rollout. The observation window continues for 24–48 hours post-100% before the flag is retired. After the observation window clears, the flag is archived — the new model becomes the default, the old model variant is removed, and the audit log entry is retained permanently.

### "What I didn't expect" insight
What I didn't expect was how much organizational friction the advance conditions would create. The technical conditions are straightforward to define. But "cost delta understood and accepted" at Step 3 requires a product or finance decision, not an engineering one. The canary rollout process forced me to build a handoff point into the workflow that I hadn't anticipated.

### Concrete Non-Software Analogy
A film developing process uses the same incremental commitment structure. You shoot a test frame, develop it, check the exposure. Then you shoot a test roll, check the grain and color. Only then do you shoot the full production roll. Each step commits more material and more time — and each step has a defined checkpoint before you proceed. Rolling back after the test frame costs one frame of film. Rolling back after the full production roll costs the entire shoot.

### "So what" sentence
The four-step sequence isn't bureaucracy — it's the minimum number of checkpoints needed to separate catastrophic failure detection from quality regression detection from cost acceptance, which are three fundamentally different kinds of decisions that require different observation windows and different decision-makers.

---

## Mermaid Diagrams

### Diagram 1 — Model Rollout Percentage Mechanics

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart TD
    A["Inbound Request"] --> B["Extract session_id"]
    B --> C["FNV-1a Hash"]
    C --> D["Bucket 0-9999"]
    D --> E{"Bucket < weight?"}
    E -- Yes --> F["Resolve model-v2"]
    E -- No --> G["Resolve model-v1"]
    F --> H["Write resolved_model_id"]
    G --> H
```

### Diagram 2 — Audit Log and Cost Attribution Flow

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart LR
    A["Flag Weight Change"] --> B["Append Audit Record"]
    B --> C["evaluation_count_snapshot"]
    D["Inference Event"] --> E["resolved_model_id field"]
    E --> F["Kafka Topic"]
    F --> G["ClickHouse Table"]
    C --> H["Cost Attribution Query"]
    G --> H
```

---

## Post Metadata JSON Block

```json
{
  "day": 22,
  "series": "ai-learning",
  "slug": "day-22-feature-flags-model-rollouts",
  "title": "Day 22 — Feature Flags for Model Rollouts",
  "subtitle": "Canary models with audit trails",
  "date": "2026-06-09",
  "tags": ["feature-flags", "model-rollouts", "canary-deployment", "flagd", "clickhouse", "audit-log"],
  "url": "https://akshantvats.github.io/Profile/blog/series/ai-learning/day-22-feature-flags-model-rollouts.html",
  "coverImage": "blog/assets/covers/day-22-feature-flags-model-rollouts.png",
  "ogImage": "blog/assets/og/day-22-feature-flags-model-rollouts.png",
  "seriesFooter": "Day 22 of 150 — Feature Flags for Model Rollouts"
}
```

---

## Format Diversity Check

Before writing the final HTML post, count the last 10 posts by format:
- incident / feature / design / deep-dive / rollout / patterns

**This post's format: deep-dive (mechanism walkthrough with a concrete implementation sequence).**

If deep-dive count is ≥ 4 in the last 10 posts, consider reframing as a "rollout" format — narrative arc shifts from "here's how the mechanism works" to "here's the sequence of decisions we made." Reference `docs/BLOG-FORMAT-MIX.md` from `akshant-150-day-plan` for current counts.

---

## Self-Review Checklist

Run through every item before `git add`. Record the count in commit message: `Self-review: N issues found and fixed.`

- [ ] **Unexplained jargon**: FNV-1a, flagd, resolved_model_id, evaluation_count_snapshot each get a 1-sentence definition on first use
- [ ] **Paragraph length**: every paragraph ≤ 3 sentences — scan each `<p>` tag manually
- [ ] **HTML validity**: count `<div` opens vs `</div>` closes — must match exactly
- [ ] **No motion tags**: zero `</motion.div>` occurrences
- [ ] **No nested anchors**: no `<a>` inside another `<a>`
- [ ] **Diagram labels**: no label text exceeds 6 words
- [ ] **Diagram node count**: each diagram ≤ 8 nodes
- [ ] **Mermaid init block**: present verbatim in both diagrams
- [ ] **No placeholder URLs**: no `example.com`, `TODO`, `localhost`, `placeholder`
- [ ] **Cover image path**: `blog/assets/covers/day-22-feature-flags-model-rollouts.png` referenced
- [ ] **Day 22 in all four locations**: `<title>`, `<h1>`, accent chip, meta line
- [ ] **Series footer text**: `Day 22 of 150 — Feature Flags for Model Rollouts`
- [ ] **Voice check**: first person throughout — no passives like "one might expect"
- [ ] **Analogy check**: each major section has exactly one physical/everyday analogy
- [ ] **"So what" check**: every section ends with a "so what" sentence
- [ ] **pre-push-check.sh**: `bash -e .agent/pre-push-check.sh blog/series/ai-learning/day-22-feature-flags-model-rollouts.html` exits 0
