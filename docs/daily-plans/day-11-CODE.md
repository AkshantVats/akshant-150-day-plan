# Work Day 11 — Code / Infra (OSS-01)

**Status:** Plan mode only — no implementation until user says `approve code`.

**Calendar day:** 11 of N · **Saturday** · **LensAI** · repo field: `infra-ai-streaming` (work happens in **upstream** VM or Vector fork)

**Shared Daily Thread:** Anomaly detection on `model_id` latency is only trustworthy if you understand how each serving framework reports time (OSS reading informs that).

---

## 1. Ticket

**OSS-01** (from `data/plan.json` day 11 `code`):

> First contribution to **VictoriaMetrics** or **Vector.dev** (good-first-issue / help-wanted). **Documentation example, benchmark, or reproducible bug report counts.** Submit PR; link in weekly notes.

**Interpretation for today:**

| In scope | Out of scope (today) |
|----------|----------------------|
| One **merged-quality upstream PR** (open + maintainer-visible is minimum; merged is ideal) | **G-09** anomaly detection in `infra-ai-streaming` consumer (calendar **day 12**) |
| Doc fix, small code fix, benchmark, or **reproducible** bug report with minimal repro | Re-running `scripts/run_chaos.sh` or Day 10 chaos proof |
| Comment on chosen issue **before** large work (VM culture) | Helm/k3d changes in infra unless needed for a doc *example* only |
| Link PR URL in **weekly notes** artifact | Profile Experience / AI HTML (separate workstreams) |

**Narrative bridge (why VM/Vector, not infra):** LensAI’s README argues Prometheus-style cardinality breaks at `model_id × tenant_id` scale — VictoriaMetrics is the direct upstream you would evaluate as an alternative metrics path; Vector is the pipeline you would use to shape inference logs/metrics before ClickHouse. Today is **reading production observability code** under interview pressure, not extending the demo stack.

---

## 2. Prerequisites

### Infra repo (`infra-ai-streaming`)

| Check | Status / action |
|-------|-----------------|
| **PR #5** (Day 10: k3d E2E, chaos scripts) | **MERGED** on GitHub (`064c234` on `origin/main`). **Not** blocked on merge. |
| Local `main` | **Stale** if last pull was before merge — local `main` may still be `218d298` (pre–Day 10). **Before any infra touch:** `git fetch origin && git checkout main && git pull origin main`. |
| Active branch `day-10-chaos-scripts` | Safe to delete locally after pull; Day 11 OSS work does **not** continue that branch. |
| E2E / chaos | Day 10 proof already on `main`; **do not** re-run chaos as Day 11 deliverable. Optional smoke: `./scripts/smoke-e2e.sh` only if you need confidence after `git pull`. |

**Honest note:** User context said “PR #5 open” — as of plan write, GitHub shows **MERGED** with CI green. Prerequisite is **sync local `main`**, not “wait for merge.”

### Plan repo (`akshant-150-day-plan`)

- [ ] `data/current-day.json` → `11` when you start the workday (local only; do not push plan repo).
- [ ] Phase 2: user approves **this file** (or edited copy) before fork/PR work.

### Upstream

- [ ] GitHub account with fork rights to **one** of: `VictoriaMetrics/VictoriaMetrics` or `vectordotdev/vector`.
- [ ] Toolchain per project: **Go 1.22+** (VM) or **Rust stable + make** (Vector) — see each repo `CONTRIBUTING.md` / `DEVELOPING.md`.

---

## 3. Step-by-step implementation checklist

### Phase A — Pick target (30–45 min)

