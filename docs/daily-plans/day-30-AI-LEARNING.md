# Day 30 — AI Learning Series Outline
## ReAct Loops as Distributed Workflows

---

## Header Block

| Field | Value |
|---|---|
| Series | AI Learning · Day 30 of 150 |
| Day | 30 |
| Topic | ReAct Loops as Distributed Workflows |
| Subtitle | Planner → tools → memory — state machine, not magic |
| Hook | Draw the loop as a saga; each tool call is a compensatable step with timeout. |
| DS Analogy | A ReAct loop is a distributed saga. The planner is the saga orchestrator. Each tool call is a compensatable step with a timeout and a defined rollback. Memory updates between steps are the saga's durable log — the record of what has been done that survives a crash. When a step fails, the question is not "what broke" but "which compensating transaction do I execute to leave the system in a consistent state." |
| Target URL | `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-30-react-loops-distributed-workflows.html` |
| Thread Connection | agent-trace-collector's span schema (trace_id, parent_span_id, tool_name, status) is the OTel representation of this exact saga structure — one span per compensatable step, parent linkage encoding the saga's dependency graph. |

---

## HTML File Target Block

| HTML Location | Required Text |
|---|---|
| `<title>` | `Day 30 — ReAct Loops as Distributed Workflows \| AI Learning Series` |
| Accent chip | `AI Learning · Day 30 of 150` |
| `<h1 class="post-title">` | `Day 30 — ReAct Loops as Distributed Workflows` |
| Meta line | `AI Learning · Day 30 of 150` |
| Series footer | `Day 30 of 150 — ReAct Loops as Distributed Workflows` |

---

## Voice Reminders

- Write in first person: "I hit this wall when...", "Here's what surprised me...", "What I didn't expect was..."
- Maximum 3 sentences per paragraph. Split immediately at 4.
- One concrete analogy per major concept — grounded in physical/everyday objects, never another software concept.
- Every section ends with a "so what" sentence.
- No bullet lists as substitute for prose.

---

## Opening Hook

**Purpose:** Establish the reframe — a ReAct loop is not a black box of AI magic, it is a state machine with defined transitions, and the right mental model for understanding it comes from distributed systems, not NLP.

**Draft:**

When I first encountered ReAct — the reasoning-then-acting loop that underlies most tool-using AI agents — my instinct was to model it the way I'd model a human decision process: fluid, contextual, hard to decompose. That instinct was wrong, and it led me to treat agent failures as inherently mysterious. The mental model that actually works, the one that makes agent behaviour predictable and debuggable, is a state machine borrowed from distributed systems: the saga pattern. Draw the loop as a saga. Make each tool call a compensatable step with a timeout. Track state transitions in a durable log. Suddenly, the "thinking" between steps is just the orchestrator deciding which compensating transaction to execute next.

The reason this reframe matters is practical. When an AI agent fails — produces wrong output, gets stuck in a loop, returns an incomplete result — the diagnosis is much faster if you know which state transition failed. A saga has a defined state: you can look at the durable log and ask "what was the last successful step." A "the AI is confused" narrative gives you nothing to work with. A "the saga is stuck at Step 4 — tool call returned ERROR and the orchestrator has no compensating path defined" gives you exactly the right fix.

---

## Section 1 — ReAct: The State Machine Underneath

**Purpose:** Explain what ReAct actually is mechanically — observe, reason, act, loop — as a state machine with named states and transitions.

**Key Points:**

