"""150-day plan data: code, blogs, threads. Status from plan_status + data/current-day.json."""

PRODUCTS = [
    ("lensai", "LensAI", 0, 29),
    ("traceforge", "TraceForge", 30, 59),
    ("routeiq", "RouteIQ", 60, 89),
    ("driftwatch", "DriftWatch", 90, 119),
    ("fineforge", "FineForge", 120, 149),
]

# (repo, start_day, end_day inclusive)
REPO_SCHEDULE = [
    ("infra-ai-streaming", 0, 13),
    ("ebpf-llm-tracer", 14, 20),
    ("distributed-flagd", 21, 27),
    ("lensai-integration", 28, 29),
    ("agent-trace-collector", 30, 36),
    ("tool-call-analyzer", 37, 43),
    ("agent-replay-engine", 44, 50),
    ("agent-benchmark-runner", 51, 57),
    ("traceforge-launch", 58, 59),
    ("semantic-cache-engine", 60, 66),
    ("cost-budget-enforcer", 67, 73),
    ("prompt-fingerprinter", 74, 76),
    ("model-quality-scorer", 77, 80),
    ("fallback-chain", 81, 87),
    ("routeiq-launch", 88, 89),
    ("shadow-traffic-router", 90, 96),
    ("llm-judge-eval", 97, 103),
    ("drift-detector", 104, 110),
    ("alert-rule-engine", 111, 117),
    ("driftwatch-launch", 118, 119),
    ("data-prep-pipeline", 120, 126),
    ("lora-trainer", 127, 133),
    ("eval-harness", 134, 137),
    ("model-registry", 138, 140),
    ("vllm-deploy-kit", 141, 147),
    ("platform-launch", 148, 149),
]

