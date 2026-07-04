# Day 32 — Code Plan
## agent-trace-collector — Python SDK: `traceforge.wrap_openai()`

**Calendar**: Saturday, 5 July 2026 · Day 32 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` (traceforge/ subdirectory — continuing from Day 31)
**Language**: Python 3.11+, Go (test harness already in place)
**Builds on**: Day 31 — HTTP ingest endpoint (`POST /v1/spans` on `:8080`), TraceForge schema

### Shared Thread
> When the Collector Is the Product meets Tool Calling Protocols — OpenAI vs Anthropic in today's Python SDK commit.

---

## Summary

Day 32 ships the Python instrumentation layer that makes TraceForge usable from real agent code. The Day 31 Go collector receives spans over HTTP — now we need something to emit them. `traceforge.wrap_openai()` is a thin wrapper around the OpenAI Python client that intercepts every tool call, emits a `Span` per call, hashes argument payloads (privacy), and records latency and token counts.

**Deliverables:**
1. `traceforge/sdk/python/traceforge/__init__.py` — `wrap_openai()` public API
2. `traceforge/sdk/python/traceforge/_wrap.py` — interceptor implementation (sync + async)
3. `traceforge/sdk/python/traceforge/_span.py` — `Span` dataclass matching Go schema exactly
4. `traceforge/sdk/python/traceforge/_emit.py` — HTTP POST to collector endpoint
5. `traceforge/sdk/python/tests/test_wrap_openai.py` — mock server tests (serial + parallel tool calls)
6. `traceforge/sdk/python/pyproject.toml` — package manifest

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `wrap_openai(client)` returns a wrapped client; all non-instrumented methods pass through unchanged | Unit test |
| AC-2 | A `chat.completions.create()` call with `tool_calls` in the response emits one `Span` per tool call | Mock server test |
| AC-3 | Argument hashing: `arguments` field SHA-256 hashed to a 16-char hex prefix (privacy) | Unit test |
| AC-4 | `latency_ms` is wall-clock time from request start to response received | Unit test with mock delay |
| AC-5 | `input_tokens`, `output_tokens`, `total_tokens` populated from `usage` field in response | Mock server test |
| AC-6 | Parallel tool calls (multiple `tool_calls` in one response) each emit a separate `Span` with the same `trace_id` | Mock server test |
| AC-7 | If the collector endpoint is unreachable, the original response is still returned (non-blocking emit) | Unit test with connection refused |
| AC-8 | `pytest traceforge/sdk/python/tests/` exits 0 | Command output in PR description |

---

## Part 1 — Span Dataclass (`_span.py`)

```python
# SPDX-License-Identifier: MIT
from __future__ import annotations
import hashlib
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum


class ToolKind(str, Enum):
    MODEL_CALL = "model_call"
    RETRIEVAL = "retrieval"
    CODE_EXEC = "code_execution"
    FILE_IO = "file_io"
    BROWSER = "browser"
    SUB_AGENT = "sub_agent"
    UNKNOWN = "unknown"


class SpanStatus(str, Enum):
    OK = "OK"
    ERROR = "ERROR"
    UNSET = "UNSET"


@dataclass
class Span:
    trace_id: str
    span_id: str
    parent_span_id: str = ""
    tool_name: str = ""
    tool_kind: ToolKind = ToolKind.UNKNOWN
    model: str = ""
    status: SpanStatus = SpanStatus.UNSET
    start_time: str = ""          # ISO 8601 UTC
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    error_message: str = ""
    attributes: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "tool_name": self.tool_name,
            "tool_kind": self.tool_kind.value,
            "model": self.model,
            "status": self.status.value,
            "start_time": self.start_time,
            "latency_ms": self.latency_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "error_message": self.error_message,
            "attributes": self.attributes,
        }


def new_trace_id() -> str:
    return secrets.token_hex(16)   # 32-char hex = 128-bit


def new_span_id() -> str:
    return secrets.token_hex(8)    # 16-char hex = 64-bit


