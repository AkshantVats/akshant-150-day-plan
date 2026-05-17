#!/usr/bin/env python3
"""Build ultra-detailed plan-days-0-74.json for Akshant's 150-day platform plan."""
import json
from datetime import date, timedelta

START = date(2026, 5, 12)  # Day 0 = Tuesday May 12, 2026; Day 4 = May 16 (today)


def weekday(d: int) -> str:
    return (START + timedelta(days=d)).strftime("%A")


def status(d: int) -> str:
    if d <= 3:
        return "done"
    if d == 4:
        return "today"
    return "pending"


def repo_for(day: int) -> str:
    if day <= 13:
        return "infra-ai-streaming"
    if day <= 20:
        return "ebpf-llm-tracer"
    if day <= 27:
        return "distributed-flagd"
    if day <= 29:
        return "lensai-integration"
    if day <= 36:
        return "agent-trace-collector"
    if day <= 43:
        return "tool-call-analyzer"
    if day <= 50:
        return "agent-replay-engine"
    if day <= 59:
        return "agent-benchmark-runner"
    if day <= 64:
        return "semantic-cache-engine"
    if day <= 69:
        return "cost-budget-enforcer"
    return "prompt-fingerprinter"


def product_for(day: int) -> tuple[str, str]:
    if day <= 29:
        return "lensai", "LensAI"
    if day <= 59:
        return "traceforge", "TraceForge"
    return "routeiq", "RouteIQ"


def is_friday(day: int) -> bool:
    return (START + timedelta(days=day)).weekday() == 4


# --- Days 0-30: code from akshant_30day_daily_plan.html, repos remapped per 150-day plan ---
CODE_0_30 = {
    0: (
        "Launch Day — public identity + repo scaffold. "
        "(1) Rewrite LinkedIn headline to Staff Engineer | Distributed Systems + AI Infra | Rust · Kafka · Kubernetes | ex-Agoda 1.5T/day TSDB · Delivery Hero · Walmart 7M sensors; refresh About with strongest numbers. "
        "(2) Rewrite GitHub profile README: who you are (2 lines), what you're building (flagship project), technical bets (Rust infra + AI observability), 'Currently building' placeholder. Dark-mode friendly, no emojis. "
        "(3) Create repo infra-ai-streaming: README only today — problem statement (why existing observability fails for LLM inference at scale), Mermaid architecture overview, target metrics (1M events/min, sub-100ms ingestion P99). Pin repo to profile."
    ),
    1: (
        "DESIGN.md for infra-ai-streaming (Staff-level artifact before more code): "
        "(1) Problem & Goals, (2) CAP — why AP over CP for ingestion, (3) Partition strategy — avoid hot partitions on model_id, "
        "(4) Backpressure — channel-based Rust ingestion, (5) Failure modes — Kafka down, ClickHouse slow, (6) Horizontal scaling plan, "
        "(7) Consistency model for analytics queries. This doc drives every later schema field."
    ),
    2: (
        "Ticket G-01 — Rust ingestion core: Axum HTTP server with POST /ingest accepting batched JSON events "
        "(model_id, latency_ms, prompt_tokens, completion_tokens, cost_usd, tenant_id). Async Kafka producer via rdkafka. "
        "Channel-based backpressure with configurable buffer size. Graceful shutdown. Verify events reach Kafka topic locally. "
        "Commit messages describe design decisions, not 'added ingestion'."
    ),
    3: (
        "Ticket G-01 (complete) — Rust ingestion core: Axum POST /ingest, rdkafka producer, channel backpressure, graceful shutdown. "
        "Verify events on Kafka. Publish Experience (Agoda quantile merge) + AI Learning Day 2 (continuous batching) if not already live."
    ),
    4: (
        "Ticket G-02 — Local dev stack + Go consumer skeleton. "
        "docker-compose.yml: Kafka (Redpanda), ClickHouse, Redis, Grafana, Prometheus — single `docker compose up`. "
        "Go consumer reads Kafka topic, logs to stdout (ClickHouse write on Day 5). Wire Rust producer → Kafka → Go consumer; verify with test event."
    ),
    5: (
        "Ticket G-03 — ClickHouse batch writer in Go consumer: buffer 1000 events OR 500ms flush, whichever first. "
        "Circuit breaker — if ClickHouse down, overflow to Redis sorted set, retry with exponential backoff. "
        "DLQ Kafka topic for events failing after 3 retries. Add OBSERVABILITY.md: ingestion_latency_ms P50/P95/P99, consumer lag, write throughput, DLQ depth, circuit breaker state — list every Prometheus metric and label cardinality."
    ),
    6: (
        "Ticket G-04 — OpenTelemetry tracing on Rust ingestion: trace each batch HTTP receipt → Kafka produce → consumer ack. "
        "Prometheus metrics: ingestion_latency_ms histogram, kafka_produce_errors_total, batch_size_events histogram. "
        "k6 load test at 1k, 10k, 50k events/sec. Write BENCHMARKS.md with results table, hardware spec, interpretation."
    ),
    7: (
        "Ticket G-05 — Grafana dashboard (4 panels): (1) ingestion throughput events/sec by tenant, (2) P99 inference latency by model_id, "
        "(3) token cost/hour per tenant, (4) Kafka consumer lag trend. Export JSON to /dashboards; screenshot for README. "
        "Update resume Open Source section + LinkedIn Featured with infra-ai-streaming link."
    ),
    8: (
        "Ticket G-06 — Token-bucket rate limiting in Rust ingestion per tenant_id (Redis shared counter for multi-instance). "
        "Per-tenant config: max events/sec, burst. Return 429 + Retry-After when exceeded. Write CHAOS.md: 5 failure scenarios — "
        "Kafka broker dies mid-ingest, ClickHouse timeout, Redis lost, ingestion OOM, network partition — expected behavior and recovery for each."
    ),
    9: (
        "Ticket G-07 — Helm charts for full stack: ingestion-engine HPA on custom Kafka lag metric, Redpanda, ClickHouse, Redis. "
        "Resource requests/limits, liveness/readiness probes, PodDisruptionBudget maxUnavailable:1, ConfigMap for tenant config. "
        "Deploy to local k3d; verify end-to-end. Add deploy/README.md with 3-command deploy."
    ),
    10: (
        "Portfolio site v1 on GitHub Pages: name, positioning, 3 project cards with status badges, LinkedIn/GitHub links, Writing section. "
        "Minimal dark HTML, no frameworks. URL goes on resume header."
    ),
    11: (
        "chaos/run_chaos.sh: (1) kill Redpanda mid-ingest, restart after 30s — verify zero loss via DLQ + WAL replay, "
        "(2) throttle ClickHouse — verify circuit breaker + Redis buffer, (3) run at 10k events/sec, capture metrics. "
        "Update CHAOS.md with actual results + Grafana screenshots."
    ),
    12: (
        "OSS-01 — First contribution to VictoriaMetrics or Vector.dev (good-first-issue / help-wanted). "
        "Documentation example, benchmark, or reproducible bug report counts. Submit PR; link in weekly notes."
    ),
    13: (
        "Ticket G-09 — Anomaly detection in Go consumer: z-score on inference latency per model_id "
        "(sliding window 100 points, flag if >3σ). On anomaly: Kafka topic anomalies, Prometheus anomalies_detected_total, Grafana alert rule."
    ),
    14: (
        "Week 2 README polish for infra-ai-streaming: Excalidraw architecture PNG, Design Decisions (3 tradeoffs), Benchmarks table, "
        "Chaos Testing summary, Getting Started under 5 commands. README should stand alone for hiring committees."
    ),
    15: (
        "Create repo ebpf-llm-tracer + DESIGN.md: zero-SDK LLM HTTP tracing via eBPF. "
        "Sections: probe attachment points (socket/connect/send), HTTP parsing for model_id and token headers, "
        "userspace agent architecture, security/CAP constraints, integration contract with infra-ai-streaming Kafka topic. "
        "Read Cilium + BCC docs; spike feasibility on local Linux VM or Docker privileged container."
    ),
    16: (
        "eBPF program v0 — trace socket syscalls for outbound HTTPS to api.openai.com / api.anthropic.com. "
        "BPF maps for connection → PID correlation. Userspace loader in Rust or Go using libbpf-rs / cilium/ebpf. "
        "Log raw connect events; no parsing yet."
    ),
    17: (
        "HTTP parsing in userspace: reassemble TLS plaintext via uprobes or capture pre-TLS on localhost test server first. "
        "Extract method, path, status, Content-Length, x-request-id, model from JSON body snippets. "
        "Unit tests with canned PCAP fixtures."
    ),
    18: (
        "Map parsed HTTP events to infra-ai-streaming ingest schema (model_id, latency_ms, prompt_tokens, completion_tokens, cost_usd, tenant_id, source=ebpf). "
        "Kafka producer from ebpf-llm-tracer userspace agent. End-to-end: curl OpenAI-compatible mock → eBPF → Kafka → existing consumer."
    ),
    19: (
        "Ticket G-10 pattern on ingestion path — add WAL to Rust ingestion (if not merged): append-only segments before Kafka produce, "
        "replay on startup for un-acked segments. Metrics wal_segments_pending, wal_replay_events_total. "
        "Parallel: harden ebpf-llm-tracer with rate limiting and drop policy when Kafka backpressures."
    ),
    20: (
        "ebpf-llm-tracer demo harness: docker-compose sidecar deployment, capture live calls to mock LLM server with zero app SDK changes. "
        "BENCHMARKS.md for probe overhead (CPU %, P99 latency delta). Document required kernel ≥5.10 and CAP_BPF."
    ),
    21: (
        "OSS-02 — Kafka or Redpanda issue/PR in consumer group rebalancing or partition assignment. "
        "ebpf-llm-tracer README: architecture diagram, demo GIF, comparison table vs SDK instrumentation (Overhead, coverage, security)."
    ),
    22: (
        "Create distributed-flagd + DESIGN.md: (1) Problem — commercial flag SaaS cost at scale, (2) etcd consensus + watch propagation, "
        "(3) gRPC streaming to edge clients, (4) AI model rollout flags — percentage traffic between model versions, (5) audit log design."
    ),
    23: (
        "distributed-flagd core in Go: HTTP CRUD for flags, etcd backend with watch, gRPC streaming push to clients. "
        "Flag types: boolean, string, percentage rollout. Docker Compose with etcd single-node for local dev."
    ),
    24: (
        "Model rollout evaluator: given tenant_id + user_id hash, resolve active model version from percentage flag. "
        "Integration hook: infra-ai-streaming ingestion adds resolved_model_id label from flagd sidecar. "
        "Tests for sticky assignment and 50/50 split stability."
    ),
    25: (
        "Kubernetes CRD for FlagDefinition + Helm chart. HPA not required; document upgrade strategy for flag schema changes. "
        "Demo: flip 10% → 50% → 100% traffic to gpt-4o-mini vs gpt-4o with Grafana cost panel showing split."
    ),
    26: (
        "Audit log: append-only Kafka topic flag_audit with who changed what flag when. "
        "CLI traceforge-flagctl for emergency kill-switch on model routes. "
        "CHAOS test: etcd leader loss during rollout — clients must fail safe to last-known-good flags."
    ),
    27: (
        "distributed-flagd BENCHMARKS.md: flag evaluation QPS, watch propagation latency P99, etcd write throughput. "
        "Cross-link ebpf + streaming repos in each README 'Platform' section."
    ),
    28: (
        "distributed-flagd polish: OpenAPI spec, client SDK stub (Go), example sidecar yaml for ingestion deployment. "
        "Remove TODOs; CI with integration test against etcd + sample flags."
    ),
    29: (
        "lensai-integration Day 1 — Create lensai-dev GitHub org; transfer infra-ai-streaming, ebpf-llm-tracer, distributed-flagd under org. "
        "Unified docker-compose at lensai-integration/quickstart: all three services + Grafana pre-provisioned. "
        "Smoke test script scripts/smoke.sh exits 0 when events flow eBPF → ingest → ClickHouse."
    ),
    30: (
        "lensai-integration launch — Product landing page (GitHub Pages): value prop, architecture diagram, demo GIF, install guide, "
        "comparison vs Datadog LLM Observability / Helicone / Langfuse (honest gaps). "
        "Publish product essay: 'LensAI — why inference observability needs a TSDB brain, not a metrics sidecar.' "
        "HN Show HN; OSS-03 OpenTelemetry Collector PR (Kafka or batch processor). Integration test on clean machine."
    ),
}

