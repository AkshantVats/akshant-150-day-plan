# Day 51 — AI Learning Blog Plan

**Title**: Day 51 — Benchmark Methodology for Agents
**Subtitle**: Tasks, seeds, success criteria
**Day index**: 51
**Hook**: Same task spec or you're comparing different jobs.

**Format**: `design` / `deep-dive` hybrid — per `docs/BLOG-FORMAT-MIX.md`'s AI Learning
table: cost/routing/methodology signals map to `design` or `deep-dive`. Teach the one
mechanism (why a benchmark needs a fixed task spec) with the DS analogy required by
CLAUDE.md section 4.5/4.3.

**DS analogy** (attr-box, physical/everyday object): a benchmark without a fixed task
spec is like timing two runners on different tracks and calling the faster time "the
better runner" — one track might be downhill, shorter, or on a tailwind. The comparison
is meaningless until both runners run the *same* course under the *same* conditions.

**Core concept**: an agent benchmark task needs three things pinned before any comparison
is meaningful — the seed (so both agents see the same "random" draws), the prompt (so
both face the same instruction), and the success criteria (so "pass" means the same thing
for both). Miss any one and a measured difference could be scenario noise, not agent
skill.

**Mermaid diagram** (≤8 nodes, labels ≤6 words): Task YAML → Agent A run + Agent B run →
Criteria grading (per agent) → Compare (divergence + pass/fail) → Benchmark Result.

**Required mermaid init block**: per CLAUDE.md section 4.5, exact block, no variations.

## Series Navigation

Previous: Day 50 — Operability — CLI as API
Next: Day 52 — TBD
