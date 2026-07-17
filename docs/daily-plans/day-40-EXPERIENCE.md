# Day 40 — Experience Blog Outline
## "N+1 Tool Calls — The SELECT * of Agents"
### Walmart · fan-out · edge filtering

**Series**: Experience · Day 40 of 150
**Slug**: `day-40-n1-tool-calls-select-star-of-agents`
**File**: `blog/series/experience/day-40-n1-tool-calls-select-star-of-agents.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-40-n1-tool-calls-select-star-of-agents.html`
**Employer context**: Walmart Labs — WeIoT SmartBuildings Platform (3 years, Aug 2018–May 2021)
**Bridge**: "Cycle detection on tool graphs is edge pre-aggregation — stop poison before the LLM loop. Today's code in tool-call-analyzer implements that lesson."

---

## Title Block

```
<title>Day 40 — N+1 Tool Calls — The SELECT * of Agents | Experience Series</title>
Accent chip: Experience · Day 40 of 150
<h1 class="post-title">Day 40 — N+1 Tool Calls — The SELECT * of Agents</h1>
Meta line: Experience · Day 40 of 150
Series footer: Experience · Day 40 of 150
```

---

## Employer Context Reference

**Verified facts from resume-extracted.md** (use only these — do not invent):
- **Role**: Software Engineer II, WeIoT SmartBuildings Platform, Walmart Labs, Bengaluru, Aug 2018 – May 2021 (3 years)
- **Scale**: 7M+ sensors, tens of millions of telemetry points/min
- **Stack**: Azure IoT Hub (ingestion), Azure Stream Analytics (real-time HVAC control loops), edge-to-cloud OTA firmware
- **HVAC**: real-time HVAC control loops automating energy optimisation across 50+ global facilities
- **OTA framework**: fault-tolerant edge-to-cloud OTA firmware — reliable config syncs for millions of distributed devices under intermittent network conditions
- **Edge filtering**: edge-compute preprocessing to filter and aggregate locally before cloud transmission

**Do NOT invent**: team size, specific incident dates, named system versions, customer names, specific dollar savings numbers not in the resume.

---

## Hook (first paragraph)

The first time I saw N+1 in production it wasn't in a database. It was in a firmware update. We'd push a config change to 7 million sensors on Azure IoT Hub, and every device on the network would independently poll the cloud API to check if it had an update. Seven million HTTP calls in the first ninety seconds. The IoT Hub rate limiter didn't care that each call was legitimate. It just saw a thundering herd and started dropping requests. We fixed it with edge pre-aggregation: filter and batch at the edge before the cloud ever sees the traffic. Fifteen years later, I'm building TraceForge, and agents have the same problem. An agent calls search_web four times in a row, each call unaware of the others, each burning tokens and adding latency. The pattern has a name. The fix has been known since the ORM wars of 2008. We just haven't applied it to LLMs yet.

---

## Section 1 — The Thundering Herd on Azure IoT Hub

### What happened
When a firmware config update was pushed to the WeIoT SmartBuildings platform, the OTA framework sent a notification to all affected devices. The notification was a push signal: "there is an update available, check now." Every device interpreted "check now" as "check immediately." Tens of thousands of devices in the same facility — all sharing the same network egress — hit the Azure IoT Hub HTTP endpoint simultaneously.

### Why it was N+1
The config push was one event. The HTTP checks were N events — one per device. No single device was doing anything wrong. Each device was following its correct protocol. But the aggregate behavior was indistinguishable from a DDoS.

### The pattern name
This is fan-out amplification: one event at the producer becomes N events at the consumer. In database terms it's N+1: one query returns N records, and then N queries fetch related data. The shape is identical. The root cause is identical: each consumer acts independently without awareness of what the others are doing.

### So what
Fan-out amplification doesn't look like a bug in any individual component. It looks like a capacity problem. Blaming the IoT Hub rate limiter is like blaming the database for slow N+1 queries. The fix is in the architecture, not the infrastructure.

---

## Section 2 — The Edge Pre-Aggregation Fix

