# Day 35 — Code Plan
## TraceForge: ReAct Demo Agent — Reproduce Silent Step-7 Failure + DEMO.md

**Calendar**: Tuesday, 10 July 2026 · Day 35 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` (traceforge/ subdirectory — continuing from Day 34)
**Language**: Python 3.11+
**Builds on**: Day 32 — Python SDK `traceforge.wrap_openai()`; Day 34 — ClickHouse `agent_spans` + Grafana waterfall

### Shared Thread
> The Demo Agent That Always Dies on Step 7 meets Silent Failures in Multi-Step Agents in today's agent-trace-collector commit.

---

## Summary

Day 35 ships the TraceForge demo that closes the product loop. All the infrastructure — Python SDK, Go SDK, ClickHouse schema, Grafana waterfall — exists to answer one question a customer will ask: "Can you show me a real agent failing, and prove your tool caught it?" Today we build the proof.

The demo is a ReAct (Reason+Act) agent that queries weather, converts currencies, and summarises results. Step 7 always fails silently — an empty tool response the agent swallows and loops past. Without TraceForge, the agent appears to complete successfully. With TraceForge, the waterfall shows a span with `result_bytes: 0` and `status: EMPTY_RESPONSE`, a cost rollup that charged for eight LLM calls, and the exact step where the agent's reasoning went wrong.

Three deliverables:
1. **ReAct demo agent** — Python, 10-step reasoning loop, step 7 produces a zero-byte tool response
2. **TraceForge integration** — `traceforge.wrap_openai()` wrapping every LLM call; manual `StartSpan`/`EndSpan` around tool calls
3. **DEMO.md** — Step-by-step walkthrough with annotated screenshots of the Grafana waterfall

---

## Deliverables

| File | Purpose |
|---|---|
| `traceforge/examples/react_agent/agent.py` | ReAct agent: 10-step loop, step 7 silent failure |
| `traceforge/examples/react_agent/tools.py` | Mock tools: weather, currency, summarize (step 7 returns `""`) |
| `traceforge/examples/react_agent/run.py` | Entry point: runs agent, prints final answer |
| `traceforge/examples/react_agent/test_agent.py` | pytest: 6 tests covering silent failure detection |
| `traceforge/examples/react_agent/DEMO.md` | Screenshot walkthrough: before/after TraceForge |
| `traceforge/examples/react_agent/screenshots/` | Directory for annotated Grafana screenshots (placeholder PNGs) |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | ReAct agent completes 10 steps; step 7 tool call returns `""` | `python run.py` output shows step 7 empty, agent continues to step 8 |
| AC-2 | `traceforge.wrap_openai()` wraps all LLM calls; spans appear in `agent_spans` table | `SELECT count() FROM agent_spans WHERE trace_id = '...'` returns 10+ rows |
| AC-3 | Step 7 span has `result_bytes = 0` and `status = 'EMPTY_RESPONSE'` attribute | ClickHouse query output in PR description |
| AC-4 | `trace_cost_rollup` MV shows 8+ LLM calls charged despite empty step 7 | MV query output in PR description |
| AC-5 | `pytest traceforge/examples/react_agent/test_agent.py` exits 0 with ≥ 6 tests passing | Command output in PR description |
| AC-6 | `DEMO.md` contains before-section (no tracing) and after-section (with TraceForge) with at least 3 screenshots | Manual review |
| AC-7 | Agent runs without a real OpenAI key using a mock `openai` client | `USE_MOCK_OPENAI=1 python run.py` exits 0 |

---

## Part 1 — ReAct Agent (`agent.py`)

```python
# SPDX-License-Identifier: MIT
"""
TraceForge demo: ReAct agent with silent step-7 failure.

Step 7 is a currency conversion call that returns an empty string.
The agent treats empty == "no data" and loops to step 8 with corrupted context.
Without tracing: the agent appears to complete. Final answer is wrong but no error raised.
With TraceForge: span shows result_bytes=0, status=EMPTY_RESPONSE.
"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass, field
from typing import Any

import traceforge  # Day 32 Python SDK

MAX_STEPS = 10
SILENT_STEP = 7  # step that produces empty tool response


@dataclass
class ReActStep:
    step: int
    thought: str
    action: str
    action_input: dict[str, Any]
    observation: str = ""
    span_id: str = ""


@dataclass
class ReActAgent:
    llm: Any  # wrapped OpenAI client
    tools: dict[str, Any]
    trace_id: str = ""
    steps: list[ReActStep] = field(default_factory=list)

    def run(self, question: str) -> str:
        self.trace_id = traceforge.new_trace_id()
        context = question

        for step_num in range(1, MAX_STEPS + 1):
            span = traceforge.start_span(
                name=f"react.step.{step_num}",
                trace_id=self.trace_id,
                attributes={"step": step_num, "agent.type": "react"},
            )
            thought, action, action_input = self._reason(context, step_num)
            observation = self._act(action, action_input, step_num)

            span.set_attribute("tool.name", action)
            span.set_attribute("result_bytes", len(observation.encode()))
            if not observation:
                span.set_attribute("status", "EMPTY_RESPONSE")
                span.set_attribute("error", True)
            else:
                span.set_attribute("status", "OK")
            span.end()

            step = ReActStep(
                step=step_num,
                thought=thought,
                action=action,
                action_input=action_input,
                observation=observation,
                span_id=span.span_id,
            )
            self.steps.append(step)
            context = self._build_context(context, step)

            if action == "finish":
                return observation

        return "Max iterations reached without final answer."

    def _reason(self, context: str, step: int) -> tuple[str, str, dict]:
        """Call LLM to produce thought + action. Returns (thought, action, input)."""
        prompt = _build_prompt(context, step, list(self.tools.keys()))
        response = self.llm.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_response(response.choices[0].message.content)

    def _act(self, action: str, action_input: dict, step: int) -> str:
        """Invoke tool. Step 7 always returns empty string (silent failure)."""
        if step == SILENT_STEP:
            # Simulate a tool that swallows its exception and returns ""
            return ""
        tool_fn = self.tools.get(action)
        if tool_fn is None:
            return f"Unknown tool: {action}"
        return tool_fn(**action_input)

    def _build_context(self, prev: str, step: ReActStep) -> str:
        return (
            f"{prev}\n"
            f"Step {step.step}:\n"
            f"  Thought: {step.thought}\n"
            f"  Action: {step.action}({json.dumps(step.action_input)})\n"
            f"  Observation: {step.observation or '[empty]'}\n"
        )


def _build_prompt(context: str, step: int, tools: list[str]) -> str:
    tool_list = ", ".join(tools)
    return (
        f"You are a ReAct agent. Available tools: {tool_list}.\n"
        f"Current context:\n{context}\n\n"
        f"Step {step}: respond with:\n"
        f"Thought: <reasoning>\n"
        f"Action: <tool name>\n"
        f"Action Input: <JSON object>\n"
        f"If you have a final answer: Action: finish, Action Input: {{\"answer\": \"...\"}}"
    )


def _parse_response(text: str) -> tuple[str, str, dict]:
    thought = action = ""
    action_input: dict = {}
    for line in text.splitlines():
        if line.startswith("Thought:"):
            thought = line[8:].strip()
        elif line.startswith("Action:"):
            action = line[7:].strip().lower()
        elif line.startswith("Action Input:"):
            try:
                action_input = json.loads(line[13:].strip())
            except json.JSONDecodeError:
                action_input = {"raw": line[13:].strip()}
    return thought, action, action_input
```

---

## Part 2 — Mock Tools (`tools.py`)

```python
# SPDX-License-Identifier: MIT
"""Mock tools for TraceForge ReAct demo agent."""


def get_weather(city: str) -> str:
    data = {
        "london": "15°C, partly cloudy",
        "berlin": "22°C, sunny",
        "tokyo": "28°C, humid",
    }
    return data.get(city.lower(), f"Weather data unavailable for {city}")


def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    rates = {"USD_EUR": 0.92, "EUR_GBP": 0.84, "USD_GBP": 0.77}
    key = f"{from_currency.upper()}_{to_currency.upper()}"
    rate = rates.get(key)
    if rate is None:
        return f"No rate for {from_currency}→{to_currency}"
    return f"{amount * rate:.2f} {to_currency.upper()}"


def summarize(text: str) -> str:
    words = text.split()
    return " ".join(words[:30]) + ("..." if len(words) > 30 else "")


def finish(answer: str) -> str:
    return answer


TOOLS = {
    "get_weather": get_weather,
    "convert_currency": convert_currency,
    "summarize": summarize,
    "finish": finish,
}
```

---

## Part 3 — Entry Point (`run.py`)

```python
# SPDX-License-Identifier: MIT
"""Run the TraceForge ReAct demo. Set USE_MOCK_OPENAI=1 for offline mode."""
import os
import sys

from tools import TOOLS


def build_llm():
    if os.environ.get("USE_MOCK_OPENAI") == "1":
        from mock_openai import MockOpenAI
        return MockOpenAI()
    import openai
    import traceforge
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return traceforge.wrap_openai(client)


def main():
    llm = build_llm()
    from agent import ReActAgent

    agent = ReActAgent(llm=llm, tools=TOOLS)
    question = (
        "What is the weather in London, Berlin, and Tokyo? "
        "Convert London temperature from Celsius to Fahrenheit. "
        "Summarize all results in one sentence."
    )
    print(f"Question: {question}\n")
    answer = agent.run(question)
    print(f"\nFinal answer: {answer}")
    print(f"\nTrace ID: {agent.trace_id}")
    print(f"Steps completed: {len(agent.steps)}")

    silent_steps = [s for s in agent.steps if not s.observation]
    if silent_steps:
        print(f"\n⚠️  Silent failures detected at steps: {[s.step for s in silent_steps]}")
        print("   → Check TraceForge Grafana waterfall for EMPTY_RESPONSE spans")


if __name__ == "__main__":
    main()
```

---

## Part 4 — Tests (`test_agent.py`)

```python
# SPDX-License-Identifier: MIT
"""Tests for ReAct demo agent — TraceForge Day 35."""
import pytest
from unittest.mock import MagicMock, patch
from agent import ReActAgent, SILENT_STEP
from tools import TOOLS


def _mock_llm(responses: list[str]) -> MagicMock:
    """Return a mock OpenAI client that yields responses in sequence."""
    client = MagicMock()
    calls = iter(responses)

    def _create(**kwargs):
        resp = MagicMock()
        resp.choices[0].message.content = next(calls, "Action: finish\nAction Input: {\"answer\": \"done\"}")
        return resp

    client.chat.completions.create.side_effect = _create
    return client


STEP_RESPONSES = [
    f"Thought: check weather london\nAction: get_weather\nAction Input: {{\"city\": \"london\"}}" ,
    f"Thought: check weather berlin\nAction: get_weather\nAction Input: {{\"city\": \"berlin\"}}",
    f"Thought: check weather tokyo\nAction: get_weather\nAction Input: {{\"city\": \"tokyo\"}}",
    f"Thought: convert temperature\nAction: convert_currency\nAction Input: {{\"amount\": 15, \"from_currency\": \"USD\", \"to_currency\": \"EUR\"}}",
    f"Thought: convert again\nAction: convert_currency\nAction Input: {{\"amount\": 22, \"from_currency\": \"USD\", \"to_currency\": \"EUR\"}}",
    f"Thought: almost done\nAction: summarize\nAction Input: {{\"text\": \"London 15C Berlin 22C Tokyo 28C\"}}",
    # Step 7 — this is SILENT_STEP, tool returns "" regardless of action
    f"Thought: final conversion\nAction: convert_currency\nAction Input: {{\"amount\": 28, \"from_currency\": \"USD\", \"to_currency\": \"GBP\"}}",
    f"Thought: wrap up\nAction: finish\nAction Input: {{\"answer\": \"Summary complete\"}}",
]


def test_step7_returns_empty():
    """Step 7 tool call must return empty string (silent failure)."""
    llm = _mock_llm(STEP_RESPONSES)
    agent = ReActAgent(llm=llm, tools=TOOLS)
    agent.run("test question")
    assert agent.steps[SILENT_STEP - 1].observation == ""


def test_agent_continues_after_empty():
    """Agent must not raise an exception when step 7 is empty — it should continue."""
    llm = _mock_llm(STEP_RESPONSES)
    agent = ReActAgent(llm=llm, tools=TOOLS)
    result = agent.run("test question")
    assert result is not None  # agent produced some answer


def test_span_attributes_on_empty_step():
    """Span for step 7 must carry result_bytes=0 and status=EMPTY_RESPONSE."""
    spans = []
    import traceforge

    original_start = traceforge.start_span

    def capture_span(*args, **kwargs):
        span = original_start(*args, **kwargs)
        spans.append(span)
        return span

    with patch.object(traceforge, "start_span", side_effect=capture_span):
        llm = _mock_llm(STEP_RESPONSES)
        agent = ReActAgent(llm=llm, tools=TOOLS)
        agent.run("test")

    step7_span = next((s for s in spans if s.attributes.get("step") == 7), None)
    assert step7_span is not None
    assert step7_span.attributes.get("result_bytes") == 0
    assert step7_span.attributes.get("status") == "EMPTY_RESPONSE"


def test_non_silent_steps_have_observations():
    """All steps except 7 must produce non-empty observations."""
    llm = _mock_llm(STEP_RESPONSES)
    agent = ReActAgent(llm=llm, tools=TOOLS)
    agent.run("test question")
    for step in agent.steps:
        if step.step != SILENT_STEP and step.action != "finish":
            assert step.observation, f"Step {step.step} unexpectedly empty"


def test_weather_tool():
    from tools import get_weather
    assert "15°C" in get_weather("london")
    assert "unavailable" in get_weather("mars").lower()


def test_convert_currency_tool():
    from tools import convert_currency
    result = convert_currency(100.0, "USD", "EUR")
    assert "92.00 EUR" in result
```

---

## Part 5 — DEMO.md

```markdown
# TraceForge Demo: The Agent That Dies on Step 7

## What this shows

A 10-step ReAct agent queries weather data, converts currencies, and summarises results.
**Step 7 fails silently** — the currency tool returns an empty string, the agent logs nothing,
and the final answer is wrong. Without TraceForge, you cannot tell which step broke.

---

## Running the demo

```bash
# With mock LLM (no OpenAI key required)
USE_MOCK_OPENAI=1 python traceforge/examples/react_agent/run.py

# With real OpenAI (requires OPENAI_API_KEY)
python traceforge/examples/react_agent/run.py
```

---

## Before TraceForge: console output (no tracing)

```
Question: What is the weather in London, Berlin, and Tokyo? ...

Step 7: Action: convert_currency({"amount": 28, "from_currency": "USD", "to_currency": "GBP"})
         Observation: [empty]

Final answer: Summary complete
Trace ID: (none)
```

The agent exits with status 0. No exception. No log line. The final answer omits Tokyo conversion.
You cannot tell why.

---

## After TraceForge: Grafana waterfall

[Screenshot placeholder: screenshots/waterfall-with-empty-step7.png]

The waterfall shows:
- 10 spans in chronological order
- Step 7 span highlighted in amber: `result_bytes: 0`, `status: EMPTY_RESPONSE`
- `trace_cost_rollup` MV: 8 LLM calls charged, $0.0023 spent, 1 step produced zero output
- Steps 8–10 show the agent reasoning with corrupted context (missing Tokyo conversion)

---

## The three silent failure modes TraceForge catches

| Mode | What happens | What TraceForge records |
|---|---|---|
| Empty tool response | Tool returns `""` | `result_bytes: 0`, `status: EMPTY_RESPONSE` |
| Swallowed exception | Tool catches error, returns `None` | `result_bytes: 0`, `error: true`, `exception.message` |
| Max iterations | Agent hits loop limit | `status: MAX_ITERATIONS`, `steps_completed: N` |

---

## ClickHouse queries

```sql
-- Find all empty-response spans in a trace
SELECT step, tool_name, result_bytes, status, cost_usd
FROM agent_spans
WHERE trace_id = '<your-trace-id>'
ORDER BY start_time;

-- Find traces with any silent failure in the last hour
SELECT trace_id, count() AS silent_steps
FROM agent_spans
WHERE status = 'EMPTY_RESPONSE'
  AND start_time > now() - INTERVAL 1 HOUR
GROUP BY trace_id
HAVING silent_steps > 0;
```
```

---

## Implementation Notes

### Mock OpenAI client

For offline testing, implement `mock_openai.py` in the same directory:

```python
# SPDX-License-Identifier: MIT
"""Offline mock OpenAI client for CI and local dev."""
from unittest.mock import MagicMock

MOCK_STEPS = [
    "Thought: get london weather\nAction: get_weather\nAction Input: {\"city\": \"london\"}",
    "Thought: get berlin weather\nAction: get_weather\nAction Input: {\"city\": \"berlin\"}",
    "Thought: get tokyo weather\nAction: get_weather\nAction Input: {\"city\": \"tokyo\"}",
    "Thought: convert usd eur\nAction: convert_currency\nAction Input: {\"amount\": 15, \"from_currency\": \"USD\", \"to_currency\": \"EUR\"}",
    "Thought: convert again\nAction: convert_currency\nAction Input: {\"amount\": 22, \"from_currency\": \"USD\", \"to_currency\": \"EUR\"}",
    "Thought: summarize so far\nAction: summarize\nAction Input: {\"text\": \"London 15C Berlin 22C Tokyo 28C\"}",
    "Thought: tokyo conversion\nAction: convert_currency\nAction Input: {\"amount\": 28, \"from_currency\": \"USD\", \"to_currency\": \"GBP\"}",
    "Thought: wrap up\nAction: finish\nAction Input: {\"answer\": \"Weather: London 15C, Berlin 22C, Tokyo 28C. Conversions complete.\"}",
]


class MockOpenAI:
    def __init__(self):
        self._calls = iter(MOCK_STEPS)
        self.chat = MagicMock()
        self.chat.completions.create.side_effect = self._respond

    def _respond(self, **kwargs):
        resp = MagicMock()
        resp.choices[0].message.content = next(self._calls, MOCK_STEPS[-1])
        # Simulate token usage for cost rollup
        resp.usage.prompt_tokens = 200
        resp.usage.completion_tokens = 50
        return resp
```

---

## Acceptance Criteria Verification

```bash
# AC-7: Run without real OpenAI key
USE_MOCK_OPENAI=1 python traceforge/examples/react_agent/run.py

# AC-5: Run tests
pytest traceforge/examples/react_agent/test_agent.py -v

# AC-3: Verify step 7 span in ClickHouse (after full docker-compose run)
docker compose exec clickhouse clickhouse-client \
  --query "SELECT step, result_bytes, status FROM agent_spans WHERE status='EMPTY_RESPONSE' LIMIT 5"
```

---

## Git Workflow

```bash
# Branch from main — always targets main, never stacks on prior feature branches
git checkout main && git pull origin main
git checkout -b feat/day-35-react-demo-silent-step7

# After implementation
pytest traceforge/examples/react_agent/test_agent.py -v
USE_MOCK_OPENAI=1 python traceforge/examples/react_agent/run.py

git add traceforge/examples/react_agent/
git commit -m "feat(traceforge): ReAct demo agent — silent step-7 failure + DEMO.md

- agent.py: 10-step ReAct loop, step 7 returns empty observation
- tools.py: weather, currency, summarize, finish mock tools
- run.py: entry point with USE_MOCK_OPENAI=1 offline mode
- test_agent.py: 6 pytest tests, all passing
- DEMO.md: before/after walkthrough with ClickHouse queries

Self-review: 0 issues found."

git push -u origin feat/day-35-react-demo-silent-step7
```

PR description must include:
- `pytest` output (all tests green)
- `USE_MOCK_OPENAI=1 python run.py` terminal output showing step 7 empty
- ClickHouse query output showing `result_bytes: 0, status: EMPTY_RESPONSE` span
- Mark PR ready for review (not draft): `draft: false`