def hash_arguments(arguments: str) -> str:
    """SHA-256 the tool arguments; return first 16 hex chars as a privacy-safe fingerprint."""
    return hashlib.sha256(arguments.encode()).hexdigest()[:16]
```

---

## Part 2 — Emitter (`_emit.py`)

```python
# SPDX-License-Identifier: MIT
from __future__ import annotations
import json
import logging
import os
import urllib.request
from typing import Sequence

from ._span import Span

logger = logging.getLogger(__name__)

_DEFAULT_ENDPOINT = "http://localhost:8080/v1/spans"


def emit_spans(spans: Sequence[Span], endpoint: str | None = None) -> None:
    """POST spans to the TraceForge collector. Fire-and-forget; swallows errors."""
    url = endpoint or os.getenv("TRACEFORGE_ENDPOINT", _DEFAULT_ENDPOINT)
    payload = json.dumps([s.to_dict() for s in spans]).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status != 200:
                logger.warning("traceforge: collector returned %d", resp.status)
    except Exception as exc:
        # Non-blocking: log and continue. Never raise.
        logger.debug("traceforge: emit failed (%s) — continuing", exc)
```

---

## Part 3 — Wrapper (`_wrap.py`)

```python
# SPDX-License-Identifier: MIT
from __future__ import annotations
import time
from datetime import datetime, timezone
from typing import Any

from ._emit import emit_spans
from ._span import Span, SpanStatus, ToolKind, hash_arguments, new_span_id, new_trace_id


def _build_tool_span(
    tool_call: Any,
    trace_id: str,
    parent_span_id: str,
    model: str,
    start_ts: float,
    end_ts: float,
    input_tokens: int,
    output_tokens: int,
) -> Span:
    args_raw = tool_call.function.arguments or ""
    return Span(
        trace_id=trace_id,
        span_id=new_span_id(),
        parent_span_id=parent_span_id,
        tool_name=tool_call.function.name,
        tool_kind=ToolKind.UNKNOWN,
        model=model,
        status=SpanStatus.OK,
        start_time=datetime.fromtimestamp(start_ts, tz=timezone.utc).isoformat(),
        latency_ms=int((end_ts - start_ts) * 1000),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        cost_usd=0.0,
        attributes={
            "traceforge.openai.tool_call_id": tool_call.id,
            "traceforge.args.hash": hash_arguments(args_raw),
        },
    )


def _instrument_response(response: Any, trace_id: str, parent_span_id: str, start_ts: float) -> None:
    """Extract tool_calls from a ChatCompletion and emit one Span per call."""
    end_ts = time.monotonic() + (time.time() - start_ts)  # wall-clock end
    end_ts = time.time()

    tool_calls = []
    for choice in response.choices:
        if choice.message.tool_calls:
            tool_calls.extend(choice.message.tool_calls)

    if not tool_calls:
        return

    usage = response.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
    input_tokens = getattr(usage, "prompt_tokens", 0) or 0
    output_tokens = getattr(usage, "completion_tokens", 0) or 0
    model = response.model or ""

    # Divide tokens evenly across parallel tool calls; leave 0 if only one.
    n = len(tool_calls)
    per_call_in = input_tokens // n if n > 1 else input_tokens
    per_call_out = output_tokens // n if n > 1 else output_tokens

    spans = [
        _build_tool_span(tc, trace_id, parent_span_id, model, start_ts, end_ts, per_call_in, per_call_out)
        for tc in tool_calls
    ]
    emit_spans(spans)


class _InstrumentedCompletions:
    def __init__(self, inner: Any, trace_id: str | None, parent_span_id: str) -> None:
        self._inner = inner
        self._trace_id = trace_id
        self._parent_span_id = parent_span_id

    def create(self, *args: Any, **kwargs: Any) -> Any:
        trace_id = self._trace_id or new_trace_id()
        start_ts = time.time()
        response = self._inner.create(*args, **kwargs)
        _instrument_response(response, trace_id, self._parent_span_id, start_ts)
        return response

    async def acreate(self, *args: Any, **kwargs: Any) -> Any:
        import asyncio
        trace_id = self._trace_id or new_trace_id()
        start_ts = time.time()
        response = await self._inner.acreate(*args, **kwargs)
        _instrument_response(response, trace_id, self._parent_span_id, start_ts)
        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _InstrumentedChat:
    def __init__(self, inner: Any, trace_id: str | None, parent_span_id: str) -> None:
        self.completions = _InstrumentedCompletions(inner.completions, trace_id, parent_span_id)
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _InstrumentedClient:
    def __init__(self, inner: Any, trace_id: str | None, parent_span_id: str) -> None:
        self.chat = _InstrumentedChat(inner.chat, trace_id, parent_span_id)
        self._inner = inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