WEEKDAY = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Explicit overrides: day -> dict keys code, exp_title, exp_sub, exp_bridge, ai_idx, ai_title, ai_sub, ai_hook, project_blog, product_blog, title
OVERRIDES = {
    0: {
        "title": "Kickoff — series launch & plan",
        "code": "Publish blog site structure; AI Learning Day 0 (series roadmap); create infra-ai-streaming repo stub; define 150-day calendar and series URLs (/experience/, /ai-learning/).",
        "exp_title": "Why I'm building AI infrastructure in public for 150 days",
        "exp_sub": "Staff engineer positioning — Agoda TSDB → LensAI narrative",
        "exp_bridge": "Sets the credibility arc: distributed systems at scale, now applied to LLM inference observability.",
        "ai_idx": 0,
        "ai_title": "Day 0 of Learning LLM Inference — The Roadmap: What an Infra Engineer Needs to Know",
        "ai_sub": "Scope, vocabulary, and how this series connects to WhiteFalcon-scale systems",
        "ai_hook": "Defines metrics schema goals for infra-ai-streaming (prefill vs decode, tokens, cost).",
    },
    1: {
        "title": "Launch — GitHub identity & first repo",
        "code": "Rewrite LinkedIn headline + About; GitHub profile README (homepage); create infra-ai-streaming with README + Mermaid architecture (1M events/min target); pin repo.",
        "exp_title": "Inside a 1.5 trillion events/day TSDB — why every off-the-shelf monitor broke",
        "exp_sub": "Agoda WhiteFalcon — Prometheus cardinality, Rust+Scala split",
        "exp_bridge": "Why LensAI ingestion must treat model_id×tenant_id as a first-class cardinality problem.",
        "ai_idx": 1,
        "ai_title": "Day 1 of Learning LLM Inference — The KV Cache Is a Memory Bandwidth Problem",
        "ai_sub": "DS lens: hot/cold tiering like Redis+S3 in WhiteFalcon",
        "ai_hook": "Adds prefill_ms + decode_ms fields to inference event schema in DESIGN.md.",
    },
    2: {
        "title": "DESIGN.md — architecture on paper",
        "code": "Write DESIGN.md: CAP (AP ingestion), partition strategy for model_id, channel backpressure, Kafka/ClickHouse failure modes, horizontal scaling plan, analytics consistency.",
        "exp_title": "Designing storage for 1.5T/day — why we bypassed POSIX for Ceph RADOS",
        "exp_sub": "Agoda cold/hot path — sequential write economics",
        "exp_bridge": "Informs ClickHouse batch writer flush policy (micro-batch vs streaming).",
        "ai_idx": 2,
        "ai_title": "Day 2 of Learning LLM Inference — Continuous Batching in vLLM: Keeping GPUs Busy",
        "ai_sub": "DS lens: Kafka consumer group rebalancing mid-flight",
        "ai_hook": "Ingestion engine batches events like a decode scheduler batches sequences.",
    },
    3: {
        "title": "Rust ingestion — first code",
        "code": "Rust Axum /ingest accepting JSON batches (model_id, latency_ms, prompt_tokens, completion_tokens, cost_usd, tenant_id); rdkafka async producer; channel backpressure; graceful shutdown; verify Kafka receive.",
        "exp_title": "When percentiles lie — correct P95/P99 across Redis hot and S3/Parquet cold tiers",
        "exp_sub": "Agoda quantile merge via histogram buckets, not averaged percentiles",
        "exp_bridge": "LensAI cannot average P99 across tenants — same merge discipline in dashboards.",
        "ai_idx": 2,
        "ai_title": "Day 2 of Learning LLM Inference — Continuous Batching in vLLM (applied to ingestion)",
        "ai_sub": "Reinforce batching with today's producer implementation notes",
        "ai_hook": "Commit documents batch size vs latency tradeoff on HTTP ingest path.",
    },
    4: {
        "title": "Docker stack + Go consumer skeleton",
        "code": "docker-compose.yml: Redpanda, ClickHouse, Redis, Grafana, Prometheus — one command up. Go consumer reads Kafka, logs stdout (ClickHouse write Day 5). E2E: Rust → Kafka → Go. Publish both blogs; share URLs only (no separate LinkedIn writing).",
        "exp_title": "Seven million IoT sensors taught me failure modes textbooks skip",
        "exp_sub": "Walmart scale — device identity, edge filtering, connection storms",
        "exp_bridge": "Compose stack models multi-tenant ingestion isolation like IoT device shards.",
        "ai_idx": 3,
        "ai_title": "Day 3 of Learning LLM Inference — Token Budgets and the Real Cost Structure",
        "ai_sub": "DS lens: metering dimensions like TSDB label cardinality",
        "ai_hook": "Validates cost_usd + prompt vs completion token split in event JSON.",
    },
    5: {
        "title": "ClickHouse writer + OBSERVABILITY.md",
        "code": "Go consumer: batch 1000 events or 500ms flush to ClickHouse; circuit breaker; Redis overflow buffer; DLQ topic after 3 retries. Add OBSERVABILITY.md — self-metrics for the pipeline.",
        "exp_title": "The RoaringBitmap cardinality trap — adding a Kubernetes dimension without index explosion",
        "exp_sub": "Agoda — series ID generation + Rust ingestion changes",
        "exp_bridge": "tenant_id × model_id cardinality guards in ClickHouse schema design.",
        "ai_idx": 4,
        "ai_title": "Day 4 of Learning LLM Inference — Model Serving Is a Queueing Problem (Triton/vLLM)",
        "ai_sub": "DS lens: worker pools and Kafka consumer groups",
        "ai_hook": "Maps queue depth metrics to ingestion_kafka_lag dashboards.",
    },
    6: {
        "title": "OpenTelemetry + BENCHMARKS.md",
        "code": "OTel traces on Rust path (HTTP→Kafka→ack); Prometheus histograms (ingestion_latency_ms, kafka errors, batch sizes). k6 at 1k/10k/50k eps; write BENCHMARKS.md with hardware spec.",
        "exp_title": "Geospatial tracking at 5,000 events/sec — why GPS polling fails",
        "exp_sub": "Delivery Hero — OSRM map-matching throughput",
        "exp_bridge": "Throughput test methodology reused for ingestion benchmarks today.",
        "ai_idx": 5,
        "ai_title": "Day 5 of Learning LLM Inference — Vector Indexes Are ANN at Scale (HNSW/IVF)",
        "ai_sub": "DS lens: inverted indexes under write pressure",
        "ai_hook": "Prepares RouteIQ semantic cache observability fields.",
    },
    7: {
        "title": "Grafana dashboard + week 1 close",
        "code": "Grafana JSON: throughput by tenant, P99 latency by model_id, token cost/hour, consumer lag. Screenshot → README. Update resume Featured + OSS section.",
        "exp_title": "Snappy to Zstd on cold-tier Parquet — 15–20% storage, <1% read latency",
        "exp_sub": "Agoda compression migration under low read frequency",
        "exp_bridge": "ClickHouse codec choice for inference event cold storage.",
        "ai_idx": 6,
        "ai_title": "Day 6 of Learning LLM Inference — RAG Is an ETL Pipeline, Not a Chat Trick",
        "ai_sub": "DS lens: chunk→embed→index like stream processing",
        "ai_hook": "Future span attributes for RAG stage latencies in TraceForge month.",
        "project_blog": "Weekly · Project — Building a Production-Grade AI Inference Observability Pipeline",
    },
    13: {
        "project_blog": "Weekly · Project — eBPF Probe Design for Zero-SDK LLM HTTP Capture",
    },
    20: {
        "project_blog": "Weekly · Project — Feature Flags for AI Model Rollouts (etcd + gRPC streaming)",
    },
    27: {
        "project_blog": "Weekly · Project — Wiring LensAI: ebpf-tracer → streaming → flagd in One Compose Stack",
    },
    29: {
        "product_blog": "Monthly · Product — LensAI: Why Inference Observability Needs a TSDB Brain, Not a Metrics Sidecar",
    },
    59: {
        "product_blog": "Monthly · Product — TraceForge: Tracing AI Agents Like Distributed Systems",
    },
    89: {
        "product_blog": "Monthly · Product — RouteIQ: Cost-First LLM Routing in Production",
    },
    119: {
        "product_blog": "Monthly · Product — DriftWatch: Closing the MLOps Loop with Shadow Eval",
    },
    149: {
        "product_blog": "Monthly · Product — The Self-Healing AI Platform: Five Products, One Loop",
    },
}