# Experience + AI + thread for days 0-30 (aligned to code)
DAILY_0_30 = [
    # day 0
    {
        "experience": {
            "title": "1.5 Trillion Events Per Day — Why We Couldn't Buy Observability",
            "subtitle": "Agoda · WhiteFalcon TSDB · the day public building started",
            "bridge": "Today I opened infra-ai-streaming because the same cardinality and throughput constraints I lived with at Agoda are now hitting every team shipping LLM inference.",
        },
        "ai": {
            "day_index": 0,
            "title": "Day 0 — The Inference Problem Is a Data Plane Problem",
            "subtitle": "Why LLM observability belongs next to your TSDB, not your APM sidebar",
            "hook": "Before KV cache math: inference telemetry is just another high-cardinality stream — and you already know how those fail.",
        },
        "thread": "Agoda-scale ingestion pain is the reason today's README defines model_id × tenant_id as first-class partition keys.",
    },
    {
        "experience": {
            "title": "Design Docs Beat Code on Day One",
            "subtitle": "Staff interviews read DESIGN.md before they read main.rs",
            "bridge": "The CAP, partition, and backpressure sections I wrote today are the contract the Rust ingestion code must obey tomorrow.",
        },
        "ai": {
            "day_index": 1,
            "title": "Day 1 — Transformer Inference Mechanics for Infra Engineers",
            "subtitle": "Prefill vs decode, KV cache, and why latency has two phases",
            "hook": "Karpathy's 'build GPT' at 1.5× — skip the training; watch the autoregressive loop and memory growth per token.",
        },
        "thread": "DESIGN.md's event schema gets prefill_ms and decode_ms fields because Blog B's two-phase latency model maps directly to observability SLOs.",
    },
    {
        "experience": {
            "title": "Ceph, POSIX, and the Lie of 'Just Use a Filesystem'",
            "subtitle": "Agoda · storage layer · zero-copy writes in Rust",
            "bridge": "Building /ingest with channel backpressure today mirrors how we avoided blocking the hot path when Ceph writes couldn't keep up with ingest bursts.",
        },
        "ai": {
            "day_index": 2,
            "title": "Day 2 — Continuous Batching in vLLM",
            "subtitle": "Why GPU utilization is a queueing problem, not a FLOPs problem",
            "hook": "Draw static vs continuous batching as Kafka consumer poll loops — same insight, different silicon.",
        },
        "thread": "Kafka batching in G-01 and vLLM continuous batching share one design rule: never wait for a full batch if the queue is starving.",
    },
    {
        "experience": {
            "title": "Seven Million Sensors Don't Fail Like Seven Hundred",
            "subtitle": "Walmart · IoT Hub · failure mode distributions at the edge",
            "bridge": "docker-compose today is the same discipline as proving the pipeline on a laptop before touching a million-device fan-out.",
        },
        "ai": {
            "day_index": 3,
            "title": "Day 3 — Token Budgets and the Real Cost of Completion",
            "subtitle": "Prompt vs completion pricing as a capacity planning exercise",
            "hook": "OpenAI and Anthropic pricing pages are SLO documents — cost_usd in your schema should recompute from token counts nightly.",
        },
        "thread": "The Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance will actually ask for it.",
    },
    {
        "experience": {
            "title": "When ClickHouse Stops Answering — Circuit Breakers I Trust",
            "subtitle": "Agoda · hot/cold tiers · Redis as shock absorber",
            "bridge": "Today's circuit breaker + Redis overflow is the same failure isolation pattern we used when analytics queries couldn't wait for cold storage.",
        },
        "ai": {
            "day_index": 4,
            "title": "Day 4 — Attention as Inverted-Index Lookup",
            "subtitle": "What the GPU computes when you 'run inference'",
            "hook": "Attention is a join over sequence positions — your TSDB already does scarier joins at query time.",
        },
        "thread": "Batch flush at 1000 events or 500ms is the ingestion-side analog of limiting attention context — bounded work per tick.",
    },
    {
        "experience": {
            "title": "Five Thousand Geo-Events Per Second — Shape of the Stream",
            "subtitle": "Delivery Hero · OSRM · throughput as a schema decision",
            "bridge": "OTel spans on the ingestion path today tag the same dimensions I'd use to debug a map-matching pipeline under peak dinner rush.",
        },
        "ai": {
            "day_index": 4,
            "title": "Day 4 — Tensor Parallelism Meets Kafka Partitions",
            "subtitle": "Model serving scale-out as a sharding problem",
            "hook": "Triton's model repository is just a partition assignment table with GPUs instead of brokers.",
        },
        "thread": "BENCHMARKS.md numbers are meaningless without labels — today's metrics mirror how I'd prove DH routing didn't drop events under load.",
    },
    {
        "experience": {
            "title": "Cardinality Is the Silent Killer — RoaringBitmap Lessons",
            "subtitle": "Agoda · Prometheus walls · model_id × tenant_id",
            "bridge": "The Grafana P99-by-model_id panel only works if I refused to explode label cardinality the way we learned at Agoda scale.",
        },
        "ai": {
            "day_index": 5,
            "title": "Day 5 — Sampling and Deterministic Routing",
            "subtitle": "Why 1% trace sampling isn't free randomness",
            "hook": "Consistent hashing for routes and consistent sampling for traces — same hash function, different failure modes.",
        },
        "thread": "Four Grafana panels are the user-facing proof that Blog A's cardinality war and Blog B's sampling discipline share one schema.",
    },
    {
        "experience": {
            "title": "Supplier APIs and Token Buckets — Wayfair's Real Circuit Breaker",
            "subtitle": "Rate limits that survived 10× surprise load",
            "bridge": "Redis token buckets on tenant_id today are the pricing-API pattern I shipped — 429 with Retry-After, not silent drop.",
        },
        "ai": {
            "day_index": 6,
            "title": "Day 6 — Quantization vs Compression Tradeoffs",
            "subtitle": "INT8/INT4 as Snappy-vs-Zstd for weights",
            "hook": "You already pick codecs by access pattern — quantization is picking precision by deployment budget.",
        },
        "thread": "CHAOS.md scenario 3 (Redis lost) exists because rate limiting without a fallback store is a decorated denial-of-service.",
    },
    {
        "experience": {
            "title": "Ten Thousand Concurrent Requests — EKS Patterns That Actually Helped",
            "subtitle": "Delivery Hero · peak · HPA limits",
            "bridge": "Helm + HPA on Kafka lag is how I'd run DH peak today — scale on consumer lag, not CPU theater.",
        },
        "ai": {
            "day_index": 7,
            "title": "Day 7 — Prompt Caching at the Infrastructure Layer",
            "subtitle": "Prefix reuse as KV-cache hit rate for dollars",
            "hook": "Anthropic/OpenAI prompt cache headers are cache-control for transformers — treat them like HTTP CDN rules.",
        },
        "thread": "HPA custom metric wiring is Blog A's peak-load story applied to the ingestion Deployment Blog B's cache economics justify.",
    },
    {
        "experience": {
            "title": "250k SKUs in Sub-Second — Event-Driven vs Polling",
            "subtitle": "Wayfair · price propagation · why streams win",
            "bridge": "Publishing the portfolio site today is shipping a read model — same as making pricing updates visible without batch lag.",
        },
        "ai": {
            "day_index": 8,
            "title": "Day 8 — RAG as an Infra Pipeline",
            "subtitle": "Chunk → embed → index → retrieve → generate latency budget",
            "hook": "RAG's bottleneck is never the LLM first — it's the fan-in on your vector store's QPS.",
        },
        "thread": "Site 'Writing' section links will point at posts that explain pipelines — today's code is another pipeline, different payload.",
    },
    {
        "experience": {
            "title": "We Killed Redpanda on Purpose — Chaos as Commit Message",
            "subtitle": "Agoda · Kafka · proving recovery beats claiming it",
            "bridge": "run_chaos.sh results go into CHAOS.md the way we'd attach postmortems to JIRA — evidence, not vibes.",
        },
        "ai": {
            "day_index": 9,
            "title": "Day 9 — GPU Memory Management for Non-CUDA Engineers",
            "subtitle": "VRAM, weight loading, and batch-size cliffs",
            "hook": "OOM on a GPU is OOM on a JVM — someone's batch size is a lie.",
        },
        "thread": "Chaos test 2 (slow ClickHouse) validates the circuit breaker Blog A lived through in tiered storage and Blog B's memory-bound batching story predicts.",
    },
    {
        "experience": {
            "title": "Reading VictoriaMetrics Source at 11pm — OSS as Interview Prep",
            "subtitle": "What production Rust teaches that tutorials skip",
            "bridge": "Today's OSS PR is practice for reading Agoda-scale codebases under time pressure — the skill transfers directly.",
        },
        "ai": {
            "day_index": 11,
            "title": "Day 11 — Serving Frameworks Compared as Queue Schedulers",
            "subtitle": "vLLM vs TGI vs Ollama — scheduling policies, not logos",
            "hook": "Ask 'what's the queue model?' before 'what's the benchmark score?'",
        },
        "thread": "Anomaly detection on model_id latency is only trustworthy if you understand how each serving framework reports time (OSS reading informs that).",
    },
    {
        "experience": {
            "title": "OTA at Scale — At-Least-Once Is a Feature, Not a Bug",
            "subtitle": "Walmart · firmware · Kafka offsets in disguise",
            "bridge": "z-score anomaly detection is edge filtering moved upstream — catch the bad device before it poisons aggregates.",
        },
        "ai": {
            "day_index": 12,
            "title": "Day 12 — Semantic Caching vs Exact-Match Redis",
            "subtitle": "Embeddings as cache keys — false positive risk as SLA",
            "hook": "Semantic cache hit = approximate nearest neighbor with business consequences — tune threshold like tail latency.",
        },
        "thread": "The anomalies topic is where exact rules end — semantic cache false positives will land in the same operational queue.",
    },
    {
        "experience": {
            "title": "Two Weeks, One README — Hiring Committees Scroll",
            "subtitle": "Proof beats promises · screenshots > adjectives",
            "bridge": "README polish today is what I'd send a Staff panel instead of a slide deck — architecture, benchmarks, chaos, quickstart.",
        },
        "ai": {
            "day_index": 13,
            "title": "Day 13 — Embeddings as Dense Time-Series IDs",
            "subtitle": "Vectors are just high-dimensional series with ANN indexes",
            "hook": "HNSW under write load feels like SSTable compaction under read pressure — you've already ops'd this class of problem.",
        },
        "thread": "Week-2 README closes infra-ai-streaming; tomorrow ebpf-llm-tracer extends observability to apps that will never install your SDK.",
    },
    {
        "experience": {
            "title": "High-Cardinality Metrics — The Prometheus Wall We Hit",
            "subtitle": "Agoda · schema design · label explosions",
            "bridge": "ebpf-llm-tracer DESIGN.md caps label cardinality because I watched model_id × pod × zone destroy a metrics stack once.",
        },
        "ai": {
            "day_index": 14,
            "title": "Day 14 — eBPF for AI Infrastructure",
            "subtitle": "Kernel probes vs SDK patches — when zero-instrumentation wins",
            "hook": "Cilium proved network observability without app changes — LLM HTTP is the next syscall surface.",
        },
        "thread": "Zero-SDK tracing is the design decision: Blog A's cardinality discipline meets Blog B's probe attachment strategy in one Kafka topic.",
    },
    {
        "experience": {
            "title": "Async Pipelines That Survived Dinner Rush",
            "subtitle": "Delivery Hero · SQS/Kinesis · decoupling notifications from analytics",
            "bridge": "Socket-level probes today are the lightest-weight tap on a path that must not add milliseconds DH couldn't afford.",
        },
        "ai": {
            "day_index": 15,
            "title": "Day 15 — Multi-Model Routing Strategies",
            "subtitle": "Cost-first vs quality-first vs latency-first — pick two",
            "hook": "Routing is policy engines — you operated feature flags for humans; models are flags with GPUs.",
        },
        "thread": "Syscall capture v0 is useless without a routing policy later — flagd will decide which model the probe's latency belongs to.",
    },
    {
        "experience": {
            "title": "Cross-Tier Query Latency — Hot Redis, Cold Ceph",
            "subtitle": "Agoda · tiering · why recent data dominates SLOs",
            "bridge": "HTTP parsing in userspace mirrors separating hot path parsing from cold storage — do the minimum work before the bus.",
        },
        "ai": {
            "day_index": 16,
            "title": "Day 16 — The Mental Model That Made LLM Infra Click",
            "subtitle": "Prefill/decode + KV cache + continuous batching in DS analogies",
            "hook": "If you can explain Kafka, you can explain inference — after you name the two phases.",
        },
        "thread": "Parsed model_id fields in eBPF events must align with the two-phase latency columns Blog B introduced on Day 1.",
    },
    {
        "experience": {
            "title": "Building in Public — The Blog Post That Outlives LinkedIn",
            "subtitle": "Architecture posts as durable hiring signals",
            "bridge": "Kafka wiring from ebpf-llm-tracer reuses the ingestion contract I benchmarked — platform thinking is reuse, not rewrite.",
        },
        "ai": {
            "day_index": 17,
            "title": "Day 17 — LLM Observability — What Actually Matters",
            "subtitle": "Arize vs Langfuse vs Helicone — schema diff against your events",
            "hook": "Add fields for tool spans and cache hits now — retrofitting schema is Agoda cardinality pain again.",
        },
        "thread": "End-to-end eBPF → ClickHouse proves LensAI's thesis: inference telemetry without vendor SDK lock-in.",
    },
    {
        "experience": {
            "title": "Rate Limiting at the Supplier Boundary — Not the Textbook Diagram",
            "subtitle": "Wayfair · token bucket in production",
            "bridge": "WAL on ingestion plus ebpf backpressure policy is the same 'never lose the write' instinct as supplier API durability.",
        },
        "ai": {
            "day_index": 18,
            "title": "Day 18 — Quantization and Model Optimization",
            "subtitle": "GPTQ vs AWQ vs bitsandbytes — pick variants like codec picks",
            "hook": "Quantized weights are a deployment flag — infra owns the matrix of {cost, latency, quality}.",
        },
        "thread": "wal_replay_events_total and probe drop counters belong in the same Grafana board — both are durability under overload.",
    },
    {
        "experience": {
            "title": "Kafka + Redis Tiering — Query Latency by Temperature",
            "subtitle": "Agoda · decoupling hot reads from cold storage",
            "bridge": "Demo harness with mock LLM proves the tracer without production keys — same staging discipline as Agoda load tests.",
        },
        "ai": {
            "day_index": 19,
            "title": "Day 19 — Agent Infrastructure — Tools, Memory, Loops",
            "subtitle": "Production agents need queues, idempotency, and traces",
            "hook": "Tool calling is RPC with hallucination risk — your streaming stack already handles worse RPC fan-out.",
        },
        "thread": "ebpf overhead benchmarks set the budget TraceForge will need when agents make ten HTTP calls per user request.",
    },
    {
        "experience": {
            "title": "Peak Kubernetes — HPA Reacts, It Doesn't Predict",
            "subtitle": "Delivery Hero · 10k concurrent · PDBs during deploys",
            "bridge": "Second OSS PR on Kafka rebalancing is credibility for the bus every LensAI component shares.",
        },
        "ai": {
            "day_index": 20,
            "title": "Day 20 — Prompt Engineering as Infra Optimization",
            "subtitle": "Prompt cache and prefix reuse in dollars per million requests",
            "hook": "Calculate savings at 1M req/day — that's the slide your PM actually reads.",
        },
        "thread": "Tracer README comparison table is the buyer's guide; prompt cache math is the CFO's guide — same product.",
    },
    {
        "experience": {
            "title": "LaunchDarkly Money — Why We Build flagd Ourselves",
            "subtitle": "Platform economics · control plane vs data plane",
            "bridge": "etcd + gRPC streaming today is DH real-time config with a different payload — model version instead of surge multiplier.",
        },
        "ai": {
            "day_index": 21,
            "title": "Day 21 — Production Reliability for LLM APIs",
            "subtitle": "Rate limits, provider outages, streaming disconnects — mapped to patterns you know",
            "hook": "Map every provider error code to: retry, circuit break, fallback model, or fail loud.",
        },
        "thread": "Percentage rollout flags are how Blog B's routing strategies become Blog A's change-management story ops teams trust.",
    },
    {
        "experience": {
            "title": "H3 vs Bounding Boxes — Geospatial Indexing That Scales",
            "subtitle": "Delivery Hero · surge detection · why naive geo fails",
            "bridge": "Sticky user hashing for model flags copies H3 cell assignment — same user, same variant, all day.",
        },
        "ai": {
            "day_index": 22,
            "title": "Day 22 — Feature Flags for Model Rollouts",
            "subtitle": "Canary models with audit trails",
            "hook": "A model rollout without audit log is a production incident waiting for a postmortem.",
        },
        "thread": "resolved_model_id on ingest events closes the loop between flagd policy and ClickHouse cost attribution.",
    },
    {
        "experience": {
            "title": "OSRM at 5000 Events/sec — When ETA Becomes Infrastructure",
            "subtitle": "Delivery Hero · route recompute budget",
            "bridge": "CRD + Helm for flags is how platform teams let app engineers self-serve rollouts without SSH.",
        },
        "ai": {
            "day_index": 23,
            "title": "Day 23 — Evaluations as Event Streams",
            "subtitle": "Eval harnesses are Kafka topics with scores",
            "hook": "LLM-as-judge output is just another event type — store it like you store metrics.",
        },
        "thread": "Live demo flipping traffic between models is the TraceForge preview — multi-step workflows need the same visibility.",
    },
    {
        "experience": {
            "title": "BigQuery Streaming vs Batch — Burst Traffic Truth",
            "subtitle": "Wayfair · data platform · slots and surprises",
            "bridge": "Audit Kafka topic for flags is BigQuery streaming inserts done right — append-only, replayable, owned.",
        },
        "ai": {
            "day_index": 24,
            "title": "Day 24 — GPU Scheduling as Resource Management",
            "subtitle": "MIG, tensor parallelism, Kubernetes extended resources",
            "hook": "You don't need CUDA — you need a scheduler that knows VRAM is finite.",
        },
        "thread": "etcd leader-loss chaos test is the flag analog of a BigQuery slot exhaustion — degrade gracefully, not randomly.",
    },
    {
        "experience": {
            "title": "Distributed Redis Rate Limits — Lua Scripts and Race Conditions",
            "subtitle": "Wayfair · sliding window in production",
            "bridge": "flagctl kill-switch is the pricing freeze switch we wished we'd had one Black Friday.",
        },
        "ai": {
            "day_index": 25,
            "title": "Day 25 — Cost Models for LLM Gateways",
            "subtitle": "Cache hit rate × cheaper model route × prompt cache",
            "hook": "Build the spreadsheet before the Rust — numbers justify the repo.",
        },
        "thread": "BENCHMARKS on flag evaluation QPS proves control-plane latency won't starve data-plane ingestion.",
    },
    {
        "experience": {
            "title": "Systems That Outlast Their Architects — Walmart Lessons",
            "subtitle": "Documentation, simplicity, operability",
            "bridge": "OpenAPI + SDK stub is writing for the team that inherits LensAI — Walmart taught me they'll exist.",
        },
        "ai": {
            "day_index": 26,
            "title": "Day 26 — Fine-Tuning vs RAG vs Prompting — Infra Cost View",
            "subtitle": "When to buy GPUs vs buy vectors vs buy nothing",
            "hook": "Staff engineers pick the cheapest path that meets SLO — not the coolest paper.",
        },
        "thread": "Three-repo cross-links in READMEs are the platform story recruiters ask for in month five — start showing it now.",
    },
    {
        "experience": {
            "title": "What I'd Redesign at Wayfair With 2026 Eyes",
            "subtitle": "Ownership · leading two teams · pricing platform",
            "bridge": "lensai-dev org is the ownership move — public platform identity, not scattered personal repos.",
        },
        "ai": {
            "day_index": 27,
            "title": "Day 27 — OpenTelemetry Collector as Integration Hub",
            "subtitle": "Exporters, processors, and why LensAI speaks OTel natively",
            "hook": "Collector processors are middleware — you've shipped worse middleware under more load.",
        },
        "thread": "smoke.sh exiting 0 is the integration test Blog A's platform narrative and Blog B's OTel lesson both require.",
    },
    {
        "experience": {
            "title": "Integration Tests — The Only Launch Criteria I Trust",
            "subtitle": "Agoda · staging discipline · compose on clean laptop",
            "bridge": "Landing page demo GIF must show eBPF → ingest → flagd → Grafana or it's marketing, not engineering.",
        },
        "ai": {
            "day_index": 28,
            "title": "Day 28 — Competitor Teardown — LensAI Positioning",
            "subtitle": "Datadog LLM Observability vs Helicone vs Langfuse — honest gaps",
            "hook": "Name what you don't do yet — credibility beats feature laundry lists.",
        },
        "thread": "Product essay draft ties competitor gaps to today's compose quickstart — one narrative, two audiences.",
    },
    {
        "experience": {
            "title": "Thirty Days of Building — What Shipped vs What Matter",
            "subtitle": "LensAI month-one · public proof",
            "bridge": "Show HN and OTel PR are distribution for the integration test I can rerun — same standard as Agoda go-live checklists.",
        },
        "ai": {
            "day_index": 29,
            "title": "Day 29 — The AI Infrastructure Stack — Full Map",
            "subtitle": "Training → inference → observability → agents — where you fit",
            "hook": "Draw the map once; every month-five product snaps onto it.",
        },
        "thread": "LensAI launch closes Month 1; tomorrow TraceForge starts because agents are multi-step distributed systems nobody traces well.",
    },
]

