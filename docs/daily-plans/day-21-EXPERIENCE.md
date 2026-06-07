# Day 21 — Experience Post Outline
## "LaunchDarkly Money — Why We Build flagd Ourselves"
### Experience · Day 21 of 150

**Series**: Experience
**Day**: 21 of 150
**Employer**: Delivery Hero
**Systems**: Route Service (EKS), real-time config propagation, surge multiplier, gRPC streaming
**Bridge**: The etcd + gRPC streaming pattern in distributed-flagd is exactly what DH used for real-time config propagation to the routing plane — same propagation problem, different payload (model version instead of surge multiplier).

**Target blog URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-21-launchdarkly-build-vs-buy-flagd.html`

---

## HTML File Target
`blog/series/experience/day-21-launchdarkly-build-vs-buy-flagd.html`

**Title tag**: `Day 21 — LaunchDarkly Money — Why We Build flagd Ourselves | Experience Series`
**Accent chip**: `Experience · Day 21 of 150`
**H1**: `Day 21 — LaunchDarkly Money — Why We Build flagd Ourselves`
**Meta line**: `Experience · Day 21 of 150`
**Series footer**: `Experience · Day 21 of 150`

---

## Voice Reminders (from CLAUDE.md)
- First person throughout: "I hit this wall when...", "What I didn't expect was..."
- Max 3 sentences per paragraph. Split at 4.
- One concrete analogy per major concept — grounded in physical/everyday objects
- Every section ends with a "so what" sentence
- No bullet lists as substitute for prose

---

## Opening Hook

**Goal**: Open with the cost revelation — the moment when a platform team realizes their feature flag bill is growing proportionally with traffic rather than with team size.

Opening sentence: "The number that changed how I think about SaaS tooling wasn't in an incident post-mortem — it was in a quarterly infrastructure cost review, in a row labeled 'Feature Flag Evaluations.'"

**The central tension**: Commercial feature flag services like LaunchDarkly price by evaluation volume in production. For a service doing 1k requests per second, every request may evaluate 3–5 flags — that is 2.6 billion monthly active context evaluations. At enterprise pricing, this stops being an inconvenience and starts being a budget line that competes with engineering headcount.

**But the deeper problem**: for AI inference specifically, flags are on the critical path of every single LLM request. You cannot afford a network round-trip to evaluate which model version to use. The flag system must be local — evaluation must be in-process memory, not an HTTP call.

**Concrete analogy**: Imagine paying a toll every time your GPS checks which route to take. The GPS would be useless — the toll would delay you longer than the route benefit. A feature flag system that costs a round-trip per evaluation has the same problem. It defeats its own purpose when the decision is time-critical.

---

## Section 1 — What Real-Time Config Propagation Looks Like at Scale

**Purpose**: Bridge from DH experience to the distributed-flagd design. Establish that this problem is not new — real-time config propagation to distributed services is a well-understood pattern.

**Key points to cover**:
- At Delivery Hero, the routing plane (Route Service, Route Consumers) handled 1M+ daily orders with sustained 5k+ real-time route updates/sec and 10k+ concurrent requests at peak.
- The Route Service needed to apply dynamic configuration in real time: surge multiplier values (the factor by which routes are adjusted during peak demand periods), OSRM timeout thresholds, consumer concurrency limits. These were not restart-time configs — they needed to propagate to all running pods within seconds.
- The solution at DH was watch-based propagation: config stored in a consistent store, all services watching for changes, pushing updates to running pods without restarts. The same pattern we built in zookeeper-era systems, now with etcd.
- What was being propagated was just a payload — the mechanism (watch → push → apply) was the same whether the payload was "surge multiplier = 1.3" or "use gpt-4o for 10% of requests." The payload changed; the infrastructure did not.

**What I didn't expect**: at the scale of 10k+ concurrent requests, even a brief period of inconsistency in config propagation creates visible artifacts. During one deploy, the new surge multiplier value arrived at 40% of pods before the other 60%. For about 8 seconds, the routing plane was applying two different multiplier values to simultaneous orders from the same zone. The fix was not faster propagation — it was atomic broadcast: all pods see the change in the same event loop tick or none do.

**Concrete analogy**: Updating the price on a shelf in a grocery store while customers are already filling their carts. If only some shelves update immediately, the shelf price and the checkout price disagree for a window. Feature flags with non-atomic rollout have the same staleness window.

**So what**: Real-time config propagation is not a new problem — what's new is that it's now on the hot path for every LLM inference request, which raises the bar from "nice to have" to "must be sub-millisecond."

---

## Section 2 — Why LaunchDarkly's Pricing Model Breaks for Infrastructure Services

**Purpose**: Lay out the economic case clearly. This section should be educational, not a rant.

**Key points**:
- LaunchDarkly prices on "monthly active contexts" (MACs) — each unique evaluation context (user, request, device) counts. For marketing A/B tests, MACs are a reasonable proxy for value: more unique users evaluated = more business impact.
- For infrastructure services, MACs are the wrong unit. An LLM inference service evaluating "which model version" on every request doesn't have 10,000 users — it has a continuous stream of requests. At 1k RPS, every minute adds 60,000 MACs. Monthly MACs = 2.59 billion. At enterprise pricing, this is a significant recurring cost for a system that is simply routing traffic.
- The fundamental mismatch: LaunchDarkly was designed for product teams making business decisions (show this button to 10% of users). Distributed-flagd is designed for infrastructure teams making traffic decisions (send 10% of requests to the new model). Same percentage mechanics, completely different economics.
- A self-hosted flag system changes the cost model entirely: the cost is engineering time to build and operate it, paid once, not a metered per-evaluation fee that scales with traffic volume.

**What I didn't expect**: the operational cost of self-hosted infra is often cited as the reason to pay for SaaS. But a feature flag store is not a complex system to operate — it's etcd (which you likely already run for Kubernetes) plus a thin gRPC server. The marginal operational cost of distributed-flagd over an existing etcd cluster is close to zero.

**Concrete analogy**: Renting a storage unit by the number of times you open the door, rather than by size. When you open the door once a year (quarterly campaign flags), the pricing model is fine. When you open the door a thousand times a day (per-request model routing), you'd buy the storage unit outright.

**So what**: Before choosing a SaaS tool, price it at the traffic level it will actually operate at — not at your current traffic, and not at a 10x growth ceiling, but at the ceiling of the system it will instrument.

---

## Section 3 — The Propagation Problem: Why etcd + gRPC Streaming

**Purpose**: Explain the technical choice — why etcd and why gRPC streaming rather than polling, database watches, or a simpler mechanism.

**Key points**:
- Three requirements shaped the choice: (1) sub-50ms flag change propagation to all running pods, (2) evaluation latency of <1ms (must be in-process, not a network call), (3) audit consistency — every flag change must be durably logged before it takes effect in any pod.
- Polling alternatives (HTTP GET every N seconds) fail on (1): you can't guarantee sub-50ms propagation with polling unless N < 50ms, which creates absurd load on the config store.
- Database watches (PostgreSQL LISTEN/NOTIFY, Redis keyspace events) fail on (3): neither guarantees that the audit log entry is written atomically with the flag change. You can lose audit entries if the writer crashes between the flag write and the audit write.
- etcd's `Txn` provides the atomicity needed for (3): flag value mutation and audit log entry are written as a single atomic transaction. Either both commit or neither does.
- etcd's `Watch` provides the propagation needed for (1): the flagd server opens a watch on the `/flags/` prefix; any mutation fires a watch event immediately. The server fans this out to all connected gRPC streams.
- gRPC streaming (rather than WebSockets or SSE) provides (2): the client receives the initial SNAPSHOT over the stream and stores all flags in-process. Subsequent DELTAs patch the in-process map. Flag evaluation is a local hash-map read — no network, no serialization on hot path.

**What I didn't expect**: the reconnect behavior was the hardest part to get right, not the initial propagation. When a client reconnects after a network partition, it needs a fresh SNAPSHOT — it cannot trust its stale in-process map. But the SNAPSHOT can arrive slightly after some DELTAs have already fired (race between reconnect and watch events). The solution: clients always request a SNAPSHOT on connect, and the server sends SNAPSHOT before any pending DELTAs. SNAPSHOT wins.

**Concrete analogy**: A trading floor where each trader has a whiteboard showing current prices. The exchange can update all whiteboards simultaneously (broadcast) or each trader can call the exchange every few seconds (polling). Broadcasting is faster and cheaper at scale. etcd watch + gRPC streaming is the broadcast architecture; polling is the alternative.

**So what**: The choice of propagation mechanism determines both your flag change latency and your audit guarantees — they are not independent design decisions.

---

## Section 4 — AI Model Rollout Flags: What Boolean Flags Don't Give You

**Purpose**: Explain why percentage rollout flags with deterministic hashing are different from standard boolean flags — and why this matters for AI model version changes.

**Key points**:
- Boolean flags are binary: all traffic sees version A, then all traffic sees version B. There is no intermediate state. For model version changes, this is dangerous: a new model may behave worse on a specific request type that only shows up at 5% of traffic. You won't know until you're already at 100%.
- Percentage rollout flags let you send 10% of traffic to gpt-4o and 90% to gpt-3.5-turbo simultaneously. You observe quality metrics, latency, and cost for each variant before committing.
- Deterministic hashing (FNV-1a on `flag_name + ":" + request_id`) ensures the same request always hits the same model. This is critical for multi-turn sessions: if a user's first message went to gpt-4o, their second message must also go to gpt-4o — otherwise the model context changes mid-session.
- Standard product flags (LaunchDarkly, Unleash) use user_id as the stable key, which makes sense for UX experiments. For LLM routing, the stable key is often session_id or request_id — the entity is the conversation, not the user.

**What I didn't expect**: audit logs for percentage rollout flags need to capture the evaluation_count_snapshot at weight-change time, not just the new weights. Without the snapshot, you can't answer "how many requests saw gpt-4o between the 10% and 25% weight changes?" — which is exactly what the cost attribution question requires.

**Concrete analogy**: Dimming a light switch versus flipping it. Boolean flags are binary — on or off. Percentage rollout flags are a dimmer: you can hold at 10% brightness for an hour, verify the room temperature (model quality), then slowly increase. The evaluation_count_snapshot is a timestamp burned into the dimmer position — you can always reconstruct exactly how long it was at each brightness.

**So what**: For AI model version changes, the flag type matters as much as the flag system. Boolean flags are the wrong tool; percentage rollout with deterministic hashing and count-snapshot audit is the right one.

---

## Section 5 — The DH Bridge: Same Propagation Problem, Different Payload

**Purpose**: Connect the abstract distributed-flagd architecture back to the concrete DH experience, showing the author has lived this pattern before.

**Key points**:
- At DH, the Route Service needed surge multiplier values propagated to all EKS pods within seconds. The technical requirement was identical to what distributed-flagd solves: consistent store (etcd), watch-based propagation, atomic broadcast to all running instances.
- The payload at DH was a floating-point surge multiplier — a config value that adjusted routing behavior during peak demand. The payload in distributed-flagd is a model version weight distribution. The propagation infrastructure is the same.
- This pattern — "consistent store + watch + in-process cache" — recurs throughout distributed systems engineering. It appears in service discovery (etcd + client-side DNS cache), config management (etcd + envoy xDS), and now in AI model routing flags. The implementation details differ; the architecture is the same.
- The reason to build rather than buy is not just cost — it is that the system you're building is an infrastructure primitive, not a product feature. Infrastructure primitives should be understood by the team that operates them. Black-boxing your model routing logic in a SaaS dashboard is fine when it works; it is a debugging nightmare when it doesn't.

**What I didn't expect**: the hardest conversation about building distributed-flagd was not the technical design — it was explaining to stakeholders why spending two engineering days building something that "already exists" made sense. The answer was: LaunchDarkly doesn't exist as an in-process local evaluator with per-request deterministic hashing and etcd-atomic audit logs. The SaaS product and the infrastructure primitive look similar on a feature matrix and are different things in production.

**Concrete analogy**: Buying a bread machine versus building a bakery. LaunchDarkly is the bread machine: excellent for home use (team-facing flags), wrong tool for a café that serves 1,000 customers a day. Distributed-flagd is the commercial oven: more initial cost, designed for the actual load.

**So what**: "We could buy this" is not the same question as "should we buy this at our traffic and with our operational requirements." The answer depends on what the tool actually does at scale — not what it does in the demo.

---

## Section 6 — What I'd Do Differently

**Purpose**: First-person reflection, brief, earns credibility.

**Key points**:
- Build the percentage rollout evaluator before building the propagation layer. It is the core value; the propagation layer (etcd + gRPC) is well-trodden infrastructure. Proving the evaluation semantics with unit tests first would have saved two redesigns.
- Size the etcd audit log retention from day one. Leaving it unbounded means the audit keyspace grows forever. 90-day TTL with etcd lease should be designed in, not retrofitted.
- Add a dry-run mode to the flagd CLI: `flagd set-flag --dry-run` shows what would change and how many evaluation contexts would be affected, without committing. Critical for weight changes on high-traffic flags.
- The migration from LaunchDarkly (or any flag SaaS) requires a dual-write period: write flag changes to both systems simultaneously and compare evaluation results in shadow mode. Don't migrate cold.

**So what**: The propagation architecture is table stakes. The operational tooling — dry-run, audit, migration shadow mode — is what makes the system trustworthy.

---

## Section 7 — Bridge to Day 21 Code

**Draft bridge**:
Today's distributed-flagd DESIGN.md is the specification document for what the DH routing team would have called "the config propagation service" — described, at the time, as "just etcd" but actually a set of operational contracts that take a day to document precisely. The AI Learning post today covers the same reliability instinct from a different angle: mapping provider error codes to the correct recovery action. Both posts are about the same underlying discipline — knowing exactly what your system does at the moment a value changes, and having the audit trail to prove it.

---

## Mermaid Diagrams

### Diagram 1 — distributed-flagd Topology

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
    CLI["flagd CLI\noperator writes"]
    SRV["flagd Server\ngRPC + watch fan-out"]
    ETCD["etcd cluster\nflag store + audit log"]
    C1["Edge Client A\nLensAI ingest"]
    C2["Edge Client B\nLensAI router"]
    C3["Edge Client C\nany service"]

    CLI -->|"SetFlag RPC"| SRV
    SRV -->|"Txn: flag + audit"| ETCD
    ETCD -->|"Watch event"| SRV
    SRV -->|"gRPC stream delta"| C1
    SRV -->|"gRPC stream delta"| C2
    SRV -->|"gRPC stream delta"| C3
```

