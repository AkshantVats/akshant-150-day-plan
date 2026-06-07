# Day 21 — AI Learning Post Outline
## "Day 21 — Production Reliability for LLM APIs"
### AI Learning · Day 21 of 150

**Series**: AI Learning
**Day**: 21 of 150
**Topic**: Production reliability patterns for LLM API calls — rate limits, provider outages, streaming disconnects
**Hook**: Map every provider error code to exactly one of four actions: retry, circuit break, fallback model, or fail loud.
**DS Analogy**: LLM provider error codes are like HTTP status codes in a service mesh — each code tells you not just what went wrong, but what your service should do next.

**Target blog URL**: `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-21-production-reliability-llm-apis.html`

---

## HTML File Target
`blog/series/ai-learning/day-21-production-reliability-llm-apis.html`

**Title tag**: `Day 21 — Production Reliability for LLM APIs | AI Learning Series`
**Accent chip**: `AI Learning · Day 21 of 150`
**H1**: `Day 21 — Production Reliability for LLM APIs`
**Meta line**: `AI Learning · Day 21 of 150`
**Series footer**: `Day 21 of 150 — Production Reliability for LLM APIs`

---

## Voice Reminders (from CLAUDE.md)
- First person throughout: "I hit this wall when...", "What I didn't expect was..."
- Max 3 sentences per paragraph. Split at 4.
- One concrete analogy per major concept — grounded in physical/everyday objects
- Every section ends with a "so what" sentence
- No bullet lists as substitute for prose

---

## Opening Hook

**Goal**: Ground the distributed systems engineer immediately — make them see this as a familiar pattern in a new domain.

Opening sentence: "I've spent years designing retry logic, circuit breakers, and fallback paths for distributed systems. The first time I wired up a production LLM API, I expected the same engineering vocabulary. What I found was that providers speak the same language — but the consequences of getting the response wrong are different."

**The core frame**: In a microservices mesh, you classify HTTP responses into three buckets: retry (5xx), don't retry (4xx), circuit break (sustained 5xx). LLM providers add a fourth category that doesn't exist in traditional HTTP services: **fail loud** — the request is fundamentally unsound, and retrying or falling back won't help. The user must fix their prompt.

**Why this matters**: A retry loop on a `context_length_exceeded` error will waste your entire rate limit budget retrying a request that will fail every time. A circuit breaker that fires on a 400 will block all traffic because of one badly formed prompt. Getting the classification wrong doesn't just affect this request — it affects every request behind it.

**Concrete analogy**: Think of LLM providers as post offices with different counters. The "retry" counter is the one that's temporarily closed — come back in 30 seconds. The "circuit break" counter is the one where the whole building has a power outage — stop sending for five minutes. The "fallback" counter is the express window — slower service, but it's open. The "fail loud" counter is the one where you've brought an oversized package — no counter can help you; you need to repack it first.

---

## Section 1 — The Error Classification Framework

**Purpose**: Give the reader the mental model up front before diving into each category.

**Key points**:
- Every LLM provider error maps to exactly one of four responses: **retry**, **circuit break**, **fallback**, **fail loud**. The mapping is not based on HTTP status codes alone — it requires reading the error type and message.
- **Retry**: the request is valid; the system is temporarily unavailable or overloaded. Retry with exponential backoff + jitter. The request will eventually succeed.
- **Circuit break**: the provider is experiencing a sustained outage or degradation. Stop sending requests for a defined window. Resume after the window and probe with a single request before fully reopening.
- **Fallback**: the primary provider or model is unavailable, but a secondary provider or model can serve this request. Switch traffic; log the degradation.
- **Fail loud**: the request itself is broken — too many tokens, invalid parameters, content policy violation, authentication failure. No amount of retrying or rerouting will fix it. Return an error to the caller immediately.

**What I didn't expect**: the boundary between "retry" and "circuit break" is time-based, not error-based. The same 429 error code means "retry" if it's a one-off and "circuit break" if it's happened 10 times in 60 seconds. You need a sliding window counter per provider endpoint to make this distinction correctly.

**Concrete analogy**: A doctor's triage system. The classification framework is triage — you're not treating the patient yet, you're deciding which door they walk through. Retry = waiting room. Circuit break = come back tomorrow, the ER is full. Fallback = different clinic. Fail loud = this is the wrong hospital; you need a specialist.