EXPERIENCE_POOL = [
    ("Agoda", "1.5T/day TSDB overview", "Prometheus cardinality limits at inference label scale"),
    ("Agoda", "Quantile merge hot/cold tiers", "Cannot average P99 across tenants in LensAI"),
    ("Agoda", "RoaringBitmap K8s dimension", "model_id × tenant_id explosion"),
    ("Agoda", "Snappy→Zstd cold tier", "ClickHouse codec economics"),
    ("Agoda", "Kafka ingestion backpressure", "Channel-based Rust producer design"),
    ("Delivery Hero", "OSRM 5k events/sec", "Event shape for geo-scale throughput"),
    ("Delivery Hero", "SQS/Kinesis decoupling", "Kafka as failure boundary"),
    ("Delivery Hero", "EKS 10k concurrent", "Helm HPA patterns for ingestion"),
    ("Delivery Hero", "H3 vs bounding boxes", "Spatial indexing mental model"),
    ("Walmart", "7M sensors IoT Hub", "Device cardinality → tenant cardinality"),
    ("Walmart", "OTA at-least-once", "DLQ + retry discipline"),
    ("Walmart", "Stream Analytics limits", "Why Kafka consumer for analytics path"),
    ("Walmart", "Edge pre-aggregation", "500ms/1000-event flush policy"),
    ("Wayfair", "250k SKU sub-second propagation", "Event-driven vs polling"),
    ("Wayfair", "Supplier circuit breakers", "Redis token bucket in Rust gateway"),
    ("Wayfair", "BigQuery streaming vs batch", "ClickHouse micro-batch tradeoff"),
    ("Wayfair", "Distributed rate limiting", "Lua atomic counters across replicas"),
    ("Stealth", "Offline-first order sync", "At-least-once mobile→kitchen"),
    ("OSS", "VictoriaMetrics/Vector PR", "Reading production observability code"),
    ("Integration", "Chaos test Kafka kill", "DLQ recovery evidence"),
]

AI_EXTENDED = [
    (7, "GPU memory & quantization intro", "VRAM like memory-mapped TSDB blocks", "Cost-aware model routing fields"),
    (8, "Serving frameworks compared", "Scheduler plugins like K8s", "Pick OTel hooks per framework"),
    (9, "Semantic caching thresholds", "Bloom false-positive tradeoffs", "RouteIQ threshold config"),
    (10, "Multi-model routing", "Load balancing + health checks", "fallback-chain design"),
    (11, "eBPF zero-SDK tracing", "Kernel tap like Walmart edge", "ebpf-llm-tracer"),
    (12, "Quantization INT8/INT4", "Codec migration triangle", "Cheaper model targets"),
    (13, "OTel for inference pipelines", "DH distributed tracing", "Span model for agents"),
    (14, "Anomaly detection z-score", "HVAC control loops", "model_id latency alerts"),
    (15, "Feature flags for model %", "Wayfair propagation", "distributed-flagd"),
    (16, "Chaos engineering", "Broker death at Agoda", "CHAOS.md evidence"),
    (17, "ClickHouse batch vs stream", "BigQuery streaming inserts", "Flush policy tuning"),
    (18, "Per-tenant rate limits", "Supplier API breakers", "429 Retry-After"),
    (19, "Helm HPA on custom metrics", "EKS peak traffic", "Kafka lag autoscale"),
    (20, "LensAI integration testing", "E2E at BrowserStack scale", "compose quickstart"),
]

