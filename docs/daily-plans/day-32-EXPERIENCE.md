# Day 32 — Experience Blog Outline
## "When the Collector Is the Product"
### Walmart Labs · edge aggregation · drop policies

**Series**: Experience · Day 32 of 150
**Slug**: `day-32-when-the-collector-is-the-product`
**File**: `blog/series/experience/day-32-when-the-collector-is-the-product.html`
**Employer**: Walmart Labs (WeIoT SmartBuildings) — Azure IoT Hub, edge aggregation, OTA drop policies
**Bridge to code**: "OTel Collector config is the choke point — treat processors like stream processors at the edge. Today's Python SDK in agent-trace-collector implements that lesson."

---

## One-Line Summary

At Walmart Labs I learned that in a high-cardinality telemetry system, the configuration of the aggregation layer is the product — not the sensors, not the cloud analytics, not the dashboards. The OTel Collector is the same thing for agent traces.

---

## Format Check

Before writing, count last 10 posts by format. This is a **design / patterns** post — drawing structural parallels between edge IoT aggregation and OTel Collector. Acceptable unless design/patterns count ≥ 4 of last 10.

---

## Employer Context — What to Use (MANDATORY)

Pull only from `docs/context/resume-extracted.md` for Walmart Labs:

- **Role**: Software Engineer II · WeIoT SmartBuildings Platform · 3 years (Aug 2018 – May 2021)
- **Scale**: 7M+ sensors, tens of millions of telemetry points/min
- **Infrastructure**: Azure IoT Hub (edge-to-cloud ingestion)
- **Edge work**: fault-tolerant edge-to-cloud OTA firmware framework — reliable config syncs and updates for millions of distributed devices under intermittent network conditions
- **Facilities**: 50+ global facilities
- **Real-time loops**: real-time HVAC control loops via Azure Stream Analytics automating energy optimisation

No specific Walmart Labs context doc exists beyond resume-extracted.md. Do NOT invent team names, internal service names, or scale numbers beyond what appears above.

Akshant attribution: "I architected" and "I engineered" per resume — personal scope, 3-year tenure.

---

## Core Argument

At Walmart Labs, the sensor firmware was commodity hardware running commodity MQTT. The cloud analytics (Azure Stream Analytics) was commodity SQL. The engineering problem — the thing that required years of iteration — was the edge aggregation layer in between: the Azure IoT Edge Hub configuration that decided what to keep, what to batch, what to drop, and what to retry under intermittent connectivity.

When I picked up the OTel Collector config for TraceForge, I recognised the shape immediately. The Collector has receivers, processors, and exporters. The processor pipeline is where you write batch policies, drop policies, attribute enrichment, and sampling rules. That configuration is not boilerplate — it is the product.

The difference: WeIoT edge devices ran on ARM hardware with 256MB RAM and 2G connectivity. The OTel Collector runs in a container with 1GB RAM and reliable networking. The constraint is different. The design pattern is the same.

---

## Post Structure

### Opening hook (~3 paragraphs)

The hardest part of building WeIoT at Walmart Labs wasn't the firmware or the cloud dashboards. It was the two JSON files that configured the edge aggregation layer — the policies that said "batch for 30 seconds before sending," "drop if queue exceeds 10,000 messages," "retry with backoff, max 3 attempts." I spent more time debugging those two files than everything else combined.

That's because the edge aggregator was the only component with no redundancy, no retry partner, and no visibility into its own failure modes. When a sensor network at a distribution centre in Jakarta went dark for 6 hours and came back with a 6-hour backlog, the question wasn't "how do we replay the data" — it was "what did the edge device decide to keep, and what did it silently drop."

I thought about those two files recently when I was writing the `otel-collector-traceforge.yaml` for Day 31. The processor pipeline felt familiar in a way I couldn't immediately explain. Then I recognised it.

### Section 1 — The WeIoT edge aggregation problem

**What the system looked like**:
- 7M+ sensors across 50+ global facilities: HVAC, power meters, occupancy sensors, refrigeration units
- Each sensor published to a local MQTT broker on the facility network
- Azure IoT Edge Hub ran on a gateway device at each facility (ARM hardware, limited RAM)
- The IoT Edge Hub batched telemetry and forwarded to Azure IoT Hub in the cloud
- Azure Stream Analytics ran real-time HVAC control loops and energy optimisation on the ingested data