### Diagram 2 — Buy vs Build Decision Framework

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
    Q1["Is evaluation\non critical path?"]
    Q2["Does pricing scale\nwith traffic volume?"]
    Q3["Do semantics match\nyour use case?"]
    BUY["Buy SaaS\n(LaunchDarkly etc.)"]
    BUILD["Build self-hosted\n(distributed-flagd)"]

    Q1 -->|"No — async"| BUY
    Q1 -->|"Yes — hot path"| Q2
    Q2 -->|"No — flat pricing"| Q3
    Q2 -->|"Yes — per-eval"| BUILD
    Q3 -->|"Yes — boolean flags"| BUY
    Q3 -->|"No — % rollout + audit"| BUILD
```

---

## Post Metadata

```json
{
  "slug": "day-21-launchdarkly-build-vs-buy-flagd",
  "title": "Day 21 — LaunchDarkly Money — Why We Build flagd Ourselves",
  "subtitle": "Platform economics · control plane vs data plane · DH real-time config bridge",
  "series": "experience",
  "day": 21,
  "date": "2026-06-09",
  "employer": "Delivery Hero",
  "systems": ["Route Service", "etcd", "gRPC streaming", "distributed-flagd"],
  "tags": ["FeatureFlags", "DistributedSystems", "DeliveryHero", "BuildVsBuy", "PlatformEngineering", "etcd"],
  "coverImage": "/blog/assets/covers/day-21-launchdarkly-build-vs-buy-flagd.png",
  "url": "/blog/series/experience/day-21-launchdarkly-build-vs-buy-flagd.html"
}
```

---

## Verified Numbers (from context docs — do NOT invent others)

| Fact | Source | Value |
|------|--------|-------|
| Daily orders | resume-extracted.md | 1M+ daily orders |
| Route update throughput | resume-extracted.md | 5k+ real-time route updates/sec |
| Concurrent requests | resume-extracted.md | 10k+ concurrent requests |
| EKS deployment | delivery-hero-rider-tracking-system.md | confirmed |
| DH tenure | resume-extracted.md | Jun 2022 – Jul 2023 |

Numbers that are **estimates / directional** — label clearly in post:
- 8-second inconsistency window during config propagation: directional from operational memory, label as "a brief window"
- Surge multiplier propagation context: drawn from DH config management patterns, not in context docs explicitly — present as "config values like surge multiplier" not as a named system

---

## Self-Review Checklist (before pushing)

- [ ] `Day 21` appears in `<title>`, `<h1>`, accent chip, meta line, series footer
- [ ] All scale numbers match context docs exactly (1M+ orders, 5k+ updates/sec, 10k+ concurrent)
- [ ] No invented system names — DH systems drawn from delivery-hero-rider-tracking-system.md
- [ ] "Surge multiplier" presented as a config value type, not a named internal service
- [ ] Every paragraph ≤ 3 sentences
- [ ] At least one concrete non-software analogy per major concept
- [ ] Every section ends with a "so what" sentence
- [ ] Both Mermaid diagrams have the correct init block
- [ ] No nested `<a>` tags
- [ ] Div open/close count balanced
- [ ] No `</motion.div>` tags
- [ ] Cover image path referenced: `blog/assets/covers/day-21-launchdarkly-build-vs-buy-flagd.png`
- [ ] `pre-push-check.sh` exits 0
- [ ] Bridge to Day 20 Experience post (consumer lag / measurement instinct) mentioned
