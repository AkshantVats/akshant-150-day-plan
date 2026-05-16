# Daily Multi-Agent Checklist — Akshant Sharma · Platform Plan

> **Source of truth** for every workday. Copy sections into agent prompts or tick boxes in [checklist.html](checklist.html).  
> **Plans vs agents:** see [WORKFLOW.md](WORKFLOW.md) — `plans/day-NN-*.md` are the implementation contract; chat plan mode is review-only until `approve code|experience|ai`.  
> **Repos:** [infra-ai-streaming](https://github.com/akshantvats/infra-ai-streaming) · [Profile](https://github.com/akshantvats/Profile)  
> **Rule:** Plan mode first → user approves → then implement. **No Day-specific execution plans in this file** — fill those per day after pre-flight.  
> **Public numbering:** Experience posts use **X of N**; AI Learning uses **N of N** (series index). **N** = open-ended series length — not a fixed count in blog copy. The local plan site may still track 150 calendar days internally.

---

## Branching & Git Standards

Use **FAANG/OSS-style branch names** — scoped to the change, not the calendar day or sprint ticket.

### Branch name format

```
<type>/<short-kebab-description>
```

| Type | When to use | Examples |
|------|-------------|----------|
| `feat/` | New capability | `feat/consumer-kafka-stdout-skeleton` |
| `fix/` | Bug fix | `fix/ingest-partition-key-tenant-model` |
| `chore/` | Tooling, compose, CI | `chore/deploy-prometheus-grafana-compose` |
| `docs/` | Docs-only | `docs/readme-e2e-quickstart` |
| `refactor/` | Behavior-preserving restructure | `refactor/consumer-config-package` |
| `test/` | Tests only | `test/consumer-batch-deserialize` |

### Rules

- **Branch off updated `main`** — short-lived; one logical theme per branch when possible.
- **PR-ready** — each branch should be reviewable as a standalone PR (clear title, Conventional Commits, tests/docs as needed).
- **Conventional Commits** on every commit (`feat`, `fix`, `docs`, `chore`, etc.).
- **No personal sprint names** in branch names — avoid `day-004-*`, `sprint-3-*`, `akshant-week-2-*`.
- **Split by commit area** when Day work spans unrelated surfaces (e.g. compose vs consumer vs docs) — prefer 2–4 focused branches over one mega-branch.
- **Daily Thread** goes in commit **body** (`Refs: …`), not in the branch name.

### Day plans reference

Code execution plans list **recommended branch name(s)** per deliverable — not `day-NNN-*` placeholders.

---

## Daily header (fill each morning)

_Last filled example: **Day 4** · 2026-05-16 (Saturday). Copy structure for Day 5+; do not delete future-day placeholders elsewhere._

| Field | Value |
|-------|--------|
| **Calendar day** | 4 of N _(internal calendar; public blogs use same pattern)_ |
| **Date** | 2026-05-16 |
| **Today's repo** | `infra-ai-streaming` (from `data/plan.json`) |
| **Branch(es)** | `feat/deploy-prometheus-grafana-redpanda-init`, `feat/consumer-kafka-stdout-skeleton` → merged to `main` |
| **Shared Daily Thread (one-liner)** | Go consumer skeleton exists so tomorrow's ClickHouse writer can aggregate cost_usd the way finance asks. |

---

## A. Master Daily Flow (orchestration)

### Pre-flight (before any agent runs)

- [x] Open local plan site: `index.html` → confirm today's row status (`today` / `pending` / `done`)
- [x] Read `data/plan.json` for **day N**: `code`, `repo`, `experience`, `ai`, `thread`, `status`
- [x] Confirm **code repo** exists locally and remote: `infra-ai-streaming` or day's repo under `akshantvats`
- [x] Confirm **Profile** repo cloned; blog folders for Experience + AI Learning series exist
- [x] Create/checkout branch(es) per **Branching & Git Standards** (e.g. `feat/consumer-kafka-stdout-skeleton`) — never commit on `main` without approval
- [x] Note cross-day carryover: open PRs, failing CI, draft blogs from yesterday
- [x] Set plan.json `status` for today to `today` if not already (local only; do not push plan site)

### Phase 1 — Plan mode (3 parallel workstreams, **no implementation**)

Run **three independent agents** in parallel. Each outputs **markdown plan only** (see [D. Multi-Agent Rules](#d-multi-agent-rules)).

| Agent | Workstream | Plan must include |
|-------|------------|-------------------|
| **A1** | Code / project dev | What, why, arch impact, files, tests, README/DESIGN updates, commit outline |
| **A2** | Experience blog (Profile) | Headline, subtitle, bridge to today's code, thread link, outline, mermaid ideas |
| **A3** | AI Learning blog (Profile) | Title format, DS analogy, hook to design, schema/API refs from code plan |

- [x] A1 plan references today's `plan.json` `code` block and target repo
- [x] A2 plan uses **Experience Series** naming; calendar **X of N**
- [x] A3 plan uses **Day N of Learning LLM Inference** (AI day index from plan)
- [x] All three plans include **Shared Daily Thread** one-liner
- [x] Cross-dependencies called out (see dependency matrix in section D)
- [x] **Stop:** no code edits, no HTML blog files, no `git push`

### Phase 2 — User approval gate

- [x] User reviews all three plans in chat (and checklist.html if helpful)
- [x] User approves, requests edits, or defers a workstream
- [x] Record approved scope per agent (what's in / out for today)
- [x] Update Shared Daily Thread if user edits the one-liner
- [x] **Gate:** do not start Phase 3 until explicit approval

### Phase 3 — Implementation (separate agents per approved workstream)

- [x] **Code agent:** branch, implement, test, docs, local commits (see [C. Code Development](#c-code-development-checklist))
- [x] **Experience blog agent:** draft in chat if not done → user review → HTML only after approval
- [x] **AI Learning blog agent:** same workflow as Experience
- [x] Agents stay in scope; escalate blockers to user, don't silently expand scope
- [x] Sync mid-day if code schema/API changed — notify blog agents before they finalize HTML

### Phase 4 — End of day

- [x] Mark day `done` in `data/plan.json` (and regenerate plan HTML if you use `generate_plan.py`)
- [x] Code: commit pointers in Profile blogs (commit SHA, PR link) — not full diffs in blogs
- [x] **Distribution:** share **published blog URLs only** (site live first); no separate LinkedIn/X post drafting in agent scope
- [x] Update master table mental note: tomorrow's pre-flight reads day N+1
- [ ] Optional: note retrofix items for prior posts (blog checklist section B)

---

## B. Blog Checklist (Experience + AI Learning)

Applies to **both** series in [Profile](https://github.com/akshantvats/Profile). One agent per series.

### Series identity & numbering

- [x] **Experience Series** (formerly "Agoda Series") — production war stories, company-scale bridge to today's code
- [x] Experience post label: **X of N** (calendar day index; **N** = open-ended — do not hardcode 150 in public copy)
- [x] **AI Learning series** title format (locked): `Day N of Learning LLM Inference — <Topic>` (N = `ai.day_index` from plan)
- [x] Subtitle tone matches prior posts (check last 1–2 in series)

### Content consistency (before writing)

- [x] Read **previous 1–2 posts** in the same series (HTML + structure, heading levels, code block style)
- [x] Match: tone, section order, syntax highlighting, footer/cross-links, diagram style
- [ ] List **retrofix suggestions** for older posts (optional backlog; do not block today):
  - [ ] _Post title / link / numbering drift_
  - [ ] _Missing mermaid where architecture is central_
  - [ ] _Thread link to sibling blog broken or missing_

### Workflow (strict)

- [x] **Draft in chat first** (outline + key paragraphs + mermaid source)
- [x] User review & approval on draft
- [x] **NO HTML file** until user explicitly approves draft
- [x] After approval: write HTML → correct blog folder in Profile → integrate into Profile site nav/index
- [x] **Publishing order:** Profile site live → verify URL → share link only (no agent-written LinkedIn/X threads)

### Publishing & cross-links (live Profile site)

**Rule:** All cross-links and published URLs must use the **live Profile site** — not local file paths, `file://`, `localhost`, or links that only work on disk.

**Canonical base:** `https://akshantvats.github.io/Profile/`

| Surface | Where | Role |
|---------|--------|------|
| Draft markdown | `plans/drafts/` in this repo | Rough content for review — **NOT** the live blog |
| Published HTML | Profile repo `blog/series/...` | What readers see on GitHub Pages |

- [x] **Draft phase:** `plans/drafts/*.md` is review-only — never treat draft paths as the public blog URL
- [x] **HTML** lives in [Profile](https://github.com/akshantvats/Profile) under `blog/series/...` (e.g. `blog/series/ai-learning/`, `blog/series/agoda/` or renamed experience path)
- [x] **Cross-links** between posts use full canonical URLs under the base above (e.g. `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html`) — or site-relative paths that resolve on Pages (e.g. `/Profile/blog/series/...`); verify against Profile repo layout before merge
- [x] **Never** use `file://`, `localhost`, `plans/drafts/`, or relative-only links in published HTML that break off GitHub Pages
- [x] **Placeholder `TBD`** in drafts for sibling posts not yet published; replace with canonical URL before HTML merge to Profile

**Examples (canonical):**

- AI Learning: `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html`
- Experience: `https://akshantvats.github.io/Profile/blog/series/agoda/` (or current experience series path when renamed)

### Mermaid & visuals

- [x] Architecture or request/flow posts include **Mermaid** (sequence, flowchart, or C4-style)
- [x] Data path / Kafka / consumer / API posts: diagram required unless user waives
- [x] Validate mermaid renders on Profile site (build/preview locally)

### Per-blog section template (both series)

Use these sections in draft and final HTML:

| Section | Experience Series | AI Learning Series |
|---------|-------------------|---------------------|
| **Headline** | Story-led, Agoda/Delivery Hero/Walmart scale | Concept-led, inference/ML systems |
| **Subtitle** | Bridge to today's shipping work | Hook to today's design decision |
| **Thread link** | Link to today's AI Learning post | Link to today's Experience post |
| **Code snippet** | Real or simplified from today's commit | Schema, API, or pseudocode from today's build |
| **Numbers** | Latency, QPS, cost, cardinality — real ranges | Metrics, complexity, memory, throughput |
| **DS analogy** | Light touch if helpful | **Required** — map concept to familiar DS/ML idea |
| **Company bridge** | **Required** — how big-tech scale informs design | Optional short production note |
| **Tradeoffs** | What we didn't do and why | Algorithm vs systems tradeoffs |
| **Cross-link** | Prior Experience post + infra-ai-streaming README | Prior AI day + relevant project doc |

### Voice & tone (match published Profile posts)

Read **full prose** from the last 1–2 posts in the same series (not CSS). Gold standard: problem-first hook, one thesis, earned numbers, one developed DS/systems analogy — not listicle or sprint meta.

| Dimension | Target voice |
|-----------|----------------|
| **Rhythm** | Mix short punchy lines (especially at hooks and turns) with medium explanatory paragraphs. Avoid uniform “one sentence per line” staccato for whole sections unless the post is deliberately thriller-paced (e.g. percentiles essay). |
| **POV** | **I** for what you saw/did/learned; **we** only for team work you were part of. Separate **team vs mine** explicitly on war stories (attr-box pattern in HTML). No false ownership of org-wide scale. |
| **Authority vs humility** | State the claim, then the constraint (“I am not claiming…”, “verify on vendor site”, “aspirational, not Day N benchmark”). Scars and wrong answers beat hype. |
| **Numbers** | Lead with *why the number matters*, then the number. Use tables for comparisons; do not bullet-dump stats. Cite public sources for company scale; do not invent peak QPS. |
| **Analogies** | One extended bridge from systems you know (TSDB, Kafka, OS schedulers) → new domain. Develop it in prose; skip gimmick one-liners (“minibar”, “cosplay”, “same muscle different silicon” unless earned once). |
| **Openings** | Scene or contradiction first (dashboard lied, batch assumption wrong, case drifted) — not Daily Thread, not finance slogan, not “textbooks teach X production teaches Y” template. |
| **Closings** | Reflection + honest next step / series footer. No engagement bait; one forward link max in footer. |
| **Never in body** | Daily Thread / ticket IDs / `plans/drafts` / editor notes; repeated slogan blocks; hedge chains (“it’s worth noting”, “in today’s landscape”); buzzwords without mechanism; “5 things” listicle tone; unqualified utilization multipliers. |

**Draft smell test:** If a paragraph could live in CHECKLIST or a PR description, rewrite as narrative. Meta belongs in HTML comments or plan repo only.

### Pre-publish checklist (each blog)

- [x] Headline + subtitle match series format
- [x] Voice & tone pass (section above) — read aloud against one gold post from same series
- [x] Correct day numbering (**X of N** Experience vs **N of N** AI Learning series index)
- [x] Sibling blog linked via Daily Thread sentence
- [x] All cross-links use live Profile URLs (`https://akshantvats.github.io/Profile/...` or verified `/Profile/blog/...` paths) — no `file://`, `localhost`, or `plans/drafts/` links
- [x] No remaining `TBD` placeholders for published sibling posts
- [x] Code/schema references match **today's actual commit** (after code agent finishes)
- [x] Mermaid present and renders
- [x] Spelling, code fences, accessible alt text for diagrams
- [x] Site build passes; URL confirmed on GitHub Pages

---

## C. Code Development Checklist

Target: day's repo (often `infra-ai-streaming`) · GitHub: `akshantvats/<repo>`.

### Planning (Phase 1 — before code)

- [x] **What** ships today (single observable outcome)
- [x] **Why** it matters for platform narrative / day N arc
- [x] **Fit in codebase** — modules touched, no orphan experiments
- [x] **Architecture impact** — Kafka topics, schemas, services, docker-compose services
- [x] **Design choices** — 2–3 options with recommendation
- [x] **Tradeoffs** — latency vs cost, consistency vs speed, etc.
- [x] **Dependencies on blogs** — what Experience/AI posts must reference (API, metric, diagram)
- [x] User approval (Phase 2 gate)

### Implementation

- [x] Branch: `<type>/<short-kebab-description>` from updated `main` (see **Branching & Git Standards**)
- [x] Small, logical commits (see message format below)
- [x] Update **README** if user-facing behavior changed
- [x] Update **DESIGN.md** if architecture/contracts changed
- [ ] Update **BENCHMARKS.md** if perf claims or baselines changed
- [x] docker-compose / Helm / config aligned with docs

### Validation

- [x] `docker compose up` (or project-standard make target) — stack healthy
- [x] Unit/integration tests pass (`go test ./...`, etc.)
- [x] Manual smoke: happy path + one failure path
- [ ] Benchmarks re-run if perf-sensitive change
- [x] Logs/metrics: no obvious PII or secret leakage

### Review (self-review before asking user to push)

- [x] Diff reviewed for debug prints, TODOs, hardcoded secrets
- [x] **Security:** inputs validated, auth boundaries respected, deps pinned
- [x] **Observability:** structured logs, metrics hooks for LensAI narrative where relevant
- [x] Error handling and graceful shutdown
- [x] Does not break Days 0–(N-1) documented quickstart commands

### Git & push policy

**Local commit message format** (Conventional Commits):

```
<type>(<scope>): <subject ≤50 chars>

<body: what and why, 1-3 sentences>
Refs: <calendar day> of N — <repo> — <one-line from Daily Thread>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.

- [x] Commits made locally with messages above
- [x] **Do not `git push`** until user explicitly says push (default: local only)
- [x] If user approves push: push branch, open PR if applicable, paste PR URL to user

---

## D. Multi-Agent Rules

### Agent model

- [ ] **Three independent agents** — one per workstream (code, Experience blog, AI blog)
- [ ] Agents do not share implementation unless user merges workstreams
- [ ] Each agent **starts in Plan mode** → markdown plan artifact only
- [ ] After user approval, agent switches to implementation for its workstream only

### Cross-workstream dependency matrix

| If this changes… | Then notify… | Before… |
|------------------|--------------|---------|
| Public API / proto / schema | AI blog agent | HTML draft finalized |
| User-visible behavior / metric | Experience blog agent | HTML draft finalized |
| README quickstart commands | Both blog agents | Publish |
| Daily Thread one-liner | All agents | Any publish |
| Repo name or day scope | All agents | Pre-flight |

- [x] Dependency rows for **today** filled in during Phase 1 plans
- [x] Code agent posts commit SHA / PR when blogs enter HTML phase

### Shared artifacts

- [x] **Shared Daily Thread** — single sentence from `plan.json` `thread`; all agents quote it
- [x] **This checklist** — reuse every day; do not fork per day
- [ ] Plan artifacts: `plan-day-NNN-code.md`, `plan-day-NNN-experience.md`, `plan-day-NNN-ai.md` (optional local names in chat or `notes/` — never commit plan site to GitHub)

### Anti-patterns (do not)

- [ ] Implement code during blog plan agent run
- [ ] Write HTML before user approves draft
- [ ] Put `file://`, `localhost`, or `plans/drafts/` links in published Profile HTML
- [ ] Push plan website or `data/plan.json` to public GitHub
- [ ] Push code without user saying push
- [ ] Write LinkedIn/X posts in agent scope (links only after site publish)

---

## E. Plan Site Integration (local only)

- [x] Daily workflow uses [checklist.html](checklist.html) (browser) + this file (copy/paste)
- [x] Nav: **Daily Checklist** on master plan and generated pages
- [x] **This repository is local-only** — see `.gitignore` and `README.md`; do not push to `akshantvats` remotes

---

## Quick reference — repositories

| Repo | Purpose |
|------|---------|
| `akshantvats/infra-ai-streaming` | Primary platform / LensAI ingestion codebase |
| `akshantvats/Profile` | Personal site + Experience + AI Learning blogs |
| `akshant-150-day-plan/` (local) | Master calendar, plan.json, checklist — **not for GitHub push** |

---

*Framework Step 1 — reusable daily checklist. Day-specific execution plans are created separately after user reviews this framework.*
