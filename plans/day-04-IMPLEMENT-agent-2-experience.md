# Day 4 — Implementation Agent 2 (Experience Blog)

**You are the Experience blog implementation agent (A2) for calendar day 4 of N.**  
**User has approved the experience workstream** (`approve experience` or `approve all`). If you were launched without that approval, **stop** and tell the user to approve via [day-04-APPROVAL-GATE.md](day-04-APPROVAL-GATE.md).

---

## Mandatory reads (session start)

1. `plans/day-04-experience-blog-plan.md` — **primary contract**
2. [CHECKLIST.md](../CHECKLIST.md) — §B Blog Checklist (Experience series)
3. [WORKFLOW.md](../WORKFLOW.md) — draft before HTML; md wins over chat

Optional: read `plans/day-04-code-plan.md` §7 for code/blog contract (JSON, stdout format).

**Do not** rely on chat summaries alone. If this IMPLEMENT file conflicts with `day-04-experience-blog-plan.md`, **the experience plan wins**.

---

## Workstream mode (check user approval level)

| User said | Your deliverable |
|-----------|------------------|
| **`approve experience`** only (default Phase 3) | **Markdown draft** in plan repo for user review — **no Profile HTML** |
| **`approve experience`** + user already approved **draft** in a prior message | **Profile HTML** + `series-index.json` per plan §1 |
| Launched without `approve experience` | **Stop** |

**Default for `approve experience`:** implement = write full draft markdown under:

```
/Users/akshant/Desktop/github/akshant-150-day-plan/plans/drafts/day-04-experience-seven-million-iot-sensors.md
```

Create `plans/drafts/` if missing.

**Do not** write `Profile/blog/.../*.html` until:

1. User explicitly approved this workstream (`approve experience`), **and**
2. User reviewed the markdown draft and said draft is approved / OK for HTML (CHECKLIST §B: “NO HTML until user explicitly approves draft”)

If the parent message says the user **already approved the draft** in chat, skip straight to HTML using the approved draft as source.

---

## Post metadata (locked)

| Field | Value |
|-------|--------|
| **Headline** | Seven Million IoT Sensors — Failure Modes Textbooks Skip |
| **Kicker** | Experience Series · **4 of N** |
| **Subtitle (hero)** | 4 of N — Experience Series · Walmart · refrigeration, HVAC, and why bad telemetry is worse than a crash |
| **Slug / filename** | `seven-million-iot-sensors-failure-modes.html` |
| **Profile path** | `blog/series/agoda/seven-million-iot-sensors-failure-modes.html` |
| **Published time** | 2026-05-16 |
| **Read time** | 14–16 min |

**Walmart alignment:** Follow experience plan §1b — corporate post citations, voice boundaries, no overclaim on throughput.

---

## Shared Daily Thread (verbatim)

First prose paragraph after title block:

> **Daily Thread (Day 4):** Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance asks.

---

## Draft content requirements

Produce a **complete markdown draft** matching experience plan §2 outline (sections 0–10 + footer):

| `id` | Header |
|------|--------|
| `scale` | Seven Million Data Points — Until a Case Stops Being Boring |
| `textbook-gap` | What Textbooks Teach vs What Production Teaches |
| `identity` | Device Identity Is a Partition Key, Not a String |
| `poison` | Poison Telemetry: The IoT Version of a Hot Partition |
| `edge-vs-cloud` | Edge Filtering vs Cloud Aggregation |
| `failure-modes` | Five Failure Modes I Still Design For |
| `compose-bridge` | Why Today's `docker compose` Is Shard Isolation Practice |
| `lensai` | Same Muscle, Different Silicon: LensAI Day 4 |
| `tradeoffs` | What We Didn't Do (and Why) |
| `stayed` | The Thing That Stayed With Me |

Include in the draft file:

1. **Three Mermaid diagrams** (A–C) — source blocks from experience plan §3
2. **Stat callout** — four numbers from plan §8 (7M+, 1.5B/day, 50+ facilities, failure classes)
3. **Code snippets** — compose excerpt + event JSON from plan §9 (update from code agent if SHA available)
4. **Cross-link** to AI Day 3 — plan §6 (placeholder URL OK until A3 publishes)
5. **Tradeoffs** — plan §10 table as prose
6. **Retrofix suggestions** — plan §11 as appendix for user yes/no
7. **Corporate citation** — link [Walmart IoT ice cream post](https://corporate.walmart.com/news/2021/01/14/how-walmart-leverages-iot-to-keep-your-ice-cream-frozen)

**Tone:** Match `when-percentiles-lie-cross-tier-queries.html` — short paragraphs, story-led, pullquote for thesis.

---

## Sync with code agent (A1)

Before finalizing draft snippets:

| Need | Source |
|------|--------|
| Final `docker-compose` service list | Code agent / `day-04-code-plan.md` |
| Go consumer log line format | Code agent stdout after E2E |
| Commit SHA | Code agent — footnote only, no full diff |

If code is not finished: use plan §9 placeholders and mark `[TBD: commit SHA]` in draft.

**Do not** claim ClickHouse writes or throughput equal to Walmart scale on laptop compose.

---

## HTML phase (only after draft approval)

When user approves draft for HTML:

1. **Template:** Copy structure from `Profile/blog/series/agoda/when-percentiles-lie-cross-tier-queries.html`
2. **Write** `Profile/blog/series/agoda/seven-million-iot-sensors-failure-modes.html`
3. **Update** `series-index.json` entry from experience plan §1
4. **Mermaid:** `<pre class="mermaid">` + CDN init (same as post 2)
5. **Local preview:** `python3 -m http.server` in Profile — verify mermaid renders
6. **No push** unless user says push

---

## Profile repo path

`/Users/akshant/Desktop/github/Profile` (or user’s local clone of `akshantvats/Profile`)

**Only touch Profile when in HTML phase** (draft approved). Default phase writes **only** to `akshant-150-day-plan/plans/drafts/`.

---

## Consistency checklist

- [ ] Kicker: **4 of N** (Experience Series)
- [ ] Walmart §1b cautions respected
- [ ] Sibling link to AI Day 3
- [ ] Daily Thread verbatim
- [ ] Mermaid ≥2
- [ ] Tradeoffs section
- [ ] No HTML in default `approve experience` path

---

## Report back

**After markdown draft:**

- Path to draft file
- Word count estimate
- Open questions / TBDs (SHA, AI URL, compose service count)
- Ask user: approve draft for HTML / request edits

**After HTML (if applicable):**

- File path + local preview URL
- `series-index.json` updated yes/no
- Retrofix items user should schedule

---

*Implementation agent A2 — Day 4 · Experience Series · 4 of N*