ReAct stands for Reasoning and Acting. The loop has four states: **Observe** (read the current context — user query, tool results from previous steps, memory state), **Reason** (generate a thought about what to do next — this is the language model's inference pass), **Act** (call a tool or produce a final answer), and **Update** (write the tool result back into the context — this is the memory update that makes the next Observe step different from the previous one). The loop continues until the Act step produces a final answer rather than a tool call.

What makes this a state machine is the durable dependency between steps. The Observe step at iteration N reads the accumulated tool results from iterations 1 through N-1. The Reason step at iteration N generates a thought conditioned on that accumulated context. The Act step at iteration N selects a tool or terminates based on the Reason output. Each iteration's Act output is a side effect that modifies the context for the next iteration's Observe. This is a state machine: the state is the context window at each iteration, the transitions are the model's inference and the tool's execution, and the terminal state is a final answer.

The "magic" of a ReAct loop is that the state transition function (Reason → Act) is implemented by an LLM rather than a hardcoded if-else tree. That's interesting, but it doesn't make the system fundamentally different from any other state machine. The state is still defined, the transitions are still deterministic given fixed inputs, and the terminal condition is still observable. Treating it as a state machine means you can instrument it the same way you'd instrument any state machine: trace each state transition, log the inputs and outputs, alert on loops that don't terminate.

**Concrete analogy:** A ReAct loop is a vending machine with a variable number of steps between coin insertion and snack delivery. The machine has defined states: waiting for input, processing selection, dispensing snack, returning change. Some selections require one step (candy bar, coin in, snack out). Some require multiple steps (a complex combo selection that verifies inventory, checks expiry, then dispenses). The machine's internal logic varies by selection, but the state machine structure — observe input, reason about what to do next, act, update internal state — is the same for every transaction. The LLM is the machine's selection-processing logic, not the machine itself.

**So what:** A ReAct loop is a state machine with a model-implemented transition function — instrumentable, debuggable, and observable using exactly the same techniques you'd apply to any async multi-step process.

---

## Section 2 — The Saga Pattern: Tool Calls as Compensatable Steps

**Purpose:** Introduce the saga pattern as the distributed systems lens for understanding multi-step agent execution.

**Key Points:**

In distributed systems, a saga is a sequence of local transactions where each transaction publishes an event or message triggering the next transaction. If a transaction fails, compensating transactions are executed to undo the partial work done by previous transactions. The saga pattern solves the same problem a ReAct loop solves: how do you perform a multi-step operation reliably when each step might fail, and when you can't lock all the resources the operation touches for the entire duration?

Mapping ReAct to saga: the saga's local transactions are the tool calls. Each tool call is a local transaction that reads from the context (the saga's durable log) and produces a result that's written back into the context. If the tool call fails — returns an error, times out, returns an unexpected result — the saga needs a compensating path: either retry the same tool with different parameters, try a different tool, or terminate with a partial result and explanation. The language model's Reason step is the saga orchestrator making this decision.

The critical property of a saga that applies directly to ReAct loops is **compensatability**: every step that can fail should have a defined compensating action. For a file-editing agent, "write a file" should have "restore the backup" as its compensation. For a web-browsing agent, "navigate to a URL" should have "return to the previous URL" as its compensation. In practice, most ReAct implementations don't define explicit compensations — they rely on the model to "figure out" how to recover. This works until it doesn't, and when it doesn't, there's no structured way to diagnose why.

**Concrete analogy:** An airport check-in process with multiple kiosks is a saga. Passenger scans passport (step 1), selects seat (step 2), pays for baggage (step 3), prints boarding pass (step 4). If step 3 fails — payment declined — the system executes compensating transactions: release the held seat (compensate step 2), invalidate the passport scan session (compensate step 1). Without defined compensations, a failed payment leaves the seat held and the passport scan active. With defined compensations, the system returns to a clean state ready for the next attempt. A ReAct loop with no defined compensating paths is the check-in system where a failed payment leaves the seat permanently held.

**So what:** Thinking of each tool call as a compensatable step forces you to define what "undo" means for every action the agent can take — which is exactly the discipline that prevents an agent from getting stuck in a partially-applied state with no recovery path.

---

## Section 3 — Timeouts, Loops, and Terminal Conditions

**Purpose:** Apply the distributed systems concept of timeouts and termination conditions to the ReAct loop — and why both are often missing in naive agent implementations.

**Key Points:**

Every distributed system has timeout semantics for its operations — a maximum duration after which an operation is declared failed and a compensating path is triggered. ReAct loops without explicit timeouts per tool call have an implicit timeout determined by the LLM's context window limit and the model's max-tokens setting. This is not a design choice — it's an accident of implementation. When a tool call hangs (a network request that never returns, a subprocess that loops indefinitely), the agent has no way to detect the hang and trigger a compensating path without an explicit timeout.

Terminal condition detection is the second gap. A saga terminates when either all transactions complete successfully or a compensating transaction fails to produce a consistent state. A ReAct loop terminates when the model produces a final answer rather than a tool call. But what prevents an agent from producing an infinite sequence of tool calls, each one moving the plan slightly forward without ever reaching the final answer? Nothing, unless the loop has an explicit maximum step count or a termination condition checker. A ReAct loop without a maximum iteration count is a saga without a terminal failure state — it can loop forever.