# Shift: day 30 starts TraceForge (Month 2)

# TraceForge days 30-59 — detailed code tasks
def code_traceforge(day: int) -> str:
    tasks = {
        30: "agent-trace-collector — DESIGN.md: agent execution graph, span schema (trace_id, span_id, parent_span_id, tool_name, model, tokens, cost_usd, status, latency_ms), tool taxonomy, OTel mapping.",
        31: "OTel Collector pipeline: receivers otlp + kafka; processors batch + attributes; exporters to ClickHouse agent_spans and Kafka agent.spans.v1. Compose overlay on LensAI quickstart.",
        32: "Python SDK traceforge.wrap_openai(): emit spans per tool_call, hash arguments, record latency/tokens. Mock server test with parallel tool calls.",
        33: "Go SDK StartSpan/EndSpan + context propagation; example weather+calculator agent; Kafka producer like infra-ai-streaming.",
        34: "ClickHouse agent_spans MergeTree ORDER BY (trace_id, start_time); MV per-trace cost; Grafana waterfall panel.",
        35: "ReAct demo agent — reproduce silent failure on step 7; DEMO.md with screenshots.",
        36: "Sampling head 10% + error tail; PII scrub processor; load test 5k spans/sec; BENCHMARKS.md.",
        37: "tool-call-analyzer DESIGN.md — canonical ToolCall struct, adapters plan, cost per invocation including retries.",
        38: "Go adapters openai/anthropic/langchain + golden JSON fixtures → Kafka tools.normalized.v1.",
        39: "Per-tool stats MVs: latency P99, error rate, cost; alert if tool >40% trace duration.",
        40: "Tool dependency graph + N+1 detection; CLI traceforge graph --trace-id.",
        41: "Bottleneck rank by exclusive time; Grafana tool cost waterfall.",
        42: "Dual-write tool cost_usd to LensAI ingest; unified tenant Grafana board.",
        43: "tool-call-analyzer README + OpenAPI; chaos test aggregator failure → Kafka buffers spans.",
        44: "agent-replay-engine DESIGN.md — event sourcing, mock tools, determinism rules.",
        45: "Trace JSONL export to MinIO, zstd, checksums, retention 30/90 days.",
        46: "Replay core + CLI traceforge replay --trace-id --stop-at-step 6.",
        47: "Diff engine traceforge diff --trace-a --trace-b — first diverging span.",
        48: "Failure injection --inject-timeout on replay; verify agent error paths.",
        49: "Replay perf: 100-step trace <3s; streaming parser memory profile.",
        50: "replay-engine CI with sample bundle; README 'debug step 7' runbook.",
        51: "agent-benchmark-runner DESIGN.md — task YAML, compare two agents, success criteria.",
        52: "Benchmark orchestrator — parallel runs, ClickHouse benchmark_runs, seed control.",
        53: "Report generator: '14 calls vs 9, diverged step 5' markdown + JSON + timeline SVG.",
        54: "Flame graph timeline colored by cost.",
        55: "LensAI integration — benchmark completion emits ingest events.",
        56: "traceforge-dev org + unified docker-compose all four repos.",
        57: "Landing page draft + benchmark screenshot + LensAI cross-link.",
        58: "Launch rehearsal + integration test; draft product essay for Day 59.",
        59: "TraceForge v1 launch HN + publish product essay + LensAI+TraceForge Grafana proof.",
    }
    return tasks.get(day, f"Continue {repo_for(day)} per DESIGN.md.")