# Month 2-5 AI concepts (index continues from 21)
AI_M2 = ["Agent span taxonomy", "ReAct loops", "Tool calling spec", "Silent tool failures", "Multi-hop cost", "Trace replay", "Deterministic mocks", "Flame graphs", "Agent benchmarks", "LangSmith comparison", "OTel collector pipelines", "Span enrichment", "Kafka for traces", "ClickHouse trace schema", "Grafana trace viewer", "SDK wrappers OpenAI", "Function call normalization", "Bottleneck tools", "Cost waterfall", "Dependency graphs", "Integration LensAI", "TraceForge launch", "Agent eval basics", "Step divergence reports", "Benchmark GPT vs Sonnet", "Load test agents", "Failure injection", "CLI replay", "Month 2 recap", "Hiring signal post"]
AI_M3 = ["Embeddings 101", "pgvector ops", "Similarity thresholds", "Cache hit rate", "TTL semantic freshness", "Token budgets in-flight", "Graceful degradation", "Budget webhooks", "Prompt fingerprinting", "Exact+semantic cache layers", "LLM-as-judge routing", "Quality scores", "Weighted routing", "Fallback chains", "Streaming passthrough", "Envoy integration", "RouteIQ decision log", "LensAI cost dashboard", "3-product test", "Latency overhead bench", "Multi-tenant isolation", "Cache poisoning risks", "RouteIQ launch", "Portkey comparison", "Cost forecast model", "Embedding pipeline ops", "Vector index maintenance", "Month 3 recap", "HN launch", "Partner integrations"]
AI_M4 = ["Shadow traffic 1%", "Fire-and-forget mirroring", "Eval queue Kafka", "Paired responses store", "LLM judge rubrics", "Cheap judge model", "Score normalization", "Statistical significance", "CUSUM drift", "Per query-type drift", "Alert root cause hints", "LensAI drift dashboard", "Auto-retrain webhook", "A/B on live traffic", "Alert rule engine", "Escalation paths", "DriftWatch launch", "4-product integration", "Netflix shadow post", "Judge bias controls", "Sample rate tuning", "Privacy in shadow eval", "Cold start models", "Month 4 recap", "MLOps loop narrative", "WhyLabs comparison", "Dataset vs model drift", "Incident replay", "On-call runbooks", "Compliance logging"]
AI_M5 = ["ClickHouse training export", "PII scrub pipeline", "Dedup strategies", "Instruction format conversion", "Train/eval split", "LoRA rank/alpha", "QLoRA 4-bit", "Training metrics stream", "Checkpoint resume", "GPU cost calculator", "Eval harness leakage", "Baseline vs fine-tuned", "Model registry semver", "Artifact metadata", "DriftWatch baseline score", "vLLM Helm deploy", "Tensor parallelism", "RouteIQ register model", "LensAI day-1 monitor", "Full loop demo", "Platform landing page", "HN platform Show HN", "5-month recap blog", "Apply tier-1 companies", "Fine-tune cost post", "Data quality essay", "Failure retrospectives", "OSS vLLM contrib", "Community launch", "Day 149 celebration"]

def repo_for(d):
    for r, s, e in REPO_SCHEDULE:
        if s <= d <= e:
            return r
    return "platform-launch"

def product_for(d):
    for slug, name, s, e in PRODUCTS:
        if s <= d <= e:
            return slug, name
    return "platform", "Platform"

def status_for(d):
    from plan_status import load_current_day, resolve_status

    return resolve_status(d, load_current_day())

