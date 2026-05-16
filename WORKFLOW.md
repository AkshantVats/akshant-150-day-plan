# Source of Truth — Plans vs Agents

This document defines how **markdown plan files**, **agent chats**, and **plan mode** interact for the 150-day multi-agent workflow. Read it at session start alongside [CHECKLIST.md](CHECKLIST.md).

---

## Canonical source

| What | Where |
|------|--------|
| **Day execution plans** | `plans/day-NN-*.md` in this repo (`akshant-150-day-plan`) |
| **Daily orchestration** | [CHECKLIST.md](CHECKLIST.md) |
| **Day metadata** | `data/plan.json` |
| **Local only** | Plan repo and `plans/` are **not pushed** to GitHub — they are your private contract with agents |

**Rule:** If chat and a plan `.md` disagree, the **`.md` wins** after you edit it. Chat summaries are not a second source of truth.

---

## Flow (planning → approval → implementation)

```
plan.json + CHECKLIST.md
        ↓
  Agent writes/updates plans/day-NN-*.md  (plan mode: no code, no HTML)
        ↓
  Human reviews in chat (summaries OK) — edits go back INTO the .md files
        ↓
  User says: approve code | approve experience | approve ai
        ↓
  Implementation agent READS the approved .md again (not chat memory alone)
        ↓
  Code / HTML / Profile writes
```

### Planning phase

- Plans live in markdown under `plans/`.
- Agents **read** the relevant `day-NN-*.md` (and CHECKLIST) at **session start**.
- Agents **write or update** those files during plan mode — not only in chat.

### Chat “plan mode”

- **Plan mode** = no implementation artifacts: no commits, no HTML, no Profile repo writes until approval.
- Chat is for **human review**: summaries, questions, diffs discussed in thread.
- Any decision that changes scope → **edit the `.md` first**, then re-approve.
- Do **not** treat Agent 1/2/3 chat briefs as authoritative; they are distillations of the md files.

### After approval

| User command | Agent reads | Then implements |
|--------------|-------------|-----------------|
| `approve code` | `plans/day-NN-code-plan.md` | infra-ai-streaming (or day’s code repo) |
| `approve experience` | `plans/day-NN-experience-blog-plan.md` | Draft in chat → HTML in Profile after approve |
| `approve ai` | `plans/day-NN-ai-learning-blog-plan.md` | AI Learning HTML in Profile |

**Blog publishing (Profile site):** Rough markdown in `plans/drafts/` is for review only — not the live blog. Published HTML lives in Profile under `blog/series/...`. Cross-links in HTML must use the live site (`https://akshantvats.github.io/Profile/...` or verified `/Profile/blog/...` paths). Never use `file://`, `localhost`, or `plans/drafts/` in published HTML; replace draft `TBD` sibling links with canonical URLs before merge. See [CHECKLIST.md](CHECKLIST.md) § B — **Publishing & cross-links**.

Implementation agents must **re-open the approved md** before coding or publishing — not rely on chat memory alone.

### Scope changes during review

1. Edit the appropriate `plans/day-NN-*.md`.
2. Tell the agent which file changed.
3. Re-approve the workstream.

---

## Per workstream files (Day 4 example)

| File | Agent | Workstream |
|------|-------|------------|
| `plans/day-04-code-plan.md` | A1 | Code — branches, compose, Go consumer, tests |
| `plans/day-04-experience-blog-plan.md` | A2 | Experience blog — outline, Walmart §1b, Mermaid, bridge |
| `plans/day-04-ai-learning-blog-plan.md` | A3 | AI Learning blog — title format, DS analogy, schema refs |

Naming pattern for other days: `day-NN-code-plan.md`, `day-NN-experience-blog-plan.md`, `day-NN-ai-learning-blog-plan.md`.

---

## What agents should do (recommended)

| Do | Don’t |
|----|--------|
| Read `plans/day-NN-*.md` at session start | Treat chat-only summaries as the contract |
| Update md when the plan changes | Implement code/HTML while still in plan mode |
| Re-read md after `approve *` | Use `day-004-*` branch names (see CHECKLIST **Branching & Git Standards**) |
| Put Daily Thread in commit bodies | Put calendar day in branch names |

**Plan mode ≠ “only talk in chat.”** Plan mode means **no implementation** until approve; the **md files are the contract**.

---

## Related docs

- [CHECKLIST.md](CHECKLIST.md) — branching, X of N / N of N numbering, daily phases
- [checklist.html](checklist.html) — interactive checklist UI
- `data/plan.json` — per-day titles, threads, repo, status
