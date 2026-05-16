# Day 4 — Implementation Agent 3 (AI Learning Blog)

**You are the AI Learning blog implementation agent (A3) for calendar day 4 of N.**  
**User has approved the ai workstream** (`approve ai` or `approve all`). If you were launched without that approval, **stop** and tell the user to approve via [day-04-APPROVAL-GATE.md](day-04-APPROVAL-GATE.md).

---

## Mandatory reads (session start)

1. `plans/day-04-ai-learning-blog-plan.md` — **primary contract**
2. [CHECKLIST.md](../CHECKLIST.md) — §B Blog Checklist (AI Learning series)
3. [WORKFLOW.md](../WORKFLOW.md) — draft before HTML; md wins over chat

Optional: `plans/day-04-code-plan.md` §7 for schema/stdout contract; `day-04-experience-blog-plan.md` §6 for cross-link copy.

**Do not** rely on chat summaries alone. If this IMPLEMENT file conflicts with `day-04-ai-learning-blog-plan.md`, **the AI plan wins**.

---

## Workstream mode (check user approval level)

| User said | Your deliverable |
|-----------|------------------|
| **`approve ai`** only (default Phase 3) | **Markdown draft** in plan repo for user review — **no Profile HTML** |
| **`approve ai`** + user already approved **draft** in a prior message | **Profile HTML** + series nav per plan |
| Launched without `approve ai` | **Stop** |

**Default for `approve ai`:** implement = write full draft markdown under:

```
/Users/akshant/Desktop/github/akshant-150-day-plan/plans/drafts/day-04-ai-day-3-token-budgets-cost-structure.md
```

Create `plans/drafts/` if missing.

**Do not** write `Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html` until:

1. User explicitly approved this workstream (`approve ai`), **and**
2. User reviewed the markdown draft and approved HTML (CHECKLIST §B)

If the parent message says the user **already approved the draft**, skip to HTML using that draft.

---

## Post metadata (locked)

| Field | Value |
|-------|--------|
| **H1** | Day 3 of Learning LLM Inference — Token Budgets and Real Cost Structure |
| **Series index** | **3 of N** (AI Learning — not calendar 4 of N in title) |
| **Subtitle** | 3 of N — AI Learning Series. Prompt vs completion pricing as capacity planning — and why `cost_usd` in the ingest schema has to reconcile with provider bills, not vibes. |
| **Target HTML** | `blog/series/ai-learning/day-3-token-budgets-cost-structure.html` |
| **Word target** | 800–1,200 words prose (shorter than Days 1–2) |
| **Read time** | ~10–12 min |

---

## Shared Daily Thread (verbatim)

First paragraph after cold open:

> Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance asks.

---

## Draft content requirements

Full markdown draft with sections from AI plan §2:

| `id` | Section |
|------|---------|
| — | Cold open + Daily Thread |
| `two-buckets` | Two token buckets on every bill |
| `pricing-table` | How providers price (asymmetric) — **dated May 2026** rates |
| `why-completion` | Why completion costs more |
| `ds-analogy` | **Required** — Spark batch vs streaming sink (plan §3) |
| `budgets` | Token budgets as capacity planning |
| `validate` | Reconciling `cost_usd` at ingest |
| `infra-today` | What this changes in infra-ai-streaming today |
| `experience-link` | Sibling Experience Day 4 (one paragraph) |
| `takeaway` | What I am taking away |
| `series-footer` | Tease Day 5 ClickHouse writer |

Include:

1. **Worked example** — plan §4.3 (gpt-4o-class; verify pricing URLs in footnotes)
2. **Pullquote** — “Completion tokens are the variable cost line item…”
3. **Two Mermaid diagrams** — A (cost flow), B (request lifecycle) from plan §5
4. **`InferenceEvent` JSON block** — match code agent commit / README (mark TBD if code pending)
5. **Footnotes** — OpenAI/Anthropic pricing + usage docs (plan §10)
6. **Do NOT duplicate** Experience content (plan §9) — Walmart/IoT/compose blast-radius owned by A2

---

## Sync with code agent (A1)

| Need | Source |
|------|--------|
| `InferenceEvent` field list | `ingestion/src/handlers/ingest.rs` / README after code freeze |
| E2E path (compose + Go stdout) | Code plan §7–§8 |
| Commit SHA | Code agent — footnote in draft |

**Validation formula** (plan §4.2):

```text
cost_usd ≈ (prompt_tokens / 1e6) * rate_input(model)
         + (completion_tokens / 1e6) * rate_output(model)
```

Mention ingest validates `cost_usd >= 0`; producer computes dollars (design decision in plan §6).

---

## Cross-link to Experience (4 of N)

Short paragraph in `experience-link` + footnote:

- Title: *Seven Million IoT Sensors — Failure Modes Textbooks Skip*
- Theme: validate before central aggregation (cost facts vs poison telemetry)
- URL: TBD until A2 publishes — use placeholder in draft

---

## HTML phase (only after draft approval)

When user approves draft for HTML:

1. **Template:** Match Day 2 AI post structure (`day-2-continuous-batching-vllm.html` or latest in series)
2. **Write** `Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html`
3. **Update** series nav / `series-index` data per Profile conventions
4. **Optional retrofix:** Day 2 footer tease → “Day 3 — Token budgets” (plan §11)
5. **Local preview** — mermaid renders
6. **No push** unless user says push

---

## Profile repo path

`/Users/akshant/Desktop/github/Profile`

**Only touch Profile in HTML phase.** Default `approve ai` writes **only** to `plans/drafts/`.

---

## Consistency checklist

- [ ] Title format: `Day 3 of Learning LLM Inference — …`
- [ ] Subtitle prefix: `3 of N — AI Learning Series.`
- [ ] DS analogy section present
- [ ] Mermaid ×2
- [ ] Daily Thread verbatim
- [ ] No Walmart war story (Experience owns)
- [ ] Word count ~800–1,200
- [ ] No HTML in default path

---

## Report back

**After markdown draft:**

- Path to draft file
- Word count
- Pricing sources dated
- TBDs (commit SHA, Experience URL)
- Ask user: approve draft for HTML / edits

**After HTML (if applicable):**

- File path + preview URL
- Retrofix note for Day 2 footer

---

*Implementation agent A3 — Day 4 · AI Learning · 3 of N*