**So what**: The classification must happen before any retry or fallback logic runs — it is the precondition for everything else.

---

## Section 2 — Rate Limit Errors (429): The Retry Class

**Purpose**: Cover the most common LLM reliability issue in production — rate limits.

**Key points**:
- Provider rate limits come in two flavors: **requests per minute (RPM)** and **tokens per minute (TPM)**. RPM limits fire when you send too many requests regardless of size. TPM limits fire when the aggregate tokens in your requests exceeds the tier cap.
- A 429 with `error.type = "rate_limit_error"` always means retry. The question is: how long to wait? OpenAI and Anthropic both return a `Retry-After` header when the limit is quota-based. Use it. Do not hardcode a backoff — read the header.
- When `Retry-After` is absent (some providers omit it on TPM limits), use exponential backoff with jitter: `wait = min(base * 2^attempt, cap) + random(0, base)`. Base: 1s. Cap: 60s. Jitter prevents the thundering herd problem when many concurrent requests all hit the rate limit simultaneously and retry at the same interval.
- Token-per-minute limits require per-request token estimation before sending. Approximate with `len(prompt_text) / 4` (rough chars-to-tokens ratio for English). If your estimate would exhaust the remaining TPM budget in the current window, queue the request instead of sending it.

**What I didn't expect**: token estimation drift. At the start of a request batch, your estimated token count and the actual count are close. After 100 requests, rounding errors compound. The provider's actual token consumption diverges from your estimate by 5–8%. I now use a leaky-bucket rate limiter with a conservative 10% headroom on the TPM budget — better to underuse your quota than to hit limits in the middle of a user-facing operation.

**Concrete analogy**: A power meter with a soft cap. Your electricity provider doesn't cut your power instantly when you exceed your plan limit — they let you run over briefly, then throttle. LLM TPM limits work the same way: you get brief bursts above the cap, then a 429 tells you to slow down. The correct response is to slow down, not to retry at full speed.

**So what**: Rate limit retries require both a backoff strategy and a token budget model — one without the other will either waste time or exhaust your quota.

---

## Section 3 — Provider Outages: The Circuit Break Class

**Purpose**: Distinguish circuit breaking from retrying — two patterns that look similar but solve different problems.

**Key points**:
- A circuit breaker exists for one reason: to stop amplifying a provider's problem into your own. When a provider is experiencing a sustained outage, each retry you send is a request that will fail, occupy a connection slot, and delay your caller. The circuit breaker cuts this amplification loop.
- The three states of a circuit breaker: **closed** (normal operation, requests pass through), **open** (failure threshold crossed, all requests fail fast without hitting the provider), **half-open** (probe state: send one request to check if the provider has recovered).
- Threshold configuration for LLM providers: open the circuit after 5 consecutive 5xx errors OR a 50% failure rate over a 60-second rolling window, whichever comes first. Wait 30 seconds in open state before moving to half-open. Require 2 consecutive successes to close.
- Provider outage signals: HTTP 500, 502, 503; connection timeouts exceeding 30 seconds; responses with `error.type = "server_error"` or `"overloaded_error"`. A `"rate_limit_error"` is NOT an outage signal — it's a capacity signal.

**What I didn't expect**: half-open state is where most circuit breaker implementations get hurt. The half-open probe fires one request. If that request happens to hit a still-degraded provider and takes 30 seconds to time out, the probe blocks the circuit breaker state machine for 30 seconds. The fix: the half-open probe must have an aggressive timeout (3 seconds, not 30) — if it doesn't get a fast healthy response, it's not ready.

**Concrete analogy**: A fuse in an electrical system. When the load exceeds safe limits, the fuse blows to protect downstream components. You don't keep plugging things in while the fuse is blown — you wait, then reset, then plug in one thing at a time to check the circuit. A circuit breaker for LLM providers is the software equivalent: blow, wait, probe with one request, then restore.

**So what**: Circuit breaking is not a retry with a longer delay — it is a different state machine that requires its own timeout, threshold, and probe logic.

---

## Section 4 — Streaming Disconnects: The Reconnect Class

**Purpose**: Address the specific challenge of streaming LLM responses — partial responses that must be handled differently from complete request failures.