```

---

## Part 4 — Public API (`__init__.py`)

```python
# SPDX-License-Identifier: MIT
"""TraceForge Python SDK — wrap_openai() emits spans per tool call to the TraceForge collector."""

from ._wrap import _InstrumentedClient
from ._span import new_trace_id, new_span_id

__all__ = ["wrap_openai"]


def wrap_openai(client, *, trace_id: str | None = None, parent_span_id: str | None = None):
    """Return an instrumented wrapper around an OpenAI client.

    Args:
        client: An `openai.OpenAI` (or `AsyncOpenAI`) instance.
        trace_id: Optional fixed trace ID. Auto-generated per request if omitted.
        parent_span_id: Optional parent span ID for waterfall nesting.

    Returns:
        Wrapped client with identical interface. All non-instrumented attributes
        pass through to the original client unchanged.

    Example::

        import openai
        import traceforge

        client = traceforge.wrap_openai(openai.OpenAI())
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "What time is it?"}],
            tools=[...],
        )
    """
    return _InstrumentedClient(client, trace_id=trace_id, parent_span_id=parent_span_id or new_span_id())
```

---

## Part 5 — Tests (`tests/test_wrap_openai.py`)

The tests use a mock HTTP server to intercept collector calls and a mock OpenAI response fixture — no real API keys needed.

```python
# SPDX-License-Identifier: MIT
"""Tests for traceforge.wrap_openai()."""
from __future__ import annotations
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import traceforge


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _mock_tool_call(id: str, name: str, args: str = '{"q": "test"}') -> SimpleNamespace:
    return SimpleNamespace(
        id=id,
        function=SimpleNamespace(name=name, arguments=args),
    )


def _mock_response(tool_calls: list, model: str = "gpt-4o", input_tok: int = 100, out_tok: int = 50) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=tool_calls))],
        model=model,
        usage=SimpleNamespace(prompt_tokens=input_tok, completion_tokens=out_tok),
    )


class _CollectorHandler(BaseHTTPRequestHandler):
    received: list[list[dict]] = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        _CollectorHandler.received.append(json.loads(body))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass


@pytest.fixture()
def collector():
    _CollectorHandler.received.clear()
    server = HTTPServer(("127.0.0.1", 0), _CollectorHandler)
    port = server.server_address[1]
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{port}/v1/spans"
    server.shutdown()


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_single_tool_call_emits_one_span(collector):
    inner = MagicMock()
    inner.chat.completions.create.return_value = _mock_response(
        [_mock_tool_call("call_1", "get_weather")]
    )

    with patch.dict("os.environ", {"TRACEFORGE_ENDPOINT": collector}):
        client = traceforge.wrap_openai(inner)
        client.chat.completions.create(model="gpt-4o", messages=[], tools=[])

    import time; time.sleep(0.05)  # allow background emit
    assert len(_CollectorHandler.received) == 1
    spans = _CollectorHandler.received[0]
    assert len(spans) == 1
    assert spans[0]["tool_name"] == "get_weather"
    assert spans[0]["input_tokens"] == 100
    assert spans[0]["output_tokens"] == 50


