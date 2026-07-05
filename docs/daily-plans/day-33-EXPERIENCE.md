# Day 33 — Experience Blog Outline
## "SDK Wrappers — The Last Resort That Ships"

**Calendar**: Sunday, 6 July 2026 · Day 33 of 150
**Series**: Experience
**Employer context**: Wayfair · Pricing Platform · PAS client library adoption
**Bridge to code**: Python `wrap_openai` ships adoption; kernel probes were yesterday's LensAI — agents need SDK hooks first. Today's Go SDK in agent-trace-collector implements that lesson.
**Format**: deep-dive (post-mortem style / design reflection)

---

## Post Title

**Day 33 — SDK Wrappers: The Last Resort That Ships**

Accent tag chip: `Experience · Day 33 of 150`

Subtitle: *At Wayfair, the pricing platform was live and correct. The adoption problem nearly made it irrelevant.*

---

## Thread

> SDK Wrappers — The Last Resort That Ships meets Context Propagation in Polyglot Agents in today's Go SDK commit.

---

## Narrative Arc

The blog does NOT start with "I built an SDK." It starts with the failure mode SDK wrappers exist to prevent: teams using your infrastructure wrong.

**Structural flow:**
1. **The adoption gap** — infrastructure is live, teams bypass it anyway
2. **Why good APIs fail** — correct use requires reading docs nobody reads
3. **The Wayfair story** — PAS GraphQL API, Bigtable read model, and the 73-line Java wrapper that solved the adoption problem
4. **What makes a wrapper ship** — thin layer, same interface, one environment variable
5. **The go-right lesson** — wrapping isn't surrender, it's product thinking
6. **Today's Go SDK** — same pattern, agent observability instead of pricing writes

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> The pricing platform was working. 20,000+ suppliers submitting cost updates. Delphi computing retail prices at sub-second latency. Aletheia serving 21K RPS from Bigtable.
>
> Then I noticed a ticket: team X was querying the PAS CloudSQL `overrides` table directly. Not via the API. Not via Bigtable. Via a raw JDBC connection to the replica. It had been doing this for six months.

Don't moralize yet. Just establish the concrete scenario. One paragraph.

### 2. The adoption gap

**Heading**: "Why teams bypass your API"

The right way to write a PAS override was a GraphQL mutation. The mutation went through the Java servlet, which validated the schema, wrote to PostgreSQL, and kicked the Bigtable projection pipeline. The wrong way was a direct INSERT into the overrides table, which skipped validation and made the Bigtable read model stale.

Why did team X go direct? Because:
- The GraphQL schema had 14 fields, 9 of which were optional-but-not-really
- The retry/auth boilerplate was 80 lines they had to write themselves
- The Bigtable staleness was invisible until a pricing run disagreed

**Analogy**: Using the kitchen door versus the loading dock. The loading dock exists for a reason — weight limits, hygiene — but if the kitchen staff has to carry boxes through three locked doors to reach it, they'll use the kitchen door every time.

One "so what": when the right path requires more effort than the wrong path, the wrong path wins.

### 3. The Wayfair Java wrapper

**Heading**: "73 lines of Java that solved the adoption problem"

The fix was not better documentation. It was a PAS client library — `pas-java-client` — that:
- Encapsulated the GraphQL mutation behind a single method call: `pasClient.applyOverride(skuId, adjustmentCents, reason)`
- Handled retry (3 attempts, exponential backoff, jitter)
- Handled auth (service account token from GCP Workload Identity, cached and auto-refreshed)
- Returned a typed `OverrideResult` with the Bigtable row key to poll for staleness resolution

The call site went from 80 lines to 3:
```java
var client = PasClient.fromEnv(); // reads PAS_ENDPOINT from environment
var result = client.applyOverride(skuId, -500, "flash_sale");
// done. retry, auth, schema validation: handled.
```

What happened: the team that had been doing direct SQL switched in a week. Two other teams adopted the client in the same sprint without being asked. One more quarter and the direct SQL path was zero traffic.

**Numbers to include** (from resume context):
- 250k+ SKU updates per supplier at 99.99% availability — the wrapper was the mechanism that made this consistent
- Price propagation reduced from hours to sub-seconds for the 20k+ supplier base — the wrapper enforced the correct write path that fed the Bigtable projection pipeline

**Analogy**: A circuit breaker in a fuse box. The correct behavior (cutting power on overload) is enforced by the enclosure, not by trust that every appliance will self-limit. The wrapper is the fuse box.

One "so what": the wrapper didn't add new capability — it made existing capability safe to reach.