Both problems have the same root cause: the distributed systems engineering concepts that govern saga design haven't been applied to agent design. Saga implementations have explicit timeout specifications per transaction and explicit terminal failure states for unrecoverable errors. Agent frameworks typically delegate both decisions to the model, which means the model must both execute the task and govern its own execution. Separating these concerns — putting timeouts and terminal conditions in the agent harness, not the model — is the architectural improvement that makes agents more reliable.

**Concrete analogy:** A timeout in a ReAct loop is like a traffic light cycle with a maximum green duration. Without a maximum, a particularly busy road could hold the light green indefinitely, starving cross traffic. The maximum isn't about the most common case — most traffic light cycles complete in well under the maximum. It's about the rare case where the detector loop fails and keeps the light green forever. Timeouts in ReAct loops handle the rare case where a tool call hangs — protecting the agent from being stuck waiting for a response that will never arrive.

**So what:** Explicit per-step timeouts and maximum iteration counts in the agent harness, not the model, are the two structural properties that separate a reliable ReAct agent from an unreliable one — both have direct precedents in saga pattern design.

---

## Section 4 — Memory as the Saga's Durable Log

**Purpose:** Explain how memory in a ReAct loop maps to the durable log in a saga, and what "durable" means for agent memory.

**Key Points:**

A saga's durable log is the record of which transactions have completed successfully. It's what allows a saga to resume after a crash: read the log, determine which transactions completed, determine which compensating transactions need to run, continue from the last consistent state. Without durability, a crash requires starting the entire saga from the beginning — every completed transaction is lost.

In a ReAct loop, the context window is the memory. It records which tool calls have been made, what results they returned, and what reasoning the model produced after each result. For a single-session agent run, the context window is durable in the sense that it accumulates across iterations — each new tool result is appended to the context. But the context window is not durable across sessions: if the agent process crashes or the session ends, the context window is lost. Resuming the agent requires starting the loop from scratch.

This is the gap that motivates externalising memory. An external memory store — a vector database, a key-value store, a structured span log — is the saga's durable log. Each tool call's result is written to the external store as it completes. If the agent crashes at step 7, the next run can query the external store to find steps 1 through 6 already completed and resume from step 7. This is exactly what agent-trace-collector's span schema enables: each span is a record of a completed saga step, persistent across agent restarts, queryable to reconstruct the execution state.

**Concrete analogy:** External agent memory is like a construction project's punch list. The punch list records every completed task: "drywall installed — room 3, floor 2" is checked off when the crew finishes and cannot be un-checked. If a crew is replaced mid-project, the new crew reads the punch list to find out what's been done and what remains. Without the punch list, a crew change means redoing the inspection of every room. The context window is the crew's verbal briefing at the start of each shift — useful, but lost when the crew goes home. The punch list survives crew changes. The external memory store survives agent restarts.

**So what:** Externalising memory as a structured log — one record per completed step, persistent across agent restarts — converts a ReAct agent from a single-session process into a resumable distributed workflow, with the same durability properties as a properly implemented saga.

---

## Section 5 — Instrumenting the Saga: Where Tracing Comes In

**Purpose:** Show how the saga mental model maps directly to the tracing infrastructure — spans, parent IDs, status codes — and why this makes agent observability a solved problem rather than a research area.

**Key Points:**

Once you think of a ReAct loop as a saga, the instrumentation question answers itself. A saga's durable log needs to record: which transaction ran, when it started, how long it took, what its result was, and which transaction it was triggered by. This is exactly an OTel span: `span_id`, `start_time`, `latency_ms`, `status`, and `parent_span_id`. The saga's dependency graph — "transaction 4 was triggered by the result of transaction 3" — is the span's `parent_span_id`. The execution tree of a ReAct loop is a span tree, and span trees are what distributed tracing was designed to collect and visualise.

The practical consequence is that building observability for a ReAct agent is not a new problem. It's the same problem as building observability for a microservice call chain. The tooling is the same: OTel spans, Jaeger or Grafana Tempo for visualisation, ClickHouse for aggregation queries. The schema is the same: trace ID for the root operation, span ID per step, parent span ID for dependency. What's new is that the "service" is an LLM inference pass and the "operation" is a tool call — the semantic labels on the spans need to capture `tool_name`, `model`, `tokens`, and `cost_usd`, which standard OTel service span schemas don't include. The schema extension is small. The infrastructure reuse is large.