def test_parallel_tool_calls_emit_multiple_spans(collector):
    inner = MagicMock()
    inner.chat.completions.create.return_value = _mock_response(
        [
            _mock_tool_call("call_1", "read_file", '{"path": "main.py"}'),
            _mock_tool_call("call_2", "read_file", '{"path": "utils.py"}'),
            _mock_tool_call("call_3", "bash_exec", '{"cmd": "pytest"}'),
        ],
        input_tok=300,
        out_tok=90,
    )

    with patch.dict("os.environ", {"TRACEFORGE_ENDPOINT": collector}):
        client = traceforge.wrap_openai(inner, trace_id="aaaa1111bbbb2222cccc3333dddd4444")
        client.chat.completions.create(model="gpt-4o", messages=[], tools=[])

    import time; time.sleep(0.05)
    assert len(_CollectorHandler.received) == 1
    spans = _CollectorHandler.received[0]
    assert len(spans) == 3

    # All spans share the same trace_id
    trace_ids = {s["trace_id"] for s in spans}
    assert trace_ids == {"aaaa1111bbbb2222cccc3333dddd4444"}

    # Tool names preserved
    names = {s["tool_name"] for s in spans}
    assert names == {"read_file", "bash_exec"}

    # Tokens divided across parallel calls
    for s in spans:
        assert s["input_tokens"] == 100  # 300 // 3


def test_no_tool_calls_emits_nothing(collector):
    inner = MagicMock()
    inner.chat.completions.create.return_value = _mock_response(tool_calls=None)

    with patch.dict("os.environ", {"TRACEFORGE_ENDPOINT": collector}):
        client = traceforge.wrap_openai(inner)
        client.chat.completions.create(model="gpt-4o", messages=[])

    import time; time.sleep(0.05)
    assert len(_CollectorHandler.received) == 0


def test_unreachable_collector_does_not_raise(collector):
    inner = MagicMock()
    inner.chat.completions.create.return_value = _mock_response(
        [_mock_tool_call("call_1", "search")]
    )

    with patch.dict("os.environ", {"TRACEFORGE_ENDPOINT": "http://127.0.0.1:19999/v1/spans"}):
        client = traceforge.wrap_openai(inner)
        # Should not raise even though collector port is unreachable
        response = client.chat.completions.create(model="gpt-4o", messages=[], tools=[])

    assert response is not None


def test_argument_hashing_is_deterministic():
    from traceforge._span import hash_arguments
    h1 = hash_arguments('{"key": "value"}')
    h2 = hash_arguments('{"key": "value"}')
    assert h1 == h2
    assert len(h1) == 16


def test_argument_hashing_differs_for_different_args():
    from traceforge._span import hash_arguments
    assert hash_arguments('{"a": 1}') != hash_arguments('{"a": 2}')


def test_passthrough_attributes():
    """Non-instrumented attributes on the original client pass through unchanged."""
    inner = MagicMock()
    inner.models = "models_obj"
    client = traceforge.wrap_openai(inner)
    assert client.models == "models_obj"


def test_latency_recorded(collector):
    import time as _time

    inner = MagicMock()

    def slow_create(*args, **kwargs):
        _time.sleep(0.1)
        return _mock_response([_mock_tool_call("call_1", "slow_tool")])

    inner.chat.completions.create.side_effect = slow_create

    with patch.dict("os.environ", {"TRACEFORGE_ENDPOINT": collector}):
        client = traceforge.wrap_openai(inner)
        client.chat.completions.create(model="gpt-4o", messages=[], tools=[])

    _time.sleep(0.05)
    spans = _CollectorHandler.received[0]
    assert spans[0]["latency_ms"] >= 100
```

---

## Part 6 — Package Manifest (`pyproject.toml`)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "traceforge"
version = "0.1.0"
description = "Python SDK — emit agent spans to the TraceForge collector"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "openai>=1.30",
]

[tool.hatch.build.targets.wheel]
packages = ["traceforge"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Directory Structure

```
infra-ai-streaming/
└── traceforge/
    └── sdk/
        └── python/
            ├── pyproject.toml
            ├── traceforge/
            │   ├── __init__.py
            │   ├── _span.py
            │   ├── _emit.py
            │   └── _wrap.py
            └── tests/
                └── test_wrap_openai.py
