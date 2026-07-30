# Day 45 — AI Learning Blog Plan

**Title**: Day 45 — Object Storage Economics for Traces
**Subtitle**: JSONL, zstd, lifecycle policies
**Hook**: Traces are logs; price them like logs.
**day_index**: 45

## Angle

Clone the GOLD post's depth (`day-2-continuous-batching-vllm.html`) and the most recent AI
Learning post's structure. This is a distributed-systems-engineer-learning-AI-infra post, not
an ML-internals post: the reader already knows storage systems, is new to why AI-agent traces
specifically need this treatment.

Cover, in order:

1. **Hook**: why trace volume explodes for agentic systems (every tool call, every model turn,
   every retry is its own event) — and why treating that like log data (not metrics, not a
   database) is the right mental model.
2. **DS analogy (attr-box)**: object storage lifecycle policies are the same shape as log
   rotation — grounded in a physical/everyday object, not another software concept.
3. **The three levers**: compression (zstd — why zstd over gzip: better ratio at comparable
   speed, frame-based so it streams), checksums (why hash the compressed bytes, not the
   original — detects corruption introduced by the compression/transport step itself), and
   retention tiering (why 30/90 days specifically — matches the WhiteFalcon-inspired hot/cold
   split referenced in today's Experience post, adapted to trace access patterns).
3. **What `pkg/export` and `pkg/objectstore` do**: the `ObjectStore` interface abstraction and
   why testing against an in-memory fake (not a live MinIO container) is the correct call for
   this stage — deterministic, fast CI, no service dependency.
4. **Mermaid diagram**: EventLog → Exporter → zstd compress → checksum → ObjectStore(MinIO)
   flow, ≤8 nodes, required init block from CLAUDE.md section 4.5, labels ≤6 words.
5. **So-what**: this is the foundation the Day 46 replay runner will read from — replay needs
   trustworthy, cheap, long-lived storage before it needs anything else.

Kicker: `Day 45 of 150`. Required mermaid init block. Max 3 sentences/paragraph.
