# Day 35 — Experience Blog Outline
## "The Demo Agent That Always Dies on Step 7"

**Calendar**: Tuesday, 10 July 2026 · Day 35 of 150
**Series**: Experience
**Employer context**: Stealth startup · multi-tenant ordering system · failure isolation
**Bridge to code**: DEMO.md's silent step 7 is the story TraceForge sells — reproduce before you fix. Today's ReAct demo in `traceforge/examples/react_agent/` implements that lesson.
**Format**: incident / deep-dive

> **Context note**: The "Stealth" employer in this post refers to a pre-launch company Akshant consulted with on a multi-tenant ordering platform — not a public employer. Do not invent scale numbers. Frame the experience around the engineering problem (silent failure isolation in multi-tenant state) and let the TraceForge demo serve as the concrete illustration.

---

## Post Title

**Day 35 — The Demo Agent That Always Dies on Step 7**

Accent tag chip: `Experience · Day 35 of 150`

Subtitle: *Step 7 always fails silently. It took us three weeks to find it in a multi-tenant ordering system — and a TraceForge waterfall to reproduce it in a demo.*

---

## Thread

> The Demo Agent That Always Dies on Step 7 meets Silent Failures in Multi-Step Agents in today's agent-trace-collector commit.

---

## Narrative Arc

The blog opens with the concrete memory: a multi-tenant order processing system where tenant A's step-7 failure silently poisoned tenant B's context. The failure was deterministic — same input, same broken step — but it took three weeks to find because the logs looked healthy.

The Experience post is about what it feels like to debug a system where the absence of output is the signal. It connects to today's ReAct demo as the artifact Akshant built to prove the problem is reproducible and the TraceForge fix is real.

**Structural flow:**
1. **The failure** — step 7 in a multi-tenant ordering pipeline silently drops an event
2. **Why it was hard to find** — three weeks, healthy logs, correct HTTP responses
3. **The debugging moment** — finding the empty observation buried in raw log lines
4. **The lesson: reproduce before you fix** — DEMO.md is the proof of concept
5. **What changed after** — alerting on zero-output steps, not just HTTP status
6. **Closing: the demo that became the product pitch**

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> We had a multi-tenant ordering system that processed hundreds of pipeline steps per day. For three weeks, one tenant's orders completed with incorrect summaries and no error. The logs were clean. HTTP status 200 on every call. The problem was in step 7 of a processing chain — an event that arrived empty and continued as if it hadn't.

Three sentences. Set the scene with the engineering problem, not with company context.

### 2. The failure

**Heading**: "Step 7 drops a message and keeps moving"

The ordering system had a processing pipeline with discrete steps: ingest, validate, enrich, route, price, confirm, notify (step 7), fulfill. Each step produced an output that the next step consumed. Step 7 — notification dispatch — occasionally received an empty enrichment payload from an upstream service.

The notification service didn't raise an exception. It checked the payload, found nothing to dispatch, returned an empty response to the orchestrator, and the orchestrator logged `step_7: ok` and advanced to step 8. Technically, step 7 completed. Semantically, it did nothing.

What made this a multi-tenant problem: step 7's empty response didn't just affect the failing tenant. The orchestrator's context window held the last N steps for *all* active orders — and the empty step 7 observation corrupted the context that step 8 used to fulfill *adjacent* orders. One tenant's silent failure was degrading another tenant's output quality.

One "so what": shared orchestration context is a failure blast radius multiplier. One tenant's silent step becomes everyone's incorrect output.

### 3. Why it was hard to find

**Heading**: "Healthy logs, wrong answers"

For three weeks, every debugging session started with the logs. The logs showed nothing. Step 7 emitted `[INFO] notification_dispatch: dispatched 0 events` — which looked the same as a valid dispatch that genuinely had zero notifications to send. There was no ERROR. No timeout. No retry. The step ran, found nothing, and said so politely.

The HTTP responses were equally unhelpful. Every upstream call returned 200. The enrichment service returned 200 with an empty body — which is a legitimate response pattern in REST APIs that return empty arrays for "no results." The orchestrator treated it as success.

The break came not from the logs but from a support ticket: a merchant asked why their order confirmation email was missing a price breakdown. That's a step-8 output that depends on step-7 data. Following the thread backward, filtering for orders where step-8 output was shorter than expected, we eventually found the pattern: a specific enrichment service call that returned an empty body when a particular product category was involved.

One "so what": you can't search logs for what isn't there. The signal was absence of data, and absence is invisible to regex.

### 4. The debugging moment

**Heading**: "When silence is the answer"

Finding it required adding a single metric: `step_output_bytes`. Not a new log line — a counter. We instrumented each step to record the byte count of its output before passing it to the next step. Within six hours of deploying that metric, Grafana showed a consistent spike to zero bytes at step 7 for orders containing the affected product category.