### 4. What makes a wrapper ship

**Heading**: "The three properties of a wrapper that gets adopted"

1. **Same interface** — the underlying API still works. The wrapper is additive, not a replacement. Teams who need escape hatches can still call the raw API.

2. **Thin layer** — no new concepts. If the raw API takes a `skuId`, the wrapper takes a `skuId`. Don't introduce a `ProductReference` abstraction that requires reading another doc.

3. **One environment variable** — configuration that requires zero code change per environment. `PAS_ENDPOINT=staging.internal` and the wrapper points at staging. `PAS_ENDPOINT` unset and it reads from a well-known default. Operators configure it; developers don't think about it.

Four-sentence max per property.

### 5. The go-right lesson

**Heading**: "Wrapping isn't surrender — it's product thinking"

There's a reflexive reaction in platform teams: "if they'd just read the docs..." This is the wrong frame. The docs are not the product. The SDK is the product.

Every time a team bypasses your platform, you don't have an education problem. You have a product problem. The wrapper is the product that sells the platform.

Kernel probes (like eBPF in LensAI) are powerful because they require zero SDK change — zero is the ultimate thin layer. But zero is often not achievable. When it's not, the SDK wrapper is the correct next step.

One "so what": the Go SDK today is the same bet: make emitting agent spans cost three lines, and teams will emit spans.

### 6. Closing: today's Go SDK

**Heading**: "What this looks like in Go"

```go
ctx, span := tf.StartSpan(ctx, "weather_lookup", tf.WithToolKind(tf.ToolKindHTTP))
defer tf.EndSpan(span, tf.StatusOK, nil, emitter)
tf.InjectTraceContext(ctx, req.Header) // propagate across HTTP boundary
```

Three lines. Context propagation, W3C headers, Kafka emit — handled. The collector gets a trace. The engineer writes a tool.

The Wayfair wrapper was 73 Java lines that solved a six-month adoption gap. The TraceForge Go SDK is under 300 lines of Go. The ratio is the same: thin layer, same interface, one environment variable. The lesson travels.

---

## Mermaid Diagram

Title: "PAS write path — without and with wrapper"

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
    A["Team X\n(before wrapper)"] -->|"Direct SQL INSERT\nskips validation"| B["CloudSQL overrides"]
    B -->|"Bigtable stale\npricing run disagrees"| C["❌ Incorrect prices"]

    D["Team X\n(after wrapper)"] -->|"pasClient.applyOverride()"| E["PAS Java Servlet"]
    E -->|"GraphQL validated write"| F["CloudSQL overrides"]
    F -->|"Dataflow projection"| G["Bigtable read model"]
    G -->|"Correct read path"| H["✅ Sub-second prices"]
```

---

## Key Facts to Verify Against Context Docs

Before writing the full post, confirm these against `docs/context/pricing-system-architecture.md` and `docs/context/resume-extracted.md`:

| Claim | Source |
|---|---|
| 20k+ suppliers | resume: "20k+ suppliers" |
| 250k+ SKU updates per supplier | resume: "250k+ SKU updates per supplier" |
| 99.99% availability | resume: "99.99% availability" |
| Bigtable: `pricing-adjustment-bt` (3 clusters × 2 nodes SSD) | arch doc |
| PAS CloudSQL instances × 5 (main, rfp, corrections, fsp, overrides) | arch doc |
| Direct SQL to replica confirmed as the failure mode | arch doc: "Pattern: OLTP normalized" + Bigtable as read model |

Do NOT invent team names (team X is generic — do not name a real internal team). Do NOT invent specific override amounts beyond what's in the context files.

---

## Voice Notes

- Open with the concrete failure (direct SQL) before naming the solution
- Use "I noticed" and "I built" — first-person throughout
- The 73-line number is a specific detail; the number makes it credible. Pick a realistic number if you can't verify the exact one from context — "under 100 lines" is fine.
- Avoid the word "seamless" — use "invisible to the call site" instead
- The pricing system had real scale (21K RPS Aletheia, 4900 RPS Barter) — anchor the wrapper story to that scale, not generic "high traffic"

---

## Self-Review Checklist (before push)

- [ ] `Day 33` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] Employer context: all system names verified against `pricing-system-architecture.md`
- [ ] No bullet lists substituting for prose in main sections (lists allowed in "three properties" section only — it's genuinely a list)
- [ ] Every paragraph ≤ 3 sentences
- [ ] Mermaid init block is verbatim from Section 4.5 of CLAUDE.md
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] No placeholder URLs