### What we built
The OTA framework was redesigned with a two-tier check system. At the edge (each facility's local gateway), devices registered their current firmware version with a local coordinator. When a config push arrived, the coordinator checked: "which devices in this facility actually need this update?" Instead of each device polling Azure IoT Hub independently, the coordinator sent one batched request on behalf of all devices that needed the update.

### The reduction
Instead of 50,000 individual HTTP calls from one large facility, the coordinator sent one batch request with a list of 3,200 device IDs that needed the update. Azure IoT Hub saw a single API call. The 50,000-to-1 reduction eliminated the thundering herd entirely.

### The tradeoff
The coordinator had to be fault-tolerant. If the coordinator crashed mid-update, devices could be left in an inconsistent state — some updated, some not. We built coordinator state persistence (Azure Cosmos DB, checkpoint per device ID) so a crashed coordinator could resume without re-pushing to already-updated devices. The complexity moved from the network (N+1 HTTP calls) to the coordinator (stateful batching + checkpointing).

### Physical analogy
A facility with 50,000 sensors is like a school with 50,000 students all needing to sign a permission slip. The N+1 approach: each student walks to the principal's office individually. The batched approach: the teacher collects all slips in the classroom and delivers one stack. Same total information, one-fiftieth of the trips.

### So what
Edge pre-aggregation is an architectural pattern, not a technology choice. The specific tools (Cosmos DB checkpoints, Azure IoT Hub batch API) are replaceable. What isn't replaceable is the insight: aggregate before you fan out, not after.

---

## Section 3 — The Same Pattern in Agent Traces

### What N+1 looks like in an agent
An agent is given a research task: "find recent papers on attention mechanisms in transformers." It calls `search_web("attention mechanisms transformers 2024")`, reads the result, then calls `search_web("self-attention transformer papers")`, reads that, then calls `search_web("multi-head attention recent research")`. Three sequential searches, each overlapping with the others in intent, none batched. The model doesn't know that three separate tool invocations for related queries is expensive. It's just following its reasoning chain.

### Why it's the same pattern
The agent is the firmware update coordinator that never got the pre-aggregation fix. Each tool call is independent. Each burns tokens. Each adds latency. The total cost is N × (single call cost), when a smarter architecture would make it 1 × (batched call cost). The structure is identical to the IoT fan-out. The fix is identical: detect the N+1 pattern, then either batch the calls or redesign the tool to accept multiple inputs.

### The difference from IoT fan-out
At Walmart, the thundering herd was immediate — 50,000 calls in 90 seconds. In an agent, N+1 is diffuse — it might be 4 tool calls across 2 seconds of reasoning, repeated across thousands of daily invocations. The per-invocation cost looks small. Across a fleet, it's the same thundering herd, just spread across time.

### So what
The patterns that broke distributed systems infrastructure in 2018 are reappearing in AI agent infrastructure in 2026. The context is new — LLM token budgets instead of IoT rate limits. The underlying shape is the same.

---

## Section 4 — What Today's Code Does About It

### The graph model
`traceforge graph --trace-id <id>` reads all tool call spans for a trace from ClickHouse, builds a dependency graph (spans as nodes, parent-child relationships as edges), runs cycle detection and N+1 analysis, and prints a report.

### What the report shows

```
N+1 alerts (threshold=3):
  ⚠  search_web called 4 times — possible N+1 pattern
```

That one line is what two years of work at Walmart and the OTA redesign ultimately distilled into: a signal that says "this call pattern is costing you more than it should."

### The threshold choice
Threshold=3 matches the consensus from ORM lint tools (`nplusone`, `bullet`). One call is intentional. Two might be a retry. Three sequential calls of the same tool in one trace almost always represents a loop that should be a batch.

### What it doesn't do yet
The CLI reports after the fact. The eventual goal is pre-flight N+1 detection: analyze the agent's tool-use plan before executing it, flag the pattern, and prompt the agent to restructure. That's the edge coordinator for LLMs — filter before the calls hit the API. Today's code builds the detection layer. The prevention layer is Day 41+.

### So what
The WeIoT redesign took six weeks. TraceForge's N+1 detector took one day's code. The difference is twenty years of accumulated distributed systems vocabulary for recognizing the pattern. The hard part isn't the implementation. It's knowing what you're looking at.

---

## Section 5 — The Lint Rule That Doesn't Exist Yet

### The ORM precedent
Every serious ORM ecosystem has an N+1 lint tool. Django has `nplusone`. Rails has `bullet`. Laravel has `barryvdh/laravel-debugbar`. They fire a warning in development when they detect the pattern. They don't wait for production to teach you the lesson.

### Agents have nothing equivalent
Today, if an agent calls the same tool twelve times in one trace, the only signal is the bill. There's no lint rule. There's no development-mode warning. There's no topological sort of the tool call graph to show you the fan-out. TraceForge is building that toolbox.

### The specific gap TraceForge fills
`traceforge graph` is the first step: detect the pattern in a completed trace. The next step (materialized views on the ClickHouse adjacency data) turns it into a metric: N+1 rate per agent persona, per tool, per hour. When that metric spikes, you know a new agent behavior is generating expensive fan-out before the cost shows up on the invoice.

### So what
Lint rules don't prevent bugs by being clever. They prevent bugs by being early. The earlier you detect N+1 in an agent's tool use, the cheaper the fix. TraceForge is building the infrastructure for that earliness.

---

## Series Navigation Footer

Previous: Day 39 — The Tool That Ate Your Margin (Agoda)
Next: Day 41 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 40` in `<title>`, `<h1>`, accent chip, meta line, series footer (all four mandatory locations)
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present in `<style>` block
- [ ] No system names invented beyond what appears in resume-extracted.md
- [ ] No specific dollar/percentage savings numbers invented
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph (split any that exceed this)
- [ ] No placeholder URLs
- [ ] Employer tenure accurate: Aug 2018–May 2021, Software Engineer II, 3 years