def code_routeiq(day: int) -> str:
    tasks = {
        60: (
            "semantic-cache-engine — DESIGN.md: embedding pipeline, pgvector schema, similarity threshold per tenant, "
            "false-positive budget, integration with LensAI cache_hit events. Define TTL and freshness decay policy."
        ),
        61: (
            "Embedding worker: call embedding API (OpenAI text-embedding-3-small or local), batch size 32, "
            "write vectors to pgvector table prompts( tenant_id, prompt_hash, embedding, created_at ). "
            "Idempotent on prompt_hash."
        ),
        62: (
            "Cache lookup path: cosine similarity search with threshold 0.92 default, tenant override in config. "
            "On hit: return cached completion + emit LensAI event cache_hit=true. On miss: pass through to router."
        ),
        63: (
            "Cache analytics: hit rate, false positive proxy (user thumbs-down webhook stub), cost saved estimate. "
            "Grafana panel + BENCHMARKS.md sweep thresholds 0.88–0.96 on held-out prompt set."
        ),
        64: (
            "semantic-cache-engine README + docker-compose with postgres/pgvector. "
            "Load test 1k QPS lookups — p99 latency under 15ms on M1 Max baseline."
        ),
        65: (
            "cost-budget-enforcer — DESIGN.md: sliding window token budgets in Redis, hard vs soft limits, "
            "graceful degradation route to cheaper model, webhook alerts at 80% budget."
        ),
        66: (
            "Middleware: before LLM call, check tenant budget; decrement estimated tokens; block or downgrade if exceeded. "
            "Unit tests for window rollover at UTC midnight and burst allowance."
        ),
        67: (
            "Admin API PATCH /tenants/{id}/budget — live budget changes without restart. Audit log to Kafka."
        ),
        68: (
            "Integration: RouteIQ stub gateway calls budget enforcer then semantic cache then model. "
            "Wire spend metrics to LensAI cost_usd stream."
        ),
        69: (
            "cost-budget-enforcer chaos: Redis down → fail closed with 503 vs fail open policy (document choice). "
            "BENCHMARKS.md for enforcement overhead microseconds per request."
        ),
        70: (
            "prompt-fingerprinter — DESIGN.md: normalize prompt (strip whitespace, canonical JSON), SHA-256 fingerprint, "
            "exact-match Redis cache layer before semantic cache. Sub-millisecond lookup."
        ),
        71: (
            "Implement fingerprinter library in Rust: normalize(), fingerprint(), redis_key(). "
            "Property tests — equivalent prompts collide, distinct prompts rarely collide."
        ),
        72: (
            "Dual-layer cache stack: L1 exact Redis, L2 semantic pgvector. Metrics l1_hit, l2_hit, miss. "
            "Document stack diagram in README."
        ),
        73: (
            "Prompt fingerprint collision drill — intentional hash clash test, verify TTL isolation."
        ),
        74: (
            "prompt-fingerprinter polish: export OpenTelemetry spans for cache tier decisions. "
            "Outline model-quality-scorer scope for Week 3 (Day 75+). Cross-link RouteIQ + LensAI docs."
        ),
    }
    return tasks[day]