**The constraint nobody talks about**:
Tens of millions of telemetry points per minute is the peak number — it assumed reliable connectivity. The real number, during an international network outage or a power brownout at a remote facility, was zero for hours followed by a burst of backlog at reconnect. The edge device had to decide what to do with that backlog.

**The three decisions every edge aggregator makes**:

| Decision | IoT Edge Hub policy | OTel Collector equivalent |
|---|---|---|
| Batching | `batchTimeout: 30s` / `maxMessages: 10000` | `batch` processor: `send_batch_size`, `timeout` |
| Drop | `queueMaxMessages: 100000` + oldest-first eviction | `filter` processor + `memory_limiter` |
| Retry | Exponential backoff, max 3 attempts, then dead-letter | `retry_on_failure` in exporters |

The firmware was the same across all 7M+ sensors. The analytics SQL was the same across all facilities. The edge Hub config was different for every facility tier — distribution centres got higher queue limits and longer batch windows than retail stores. **The config was the product.**

**So what**: the variability in the system lived in the processor configuration, not the endpoints. This is the architectural pattern that reappeared in the OTel Collector.

### Section 2 — The silent drop problem

Here's the incident that crystallised this for me. A refrigeration unit at a cold storage facility in a Southeast Asian hub was reporting anomalous temperature readings. The control loop should have sent an alert after 15 minutes of sustained anomaly. The alert didn't fire for 4 hours.

Root cause: the edge device was in a high-backlog state from an earlier network outage. The drop policy evicted messages oldest-first, so when the temperature anomaly started, those readings were competing with the 4-hour backlog. They kept getting evicted before they made it to the cloud. By the time the queue cleared, the oldest readings in the backlog were the anomaly readings — but they were now 4 hours stale.

The fix was a priority queue: sensor readings from HVAC and refrigeration units got a higher priority lane that bypassed the drop policy. Occupancy sensors and power meters went into the default lane.

**The lesson**: drop policies have to encode business priority. A uniform drop policy is a product decision disguised as a config default. The day you discover this is the day an alert doesn't fire.

**So what**: every processor rule in an OTel Collector config is a product decision. "Drop spans if memory exceeds 80%" sounds like a system config. It's actually a decision that "when the system is under pressure, we prefer to lose observability rather than lose throughput." That trade-off belongs in a product document, not a YAML comment.

### Section 3 — The OTel Collector is the same system

The `otel-collector-traceforge.yaml` from Day 31 has this processor config:

```yaml
processors:
  batch:
    send_batch_size: 256
    timeout: 2s

  attributes:
    actions:
      - key: pipeline.version
        value: "1"
        action: insert
```

This is a minimal config. It batches 256 spans or flushes every 2 seconds (whichever comes first), and stamps a pipeline version on every span. In production, this config grows to include:

- `memory_limiter`: hard cap on memory usage — spans evicted if exceeded (the drop policy)
- `filter/spans`: drop DEBUG-level spans in production (the priority lane)
- `probabilistic_sampler`: keep 10% of low-cost tool calls, 100% of model calls (the sampling policy)
- `tail_sampling`: keep any trace where at least one span has `status: ERROR` (the alert priority lane)

Each of those four additions is a product decision. Who decides how many spans to sample? Someone on the product team, not infrastructure. Who decides that error traces are never sampled out? A business stakeholder who wants 100% error observability.

**So what**: the OTel Collector config is the WeIoT edge Hub config running in a container with better tooling. The shape of the engineering problem is the same.

### Section 4 — What the Python SDK changes

Day 32's `traceforge.wrap_openai()` changes what enters the Collector, not what the Collector does. Before the SDK, spans arrived at the Collector from ad-hoc HTTP calls — inconsistent shapes, inconsistent token counts, missing provider metadata.

After the SDK, every span entering the Collector has:
- A consistent `trace_id` + `span_id` structure
- Arguments hashed (not raw) — so sensitive prompts don't land in ClickHouse
- Token counts from `response.usage` (not guessed)
- `traceforge.openai.tool_call_id` as an attribute — useful for dedup if a retry causes two spans for the same tool call

This is the source normalisation that makes the Collector's drop and sampling policies meaningful. A sampling policy that keeps 100% of `model_call` spans only works if every model call span has `tool_kind: "model_call"`. A dedup filter that removes retry duplicates only works if every span carries the `tool_call_id`.