This is exactly what agent-trace-collector encodes. The `Span` schema in `pkg/schema/span.go` is a standard OTel span with four additional fields: `tool_name`, `model`, `input_tokens`/`output_tokens`, and `cost_usd`. Everything else — trace ID, span ID, parent span ID, status, latency — is standard OTel. The span forwards to a standard OTel Collector, which routes to ClickHouse via the same pipeline built in OSS-03. The agent observability infrastructure reuses every component from the LLM inference observability infrastructure.

**Concrete analogy:** Instrumenting a ReAct loop with OTel spans is like adding GPS tracking to a delivery route that already has package scanning. The package scanning system (OTel infrastructure) already tracks: when a package was scanned, where, and which delivery it belongs to. Adding GPS coordinates to each scan record (the four new span fields) gives you richer information without building a new tracking system. The new fields extend the existing schema. The existing infrastructure handles collection, storage, and visualisation. You're not building something new — you're extending something that already works.

**So what:** A ReAct agent's execution is naturally representable as an OTel span tree, which means the entire observability problem is solved by adding four fields to a standard span schema — no custom UI, no agent-specific visualisation tooling, no new storage system.

---

## Mermaid Diagrams

### Diagram 1 — ReAct Loop as Saga State Machine

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
    [*] --> Observe
    Observe --> Reason: context accumulated
    Reason --> Act: thought generated
    Act --> Update: tool result returned
    Update --> Observe: context extended
    Act --> [*]: final answer
    Act --> Compensate: tool error or timeout
    Compensate --> Reason: compensation chosen
```

**Caption:** A ReAct loop as a saga state machine. `Act → Compensate → Reason` is the loop's recovery path — the orchestrator (language model) receives the error and decides which compensating action to take next. Without this path being explicit, a tool error collapses to "the agent is stuck."

### Diagram 2 — Span Tree for a Three-Step ReAct Execution

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
    A["Root span\nmodel_call · 1.2s"] --> B["Span: Read file\nfile_io · 42ms · OK"]
    A --> C["Span: Bash command\ncode_exec · 340ms · OK"]
    A --> D["Span: Edit file\nfile_io · 28ms · OK"]
    C --> E["Sub-span: test run\ncode_exec · 290ms · OK"]
```

**Caption:** Each step in the ReAct loop becomes a child span of the root model call. The `parent_span_id` encodes the dependency graph. The Bash command's sub-span (the test run it triggered) is a child of the Bash span — preserving the execution tree's structure in the trace data.

---

## Post Metadata JSON Block

```json
{
  "slug": "day-30-react-loops-distributed-workflows",
  "title": "Day 30 — ReAct Loops as Distributed Workflows",
  "subtitle": "Planner → tools → memory — state machine, not magic",
  "series": "ai-learning",
  "day": 30,
  "date": "2026-07-03",
  "url": "https://akshantvats.github.io/Profile/blog/series/ai-learning/day-30-react-loops-distributed-workflows.html",
  "coverImage": "blog/assets/covers/day-30-react-loops-distributed-workflows.png",
  "ogImage": "blog/assets/og/day-30-react-loops-distributed-workflows.png",
  "tags": ["DistributedSystems", "AIInfrastructure", "GPUComputing", "Observability", "BackendEngineering", "ReAct"]
}
```

---

## Self-Review Checklist

- [ ] `Day 30` appears in `<title>`, `<h1>`, accent tag chip, and meta line
- [ ] Series footer reads `Day 30 of 150 — ReAct Loops as Distributed Workflows`
- [ ] All `<div` opens and `</div>` closes are balanced
- [ ] Zero `</motion.div>` tags
- [ ] No `<a>` nested inside another `<a>`
- [ ] At least one `class="prose"` div present
- [ ] `.series-nav`, `.series-posts`, `.series-post` CSS classes present in `<style>` block
- [ ] Every paragraph is ≤ 3 sentences
- [ ] Every major section has a "so what" closing sentence
- [ ] Every major concept has one concrete non-software analogy
- [ ] Both Mermaid diagrams use the exact init block — no variations
- [ ] Every Mermaid node label is ≤ 6 words
- [ ] Each diagram has ≤ 8 nodes
- [ ] No placeholder URLs
- [ ] Cover image path: `blog/assets/covers/day-30-react-loops-distributed-workflows.png`
- [ ] OG image path: `blog/assets/og/day-30-react-loops-distributed-workflows.png`
- [ ] Previous AI Learning post (day-29) footer updated to link to this post
- [ ] `series-index.json` entry added with correct schema
- [ ] `pre-push-check.sh` exits 0 before any `git push`
- [ ] Commit message includes `Self-review: N issues found and fixed.`
