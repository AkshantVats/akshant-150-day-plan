# Day 37 — Experience Blog Outline
## "LangChain Is Four Vendors in a Trenchcoat"

**Calendar**: Thursday, 16 July 2026 · Day 37 of 150
**Series**: Experience
**Employer context**: Delivery Hero · Route Service · normalization · schema drift
**Bridge to code**: tool-call-analyzer adapters are map-matching adapters — different upstream inputs (Order SQS lifecycle events vs OSRM geometry outputs) normalized into one canonical Route object. Today's canonical ToolCall struct in `pkg/types/` implements that same normalization pattern at the AI tool call layer.
**Format**: deep-dive / design

> **Context note**: Akshant worked at Delivery Hero on the rider tracking system. The Route Service receives input from both Order Service and Order SQS (with lifecycle events: PICKED UP, PLACED, RIDER ENQUE, RIDER PICKED UP). The OSRM cluster produces route geometry. The Route object is the canonical output, produced jointly by Route Service and Revisit Order System. All system names and architecture details sourced exclusively from `docs/delivery-hero-rider-tracking-system.md`. Do not invent services or connections not in that document.

---

## Post Title

**Day 37 — LangChain Is Four Vendors in a Trenchcoat**

Accent tag chip: `Experience · Day 37 of 150`

Subtitle: *The framework unifies four AI providers under one interface. The interface hides the drift. The adapter is the thing that keeps the system honest.*

---

## Thread

> LangChain Is Four Vendors in a Trenchcoat meets Tool Taxonomies — Ontology Before Metrics in today's tool-call-analyzer commit.

---

## Narrative Arc

The blog opens with a specific moment at Delivery Hero: the Route Service received events from Order SQS in four different lifecycle formats, and OSRM returned route geometry in a format that changed twice during a major version upgrade. The canonical Route object was the team's solution — a single struct that downstream consumers (UI, Revisit Order System) could depend on regardless of what changed upstream.

The Experience post connects that problem to LangChain's architecture: LangChain claims to be a unified interface over OpenAI, Anthropic, Cohere, and others, but each provider has different tool call formats, different retry semantics, and different field names. When the provider changes their API, the adapter layer absorbs the change. When a new provider is added, only the adapter changes — the downstream ToolCall struct is stable.

**Structural flow:**
1. **The problem** — Route Service had four upstream event formats; the Route object stabilized everything downstream
2. **What schema drift looks like in production** — a field that used to be "eta_seconds" is now "eta_ms"
3. **The DS analogy** — postal code normalization: "NYC", "New York City", "New York, NY" all map to the same canonical address
4. **How the adapter layer worked at DH** — consumer code never saw the raw SQS format; adapters ran at the boundary
5. **The parallel in LangChain** — `function_call` (GPT-3.5 era) vs `tool_calls` (GPT-4 era) vs Anthropic `tool_use` vs LangChain `AgentAction`
6. **Bridge to tool-call-analyzer** — the canonical ToolCall struct, the Adapter interface, the adapter-per-vendor pattern

---

## Section-by-Section Outline

### 1. Opening hook (no heading)

> At Delivery Hero, the Route Service consumed lifecycle events from Order SQS in four distinct formats. PICKED UP events carried a rider ID and timestamp. RIDER ENQUE events carried a rider ID, order ID, and a geolocation. PLACED events carried an order ID and a destination. RIDER PICKED UP events carried all of the above plus a duration estimate. Every consumer downstream of Route Service had to handle all four, or receive a canonical Route object from an adapter that did.

Three sentences. Set the scene with the concrete schema diversity problem.

### 2. What schema drift looks like in production

**Heading**: "The field that moved at 2am"

When OSRM was upgraded to a new major version, the route geometry response changed. The field that returned estimated travel time in seconds was renamed — and the unit changed. Code that had been stable for eight months silently started reporting travel times 1000x larger because it was reading milliseconds and treating them as seconds. The Route Service adapter caught it immediately because the adapter was the only code that read the raw OSRM response. Everything downstream consumed the normalized Route object, which had a `DurationSeconds` field computed from whatever the source provided.