def daily_traceforge(day: int) -> dict:
    idx = day - 30
    experiences = [
        ("Step 7 Failed Silently — And Nobody Had a Span", "Delivery Hero · async pipelines · visibility", "agent-trace-collector exists because DH taught me the worst outages are the ones between services you already monitor."),
        ("Tool Calls Are RPCs With Marketing", "Agoda · fan-out · retries", "Wrapping OpenAI today is no different from instrumenting an internal gRPC service — same span boundaries, different JSON."),
        ("When the Collector Is the Product", "Walmart · edge aggregation · drop policies", "OTel Collector config is the choke point — treat processors like stream processors at the edge."),
        ("SDK Wrappers — The Last Resort That Ships", "Wayfair · client libraries · adoption", "Python wrap_openai ships adoption; kernel probes were yesterday's LensAI — agents need SDK hooks first."),
        ("ClickHouse for Traces — Not Just Metrics", "Agoda · MergeTree · sort keys", "ORDER BY (trace_id, start_time) is the same hot-key thinking as Agoda's query patterns — locality matters."),
        ("The Demo Agent That Always Dies on Step 7", "Stealth · multi-tenant ordering · failure isolation", "DEMO.md's silent step 7 is the story TraceForge sells — reproduce before you fix."),
        ("Sampling Without Lying", "Agoda · tail sampling · SLO integrity", "Head 10% + error tail sampling is how I'd trace 1.5T events/day without bankrupting storage."),
        ("LangChain Is Four Vendors in a Trenchcoat", "Delivery Hero · normalization · schema drift", "tool-call-analyzer adapters are DH map-matching — different inputs, one canonical route object."),
        ("Golden Files — How Platforms Survive API Drift", "Wayfair · contract tests · supplier APIs", "Recorded JSON fixtures are supplier sandbox responses for AI APIs."),
        ("The Tool That Ate Your Margin", "Agoda · cost attribution · outliers", "Per-tool cost rollup is cardinality-aware billing — Finance asks the same question Platform did."),
        ("N+1 Tool Calls — The SELECT * of Agents", "Walmart · fan-out · edge filtering", "Cycle detection on tool graphs is edge pre-aggregation — stop poison before the LLM loop."),
        ("Exclusive Time — Flame Graphs for Money", "Delivery Hero · OSRM critical path · ETA", "Bottleneck rank is critical path on a DAG — DH route recompute taught me to look for the slow edge."),
        ("One Dashboard for Inference and Tools", "Agoda · unified telemetry · tenant view", "Dual-write to LensAI is hot/cold tiering for observability — one query face, two pipelines."),
        ("Kafka as Shock Absorber — Again", "Agoda · backpressure · consumer lag", "Chaos on analyzer proves TraceForge fails like infra-ai-streaming — queued, not dropped."),
        ("Event Sourcing — But the Events Hallucinate", "Wayfair · idempotent replays · pricing", "Replay mocks are idempotent consumers — Wayfair price replay with frozen inputs."),
        ("S3 for Traces — Compliance and Cost", "Agoda · retention · cold storage", "JSONL on MinIO is Ceph for traces — cheap bytes, replayable history."),
        ("Replay Step 6 — Stop Before the Blast Radius", "Walmart · OTA rollback · partial deploy", "--stop-at-step is OTA rollback for agents — fix before step 7 ships."),
        ("Diff Two Traces — Git Blame for Agents", "Delivery Hero · route divergence · A/B", "First diverging span is where two drivers got different ETAs — same debugging muscle."),
        ("Inject Timeout — Chaos for Tool RPCs", "Wayfair · circuit breakers · failure injection", "Synthetic timeout injection is supplier chaos testing — know the breaker trips."),
        ("Streaming Parser — Don't OOM the Debugger", "Agoda · bounded memory · large queries", "Streaming JSONL is paginated TSDB queries — never load the whole day into RAM."),
        ("Copy-Paste Debuggability", "Stealth · on-call · operability", "README 'debug step 7' is runbook culture — ops-friendly beats clever."),
        ("Benchmark Agents Like Load Tests", "Agoda · k6 · methodology", "benchmark-runner task YAML is k6 scenario for agents — same stats, different victim."),
        ("Parallel Runs — Respect the Rate Limit", "Delivery Hero · peak · concurrency caps", "Concurrency limit on benchmarks is DH dinner-rush throttling — don't DDoS yourself."),
        ("14 Calls vs 9 — The Report Hiring Managers Get", "Agoda · efficiency · cost per outcome", "Comparison markdown is the executive summary of a trace — dollars and steps, not vibes."),
        ("Flame Graphs — LLM Time vs Tool Time", "Walmart · HVAC control loop · latency", "Color by cost is control-loop tuning — which actuator spends the energy."),
        ("Two Products, One Tenant Bill", "Wayfair · unified metrics · finance", "LensAI integration proves platform not portfolio — one customer, one invoice line."),
        ("Org Boundaries — Public Platform Identity", "Wayfair · leading teams · ownership", "traceforge-dev org is how you signal maintained product, not weekend repo."),
        ("Launch Week — Integration or Nothing", "Agoda · go-live checklist · staging", "Cross-product Grafana test is Agoda launch gate — no screenshot without rerun script."),
        ("TraceForge — Agents Need a Flight Recorder", "Delivery Hero · operations · postmortems", "Month 2 essay ties benchmark report to DH postmortem format — steps, cost, divergence."),
    ]
    ai_topics = [
        (31, "ReAct Loops as Distributed Workflows", "Planner → tools → memory — state machine, not magic", "Draw the loop as a saga; each tool call is a compensatable step with timeout."),
        (32, "OpenTelemetry Semantics for Agents", "span kinds, attributes, and what to standardize now", "Align attribute names with your ClickHouse columns before v1 ships."),
        (33, "Tool Calling Protocols — OpenAI vs Anthropic", "JSON schema, parallel calls, refusal handling", "Normalize in the adapter; never in the dashboard SQL."),
        (34, "Context Propagation in Polyglot Agents", "W3C tracecontext through Python and Go", "Broken context = broken parent_span_id = useless waterfall."),
        (35, "Trace Storage Layout — Sort Keys Matter", "MergeTree, ZSTD, projections for trace queries", "Optimize for trace_id lookup first; global analytics second."),
        (36, "Silent Failures in Multi-Step Agents", "Empty tool results, swallowed exceptions, max iterations", "Alert on zero-byte tool responses — they're the new 500."),
        (37, "Tail Sampling for Agent Traces", "Always keep errors and high-cost traces", "Head sample the happy path; tail sample the expensive path."),
        (38, "Tool Taxonomies — Ontology Before Metrics", "http.search vs db.query vs code.exec", "Bad taxonomy makes every dashboard lie gently."),
        (39, "Adapter Pattern for Vendor Drift", "Versioned normalizers behind stable structs", "Golden files are your contract tests when OpenAI changes JSON."),
        (40, "Exclusive Time vs Wall Time", "Why summing span durations double-counts", "Exclusive time is how you find the tool that actually blocked completion."),
        (41, "Graph Algorithms on Traces", "DAG validation, cycle detection, N+1 alerts", "N+1 tools is SELECT in a loop — automate the lint rule."),
        (42, "Cost Waterfalls — CFO-Friendly Visuals", "Stacked cost by tool per trace", "Waterfall beats table when persuading teams to drop a tool."),
        (43, "Unified Billing Events — One Envelope", "Same ingest schema for inference and tools", "tenant_id + trace_id joins finance to engineering."),
        (44, "Backpressure on Analytics Pipelines", "Kafka consumer lag on tool stats", "Slow aggregator must not block span ingest — split topics."),
        (45, "Event Sourcing for Agent Runs", "Append-only steps, deterministic replay", "Replay is Kafka log compaction for agent state."),
        (46, "Object Storage Economics for Traces", "JSONL, zstd, lifecycle policies", "Traces are logs; price them like logs."),
        (47, "Deterministic Mocks — Record and Replay", "VCR pattern for LLM agents", "Mock tools return bytes from trace — not live HTTP."),
        (48, "Diff Semantics — Structural vs Textual", "First divergence detection on spans", "Git diff for trees — stop at first changed tool output."),
        (49, "Fault Injection for Tool RPCs", "Timeouts, 500s, stale cache", "Chaos mesh for agents — inject before production does."),
        (50, "Streaming Parsers — OOM-Safe Debugging", "Iterators over multi-MB traces", "Replay must work on laptop RAM — stream everything."),
        (51, "Operability — CLI as API", "replay, diff, graph subcommands", "If it's not scriptable, on-call won't run it at 3am."),
        (52, "Benchmark Methodology for Agents", "Tasks, seeds, success criteria", "Same task spec or you're comparing different jobs."),
        (53, "Statistical Rigor — N Runs, Confidence", "Don't benchmark once", "Run 30 times; report median cost and p95 steps."),
        (54, "Human-Readable Benchmark Reports", "Narrative + numbers beat dashboards alone", "Lead with 'step 5 diverged' — story first, flame second."),
        (55, "Flame Graphs — CPU Profile for Agents", "LLM wait vs tool exec vs queue", "Wide bars are where budget died — color by dollars."),
        (56, "Cross-Product Metrics — LensAI × TraceForge", "Join keys and dashboard contracts", "One tenant_id to rule cost — design the join on Day 1."),
        (57, "Monorepo vs Multi-Repo — Platform Packaging", "Compose files as integration contract", "Buyers install compose, not git clone four times."),
        (58, "Launch Narrative — Benchmark as Hero Demo", "Show 14 vs 9 on HN", "Lead with comparison report screenshot — instant comprehension."),
        (59, "Month 2 Synthesis — Agents Are Distributed Systems", "TraceForge thesis in one page", "Tomorrow RouteIQ routes; today you trace — platform story continues."),
    ]
    exp = experiences[min(idx, len(experiences) - 1)]
    ai = ai_topics[min(idx, len(ai_topics) - 1)]
    ai_idx = day
    return {
        "experience": {
            "title": exp[0],
            "subtitle": exp[1],
            "bridge": exp[2] + f" Today's code in {repo_for(day)} implements that lesson.",
        },
        "ai": {
            "day_index": ai_idx,
            "title": f"Day {ai_idx} — {ai[1]}",
            "subtitle": ai[2],
            "hook": ai[3],
        },
        "thread": f"{exp[0].split('—')[0].strip()} meets {ai[1]} in today's {repo_for(day)} commit.",
    }