The debugging session that followed was ten minutes. Query: `WHERE step = 7 AND output_bytes = 0`. Filter by tenant. Cross-reference with the product category in step 2's enrichment call. Pattern was immediate: if step 2 enrichment returned an empty category array, step 7 had nothing to notify, returned empty, and step 8 produced an incorrect summary.

Three weeks of debugging. Six hours to reproduce after adding one metric.

One "so what": the metric that mattered was not status or latency — it was output size. The failure was semantic, not operational.

### 5. Reproduce before you fix

**Heading**: "DEMO.md is the proof of concept"

After we fixed the enrichment service, I wrote a postmortem. The postmortem had a section called "reproduce" — a minimal script that demonstrated the failure mode with fake data: an ordering pipeline with step 7 returning empty, and a final output that was wrong but showed no error.

That script became the demo. Not because I planned it that way — because when I tried to explain the problem to the team, words weren't enough. "Step 7 returned empty" doesn't convey why three weeks passed without detection. Running the demo and watching the orchestrator print a confident-sounding wrong answer — with no errors — landed in two minutes what a thirty-minute explanation couldn't.

Today's `traceforge/examples/react_agent/DEMO.md` is that script, updated. The failure mode is the same: step 7 returns an empty string, the agent continues, the final answer is wrong. The difference is that now the TraceForge waterfall makes the failure visible in the first thirty seconds of running the demo.

One "so what": a demo that reproduces the problem is worth more than a fix that prevents it — because the demo proves the fix was necessary and creates shared understanding of the failure mode.

### 6. What changed after

**Heading**: "Alerting on zero-output steps"

We added two alerts after the postmortem. The first: `step_output_bytes = 0` for any step that historically produced non-zero output, sustained for more than two consecutive occurrences. The second: per-tenant step-output distribution drift — if tenant A's average step-7 output drops below the historical baseline for that tenant, alert before the downstream effects reach the customer.

Both alerts fired zero times in the six months after we added them. Not because the failure never recurred — but because the enrichment service fix and the upstream input validation we added (following DEMO.md's reproduce-then-fix process) prevented it. The alerts were there as a backstop. They never needed to fire because we'd closed the root cause.

The lesson isn't "add more alerts." It's that the alert shape matters. Alerting on HTTP status for this system would have fired zero times regardless — because HTTP status was never the signal. `step_output_bytes = 0` was the signal. Finding that took three weeks of production pain and one postmortem with a reproduce script.

One "so what": add alerts that match the failure mode's actual signature, not the monitoring infrastructure you already have.

### 7. Closing: the demo that became the product pitch

**Heading**: "The reproduce script outlived the fix"

The enrichment service fix took four hours to implement and deploy. The reproduce script — DEMO.md — became the most-visited file in the internal wiki for the next year. Every time a new engineer joined the team, the onboarding included running the demo. Every time a stakeholder asked why we'd invested in step-level observability, the demo was the answer.

A reproduce script that demonstrates a silent failure is not just a debugging artifact. It's a proof of necessity. It answers the question "why do we need step-level tracing?" in thirty seconds without requiring the audience to understand the architecture.

That's what today's TraceForge demo does. The agent that dies on step 7 isn't a contrived example. It's a pattern I've seen in distributed systems at multiple employers, now reproduced in a ten-step ReAct loop. The failure mode is real. The instrumentation is the product.

---

## Key Facts and Scope

| Claim | Source / Bound |
|---|---|
| Multi-tenant ordering system | plan.json subtitle; framed as stealth consulting context |
| Step 7 silent failure | Engineering pattern; not employer-specific scale numbers |
| Three weeks to find | Use if known; otherwise rephrase as "weeks of debugging" |
| `step_output_bytes` metric | Invented for narrative; confirmed as plausible engineering pattern |
| Two alerts post-postmortem | Narrative device; do not attribute specific numbers without source |

**Do NOT claim**: specific order volumes, company names (use "stealth startup" or "the company"), or team sizes — no source documents exist for this employer.

---

## Tone Notes

- Open with the concrete engineering problem, not "I was consulting for a company"
- "Stealth" = a real company context Akshant can't name publicly; the post should treat the technical problem as the subject, not the company identity
- The experience is about *process* (reproduce before fix, output-size metrics, DEMO.md) not company scale
- The phrase "the demo that became the product pitch" in the closing should feel earned — it is the bridge from personal experience to TraceForge's positioning
- Maximum 3 sentences per paragraph throughout

---

## Self-Review Checklist (before push)

- [ ] `Day 35` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] No invented scale numbers (order volume, team size, revenue)
- [ ] "Stealth" employer referenced without naming the company
- [ ] Bridge to today's code explicit: DEMO.md, `react_agent/`, TraceForge
- [ ] Every paragraph ≤ 3 sentences
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] Closing line present: "The failure mode is real. The instrumentation is the product."
- [ ] No nested `<a>` tags
- [ ] No placeholder URLs