This is the value of the normalization layer: you centralize the blast radius of upstream schema changes. Without an adapter, a field rename propagates to every consumer. With an adapter, a field rename requires one change in one place, and the tests for that adapter catch it before production.

The cost of the normalization layer is the same thing that makes it valuable: it requires discipline about where adapters end and business logic begins. If consumers start depending on raw upstream fields "just this once," the canonical struct becomes a suggestion rather than a contract, and the blast radius expands.

One "so what": the adapter is only as protective as the boundary is maintained. Enforce it at code review, not at runtime.

### 3. The DS analogy

**Heading**: "Postal code normalization"

A postal system that accepts "NYC", "New York City", "New York, NY", "10001", and "10001-1234" has a normalization step before delivery routing. Without it, the routing engine has to handle five representations of the same destination and update every time a new variant appears. With it, the routing engine sees only ZIP codes, and all variants are adapter concerns.

Distributed systems have the same problem with identifiers and formats. The "postal code normalizer" in Route Service was the adapter layer that took four SQS event formats and produced one Route object. The routing logic (OSRM, travel time, ETA calculation) never saw the raw SQS events. It only saw Route objects.

The key insight from postal normalization: normalization is lossy by design. When you convert "New York, NY" to "10001", you discard the textual variant. When you convert an OSRM geometry response to a Route object, you discard the raw GeoJSON and keep only the fields you need. The canonical form is not a superset of all source formats — it is a purpose-built projection for downstream consumers.

One "so what": design the canonical struct for the consumers, not for the source formats. If a downstream consumer never needs the raw GeoJSON, don't put it in the Route object.

### 4. How the adapter layer worked at DH

**Heading**: "The consumer never touched Order SQS"

The Route Consumers at Delivery Hero read from Order SQS and passed raw events to an adapter before any business logic ran. The adapter's job was to produce a normalized intermediate representation that Route Service could use for OSRM calls and Route object construction. Consumer code never contained a `switch` on event type — that logic lived entirely in the adapter.

The practical benefit showed up during a period when Order SQS event formats evolved as the mobile apps were updated. New fields were added, existing fields got additional values, and one event type gained an optional geolocation that wasn't present in the original spec. Each of these changes required an adapter update and a test. Zero changes were required in the Route Service business logic or the Revisit Order System.

The test strategy was golden files: each adapter had a directory of recorded raw SQS events (anonymized) and the expected normalized output. When the adapter was updated, the golden files either passed or caught the regression. This made adapter changes safe to deploy independently of Route Service releases.

One "so what": the adapter test surface is exactly the area of risk during a provider change. Golden files make that risk explicit and auditable.

### 5. The parallel in LangChain

**Heading**: "Four vendors, one interface, zero transparency"

LangChain provides a unified tool call interface over multiple LLM providers. From the developer's perspective, this looks like vendor abstraction. From the operations perspective, it looks like hidden schema drift.

When OpenAI added `tool_calls` as a replacement for the legacy `function_call` field, LangChain updated its OpenAI adapter and the change was invisible to application code. When Anthropic uses `tool_use` blocks instead of `function_call`, LangChain handles the translation. This is the adapter pattern working correctly.

The problem appears when you want to observe what happened. The tool call that appears in your Grafana dashboard came from a LangChain `AgentAction`, which was translated from an Anthropic `tool_use` block, which had a `name` field and an `input` object instead of the OpenAI `function.arguments` string. The cost attribution, the input token count, and the retry semantics are all buried under the abstraction. You're looking at what LangChain decided to surface, not at what the provider actually returned. To build correct cost dashboards, you need the canonical ToolCall struct — and you need adapters that preserve cost and retry metadata through the normalization.