- [ ] Read VM contributing guidance: [VictoriaMetrics contributing](https://docs.victoriametrics.com/victoriametrics/contributing/) and [issue #10608](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/10608) (no guaranteed `good first issue` labels — **ask on issue before coding**).
- [ ] Or filter Vector: [good first issue](https://github.com/vectordotdev/vector/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).
- [ ] Choose **one** issue from §Suggested issues below; post comment: “I’d like to work on this — OK to open a PR?”
- [ ] Record issue URL + acceptance sketch in a scratch note (for weekly notes).

### Phase B — Environment (45–60 min)

- [ ] Fork upstream → clone to e.g. `~/Desktop/github/VictoriaMetrics` or `~/Desktop/github/vector`.
- [ ] Create branch per [CHECKLIST.md](../../CHECKLIST.md) **Branching & Git Standards** (upstream repo, not `day-011-*`):
  - VM doc: `docs/vm-cardinality-best-practices` or `docs/quickstart-relabel-example`
  - Vector: `fix/memory-enrichment-metric-total-suffix` or `docs/tracing-log-filters-guide`
- [ ] Install deps; run project test command once on **clean fork default branch** to verify toolchain.

### Phase C — Implement (2–4 h)

- [ ] Implement smallest change that satisfies issue + maintainer reply.
- [ ] Run upstream tests for touched packages (see §Test/proof).
- [ ] Self-review: no drive-by refactors; Conventional Commit subject ≤50 chars.

### Phase D — Submit & link (30 min)

- [ ] Push fork branch; open PR against upstream `master` / `main`.
- [ ] PR description: problem, approach, test command output (paste), link to issue (`Fixes #…` only if maintainer agreed).
- [ ] Add PR link to weekly notes (§Files).
- [ ] Optional infra pointer: one-line in [infra-ai-streaming README](https://github.com/AkshantVats/infra-ai-streaming#why-this-exists) **only if** user approves scope creep — default **skip** for Day 11.

### Phase E — Showcase for user (CHECKLIST Phase 3.5)

- [ ] Paste upstream PR URL, issue URL, and copy-paste test command + pass output.
- [ ] **No push** to plan repo unless user asks; upstream PR is the primary artifact.

---

## 4. Acceptance criteria (measurable)

| # | Criterion | Proof |
|---|-----------|--------|
| 1 | **Upstream PR opened** | Public PR URL on `VictoriaMetrics/VictoriaMetrics` or `vectordotdev/vector` |
| 2 | **Issue linkage** | PR body references issue; comment thread shows maintainer OK or doc-only path |
| 3 | **Quality bar** | CI/checks on PR are **green** or **pending with no local failures** you could fix |
| 4 | **Tests/docs** | Doc PR: rendered preview or maintainer doc build path; code PR: package tests run locally with pasted output |
| 5 | **Weekly notes** | PR URL recorded in plan repo weekly notes file (§6) |
| 6 | **Infra untouched** | No requirement to change `infra-ai-streaming` for OSS-01; local `main` pulled if you verified stack |
| 7 | **Out of scope honored** | No G-09 code, no `run_chaos.sh` re-run as deliverable |

**Stretch (not required for day `done`):** PR merged upstream; maintainer review comments addressed same day.

---

## 5. Files to create / modify

### Upstream (primary)

Depends on chosen issue — examples:

| Track | Likely paths |
|-------|----------------|
| **Vector #25455** | `lib/vector-common/src/internal_event/metric_name.rs`, metric registration sites, `docs/specs/instrumentation.md` cross-check, generated metric doc if applicable |
| **Vector #970 (docs)** | `website/content/en/docs/...`, `docs/DOCUMENTING.md` references |
| **VM #8038** | `docs/` markdown under VictoriaMetrics doc tree (confirm path in issue) |

### Plan repo (this repo)

| Path | Action |
|------|--------|
| `docs/daily-plans/day-11-CODE.md` | This plan (committed) |
| `docs/weekly-notes/week-02.md` | **Create or update** — add `## OSS-01 (Day 11)` with issue URL, PR URL, one-line outcome |

### Infra (optional, default none)

| Path | Action |
|------|--------|
| [infra-ai-streaming README](https://github.com/AkshantVats/infra-ai-streaming/blob/main/README.md) | Optional “Related OSS” bullet with PR link — **only if user wants cross-link** |
| [docs/PROJECT-STATUS.md](https://github.com/AkshantVats/infra-ai-streaming/blob/main/docs/PROJECT-STATUS.md) | No change required for OSS-01 |

---

## 6. Branch naming

Per [CHECKLIST.md](../../CHECKLIST.md) — **no** `day-011-*`, `sprint-*`, or calendar day in branch name.

| Repo | Recommended branch |
|------|-------------------|
| `vectordotdev/vector` | `fix/memory-enrichment-counters-total-suffix` (if #25455) |
| `vectordotdev/vector` | `docs/tracing-log-filter-guide` (if #970 or #21735 sub-item) |
| `VictoriaMetrics/VictoriaMetrics` | `docs/best-practices-cardinality` (if #8038) |
| `VictoriaMetrics/VictoriaMetrics` | `docs/examples-vmagent-inference-labels` (if you add a doc **example** tied to LensAI labels) |

**Commit body** (upstream): optional `Refs: 11 of N — OSS-01 — <Daily Thread one-liner>` in plan-repo commits only; upstream projects often prefer issue-only footers — follow their CONTRIBUTING.md.

---

## 7. Suggested issues (pick one)

Verify labels/state on GitHub before starting; maintainers may assign or close.

### Option A — **Vector #25455** (recommended default)

**Title:** `metrics: rename memory enrichment table counters to end with _total`  
**Why:** Small, spec-driven, tests grep-able, aligns with LensAI Prometheus instrumentation story.  
**Risk:** Low; may touch generated metric names — run Vector’s metric/doc generation steps from CONTRIBUTING.

### Option B — **Vector #970**

**Title:** Write documentation about how to use tracing filters (`LOG=vector[...]`)  
**Why:** Pure docs; labeled `good first issue`; supports “how frameworks report time” thread.  
**Risk:** Issue is old (2019); confirm still wanted via comment first.

### Option C — **VictoriaMetrics #8038**

**Title:** Add best Practices Documentation  
**Why:** Doc-only fits plan.json literally; connects to **cardinality** war from infra README.  
**Risk:** VM maintainers want discussion before large doc PRs ([#10608](https://github.com/VictoriaMetrics/VictoriaMetrics/issues/10608)); scope can balloon — negotiate a **single page/section** in issue comment.

**Not recommended Day 11:** VM #10792 (assigned), #10133 (deep vmstorage), Vector k8s source #25137 (large feature).

---

## 8. Test / proof commands

### Vector (if #25455 or code path)

```bash
cd ~/Desktop/github/vector
cargo test -p vector-common
# or full component per CONTRIBUTING.md:
make test-rust
```

Paste CI-equivalent output in PR and user showcase.

### VictoriaMetrics (if doc/code)

```bash
cd ~/Desktop/github/VictoriaMetrics
go test ./lib/...   # narrow to touched package per issue
# Doc-only: follow docs build in repo README / Makefile target
```

### Infra (optional sanity after `git pull`)

```bash
cd /Users/akshant/Desktop/github/infra-ai-streaming
git checkout main && git pull origin main
./scripts/smoke-e2e.sh
```

### Proof artifact for parent agent / user

- Upstream PR URL
- Issue URL + your “OK to PR?” comment link
- Test command + last 20 lines of success output
- Weekly notes file path with PR linked

---

## 9. Time estimate and risks

| Item | Estimate |
|------|----------|
| Issue pick + maintainer ping | 0.5 h |
| Fork/toolchain | 0.5–1 h |
| Implementation + tests | 2–4 h |
| PR + weekly notes | 0.5 h |
| **Total** | **4–6 h** (Saturday box) |

| Risk | Mitigation |
|------|------------|
| VM issue closed as “needs design” | Pivot to Vector #25455 same day |
| Vector `make` / Rust build slow on laptop | Use `cargo test -p <crate>` scoped to change |
| PR not merged by EOD | Still satisfies OSS-01 if **submitted** + linked; merge is stretch |
| Scope creep into infra G-09 | Defer to `docs/daily-plans/day-12-CODE.md` (not written yet) |
| Stale local `main` | `git pull` before judging stack health |

---

## 10. Out of scope

- **G-09** — z-score anomaly detection, `ai_anomalies` topic, Grafana alert (calendar day **12**).
- **Chaos** — `scripts/run_chaos.sh`, CHAOS.md edits, slow-ClickHouse scenario re-proof.
- **Profile blogs** — Experience “Reading VictoriaMetrics Source at 11pm” and AI “Serving Frameworks Compared…” are separate approvals.
- **Plan site push** — plan repo stays local-only.
- **infra-ai-streaming feature PR** unless user explicitly expands scope.

---

## 11. Definition of done (user approval gate)

User can mark Day 11 code workstream approved when:

- [ ] This plan reviewed; user said **`approve code`** (or listed edits applied here).
- [ ] One upstream OSS PR is **open** (or merged) with green/local-passing checks.
- [ ] Weekly notes entry contains PR + issue links.
- [ ] Showcase block pasted in chat (PR URL, test command, expected pass).
- [ ] User sign-off recorded before any optional infra README cross-link PR.

**After approval → implementation:** Re-read this file; execute §3 checklist; do not rely on chat summary alone ([WORKFLOW.md](../../WORKFLOW.md)).

---

## Cross-workstream dependencies

| Consumer | Needs from OSS work |
|----------|---------------------|
| **Experience blog** | Which codebase you read (VM vs Vector), one “aha” from source (file:function), PR link |
| **AI blog** | Queue/scheduling analogy only — optional name-drop of framework metrics labels |
| **Day 12 code (G-09)** | Independent; benefits from VM/Vector time semantics awareness in thread |

**Freeze before Experience HTML:** final PR URL (or honest “open, not merged”); one code citation path (file + symbol) from reading upstream.
