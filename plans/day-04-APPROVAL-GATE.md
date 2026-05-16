# Day 4 — Approval Gate & Implementation Launch

**Calendar day:** 4 of N · **Date:** 2026-05-16  
**Phase 1 (plan mode):** Complete — three plan files are the contract.  
**Phase 2 (this doc):** User approval → parent launches Phase 3 implementation agents.

---

## Source of truth

| Artifact | Role |
|----------|------|
| `plans/day-04-code-plan.md` | Code workstream (A1) |
| `plans/day-04-experience-blog-plan.md` | Experience blog (A2) |
| `plans/day-04-ai-learning-blog-plan.md` | AI Learning blog (A3) |
| [WORKFLOW.md](../WORKFLOW.md) | Plans vs chat; md wins on conflict |
| [CHECKLIST.md](../CHECKLIST.md) | Branching, validation, blog workflow |

**If chat and a plan `.md` disagree, edit the `.md` first, then re-approve.**

Plan-mode agent chats are **not** authoritative — they distilled into the three `day-04-*-plan.md` files above.

---

## What the user must reply

Reply in the **parent** chat with **one** of:

| Command | Effect |
|---------|--------|
| **`approve all`** | Launch all three implementation agents in parallel |
| **`approve code`** | Launch code agent only (A1) |
| **`approve experience`** | Launch Experience blog agent only (A2) |
| **`approve ai`** | Launch AI Learning blog agent only (A3) |

You may approve workstreams on different days; each approval is independent.

**Not valid for implementation:** silence, “looks good”, or edits in chat without an explicit `approve *` command.

---

## After approval — parent orchestration

1. **Re-read** the user’s approval scope (`all` vs single workstream).
2. **Launch parallel Task agents** (one per approved workstream) with prompts that **point to the IMPLEMENT file**, not chat memory alone:

| Workstream | Launch prompt must include |
|------------|----------------------------|
| Code | Read and follow `plans/day-04-IMPLEMENT-agent-1-code.md` |
| Experience | Read and follow `plans/day-04-IMPLEMENT-agent-2-experience.md` |
| AI Learning | Read and follow `plans/day-04-IMPLEMENT-agent-3-ai.md` |

3. **Do not** re-run plan mode unless the user asks to revise plans.
4. **Do not** write to `infra-ai-streaming` or `Profile` from the parent unless the user already approved that workstream in this session.

### Suggested parent launch message (template)

```text
Day 4 implementation — approved: [all | code | experience | ai]

Agent 1 (if code): Execute plans/day-04-IMPLEMENT-agent-1-code.md end-to-end.
Agent 2 (if experience): Execute plans/day-04-IMPLEMENT-agent-2-experience.md end-to-end.
Agent 3 (if ai): Execute plans/day-04-IMPLEMENT-agent-3-ai.md end-to-end.

Re-read the matching day-04-*-plan.md before any writes. Report blockers to user.
```

---

## What each implementation agent does (summary)

| Agent | IMPLEMENT file | Repo / output | Push policy |
|-------|----------------|---------------|-------------|
| **A1 Code** | `day-04-IMPLEMENT-agent-1-code.md` | `/Users/akshant/Desktop/github/infra-ai-streaming` | Local commits OK; **no `git push`** unless user says push |
| **A2 Experience** | `day-04-IMPLEMENT-agent-2-experience.md` | Markdown draft in `plans/drafts/` (default); Profile HTML only if user already approved experience **and** draft approved | No Profile push unless user says push |
| **A3 AI Learning** | `day-04-IMPLEMENT-agent-3-ai.md` | Markdown draft in `plans/drafts/` (default); Profile HTML only if user already approved ai **and** draft approved | No Profile push unless user says push |

---

## Shared Daily Thread (all agents)

> Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance asks.

Paste verbatim in commit bodies (code) and blog drafts (A2/A3).

---

## Cross-workstream sync (Day 4)

| When | Who notifies whom |
|------|-------------------|
| Code E2E passes | Blog agents — final compose service list, consumer log format, commit SHA |
| Blog drafts need JSON/log quotes | Code agent — freeze test event + stdout snippet per code plan §7 |
| User changes Daily Thread | Edit `data/plan.json` + all three plan md files → re-approve affected streams |

**Blog HTML** (Profile) requires draft approval **and** code SHA for accurate snippets — see CHECKLIST §B workflow.

---

## Files in this launch pack

```
plans/day-04-code-plan.md              ← plan (done)
plans/day-04-experience-blog-plan.md   ← plan (done)
plans/day-04-ai-learning-blog-plan.md  ← plan (done)
plans/day-04-APPROVAL-GATE.md          ← this file
plans/day-04-IMPLEMENT-agent-1-code.md
plans/day-04-IMPLEMENT-agent-2-experience.md
plans/day-04-IMPLEMENT-agent-3-ai.md
plans/drafts/                          ← blog markdown drafts (created by A2/A3)
```

---

## Anti-patterns

- Implementing code or Profile HTML **before** explicit `approve *`
- Treating plan-mode chat as the contract instead of the `.md` files
- Branch names like `day-004-*` (use CHECKLIST FAANG/OSS names)
- Pushing plan repo, code, or Profile without user saying push
- Writing LinkedIn/X posts in agent scope (published URLs only, per CHECKLIST)

---

*Local only — do not push `akshant-150-day-plan` to GitHub.*