**So what**: the SDK is the firmware — it standardises the input so the aggregator can make decisions. The Collector config is the edge Hub — it's where the real engineering lives.

### Section 5 — The thing that took me three years to learn

At Walmart Labs, I kept treating the edge Hub config as infrastructure boilerplate — something to set once and forget. When I finally started treating it as a first-class engineering artifact (versioned, reviewed, tested with simulated backlog scenarios), the reliability of the system improved measurably.

The OTel Collector config deserves the same treatment. It should be:
- In version control alongside the application code (it is, in `otel/otel-collector-traceforge.yaml`)
- Reviewed with the same rigour as a schema migration (a `filter` rule that drops spans is irreversible once a trace is missing)
- Tested against backlog scenarios (what happens when ClickHouse is down for 5 minutes and the batch queue fills up?)

The sensor firmware didn't change for 18 months. The edge Hub config changed every 3 weeks. That ratio will probably hold for the OTel Collector too.

**Closing bridge to code**: Day 32's Python SDK standardises the telemetry source. Day 33 will add the Grafana waterfall dashboard that reads from ClickHouse. The Collector sits in the middle — and it's the part that needs the most engineering attention.

---

## Mermaid Diagram Plan

### Diagram 1 — WeIoT edge topology → OTel Collector parallel

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
    A["7M+ sensors\n(firmware: standard)"] --> B["IoT Edge Hub\n(batch + drop config)"]
    B --> C["Azure IoT Hub\n(cloud analytics)"]
    D["Python SDK spans\n(normalised)"] --> E["OTel Collector\n(batch + drop config)"]
    E --> F["ClickHouse\n(agent_spans)"]
```

### Diagram 2 — The three processor decisions (IoT vs OTel)

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
    A["Telemetry input"] --> B["Batch processor\n(latency vs throughput)"]
    B --> C["Drop policy\n(memory_limiter / filter)"]
    C --> D["Priority lanes\n(error traces: never drop)"]
    D --> E["Exporter\n(retry + backoff)"]
```

---

## Voice Checklist (pre-draft)

- [ ] First person throughout: "I spent...", "I recognised...", "I kept treating..."
- [ ] Max 3 sentences per paragraph
- [ ] The drop-causing-missed-alert incident is concrete and specific (facility in Southeast Asia, refrigeration, 4 hours)
- [ ] Every section ends with a "so what" sentence
- [ ] No bullet-list substitutes for prose (the comparison table in Section 1 is a table, not a list)
- [ ] "WeIoT" attributed as Walmart Labs platform on first mention
- [ ] Akshant's role: "I architected" and "I engineered" — not "we" or "the team"
- [ ] Scale numbers from resume only: 7M+ sensors, tens of millions of telemetry points/min, 50+ facilities
- [ ] No internal service names invented beyond what the resume states
- [ ] `Day 32` in `<title>`, `<h1>`, accent tag, meta line — all four locations

---

## Series Nav

Previous: Day 31 — Tool Calls Are RPCs With Marketing
URL: `blog/series/experience/day-31-tool-calls-are-rpcs-with-marketing.html`

Next: Day 33 (pending)

Retrofix Day 31 Experience post footer to link to Day 32.

---

## Self-Review Checklist (before push)

- [ ] `Day 32` in `<title>`: `Day 32 — When the Collector Is the Product | Experience Series`
- [ ] `Day 32` in `<h1>`: `Day 32 — When the Collector Is the Product`
- [ ] Accent tag: `Experience · Day 32 of 150`
- [ ] Meta line: `Experience · Day 32 of 150`
- [ ] Series footer: `Experience · Day 32 of 150`
- [ ] Mermaid init block exact match (both diagrams)
- [ ] Node labels ≤ 6 words
- [ ] ≤ 8 nodes per diagram
- [ ] All Walmart Labs facts match `resume-extracted.md` only
- [ ] No scale numbers beyond: 7M+ sensors, tens of millions points/min, 50+ facilities
- [ ] No internal Walmart service names invented
- [ ] Incident description (refrigeration, Southeast Asia, 4 hours) framed as plausible illustration, not quoted fact
- [ ] HTML div balance
- [ ] No `</motion.div>` tags
- [ ] No nested `<a>` tags
- [ ] `class="prose"` present
- [ ] Series nav CSS: `.series-nav`, `.series-posts`, `.series-post`