def daily_routeiq(day: int) -> dict:
    idx = day - 60
    experiences = [
        ("Semantic Cache — Wayfair Pricing Deja Vu", "Wayfair · near-duplicate SKU updates", "Near-duplicate prompts need the same tolerance pricing had for 'almost same' supplier feeds."),
        ("Embeddings Are Batch Jobs", "Agoda · compaction windows", "Embedding worker batching is compaction — amortize API cost, control lag."),
        ("False Positives Have a Dollar Cost", "Delivery Hero · wrong ETA", "A cache false positive is a wrong ETA — threshold is an SLO."),
        ("Hit Rate Without Honesty Is Vanity", "Agoda · dashboard trust", "Cache analytics must show false-positive proxies or operators won't trust hit rate."),
        ("pgvector Under Load", "Agoda · index hot spots", "ANN index tuning is hot-partition management for vectors."),
        ("Token Budgets — Finance Meets Gateway", "Wayfair · spend caps", "Budget enforcer is supplier spend caps for tokens."),
        ("Midnight Rollover Bugs", "Walmart · UTC boundaries", "Sliding window rollover tests are IoT billing boundary tests."),
        ("Live Budget PATCH — Ops Can't Wait for Deploy", "Delivery Hero · live tuning", "Admin API is surge multiplier changes without redeploy."),
        ("Stub Gateway — Compose Before Polish", "Stealth · vertical slice", "RouteIQ stub proves stack order: budget → cache → model."),
        ("Fail Closed vs Open — Pick and Document", "Agoda · outage modes", "Redis-down policy is the same 'stop ingestion vs buffer' call."),
        ("Exact Match Before Fuzzy", "Agoda · tiered caches", "Fingerprint L1 is Redis hot tier before Ceph semantic tier."),
        ("Normalization Is Contract Testing", "Wayfair · canonical keys", "Prompt normalize() is canonical SKU keying."),
        ("Two-Tier Cache Metrics", "Agoda · hit ratio by tier", "l1_hit/l2_hit/miss is hot/cold query stats for prompts."),
        ("Hash Collisions Happen", "Walmart · OTA version mixups", "Collision drill is firmware version isolation testing."),
        ("OTel for Cache Tiers", "Delivery Hero · trace the decision", "Export spans for L1/L2/miss — RouteIQ decisions must be visible in LensAI."),
    ]
    ai_topics = [
        (60, "Semantic Caching Economics", "Threshold vs savings curve", "Sweep 0.88–0.96 on real prompts — plot dollars, not vibes."),
        (61, "Embedding Pipelines", "Batch, idempotency, backfill", "prompt_hash idempotency is Kafka exactly-once for vectors."),
        (62, "ANN Search at QPS", "pgvector indexes and latency", "IVFFlat vs HNSW — pick like pick MergeTree order key."),
        (63, "Cache Quality Metrics", "Hit rate, precision proxy, TTL", "Track thumbs-down rate on cache hits if you can."),
        (64, "Load Testing ANN", "1k QPS methodology", "Same k6 discipline as ingestion — p99 under SLA."),
        (65, "Token Budgets as Rate Limits", "Sliding windows in Redis", "Lua atomicity again — budgets race like rate limits."),
        (66, "Hard vs Soft Limits", "Block vs downgrade", "Soft limit routes to cheaper model — DH surge pricing analog."),
        (67, "Live Config for Spend", "Admin APIs without restart", "Budget PATCH is feature flag for money."),
        (68, "Gateway Middleware Ordering", "Budget → cache → route", "Order matters — wrong order leaks spend."),
        (69, "Failure Policies for Budget Redis", "503 vs passthrough", "Document the outage mode — auditors will ask."),
        (70, "Prompt Fingerprints", "SHA-256 of canonical form", "Exact cache is dedup at ingress."),
        (71, "Canonicalization Rules", "Whitespace, JSON key order", "Same rules as stable API hashing."),
        (72, "L1/L2 Stack Design", "Redis then pgvector", "Two-tier is Agoda hot/cold again."),
        (73, "Collision Handling", "TTL isolation on clash", "Treat like rare UUID collision — isolate blast radius."),
        (74, "Quality Scorer Preview", "Routing needs scores", "Tomorrow model-quality-scorer closes the RouteIQ loop."),
    ]
    exp = experiences[min(idx, len(experiences) - 1)]
    ai = ai_topics[min(idx, len(ai_topics) - 1)]
    ai_idx = day
    return {
        "experience": {"title": exp[0], "subtitle": exp[1], "bridge": exp[2] + f" Today's {repo_for(day)} work makes that concrete."},
        "ai": {"day_index": ai_idx, "title": f"Day {ai_idx} — {ai[1]}", "subtitle": ai[2], "hook": ai[3]},
        "thread": f"{exp[0]} and {ai[1]} share today's design decision in {repo_for(day)}.",
    }