def code_default(d, repo):
    w = WEEKDAY[(d + 1) % 7]
    if w == "Mon":
        return f"DESIGN.md for {repo}: goals, partitions, backpressure, failure modes, integration points."
    if w == "Fri":
        return f"{repo}: unit/integration tests, BENCHMARKS.md update, README polish, commit benchmark numbers."
    if d in (28, 29, 58, 59, 88, 89, 118, 119, 148, 149):
        return f"{repo}: integration tests, launch checklist, demo GIF, cross-product wiring documentation."
    features = {
        "Tue": "core data path / primary API",
        "Wed": "reliability + observability hooks",
        "Thu": "K8s manifests or advanced feature",
    }
    return f"{repo}: implement {features.get(w, 'feature')} — one shippable commit with design note in message."

def ai_for(d):
    if d in OVERRIDES and "ai_idx" in OVERRIDES[d]:
        o = OVERRIDES[d]
        return o["ai_idx"], o["ai_title"], o["ai_sub"], o["ai_hook"]
    if d <= 20:
        for item in AI_EXTENDED:
            if item[0] == d:
                idx, title, sub, hook = item[0], item[1], item[2], item[3]
                return idx, f"Day {idx} of Learning LLM Inference — {title}", f"DS lens: {sub}", hook
    if 30 <= d <= 59:
        i = d - 30
        t = AI_M2[i % len(AI_M2)]
        return d - 9, f"Day {d-9} of Learning LLM Inference — {t}", f"DS lens: TraceForge / {repo_for(d)}", f"Shapes {repo_for(d)} design today."
    if 60 <= d <= 89:
        t = AI_M3[d - 60]
        return d - 9, f"Day {d-9} of Learning LLM Inference — {t}", f"DS lens: RouteIQ / {repo_for(d)}", f"Shapes {repo_for(d)} design today."
    if 90 <= d <= 119:
        t = AI_M4[d - 90]
        return d - 9, f"Day {d-9} of Learning LLM Inference — {t}", f"DS lens: DriftWatch / {repo_for(d)}", f"Shapes {repo_for(d)} design today."
    t = AI_M5[d - 120]
    return d - 9, f"Day {d-9} of Learning LLM Inference — {t}", f"DS lens: FineForge / {repo_for(d)}", f"Shapes {repo_for(d)} design today."

def exp_for(d):
    if d in OVERRIDES and "exp_title" in OVERRIDES[d]:
        o = OVERRIDES[d]
        return o["exp_title"], o["exp_sub"], o["exp_bridge"]
    co, title, bridge = EXPERIENCE_POOL[d % len(EXPERIENCE_POOL)]
    return title, f"From {co} — applied to {repo_for(d)} today", bridge

def build_day(d):
    o = OVERRIDES.get(d, {})
    repo = repo_for(d)
    slug, pname = product_for(d)
    ai_idx, ai_title, ai_sub, ai_hook = ai_for(d)
    if d in OVERRIDES and "ai_title" in OVERRIDES[d]:
        ai_idx = OVERRIDES[d]["ai_idx"]
        ai_title = OVERRIDES[d]["ai_title"]
        ai_sub = OVERRIDES[d]["ai_sub"]
        ai_hook = OVERRIDES[d]["ai_hook"]
    exp_t, exp_s, exp_b = exp_for(d)
    code = o.get("code", code_default(d, repo))
    thread = f"Same-day thread: {ai_hook} ↔ {exp_b}"
    proj = o.get("project_blog")
    if proj is None and WEEKDAY[(d + 1) % 7] == "Fri" and d not in (29, 59, 89, 119, 149):
        proj = f"Weekly · Project — {repo}: architecture decisions + benchmarks this week"
    prod = o.get("product_blog")
    if prod is None and d in (29, 59, 89, 119, 149):
        prod = OVERRIDES.get(d, {}).get("product_blog") or f"Monthly · Product — {pname} shipped: platform thinking essay"
    return {
        "day": d,
        "status": status_for(d),
        "weekday": WEEKDAY[(d + 1) % 7],
        "title": o.get("title", f"Build day — {repo}"),
        "product": slug,
        "product_name": pname,
        "repo": repo,
        "code": code,
        "experience": {"title": exp_t, "subtitle": exp_s, "bridge": exp_b},
        "ai": {"day_index": ai_idx, "title": ai_title, "subtitle": ai_sub, "hook": ai_hook},
        "thread": thread,
        "project_blog": proj,
        "product_blog": prod,
    }

def all_days():
    return [build_day(d) for d in range(150)]