**Key points**:
- Most modern LLM APIs return responses as server-sent events (SSE): a stream of `data: {"delta": {"content": "..."}}` chunks. The stream can disconnect mid-response for network reasons unrelated to the provider's health.
- A mid-stream disconnect is not a provider error — it is a transport error. The provider may have successfully generated 60% of the response. The retry decision depends on whether the response is resumable.
- Most LLM providers do not support resume-from-offset. If the stream disconnects mid-response, you must restart the entire request. This is expensive for long-generation tasks (e.g., 2,000-token code generation). The mitigation is to checkpoint the partial response.
- Checkpoint pattern: as each `delta` arrives, append to an in-memory buffer. On disconnect, log the partial response and the last received position. If the caller accepts partial responses (e.g., streaming to a user in a UI), deliver what you have and surface the disconnect cleanly. If the caller requires a complete response, restart the full request.

**What I didn't expect**: streaming disconnects surface a race condition in concurrent request handling. Two goroutines — one reading the stream, one writing the checkpoint — can both see the disconnect simultaneously. If the checkpoint write happens after the stream reader marks the request as failed, the checkpoint is lost. The fix: the checkpoint write must be synchronous inside the stream reader's event loop, not in a concurrent goroutine.

**Concrete analogy**: Recording a phone call where the line drops halfway through. You can't resume from the dropout point — you have to call back. But if you took notes during the call, you know what was already said and can start the second call from where the first left off. Streaming checkpoints are your notes.

**So what**: Streaming disconnects require a distinct handling path from request failures — the partial response is valuable data, not an error to be discarded.

---

## Section 5 — The Decision Tree: Error Code → Action

**Purpose**: Give the reader a concrete, actionable reference for the most common provider error codes.

**This section is implemented as a table in the HTML post — prose introduction, then a decision table.**

**Table: LLM Provider Error Code → Action**

| Error / Signal | HTTP Status | Error Type | Action | Notes |
|---|---|---|---|---|
| Rate limit (RPM/TPM) | 429 | `rate_limit_error` | Retry with backoff | Use `Retry-After` header if present |
| Provider overloaded | 529 (Anthropic) / 503 | `overloaded_error` | Retry 2×, then circuit break | Short window: <3 retries |
| Server error | 500 | `server_error` | Retry 1×, then circuit break | Single retry; escalate to circuit if persistent |
| Bad gateway / timeout | 502 / 504 | — | Circuit break immediately | Infrastructure issue, not transient |
| Context length exceeded | 400 | `context_length_exceeded` | Fail loud | User must shorten prompt |
| Invalid API key | 401 | `authentication_error` | Fail loud | Do not retry; alert ops immediately |
| Content policy violation | 400 | `content_filter` | Fail loud | Request is fundamentally refused |
| Model not found | 404 | `not_found_error` | Fail loud | Wrong model ID; check config |
| Malformed request | 400 | `invalid_request_error` | Fail loud | Bug in request construction |
| Streaming disconnect | — | (transport error) | Checkpoint + restart | Deliver partial if caller accepts |
| Provider offline (multi-region) | — | (connection refused) | Fallback provider | Switch to backup API endpoint |

**Key insight to cover in prose**: the `error.type` field, not the HTTP status code, is the definitive signal. An HTTP 400 covers both "your prompt is too long" (fail loud) and "your JSON payload is malformed" (fail loud, but different fix). An HTTP 503 covers both "we're overloaded" (retry) and "we're doing maintenance" (circuit break for longer). Always read the `error.type` field.

**What I didn't expect**: provider error taxonomy is not standardized. OpenAI and Anthropic use similar structures (`error.type`, `error.message`) but different type strings. A production-grade LLM client library needs a normalization layer that maps provider-specific error codes to your own internal error taxonomy before the retry/circuit-break/fallback decision logic runs.

---

## Section 6 — Putting It Together: A Minimal Reliability Layer

**Purpose**: Show what the full reliability layer looks like in code — brief, concrete, not a full library.