FRIDAY_PROJECT_BLOGS = [
    {"title": "Week 1 — infra-ai-streaming: From Empty Repo to Grafana Proof", "subtitle": "Ingestion benchmarks, OTel, and the DESIGN.md that hires"},
    {"title": "Week 2 — Production Hardening: Chaos, Rate Limits, and Helm", "subtitle": "Why README screenshots matter more than feature lists"},
    {"title": "Week 3 — eBPF Zero-SDK Tracing for LLM HTTP", "subtitle": "ebpf-llm-tracer architecture and Kafka integration"},
    {"title": "Week 4 — distributed-flagd and Model Rollouts", "subtitle": "etcd, gRPC streaming, and percentage canaries"},
    {"title": "Week 5 — agent-trace-collector: Tracing the Silent Step 7", "subtitle": "OTel spans, ClickHouse waterfalls, and the demo agent"},
    {"title": "Week 6 — tool-call-analyzer: Where Agent Budgets Die", "subtitle": "Normalization, graphs, and cost waterfalls"},
    {"title": "Week 7 — agent-replay-engine: Event Sourcing for Agents", "subtitle": "Deterministic replay and diff-at-step-5"},
    {"title": "Week 8 — agent-benchmark-runner: 14 Calls vs 9", "subtitle": "Benchmark methodology and TraceForge v1 launch prep"},
    {"title": "Week 9 — semantic-cache-engine: When Redis Is Not Enough", "subtitle": "pgvector thresholds and false-positive budgets"},
    {"title": "Week 10 — cost-budget-enforcer: Spend Limits as Middleware", "subtitle": "Sliding windows and graceful downgrade"},
    {"title": "Week 11 — prompt-fingerprinter: L1 Exact Before L2 Semantic", "subtitle": "Dual-layer cache stack design"},
]