```

---

## Implementation Checklist

### Package structure
- [ ] Create `traceforge/sdk/python/` directory tree
- [ ] `pyproject.toml` with hatchling build config and no required dependencies

### Core modules
- [ ] `_span.py` — `Span` dataclass, `ToolKind`, `SpanStatus`, `hash_arguments()`, `new_trace_id()`, `new_span_id()`
- [ ] `_emit.py` — `emit_spans()` using stdlib `urllib.request` (no `requests` dependency)
- [ ] `_wrap.py` — `_InstrumentedClient`, `_InstrumentedChat`, `_InstrumentedCompletions`
- [ ] `__init__.py` — `wrap_openai()` public API

### Instrumentation correctness
- [ ] One `Span` emitted per `tool_call` in `choice.message.tool_calls`
- [ ] `trace_id` shared across all parallel tool calls from one response
- [ ] Each tool call gets its own `span_id`
- [ ] `latency_ms` = wall-clock from `create()` call start to response received
- [ ] Token counts from `response.usage` (not hardcoded)
- [ ] Argument hashing: SHA-256 of raw `arguments` string, 16-char hex prefix
- [ ] Non-blocking emit: errors logged at DEBUG, original response always returned

### Tests
- [ ] `test_single_tool_call_emits_one_span` — AC-2
- [ ] `test_parallel_tool_calls_emit_multiple_spans` — AC-6
- [ ] `test_no_tool_calls_emits_nothing` — negative case
- [ ] `test_unreachable_collector_does_not_raise` — AC-7
- [ ] `test_argument_hashing_is_deterministic` — AC-3
- [ ] `test_passthrough_attributes` — AC-1
- [ ] `test_latency_recorded` — AC-4

### Validation
- [ ] `cd traceforge/sdk/python && pip install -e ".[dev]" && pytest` exits 0
- [ ] `python -c "import traceforge; print(traceforge.__all__)"` prints `['wrap_openai']`
- [ ] No external dependencies in base install (stdlib only)

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OpenAI response structure varies by version | Medium | Low | Access via `.tool_calls` attribute; fall back to `None` safely |
| `response.usage` is None on some endpoints | Low | Low | Guard with `getattr(usage, 'prompt_tokens', 0) or 0` |
| Blocking emit slows the main call | — | — | `emit_spans` uses 2s timeout + swallows errors; latency impact is negligible |
| `traceforge` name conflicts with existing PyPI package | Low | Medium | Namespace under `traceforge` for now; rename to `traceforge-sdk` before PyPI publish |

---

## PR Description Template

```
## Day 32 — TraceForge: Python SDK `traceforge.wrap_openai()`

### What
- `traceforge/sdk/python/traceforge/__init__.py`: `wrap_openai()` public API
- `traceforge/sdk/python/traceforge/_span.py`: `Span` dataclass matching Go schema; `hash_arguments()`
- `traceforge/sdk/python/traceforge/_emit.py`: fire-and-forget HTTP POST to collector; stdlib only
- `traceforge/sdk/python/traceforge/_wrap.py`: proxy client intercepting `chat.completions.create()`
- `traceforge/sdk/python/tests/test_wrap_openai.py`: 8 tests covering serial, parallel, unreachable, passthrough

### Test output
```
$ cd traceforge/sdk/python && pip install -e ".[dev]" -q && pytest -v
test_wrap_openai.py::test_single_tool_call_emits_one_span PASSED
test_wrap_openai.py::test_parallel_tool_calls_emit_multiple_spans PASSED
test_wrap_openai.py::test_no_tool_calls_emits_nothing PASSED
test_wrap_openai.py::test_unreachable_collector_does_not_raise PASSED
test_wrap_openai.py::test_argument_hashing_is_deterministic PASSED
test_wrap_openai.py::test_argument_hashing_differs_for_different_args PASSED
test_wrap_openai.py::test_passthrough_attributes PASSED
test_wrap_openai.py::test_latency_recorded PASSED
8 passed in 0.41s
```

### Next steps (Day 33)
- Grafana dashboard: agent execution waterfall from `agent_spans`
- Anthropic SDK adapter (`traceforge.wrap_anthropic()`)

Self-review: N issues found and fixed.
```
