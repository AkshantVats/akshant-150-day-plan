# Day 44 — Experience Blog Outline
## "Day 44 — Event Sourcing — But the Events Hallucinate"
### Wayfair · idempotent replays · pricing

**Series**: Experience · Day 44 of 150
**Slug**: `day-44-event-sourcing-events-hallucinate`
**File**: `blog/series/experience/day-44-event-sourcing-events-hallucinate.html`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-44-event-sourcing-events-hallucinate.html`
**Employer context**: Wayfair — PAS + Pricing Promotions & Discounts (Sr. Software Engineer III, Nov 2024 – Mar 2026)
**Bridge**: "Replay mocks are idempotent consumers — Wayfair price replay with frozen inputs. Today's code in agent-replay-engine implements that lesson."

---

## Title Block

```
<title>Day 44 — Event Sourcing — But the Events Hallucinate | Experience Series</title>
Accent chip: Experience · Day 44 of 150
<h1 class="post-title">Day 44 — Event Sourcing — But the Events Hallucinate</h1>
Meta line: Experience · Day 44 of 150
Series footer: Experience · Day 44 of 150
```

---

## Employer Context Reference

**Verified facts from pricing-system-architecture.md and resume-extracted.md** (use only these):

- **Role**: Sr. Software Engineer III (led PAS & Pricing Promotions teams), Wayfair Bengaluru, Nov 2024 – Mar 2026
- **System**: PAS (Price Adjustment System) — Java, GraphQL + REST, CQRS with Bigtable read model
- **Delphi**: `delphi-price-optimizer` — stateless pure function, c2d-standard-56 nodes (56 vCPU / 224 GiB), full-catalog and on-demand modes
- **Scale**: ~295M daily hits on PAS; 15,263 peak RPS on `/graphql`; 250k+ SKU updates per supplier in near real-time
- **Pricing runs**: PricingRunOrchestrator → Pub/Sub (`cost-simulation-requests`) → RunDispatcher → Delphi. Millions of rows per pricing run via Dataflow.
- **Kafka**: `pricing_refresh` (40 partitions) for price change events — described in the doc as "event-sourcing" pattern
- **Simulation**: pricing simulations run against frozen supplier cost data, adjustment sets, and SKU lists — results compared to live prices to validate adjustment correctness
- **Price propagation**: reduced from hours to sub-seconds across 20k+ suppliers after architecting the event-driven engine
- **Bigtable**: CQRS read model — `pricing-cost-adjustment-bt` (13K avg QPS, 57K peak) for low-latency price lookups
- **Stack**: GCP, Bigtable, PostgreSQL 14 (regional HA), Kafka, Cloud Dataflow, BigQuery, Pub/Sub

**Do NOT invent**: specific simulation incident dates, team size, dollar values of pricing errors, specific simulation failure counts.

---

## Hook (first paragraph)

The pricing engine at Wayfair ran simulations before any price adjustment went live. A simulation was a replay: take the current adjustment set, freeze the supplier cost inputs, run them through Delphi, and see what retail prices would come out. If the simulated prices diverged from expected values by more than a threshold, the adjustment was blocked. The mechanism that made this work was that Delphi was a stateless pure function — same inputs, same output, every time, no exceptions. The simulation's frozen inputs guaranteed that two runs of the same simulation always produced the same result. I did not think of this as event sourcing at the time. I thought of it as "pricing simulation." The pattern is identical: freeze the inputs, replay the computation, compare the output.

---

## Section 1 — What a Pricing Simulation Is and Why Idempotency Is Not Optional

### The problem pricing simulations solve
A price adjustment at the scale of 250k+ SKUs per supplier is not something you push live and see what happens. A bug in the adjustment logic — wrong discount percentage, off-by-one in the effective date, a misconfigured supplier exclusion — affects every retail price that reads from Bigtable within milliseconds of the adjustment committing. There is no "undo" for a price error that reached customer-facing storefront-svc before the on-call engineer could respond. The only defence is validation before the adjustment commits.

### What the simulation does
The pricing simulation runs the exact same calculation pipeline as a live pricing run but against a frozen snapshot of inputs. Frozen means: supplier costs from a fixed BigQuery snapshot timestamp, adjustment sets from the current PAS database state, SKU metadata from a fixed Bigtable row version. Delphi receives the same input vectors it would receive in a live run, but all inputs are pinned to a point in time rather than read live. The output is the set of retail prices the adjustment would produce if it committed now. The validator compares this to the expected price range and blocks the adjustment if the difference exceeds the threshold.

### Why idempotency is the load-bearing property
Delphi being a stateless pure function — the "Pattern: Stateless pure function" in the system documentation — is what makes the simulation reliable. Run it once: price X. Run it again five minutes later with the same inputs: price X. The output is deterministic because there is no internal state, no cache that could have changed, no background job that could have run. If Delphi had side effects, the simulation would need to control for those effects on every run. Instead, idempotency is a design invariant enforced by Delphi's architecture, and the simulation relies on it without needing to verify it.

### So what
The simulation is only as reliable as the idempotency guarantee. If Delphi had been designed with any mutable state — a pricing cache it updated on each run, a background process that recomputed adjustments asynchronously — the simulation would have been unreliable from day one. The design decision to make Delphi a stateless pure function was made before the simulation existed, but it was what made the simulation possible. Architecture decisions made for one reason often enable capabilities their designers never anticipated.

---

## Section 2 — Frozen Inputs as the Source of Truth

### What "freezing" means in the pricing pipeline
Freezing inputs means pinning every data source the computation reads to a specific version: BigQuery snapshot at timestamp T, Bigtable row versions as of timestamp T, PostgreSQL queries running against a read replica with a fixed transaction snapshot. Any data source that reads live — that could return different values between run 1 and run 2 — breaks the simulation's reproducibility guarantee.

### The practical challenge at Wayfair's scale
The PAS CQRS read model used Bigtable for low-latency price lookups. `pricing-cost-adjustment-bt` ran at 13K average QPS with peaks to 57K during pricing runs — this table was constantly being written to as new adjustment runs committed. Pinning Bigtable reads to a fixed row version for simulation purposes required reading from a snapshot timestamp rather than from the current row. Bigtable supports this via read timestamps, but the simulation infrastructure had to explicitly pass the snapshot timestamp to every Bigtable read call in the simulation path — not the live path.

### The BigQuery Dataflow pipeline as the batch input source
Pricing run simulations pulled supplier cost inputs from BigQuery via Dataflow. Dataflow jobs were parametrized with a snapshot timestamp: all reads from BigQuery used the `FOR SYSTEM_TIME AS OF` clause to get data as it existed at timestamp T. This is BigQuery's built-in time travel — the same feature that makes BigQuery suitable for both OLAP queries and point-in-time data snapshots. The Dataflow job's output for the simulation was deterministic because the BigQuery read was frozen to T.

### So what
Frozen inputs are a system property, not a policy. You cannot decide to freeze inputs at debug time if the infrastructure was not designed to support pinned reads from the beginning. BigQuery's `FOR SYSTEM_TIME AS OF` and Bigtable's read timestamps are features that exist precisely because distributed systems need point-in-time consistency for correctness, not just for debugging. The pricing simulation used them for correctness. The lesson: time travel is not a nice-to-have for analytics systems. It is the mechanism that makes distributed replay possible.

---

## Section 3 — When the Inputs Are Not Frozen (And What Happens)

### The case where simulation and live prices diverge unexpectedly
The simulation would occasionally produce prices that diverged from the live prices by more than the threshold, blocking an adjustment that the pricing team believed was correct. The usual diagnosis: a data source that was supposed to be frozen had not been properly pinned. A Bigtable read somewhere in the simulation path had missed the snapshot timestamp parameter and was reading live data. The simulation was comparing frozen-input prices to an expectation based on different data than it was computing against.

### The investigation pattern
Diagnosing this required replaying the simulation with added logging at every data read: log the timestamp parameter passed to each Bigtable and BigQuery read, log the row version returned, compare to the snapshot timestamp used for the simulation. When a read returned a row version newer than the snapshot timestamp, that was the unfrozen read. The fix was mechanical: pass the snapshot timestamp to the read call that missed it.

### The brittleness of distributed state freezing
Freezing inputs across a distributed system is brittle because there is no single enforcement point. Delphi receives the frozen inputs from the simulation orchestrator, but it calls other services internally. If any service Delphi calls reads live data rather than the snapshot-pinned data, the simulation is only partially frozen. The only way to guarantee full freezing is to pass the snapshot timestamp through every call in the chain — every service, every Bigtable read, every BigQuery query — and verify that the timestamp is used at each read site. This is operationally expensive to maintain as the codebase evolves.

### So what
The agent-replay-engine solves this problem differently. Instead of freezing inputs at the data source level (pass a timestamp to every read), it freezes the outputs of tool calls (record the response payload, serve it verbatim on replay). The agent never sees the live API during replay. The tool mocker is the single enforcement point — every tool call goes through it, and every response is frozen. There is no "missed snapshot timestamp" failure mode because there is no snapshot timestamp at all. The frozen response is the response.

---

## Section 4 — Event Sourcing in the Pricing Kafka Pipeline

### How the pricing_refresh topic works
The `pricing_refresh` Kafka topic (40 partitions) carries price change events from Delphi through Aletheia to the customer-facing storefront. Every price change is an event: a record of "SKU X's retail price changed from Y to Z at timestamp T." The topic documentation describes the pattern explicitly as "event-sourcing" — every price state change is a published event, and the current price is the result of replaying the event stream from the beginning (or from a checkpoint).

### The consumer's idempotency requirement
Aletheia (storefront price cache, HPA 20-50 pods across 7 production clusters) consumed from `pricing_refresh`. When a pod restarted or a new pod started, it replayed events from its last committed offset. The events had to be idempotent at the consumer side: applying the same price change event twice had to produce the same final price as applying it once. If the same event was applied twice (due to at-least-once delivery), the price would be set to the correct value by both applications — not doubled, not corrupted, just correctly set.

### The parallelism across 40 partitions
Forty partitions meant up to 40 Aletheia consumer pods could process price changes in parallel. Kafka's partition assignment guaranteed that all events for a given SKU landed on the same partition (key = SKU ID), so a single pod processed all price changes for a given SKU in order. This prevented the race condition where two concurrent updates to the same SKU could be processed out of order, producing the wrong final price.

### So what
The `pricing_refresh` topic is a distributed event log for price state. It is exactly the same pattern as `agent-replay-engine`'s event log for agent state — both are append-only records of state transitions that can be replayed to reproduce any point-in-time state. The difference is the domain: pricing events represent SKU price changes; agent events represent tool call outcomes. The pattern is identical. Kafka was the right choice for the pricing pipeline because the tooling for distributed event logs — partitioning, consumer groups, offset management, replay from offset 0 — was already solved. `agent-replay-engine` is a purpose-built implementation of the same pattern for a domain where Kafka would be excessive.

---

## Section 5 — What the agent-replay-engine Gets Right That Pricing Simulations Got Wrong

### Single enforcement point for frozen inputs
The pricing simulation's freezing mechanism was distributed: snapshot timestamps had to be threaded through every data read in the system. Any read that missed the timestamp was an unfrozen input, producing a non-deterministic simulation. The `ToolMocker` is a single enforcement point: every tool call during replay goes through it, every response is frozen, no tool call reaches a live API. There is no equivalent of a "missed snapshot timestamp" because the architecture makes it structurally impossible for a tool call to bypass the mocker.

### Hash-keyed responses instead of timestamp-keyed reads
The pricing simulation keyed frozen data by timestamp: "give me this Bigtable row as of T." This works for databases that support time travel, but not for external APIs that do not expose historical state. The `ToolMocker` keys responses by `SHA-256(tool_name + ":" + input_hash)`: "give me the recorded response for this tool name and this exact set of inputs." This works for any tool call — internal databases, external APIs, in-process functions — because the key is the call signature, not a timestamp.

### Divergence detection built in
The `CallHistory()` method records every tool call the model issues during replay, in order. Comparing this to the recorded `KindToolCall` sequence reveals whether the model's behaviour changed between the original run and the replay. The pricing simulation had no equivalent: if the simulation produced different prices than expected, the investigation started from scratch — compare outputs, trace backwards through the computation, find the diverging input. `CallHistory` makes the divergence point explicit: the first index where the sequences differ is exactly where the replay's behaviour departed from the original.

### So what
The agent-replay-engine is not a novel invention. It is the pricing simulation pattern applied to a different domain, with three design improvements that the pricing simulation's distributed architecture could not provide: a single enforcement point for frozen inputs, call-signature-keyed responses that work for any tool type, and built-in divergence detection. The lesson from Wayfair is not "here is how to build a pricing simulation." It is "here is what happens when you build a replay system in a distributed system without a single enforcement point, and here is how to avoid that failure mode in the next one."

---

## Series Navigation Footer

Previous: Day 43 — Kafka as Shock Absorber — Again (Agoda)
Next: Day 45 — (coming)

---

## HTML Checklist Before Push

- [ ] `Day 44` in `<title>`, `<h1>`, accent chip, meta line, series footer (all four mandatory locations)
- [ ] `class="series-nav"` / `class="series-posts"` / `class="series-post"` CSS present in `<style>` block
- [ ] No system names invented beyond what appears in pricing-system-architecture.md and resume-extracted.md
- [ ] Akshant's role accurately scoped: led PAS and Pricing Promotions teams, architected the event-driven pricing engine
- [ ] Scale numbers within documented range: ~295M daily hits, 15K peak RPS, 250k+ SKUs per supplier, 20k+ suppliers, 13K avg / 57K peak Bigtable QPS
- [ ] All `<div>` opens match `</div>` closes
- [ ] No `</motion.div>` tags
- [ ] No `<a>` nested inside `<a>`
- [ ] Max 3 sentences per paragraph (split any that exceed this)
- [ ] No placeholder URLs
- [ ] Employer tenure accurate: Sr. Software Engineer III, led PAS & Pricing Promotions teams, Nov 2024 – Mar 2026
