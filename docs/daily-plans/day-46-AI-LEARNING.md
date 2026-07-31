# Day 46 — AI Learning Blog Plan

**Title**: Day 46 — Deterministic Mocks — Record and Replay
**Subtitle**: VCR pattern for LLM agents
**Hook**: Mock tools return bytes from trace — not live HTTP.
**day_index**: 46

## Angle

Clone the GOLD post's depth (`day-2-continuous-batching-vllm.html`) and the most recent AI
Learning post's structure. This is a distributed-systems-engineer-learning-AI-infra post: the
reader already knows testing/mocking as a general practice, is new to why *agent* runs
specifically need a record/replay approach rather than a hand-written stub.

Cover, in order:

1. **Hook**: an agent run is non-deterministic by default — model issues tool calls, tool calls
   hit live APIs, APIs return data that changes over time. Re-running the same prompt against
   live tools rarely reproduces a bug, because the responses that triggered it are gone.
2. **DS analogy (attr-box)**: this is the VCR test pattern (record a real HTTP interaction once,
   replay the frozen cassette on every subsequent run) — grounded in an actual cassette
   recorder, not another software concept. Record once, play back byte-for-byte, forever.
3. **The two pieces**: `ToolMocker` (serves a frozen response for a `(tool_name, input_hash)`
   composite key — why composite, not just input hash: two different tools can receive
   identical input and must not collide on the same frozen response) and `replay.Run` (walks
   the recorded `tool_call` sequence in order, asking the mocker for each response, and can
   halt after N steps instead of always running to the end).
4. **Why partial replay matters for agents specifically**: a single-function unit test either
   passes or fails; a multi-step agent run has intermediate state worth inspecting mid-flight.
   `--stop-at-step` is that inspection point — bridges to today's Experience post's OTA-rollback
   framing (stop before the step you already know is broken, not after).
5. **Mermaid diagram**: EventLog → ToolMocker(frozen responses) → replay.Run(stopAtStep) →
   Result(Output | StoppedEarly) flow, ≤8 nodes, required init block from CLAUDE.md section 4.5,
   labels ≤6 words.
6. **So-what**: deterministic replay is what turns "the bug happened once, in production, days
   ago" into "the bug reproduces locally, on demand" — the actual precondition for fixing it.

Kicker: `Day 46 of 150`. Required mermaid init block. Max 3 sentences/paragraph.