**Key points to cover** (prose, not a code dump):
- The reliability layer has three components that run in sequence: (1) token budget check (before sending), (2) circuit breaker state check (before sending), (3) error classifier (after receiving).
- After the error classifier runs: retry schedules a re-attempt with backoff; circuit-break events increment the breaker counter; fallback switches the provider; fail-loud propagates the error to the caller with a structured message.
- The tracing contract: every request that goes through the reliability layer should emit a span with: provider, model, error_class (retry/circuit/fallback/loud), attempt_number, token_count_estimate. Without this, debugging reliability incidents in production is guesswork.
- The one design invariant: the reliability layer must never swallow a fail-loud error. If `context_length_exceeded` is caught and retried, you will burn your entire rate limit budget in seconds. The error classifier runs before any retry logic, and fail-loud errors exit immediately.

**Concrete analogy**: A mail sorting room with four chutes: retry chute (temporary hold), circuit break chute (hold until facility reopens), fallback chute (redirect to alternate branch), and fail loud chute (return to sender, cannot deliver). Every piece of mail passes through the sorting room first. Nothing bypasses the sorter.

**So what**: The reliability layer's value is not in the retry logic itself — it is in the upfront classification that prevents the wrong logic from running on the wrong error.

---

## Mermaid Diagrams

### Diagram 1 — Error Classification Decision Tree

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
    ERR["Provider Error\nreceived"]
    CLS["Read error.type\nfield"]
    RATE["rate_limit_error\n429"]
    SRV["server_error\noverloaded_error"]
    NET["502/504\nconnection refused"]
    CTX["context_length_exceeded\ncontent_filter\nauth_error"]
    RETRY["RETRY\nbackoff + jitter"]
    CB["CIRCUIT BREAK\nopen breaker"]
    FB["FALLBACK\nswitch provider"]
    LOUD["FAIL LOUD\nreturn to caller"]

    ERR --> CLS
    CLS --> RATE --> RETRY
    CLS --> SRV -->|"< 3 attempts"| RETRY
    SRV -->|"≥ 3 attempts"| CB
    CLS --> NET --> CB
    CB -->|"multi-region?"| FB
    CLS --> CTX --> LOUD
```

### Diagram 2 — Circuit Breaker State Machine

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
stateDiagram-v2
    [*] --> Closed
    Closed --> Open : "5 consecutive 5xx\nor 50% failure rate / 60s"
    Open --> HalfOpen : "wait 30s"
    HalfOpen --> Closed : "2 consecutive successes"
    HalfOpen --> Open : "probe fails\nor times out (3s)"
```

---

## Post Metadata

```json
{
  "slug": "day-21-production-reliability-llm-apis",
  "title": "Day 21 — Production Reliability for LLM APIs",
  "subtitle": "Rate limits, provider outages, streaming disconnects — mapped to patterns you know",
  "series": "ai-learning",
  "day": 21,
  "date": "2026-06-09",
  "tags": ["LLMInfrastructure", "CircuitBreaker", "RateLimiting", "AIInfrastructure", "DistributedSystems", "ProductionReliability"],
  "coverImage": "/blog/assets/covers/day-21-production-reliability-llm-apis.png",
  "url": "/blog/series/ai-learning/day-21-production-reliability-llm-apis.html"
}
```

---

## Format Diversity Check

This post is a **patterns / framework** format — a decision framework with error classification table. Check last 10 posts before writing to verify patterns count < 4 of 10. If patterns count is already 4, shift to a **deep-dive** format focused on the circuit breaker implementation specifically.

---

## Self-Review Checklist (before pushing)

- [ ] `Day 21` appears in `<title>`, `<h1>`, accent chip, meta line, series footer
- [ ] Error classification table has all 10 rows from the outline
- [ ] `error.type` vs HTTP status distinction clearly made in prose
- [ ] Every paragraph ≤ 3 sentences
- [ ] DS analogy present per major concept (post office counters, power meter, fuse, recording phone call, mail sorting room)
- [ ] Every section ends with a "so what" sentence
- [ ] Both Mermaid diagrams have the correct init block
- [ ] stateDiagram-v2 syntax verified (not flowchart for circuit breaker states)
- [ ] No nested `<a>` tags
- [ ] Div open/close count balanced
- [ ] No `</motion.div>` tags
- [ ] Cover image path referenced: `blog/assets/covers/day-21-production-reliability-llm-apis.png`
- [ ] `pre-push-check.sh` exits 0
- [ ] Bridge to Day 21 Experience post (flag change as reliability audit trail) present in series footer
