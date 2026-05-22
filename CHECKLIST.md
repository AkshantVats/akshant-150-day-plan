# Daily Multi-Agent Checklist — Akshant Sharma · Platform Plan

> **Source of truth** for every workday. Copy sections into agent prompts or tick boxes in [checklist.html](checklist.html).  
> **Plans vs agents:** see [WORKFLOW.md](WORKFLOW.md) — `plans/day-NN-*.md` are the implementation contract; chat plan mode is review-only until `approve code|experience|ai`.  
> **Repos:** [infra-ai-streaming](https://github.com/akshantvats/infra-ai-streaming) · [Profile](https://github.com/akshantvats/Profile)  
> **Rule:** Plan mode first → user approves plans → **implement per workstream on command** (e.g. “implement code”, “draft experience”, “publish AI”) — do not auto-run all three after one approval. **No Day-specific execution plans in this file** — fill those per day after pre-flight.  
> **Public numbering:** Experience = **Experience X of N** (1-based series index); AI Learning = **Day X of N** (0-based series index). **N** in kickers = open-ended series length — not “150” in public copy. **Calendar day** (150-day plan) ≠ **blog episode index** — see [Blog numbering vs calendar day](#blog-numbering-vs-calendar-day-authoritative) below.

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

_Last filled example: **Day 6** · 2026-05-18 (Monday). Copy structure each morning; do not delete future-day placeholders elsewhere._

| Field | Value |
|-------|--------|
| **Calendar day** | 6 of N _(set `data/current-day.json` → `current_day`; run `python3 generate_plan.py` to refresh site)_ |
| **Date** | 2026-05-18 |
| **Today's repo** | `infra-ai-streaming` (from `data/plan.json`) |
| **Branch(es)** | _(fill per day — e.g. `feat/grafana-dashboard-four-panels`)_ |
| **Shared Daily Thread (one-liner)** | _(from `plan.json` `thread` for day 6)_ |

---

## A. Master Daily Flow (orchestration)

### Pre-flight (before any agent runs)

- [x] Open local plan site: `index.html` → confirm today's row status (`today` / `pending` / `done`)
- [x] Read `data/plan.json` for **day N**: `code`, `repo`, `experience`, `ai`, `thread`, `status`
- [x] Confirm **code repo** exists locally and remote: `infra-ai-streaming` or day's repo under `akshantvats`
- [x] Confirm **Profile** repo cloned; blog folders for Experience + AI Learning series exist
- [x] Create/checkout branch(es) per **Branching & Git Standards** (e.g. `feat/consumer-kafka-stdout-skeleton`) — never commit on `main` without approval
- [x] Note cross-day carryover: open PRs, failing CI, draft blogs from yesterday
- [ ] Bump `data/current-day.json` `current_day` to today's calendar day; run `python3 generate_plan.py` (local only; do not push plan site)

### Phase 1 — Plan mode (3 parallel workstreams, **no implementation**)

Run **three independent agents** in parallel. Each outputs **markdown plan only** (see [D. Multi-Agent Rules](#d-multi-agent-rules)).

| Agent | Workstream | Plan must include |
|-------|------------|-------------------|
| **A1** | Code / project dev | What, why, arch impact, files, tests, README/DESIGN updates, commit outline |
| **A2** | Experience blog (Profile) | Headline, subtitle, bridge to today's code, thread link, outline, mermaid ideas |
| **A3** | AI Learning blog (Profile) | Title format, DS analogy, hook to design, schema/API refs from code plan |

- [x] A1 plan references today's `plan.json` `code` block and target repo
- [x] A2 plan uses **Experience (N − 1) of N** kicker for calendar day **N** (1-based series index)
- [x] A3 plan uses **Day (N − 1) of Learning LLM Inference** (`ai.day_index` = **N − 1** from plan, 0-based)
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
- [ ] **On command only** — after Phase 2 approval, wait for explicit user instruction per workstream; one approved plan does not authorize all three implementations in one run
- [x] Agents stay in scope; escalate blockers to user, don't silently expand scope
- [x] Sync mid-day if code schema/API changed — notify blog agents before they finalize HTML

### Phase 3.5 — Local verification & user showcase (mandatory before PR)

**Order:** implement → **test locally** → **showcase to user** → **user explicitly approves** → **only then** push branch + open PR.

Do **not** open a PR until the user has run (or watched) local proof and signed off. Past regret: infra PR #2 and Profile PR #1 shipped without this gate.

| Surface | What to verify locally |
|---------|-------------------------|
| **infra-ai-streaming** | `docker compose up` (Redis, Redpanda, ClickHouse, Prometheus, Grafana healthy); consumer + ingestion running; `curl` ingest → Kafka → consumer → ClickHouse; Grafana product + E2E dashboards load with data |
| **Profile blogs** | `python3 -m http.server` from repo root; open new post URLs, `blog/series-index.json` nav, on-page heroes, `og:image` paths (file exists; absolute URLs checked after Pages deploy) |
| **Plan site** (optional) | `index.html` / checklist.html — calendar day row matches `data/plan.json` |

**Agent showcase (required before asking for push/PR):**

- Paste **exact commands** the user should run (copy-paste ready).
- Paste **URLs** to open (Grafana UIDs, local blog paths, Prometheus targets).
- State **what to look for** per panel/section (expected metric, row count, kicker index).
- Note known fixes on the branch (e.g. ClickHouse datasource `jsonData.host`) if panels may be empty until compose restart.

**User sign-off (explicit phrase required):**

- User must say they tested locally and approve push/PR — e.g. **"approved — push and open PR"**, **"LGTM push"**, or **"merge-ready"** with scope named (infra / Profile / both).
- **No PR** and **no `git push`** until that phrase (same as [Git & push policy](#git--push-policy) in section C).

- [ ] Local verification checklist completed (infra compose + dashboards, and/or Profile `http.server` preview)
- [ ] User received showcase (commands + URLs + pass criteria)
- [ ] User sign-off recorded in chat
- [ ] **Then only:** push feature branch(es) and open PR(s) — PR creation is the **last** step, not part of implementation

### Phase 4 — End of day

- [x] Mark day `done` in `data/plan.json` (set `status` to `done` for completed day, then bump `data/current-day.json` and run `python3 generate_plan.py`)
- [x] Code: commit pointers in Profile blogs (commit SHA, PR link) — not full diffs in blogs
- [x] **Distribution:** share **published blog URLs only** (site live first); no separate LinkedIn/X post drafting in agent scope
- [x] Update master table mental note: tomorrow's pre-flight reads day N+1
- [ ] Optional: note retrofix items for prior posts (blog checklist section B)

### Phase 4 — Day completion gates (before marking `done`)

Use when the day ships **code + observability + blogs** (Day 4 pattern). Do not mark `plan.json` `done` until each applicable row passes.

| Gate | Proof required |
|------|----------------|
| **E2E pipeline** | Reproducible path documented (README quickstart or script): e.g. ingest/event → Kafka → consumer visible in logs/metrics; paste command + expected output or screenshot |
| **Grafana** (if in scope) | Dashboard JSON committed under repo `dashboards/` (or compose provisioning); README or PR includes screenshot; panels match today's metrics/schema story |
| **Code remote** | User said **push** — branch on remote, PR link if applicable (default remains local-only until explicit push) |
| **Profile publish** | Approved HTML merged; GitHub Pages live; canonical post URLs verified (hard refresh); commit SHA in blogs matches shipped code |
| **Social preview** | `og:image` absolute HTTPS URLs return 200; re-scrape after deploy ([LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/), X card validator if needed) — caches lag 1–24h |

- [ ] All gates for today checked off (waive only with user note in chat)

---

## B. Blog Checklist (Experience + AI Learning + LensAI)

Applies to **all Profile blog series** in [Profile](https://github.com/akshantvats/Profile). One agent per series when multiple ship same day. **Authoritative publish detail:** [Profile `blog/NEW-POST-CHECKLIST.md`](https://github.com/akshantvats/Profile/blob/main/blog/NEW-POST-CHECKLIST.md).

### Experience & AI blogs — format mix (not incident-only)

Across the 150-day plan, **do not** frame every Experience or AI Learning post as a daily production incident. Mix formats per [`docs/BLOG-FORMAT-MIX.md`](docs/BLOG-FORMAT-MIX.md).

| Step | Action |
|------|--------|
| Pre-flight | Read **BLOG-FORMAT-MIX.md** (format table + mapping from `experience.title` / `code` ticket). |
| Assign format | Before Phase 1 blog plans: pick format ID (`incident`, `feature`, `design`, `deep-dive`, `rollout`, `patterns`, `meta`). Check [`data/blog-format-hints.json`](data/blog-format-hints.json) for calendar day **N** if present. |
| Phase 1 plans | A2/A3 must state **format + rationale + one gold post** to emulate (paths in BLOG-FORMAT-MIX.md). |
| Quota | Soft guideline: **≤ ~40%** `incident`-style posts across both series over 150 days — rebalance if recent posts skew outage-heavy. |

`plan.json` **titles stay**; format doc controls **narrative structure** (postmortem vs shipped feature vs design essay, etc.).

### Blog numbering vs calendar day (authoritative)

**Calendar day** = **N** in the 150-day plan (`plan.json` `day`, checklist “Day N”, code commit `Refs: N of N`).  
**Published blog episode index** on that calendar day should be **N − 1**, not N — blogs trail the plan by one index so Day 0 / launch content can ship on calendar day 0 without skipping numbers later.

| Series | Index base | On calendar day **N**, latest shipped kicker | Example (N = 5) |
|--------|------------|-----------------------------------------------|-----------------|
| **Experience** | **1-based** | **Experience (N − 1) of N** | Four experience posts live → latest **Experience 4 of N** ✓ |
| **AI Learning** | **0-based** | **Day (N − 1) of N** | Through **Day 4 of N** — not Day 5 yet |

**AI Learning post count (0-based, includes Day 0 roadmap on launch):**

- After calendar day **N** closes (all posts through index **N − 1** shipped): **N posts** total, filenames/indices **0 … N − 1** (e.g. calendar day 5 → `day-0` … `day-4` → **5 files**).
- If you count only **numbered curriculum days after the Day 0 roadmap** (exclude Day 0 from the count): **N − 1** posts on calendar day **N** (e.g. day 5 → Days 1–4 → **4** “learning” posts). Say which convention you mean in plans; agents default to **0-based indices including Day 0**.

**Experience backlog does not change the rule.** Plan days 1–2 may still list experience titles that ship later; kickers follow **publication order in the Experience series** (1, 2, 3, …), not “which calendar day the outline was written.” On calendar day **N**, the highest Experience kicker is still **(N − 1) of N** when you ship one experience post per plan day from day 0.

**Intentionally deferred (not blocking):** Experience posts for plan **days 1–2** — *Design Docs Beat Code on Day One* (day 1) and *Ceph, POSIX, and the Lie of 'Just Use a Filesystem'* (day 2). Code and AI Learning for those calendar days shipped; experience titles remain in `plan.json` for later backlog. Do not block G-tickets, checklist gates, or marking a calendar day `done` on these.

**Sidebar kicker ↔ filename ↔ `plan.json` (must agree):**

| Field | Rule |
|-------|------|
| HTML filename | `day-<index>-<slug>.html` where `<index>` = AI `day_index` (0-based) |
| Sidebar / `series-index.json` `kicker` | `Day <index> of N` or `Experience <index> of N` — same `<index>` as filename |
| `data/plan.json` → `ai.day_index` | Set to **N − 1** on calendar day **N** (the post you ship **that** day), not **N** |

Pre-flight on calendar day **N**: highest AI file should be `day-(N-1)-*.html` with kicker **Day (N − 1) of N**; `plan.json` for day **N** must not set `ai.day_index` to **N**.

**Known drift (fix, do not normalize forward):**

- **AI:** Live posts `day-0` … `day-3` plus **`day-5-*` (skipped Day 4)** — on calendar day 5 you should be through **Day 4**, not Day 5; Day 5 content likely shipped early / conflated with G-03. Add `day-4-*.html`, retitle/rename or deprecate mis-indexed `day-5-*`, set plan day 5 `ai.day_index` to **4** (plan currently jumps **3 → 5** — insert day_index **4**).
- **Experience:** Latest **Experience 4 of N** on calendar day 5 matches the rule; do not renumber older kickers because days 1–2 backlog shipped out of plan order.

- [ ] Pre-flight: calendar day **N** → confirm latest AI kicker is **Day (N − 1) of N** and Experience is **Experience (N − 1) of N** (if shipping today)
- [ ] `plan.json` `ai.day_index` for today = **N − 1** (not `day` field)
- [ ] New HTML: filename index = sidebar kicker index = `ai.day_index`
- [ ] `series-index.json` kickers match published indices (no gap in public nav without a draft placeholder)

### Series identity & numbering

**Three top-level series only** (index, `series-index.json`, cover badges) — use folder slugs exactly:

| Slug | Role | Kicker / numbering on site (not on cover PNG) |
|------|------|-----------------------------------------------|
| `ai-learning` | Inference / ML systems curriculum | `Day X of N` in HTML/meta/sidebar |
| `experience` | Production war stories (Agoda-scale bridge in prose) | `Experience X of N` in sidebar — **not** calendar plan day in kickers |
| `lensai` | Product / platform essays | e.g. `LensAI · Product` |

- [ ] **No `agoda/` top-level series** — legacy path is `experience`; Agoda is company context in copy, not a series slug
- [x] **Experience Series** — production war stories, company-scale bridge to today's code
- [x] Experience post label: **Experience X of N** in sidebar (`series-index.json`); **N** = open-ended — do not hardcode 150 in public copy
- [x] **AI Learning series** title format (locked): `Day X of Learning LLM Inference — <Topic>` (**X** = `ai.day_index`, 0-based; on calendar day **N**, **X = N − 1**)
- [ ] **LensAI series** — product narrative; kickers per NEW-POST-CHECKLIST when that workstream is in scope
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
- [x] **HTML** lives in [Profile](https://github.com/akshantvats/Profile) under `blog/series/<slug>/` — only `ai-learning`, `experience`, or `lensai` (**Experience posts:** `blog/series/experience/` — not `agoda/`)
- [x] **Cross-links** between posts use full canonical URLs under the base above (e.g. `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html`) — or site-relative paths that resolve on Pages (e.g. `/Profile/blog/series/...`); verify against Profile repo layout before merge
- [x] **Never** use `file://`, `localhost`, `plans/drafts/`, or relative-only links in published HTML that break off GitHub Pages
- [x] **Placeholder `TBD`** in drafts for sibling posts not yet published; replace with canonical URL before HTML merge to Profile

**Examples (canonical):**

- AI Learning: `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-3-token-budgets-cost-structure.html`
- Experience: `https://akshantvats.github.io/Profile/blog/series/experience/…`
- LensAI: `https://akshantvats.github.io/Profile/blog/series/lensai/…`

### Cover art & social previews (Profile)

- [ ] **Dimensions:** hero + `og:image` assets **1200×630** PNG (1.91:1); duplicate under `blog/assets/og/<slug>.png` and `blog/assets/covers/<slug>.png`
- [ ] **`og:image` / `twitter:image`:** **absolute HTTPS** only — e.g. `https://akshantvats.github.io/Profile/blog/assets/og/<slug>.png` plus `og:image:width` 1200 and `og:image:height` 630 — **every post** (new + retrofix); run OG audit before ship
- [ ] **On-page hero:** wide cover after `</header>` (`post-cover-wrap` / `post-cover` pattern from sibling post); `width="1200"` `height="630"` on `<img>`
- [ ] **Badge on PNG:** series label only — `AI LEARNING SERIES`, `EXPERIENCE SERIES`, or `LENSAI · PRODUCT` + post title as headline — **no episode numbers on the image** (`Day X of N`, `Experience X of N`, `Post 2 of 5`, etc. stay in HTML/meta/sidebar only)
- [ ] **Regenerate from content** when topic/visual drifts: `Profile/scripts/generate_covers_from_content.py` → art in `scripts/cover_generated/` → `generate_blog_covers.py --from-content` (see Profile `scripts/README.md`)
- [ ] After Pages deploy: verify image URL in browser; **LinkedIn Post Inspector** (and X card validator if used) to refresh scrape cache

### Mermaid & visuals

- [x] Architecture or request/flow posts include **Mermaid** (sequence, flowchart, or C4-style)
- [x] **No cap at one diagram** — use as many as the post needs (gold posts: IoT = 3, AI Day 2 = 3, percentiles = 2). Typical architecture war stories: **2–3** (lifecycle + hot path + failure/observability). Waive only with explicit user note.
- [x] Data path / Kafka / consumer / API posts: diagram required unless user waives
- [x] Validate mermaid renders on Profile site (build/preview locally)

### Standing rules (all blogs — quick gate)

| Rule | Requirement |
|------|-------------|
| **Series path** | HTML only under `blog/series/ai-learning/`, `blog/series/experience/`, or `blog/series/lensai/` — **never** `blog/series/agoda/` for new posts (legacy `agoda/` may redirect only). |
| **`data-series-slug`** | Must match series slug (`experience`, `ai-learning`, `lensai`). |
| **Canonical + cross-links** | `https://akshantvats.github.io/Profile/blog/series/<slug>/<file>.html` — verify live after Pages deploy. |
| **OG / Twitter** | Every published post: `og:image` + `twitter:image` = **absolute HTTPS** to `blog/assets/og/<slug>.png` (1200×630); duplicate in `blog/assets/covers/`; on-page hero. Re-scrape LinkedIn Post Inspector after deploy. Parent agent audits retroactively. |
| **Cover badge** | Series label + title on PNG only — **no** episode numbers on image. |
| **Mermaid** | As many diagrams as needed for clarity (see above); alt text on each. |
| **Numbers** | Company-scale from **public sources** (annual report, AWS/Google case studies, vendor blogs). Resume/build metrics labeled as **team scope** or **systems I owned** — do not imply global peak without a source. |

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
- [x] Correct series numbering (**Experience X of N** vs **Day X of N** AI Learning — per series rules above)
- [x] Sibling blog linked via Daily Thread sentence
- [x] All cross-links use live Profile URLs (`https://akshantvats.github.io/Profile/...` or verified `/Profile/blog/...` paths) — no `file://`, `localhost`, or `plans/drafts/` links
- [x] No remaining `TBD` placeholders for published sibling posts
- [x] Code/schema references match **today's actual commit** (after code agent finishes)
- [x] Mermaid present and renders
- [x] Spelling, code fences, accessible alt text for diagrams
- [x] Cover art + `og:image` gates above (if post ships today)
- [x] Site build passes; URL confirmed on GitHub Pages

### Portable content workflow (optional / deferred)

Lightweight cross-posting helpers in Profile — **not required every day**; user may defer branch work.

- [ ] **LinkedIn article paste:** `Profile/scripts/html_to_linkedin_article.py` → text + diagram PNGs under `scripts/linkedin-export/` (section-by-section paste)
- [ ] **Future:** Mermaid → static PNG in export pipeline (Kroki / `mermaid-cli` — see Profile `scripts/README.md`); no blocker for HTML publish

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
- [x] Complete [Phase 3.5 — Local verification & user showcase](#phase-35--local-verification--user-showcase-mandatory-before-pr) before any push or PR
- [x] If user approves push (sign-off phrase): push branch, **then** open PR if applicable, paste PR URL to user — never open PR before approval

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
- [ ] Run all three implementations after a single plan approval without per-workstream user command
- [ ] Write HTML before user approves draft
- [ ] Use `day-NN-*` or sprint names in branch names (use `feat/` etc. per **Branching & Git Standards**)
- [ ] Put `file://`, `localhost`, or `plans/drafts/` links in published Profile HTML
- [ ] Push plan website or `data/plan.json` to public GitHub
- [ ] Push code without user saying push
- [ ] Open a PR before user local test + explicit sign-off ([Phase 3.5](#phase-35--local-verification--user-showcase-mandatory-before-pr))
- [ ] Write LinkedIn/X posts in agent scope (links only after site publish)

---

## E. Plan Site Integration (local only)

- [x] Daily workflow uses [checklist.html](checklist.html) (browser) + this file (copy/paste)
- [x] Nav: **Daily Checklist** on master plan and generated pages
- [x] **This repository is local-only** — see `.gitignore` and `README.md`; do not push to `akshantvats` remotes

### Current calendar day (single knob)

| File | Purpose |
|------|---------|
| `data/current-day.json` | `{"current_day": N}` — **only place** to set which day is **Today** on the plan site |
| `data/plan.json` | Merged content + per-day `status`; `done` on a day is preserved when regenerating |
| `python3 generate_plan.py` | Rebuilds `index.html`, product/project pages; applies `current_day` → `today` / prior days `done` |

**Morning:** set `current_day` to today's calendar day → run generator.  
**End of day:** set completed day `status` to `done` in `plan.json` (or rely on `current_day` > that day) → bump `current_day` to N+1 → run generator.

---

## Quick reference — repositories

| Repo | Purpose |
|------|---------|
| `akshantvats/infra-ai-streaming` | Primary platform / LensAI ingestion codebase |
| `akshantvats/Profile` | Personal site + Experience + AI Learning blogs |
| `akshant-150-day-plan/` (local) | Master calendar, plan.json, checklist — **not for GitHub push** |

---

*Framework Step 1 — reusable daily checklist. Day-specific execution plans are created separately after user reviews this framework.*
