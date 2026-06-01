# AI Learning Day 15 — Multi-Model Routing Strategies

**Status:** DONE — blog published to main branch.

**URL:** https://akshantvats.github.io/Profile/blog/series/ai-learning/day-15-multi-model-routing-strategies.html

**File:** `blog/series/ai-learning/day-15-multi-model-routing-strategies.html`

---

## Summary

**Title:** Day 15 — Multi-Model Routing Strategies

**Subtitle:** Cost-first vs quality-first vs latency-first routing between LLM models — routing policy as a feature flag engine with GPUs.

**Hook (plan.json):** *Routing is policy engines — you operated feature flags for humans; models are flags with GPUs.*

Hook correctly placed at top of post. ✓

---

## Key themes covered

1. **Feature flag analogy** — LaunchDarkly / Flipt rules map 1:1 to model routing rules; the predicate language is identical, the variant is now a GPU endpoint
2. **Three-axis tradeoff** — cost vs quality vs latency (CAP theorem equivalent for routing operators)
3. **Policy engine design** — priority-ordered rules, intent classifier (5–10ms), per-tier overrides
4. **Shadow routing** — duplicate traffic to candidate model for offline quality evaluation; promotion gated on statistical confidence over N=1000 requests
5. **LensAI connection** — routing decision (rule_id + matched_rule) must be fields on InferenceEvent, not just model_id; schema extension target for Day 15+

---

## Series position

- Previous: Day 14 — eBPF for AI Infrastructure (theory/design)
- This: Day 15 — routing policy (what to do with the traces from Day 14)
- Next: Day 16 — SSL_write uprobe (implementation continues)

---

## Mermaid diagram

Post includes a routing flowchart: REQ → POLICY → LARGE/MID/SMALL model nodes, with `%%{init:` theme block. ✓

---

## Series thread (plan.json)

> Syscall capture v0 is useless without a routing policy later — flagd will decide which model the probe's latency belongs to.

This connection is explicitly made in the post's LensAI section. ✓