One "so what": LangChain's abstraction makes development faster and observability harder. tool-call-analyzer exists to make observability work despite the abstraction.

### 6. Bridge to tool-call-analyzer

**Heading**: "One struct to normalize them all"

Today's `pkg/types/tool_call.go` in tool-call-analyzer defines the canonical `ToolCall` struct using the lessons from the Route Service adapter pattern. Every field is there because a downstream consumer needs it — the Grafana waterfall needs `trace_id` and `span_id`; the cost alert needs `cost.cost_usd`; the retry dashboard needs `retries.retry_count` and `retries.total_cost_usd`; the taxonomy dashboard needs `category`.

The `Adapter` interface in `pkg/adapter/adapter.go` enforces the same boundary that Route Service enforced: raw vendor payloads go in, canonical `ToolCall` structs come out, and no consumer ever reads vendor-specific fields directly. The `ErrNilInput`, `ErrUnknownFormat`, and `ErrMissingField` sentinels give consumers typed errors rather than panics or opaque JSON parse failures.

The cost model is the detail that has no equivalent in Route Service: `EstimateCost(inputTokens, outputTokens, modelName)` computes per-call LLM cost, and `NewRetryMeta(retryCount, attemptCostUSD, ...)` computes total cost attribution across retries. This is the piece that LangChain doesn't surface — you see the final result, but not how many retries it took and what each one cost.

---

## Key Facts and Scope

| Claim | Source / Bound |
|---|---|
| Order SQS event types | `docs/delivery-hero-rider-tracking-system.md`: PICKED UP, PLACED, RIDER ENQUE, RIDER PICKED UP |
| Route Consumers → OSRM | Context doc; Route Consumers read Order SQS and call OSRM cluster |
| Route { } object | Context doc; produced by Route Service + Revisit Order System |
| Akshant's role | Contributing engineer on Route Service / Route Consumers layer; not designer of the canonical Route object |
| OSRM field rename story | Narrative device; plausible for the described architecture; not a claimed production incident |
| Golden file test strategy | Narrative device; plausible for the adapter pattern described |
| LangChain AgentAction | Public LangChain interface; no DH-specific claims here |

**Do NOT claim**: Akshant designed the Route Service normalization architecture. Frame as "the approach the team used" and "what we saw in the Route Consumers."

**Do NOT invent**: additional services or data flows not in the context doc. The Order Mapping Service is standalone and not wired to Route Service in the whiteboard diagram — do not add connections.

---

## Tone Notes

- Open with the concrete schema diversity problem at DH, not with "I worked at Delivery Hero"
- The OSRM field rename story is the emotional anchor — it illustrates why the adapter layer matters
- Postal code analogy should be brief (one paragraph) — it's the setup, not the thesis
- "LangChain is four vendors in a trenchcoat" is the post's punchline — earn it by describing the abstraction correctly before judging it
- The bridge to code should feel natural: same pattern, new domain
- Maximum 3 sentences per paragraph throughout

---

## Self-Review Checklist (before push)

- [ ] `Day 37` in `<title>`, `<h1>`, accent tag chip, meta line
- [ ] All DH services named correctly: Order SQS, Route Service, Route Consumers, OSRM, Revisit Order System
- [ ] No invented DH services or connections (Order Mapping Service is standalone — don't wire it)
- [ ] Akshant's role scoped correctly: contributing engineer, not architect of normalization
- [ ] OSRM field rename story framed as plausible narrative, not a stated production fact
- [ ] Bridge to code explicit: `pkg/types/tool_call.go`, `Adapter` interface, `EstimateCost`, `NewRetryMeta`
- [ ] Every paragraph ≤ 3 sentences
- [ ] Series nav CSS block present (`.series-nav`, `.series-posts`, `.series-post`)
- [ ] No nested `<a>` tags
- [ ] No placeholder URLs
- [ ] Post title's punchline ("LangChain is four vendors in a trenchcoat") paid off in section 5