def friday_project_blog(day: int) -> dict | None:
    if not is_friday(day):
        return None
    week_idx = day // 7
    if week_idx < len(FRIDAY_PROJECT_BLOGS):
        return FRIDAY_PROJECT_BLOGS[week_idx]
    return {"title": f"Week {week_idx + 1} — {repo_for(day)} synthesis", "subtitle": "Architectural decisions from this week's commits"}

PRODUCT_BLOGS = {
    29: {
        "title": "LensAI — Why Inference Observability Needs a TSDB Brain",
        "subtitle": "Not a metrics sidecar: eBPF + streaming + flags as one product",
    },
    59: {
        "title": "TraceForge — Agent Observability Is Distributed Tracing With Money on the Line",
        "subtitle": "Collector, analyzer, replay, benchmark — Month 2 product essay",
    },
}


def code_for(day: int) -> str:
    if day in CODE_0_30:
        return CODE_0_30[day]
    if day <= 59:
        return code_traceforge(day)
    return code_routeiq(day)


def build_day(day: int) -> dict:
    prod, prod_name = product_for(day)
    entry = {
        "day": day,
        "status": status(day),
        "weekday": weekday(day),
        "product": prod,
        "product_name": prod_name,
        "repo": repo_for(day),
        "code": code_for(day),
        "project_blog": friday_project_blog(day),
        "product_blog": PRODUCT_BLOGS.get(day),
    }
    if day <= 29:
        d = DAILY_0_30[day]
        entry["experience"] = d["experience"]
        entry["ai"] = d["ai"]
        entry["thread"] = d["thread"]
    elif day <= 59:
        tf = daily_traceforge(day)
        entry["experience"] = tf["experience"]
        entry["ai"] = tf["ai"]
        entry["thread"] = tf["thread"]
    else:
        rq = daily_routeiq(day)
        entry["experience"] = rq["experience"]
        entry["ai"] = rq["ai"]
        entry["thread"] = rq["thread"]
    return entry


def main():
    days = [build_day(d) for d in range(75)]
    out = {"version": 1, "range": [0, 74], "generated": "2026-05-16", "days": days}
    path = "/Users/akshant/Downloads/akshant-150-day-plan/data/plan-days-0-74.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(path, len(days))


if __name__ == "__main__":
    main()
