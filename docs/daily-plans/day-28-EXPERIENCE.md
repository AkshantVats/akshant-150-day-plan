# Day 28 — Experience Series Outline
## Integration Tests — The Only Launch Criteria I Trust

---

## Header Block

| Field | Value |
|---|---|
| Series | Experience |
| Day | 28 of 150 |
| Employer | Agoda |
| Systems | WhiteFalcon TSDB · cross-tier query engine · staging pipeline discipline |
| Bridge | Landing page demo GIF must show eBPF → ingest → flagd → Grafana or it's marketing, not engineering. |
| Slug | `day-28-integration-tests-launch-criteria` |
| Date | 2026-06-12 |

---

## HTML File Target

```html
<title>Day 28 — Integration Tests — The Only Launch Criteria I Trust | Experience Series</title>
```

| HTML location | Required text |
|---|---|
| Accent tag chip | `Experience · Day 28 of 150` |
| `<h1 class="post-title">` | `Day 28 — Integration Tests — The Only Launch Criteria I Trust` |
| Meta line | `Experience · Day 28 of 150` |
| Series footer | `Experience · Day 28 of 150` |

---

## Voice Reminders

- Write in first person throughout: "I hit this wall when...", "What I didn't expect was...", "Here's what surprised me..."
- Maximum 3 sentences per paragraph. Split immediately at 4.
- One concrete non-software analogy per major concept — grounded in physical/everyday objects.
- Every section ends with a "so what" sentence that lands the practical takeaway.
- No bullet lists as substitute for prose. Lists only for ordered steps where prose is harder.
- Use only verified Agoda numbers from the Verified Numbers table below.

---

## Target Blog URL

`https://akshantvats.github.io/Profile/blog/series/experience/day-28-integration-tests-launch-criteria.html`

---

## Opening Hook

**Purpose:** Drop the reader into a specific moment when a unit-tested system failed in production — not because the tests were wrong, but because they never ran the full pipeline together.

**Draft:**

Three weeks before we shipped the cross-tier query extension in WhiteFalcon, every unit test was green. The histogram merge logic had 100% branch coverage. The Redis hot-tier fetcher tests passed. The S3 cold-tier fetcher tests passed. The merge function was mathematically correct — I'd verified it against five different time ranges by hand. But we had never run the full sequence — Redis fetch, S3 fetch, merge, and Grafana query — against a real dataset on a real Kafka-backed pipeline in a staging environment. The day we did, the query returned the wrong result for ranges crossing the hot/cold boundary at exactly the 3-hour mark, when a compaction job was mid-run and the S3 partition was split across two files. No unit test could have found this. Only the integration test did.

That experience is why I trust one thing when deciding whether a system is ready to launch: does it work end-to-end on data that looks like production data, in an environment that looks like production, running from a clean state? Everything else — unit tests, code review, staging smoke tests on synthetic data — is evidence that the components are correct. Integration tests are the only evidence that they work together. And for a distributed system where the interesting failures are exactly the ones at the boundaries between components, that distinction is the whole ballgame.

---

## Section 1 — The Integration Test Gap

**Purpose:** Name the specific failure mode that integration tests prevent — and why unit tests cannot catch it.

**Key Points:**

Unit tests verify component behavior in isolation. They're fast, deterministic, and give immediate feedback on individual functions. They're the right tool for testing that the histogram merge function returns the correct output for a given pair of bucket arrays. But they cannot test that the histogram bucket arrays received from the Redis hot tier and the S3 cold tier are in the same format, covering the same bucket boundaries, with the same time alignment. That's a contract between two components, and unit tests only test one component at a time.

The integration test gap lives at every boundary between components: between the Kafka consumer and the storage layer it writes to, between the storage layer and the query engine that reads from it, between the query engine and the Grafana plugin that formats the response. Each boundary has an implicit contract — a set of assumptions each component makes about what the other will produce. Integration tests are the only tests that can verify these contracts are actually being kept in practice.

In the WhiteFalcon case, the implicit contract was that the S3 cold-tier partition files for a given time range would always be complete when a query crossed the hot/cold boundary. The contract was violated during compaction — when new S3 files were being written, the old ones were marked as pending-delete but not yet removed, and the query engine's file discovery logic returned both the old and new files for the same time range. The result was double-counted histogram data. Unit tests could not have found this because it required three components (compaction job, S3 file discovery, query engine) to be running simultaneously against real data.

**Concrete analogy:** Unit tests are like checking each ingredient separately before cooking — confirming the flour is fresh, the eggs are uncracked, the butter is soft. Integration tests are like making the recipe once and tasting it. You can't know how the dish turns out from inspecting the ingredients individually. The interaction between heat, timing, and specific quantities is something you can only test by actually cooking it.

**So what:** Unit tests are necessary but not sufficient for distributed systems — the interesting bugs live at component boundaries, and only integration tests can find them.

---

## Section 2 — Staging Discipline at Agoda

**Purpose:** Show what "real integration testing" looked like at Agoda scale — and why the specific discipline of running on a clean machine matters.

**Key Points:**

WhiteFalcon's staging environment was a reduced-scale replica of production. It ran the full pipeline — Kafka with a subset of the 1.5T daily events forwarded from production, Rust consumers writing to Redis, compaction jobs running on a 10-minute cycle instead of hourly, Scala query engine pointing at staging S3, Grafana connected to the staging query endpoint. The purpose was not to test performance — you can't test 1.5T events/day on a staging cluster. The purpose was to test the correctness of the pipeline under production-like conditions, including production-like data shapes, compaction timing, and query patterns.

The discipline I learned from this staging environment was the clean-machine requirement. Every integration test run started from a clean state — empty Redis, empty S3 prefix, no compaction job history. This was not about realism. Production was never in a clean state. The clean-machine discipline existed because it made failures reproducible. When a test failed from a pre-existing state, the root cause could be in the test's setup or in the system under test — and untangling the two was expensive. A clean starting state meant every failure was a system failure, not a state artifact.

The compose-on-clean-laptop formulation is the same discipline applied to a single developer machine. If the integration test only works on the CI server, or only works after a specific manual setup sequence, it's not an integration test — it's a demo. A real integration test is something you can run from a fresh `git clone` and get a meaningful result. The ceremony required to run a test is a direct measure of how well the test actually validates the system.

**Concrete analogy:** A clean-machine integration test is like a fire drill. The point of a fire drill is not to practice when the fire alarm is already ringing — the point is to discover whether the evacuation procedure works before there's a real fire. Running the drill starting from normal working conditions, not from a pre-staged "everyone is already at the exits" state, is what makes it a real test. A staged fire drill is a performance review, not a safety check.

**So what:** Staging discipline — clean state, production-like data, reproducible setup — is the difference between a test that provides evidence the system works and a test that provides evidence the test can run.

---

## Section 3 — The Histogram Bug: What Clean Staging Found

**Purpose:** Walk through the specific integration test failure from the opening hook in concrete detail — what the test actually found and why no other test could have found it.

**Key Points:**

The cross-tier query extension I built extended WhiteFalcon's Scala query engine to handle time ranges crossing the hot/cold boundary. The correct approach was to fetch histogram bucket counts from both tiers and merge them before computing quantiles — add corresponding bucket counts, then compute P95 or P99 on the merged histogram. The math was correct. The unit tests were thorough. The merge function returned the right result for every input I hand-crafted.

The integration test failure appeared when the test sent a query for a time range ending in the Redis hot tier and starting in S3 during a compaction window. Compaction at Agoda ran hourly — it merged hourly S3 Parquet files into 3-hour files. During the merge window, both the hourly file and the in-progress 3-hour file existed in S3 with overlapping time ranges. The query engine's S3 file discovery returned both files. The bucket counts were summed from both files, meaning bucket counts for the overlapping time range were doubled. The resulting P99 latency from the cross-tier query was approximately 1.3x the actual P99 — a systematic error appearing in every production query crossing a compaction boundary.

What the integration test did that no unit test could: it ran the compaction job during the query. The compaction timing wasn't controlled — it was running on a 10-minute cycle in staging, and the integration test happened to query during a compaction window. In production, this would have happened roughly once per hour. Infrequent enough that the bug might have shipped and been attributed to "normal variance" for weeks before being diagnosed.

**Concrete analogy:** Finding a bug during a compaction window is like discovering that a bridge sways in crosswinds only while a resurfacing crew is applying new asphalt. The bridge is fine empty and fine under normal traffic. But the combination of reduced structural stiffness during resurfacing and lateral wind load produces resonance that static load tests never reveal. Integration tests are the wind tunnel. Unit tests are the static load test.

**So what:** The integration test found a systematic correctness bug — one producing wrong results on every query crossing a compaction boundary — because it ran the full pipeline including background jobs that unit tests never simulate.

---

## Section 4 — What "Compose on Clean Laptop" Means

**Purpose:** Define "compose on clean laptop" as an engineering discipline, not just a convenience.

**Key Points:**

"Compose on clean laptop" means the integration test runs with a single command from a fresh `git clone` on a machine that has never seen the codebase before. The test sets up its own infrastructure (databases, message brokers, background services), runs against that infrastructure, and tears it down. It makes no assumptions about machine state except that Docker is installed. If the test requires additional setup — manual configuration, a pre-existing service, a credential that has to be manually obtained — it fails the clean-laptop criterion.

This discipline has a practical consequence: it forces the developer to encode all configuration into the test setup. Every environment variable, every service address, every schema creation step must be handled by the test's setup phase. The temptation to rely on "everyone knows they need to run the migration first" or "you need to have the Redis instance already running" is eliminated by the clean-laptop requirement. The test either handles it or the test fails.

The second consequence is that the clean-laptop test is self-documenting. A developer who has never seen the codebase can run the integration test and learn — from watching it set up and execute — what services the system depends on, how they interact, and what a successful run looks like. This is operational documentation that never becomes stale because it runs against the actual code.

**Concrete analogy:** A clean-laptop integration test is like a recipe that includes all the steps, not just the cooking steps. A recipe that says "sauté the onions in the pan" assumes you already have a hot pan and prepared onions. A recipe that says "heat 2 tablespoons of oil in a 10-inch pan over medium heat, add one diced onion, sauté until translucent (about 5 minutes)" is self-contained. The second recipe works for any cook. The first recipe only works for cooks who already know what "prepared onions" means. Integration tests are the second kind of recipe.

**So what:** The clean-laptop discipline converts integration tests from "things that work in CI with the right setup" into "executable specifications that any engineer can run and learn from."

---

## Section 5 — The Bridge: LensAI's Smoke Test as Integration Contract

**Purpose:** Connect the Agoda staging discipline to lensai-integration's docker-compose quickstart.

**Key Points:**

The `scripts/smoke.sh` in lensai-integration is the same discipline applied to LensAI's entire stack. It runs from a clean docker state, starts all services via docker-compose, injects a synthetic inference event, and verifies the event flows from the ingest endpoint through Kafka to ClickHouse and appears in the Grafana dashboard. Exit 0 means the pipeline works. Exit 1 means it doesn't. There's no ambiguity, no manual steps, no "it works on my machine" qualification.

The reason this matters specifically for LensAI's launch is the demo GIF. The landing page for a developer-focused open-source project needs to show the product working, not describe it working. A demo GIF showing eBPF tracing requests, those requests appearing in ClickHouse, and a Grafana dashboard updating in real time is worth more than any architecture diagram. But the demo GIF is only credible if the system it depicts is the system in the repository — if a developer can clone the repo, run one command, and see the same thing. The smoke test is the engineering contract that makes the demo GIF honest.

The WhiteFalcon lesson that applies directly here: the integration test found a systematic error because it ran the full pipeline including compaction. The LensAI smoke test must run the full pipeline including the eBPF tracer — the component most likely to have environment-specific behavior. Finding that failure in the smoke test, before the demo GIF is recorded, is the value of the integration test discipline.

**Concrete analogy:** The demo GIF is the advertisement for the product. The smoke test is the quality inspection ensuring the advertisement matches the product. An advertisement for a product that doesn't work as shown isn't a marketing problem — it's an integrity problem. The integration test is the check that the advertisement is honest.

**So what:** Building smoke.sh as Day 1 of lensai-integration means the LensAI demo GIF will be an accurate representation of a system any developer can reproduce — and that's the only kind of demo that builds the trust a developer tool needs.

---

## Section 6 — What I'd Do Differently

**Purpose:** Honest retrospective on integration testing at Agoda and what that changes about how I build LensAI.

**Key Points:**

I'd add integration tests at the same time as unit tests, not after. At Agoda, integration tests were added after the component was complete — retrofit exercises verifying the finished system. Writing them after the fact meant the test was designed around the current behavior, including bugs. A test written in parallel with development would have found the compaction boundary bug earlier in the implementation cycle, not three weeks before ship.

I'd make integration test infrastructure disposable and cheap. At Agoda, staging was a persistent environment shared across the team — it had history, pre-existing data, and occasional state corruption from parallel test runs. The docker-compose + testcontainers approach is better: each test run starts clean, runs in isolation, and tears down completely. The cost is slightly longer setup time per run. The benefit is deterministic, reproducible results with no state contamination between runs.

Finally, I'd treat integration test failures as harder blockers than unit test failures. At Agoda, an integration test failure in staging sometimes triggered a "we'll investigate after ship" response because the failure appeared intermittent. The compaction boundary bug appeared intermittent because compaction timing was not controlled. A controlled test that deliberately triggers compaction during the query would have made the failure deterministic and non-dismissable. Building determinism into integration test design is the discipline that prevents "intermittent" from becoming a reason not to fix things.

**What I didn't expect:** The most valuable integration tests at Agoda were not the ones verifying the happy path. They were the ones deliberately triggering edge cases — compaction during query, Redis eviction during hot-tier fetch, Kafka consumer lag during high write rate. These tests were harder to write and slower to run. They found exactly the bugs that would have been production incidents.

**Concrete analogy:** Mandatory flight simulator recurrency training for pilots is the right parallel. The simulator doesn't test normal flying — commercial pilots are excellent at normal flying. It tests scenarios that almost never happen but require immediate, correct responses when they do: engine failure on takeoff, hydraulic system loss at altitude, dual autopilot failure. Integration tests that deliberately break things are the flight simulator for distributed systems.

**So what:** Integration tests that deliberately break things — trigger compaction, evict cache entries, introduce consumer lag — are more valuable than tests verifying everything works when nothing goes wrong, and the investment in building them pays back the first time they find a bug before it reaches production.

---

## Mermaid Diagrams

### Diagram 1 — WhiteFalcon Cross-Tier Query + Compaction Bug

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart TD
    A["Scala query engine"] --> B["Redis hot tier"]
    A --> C["S3 cold tier"]
    C --> D["Compaction running"]
    D --> E["Old + new files both returned"]
    B --> F["Merge histogram buckets"]
    E --> F
    F --> G["Double-count: P99 inflated 1.3x"]
    G --> H["Integration test finds it"]
```

**Caption:** During compaction, both the original hourly file and the in-progress 3-hour file existed in S3 with overlapping time ranges. File discovery returned both, causing bucket double-counting. The integration test found this because it ran the compaction job during the query — something no unit test simulates.

### Diagram 2 — Clean-Laptop Integration Test Lifecycle

```
%%{init: {
  'theme': 'base',
  'themeVariables': {
    'primaryColor': '#1e3a5f',
    'primaryTextColor': '#f0f4f8',
    'primaryBorderColor': '#4a90d9',
    'lineColor': '#4a90d9',
    'secondaryColor': '#0d2137',
    'tertiaryColor': '#0a1a2e',
    'background': 'transparent',
    'nodeBorder': '#4a90d9',
    'clusterBkg': '#0d2137',
    'titleColor': '#f0f4f8',
    'edgeLabelBackground': '#0d2137'
  }
}}%%
flowchart LR
    A["git clone + docker up"] --> B["Services start clean"]
    B --> C["Inject test event"]
    C --> D["Verify end-to-end flow"]
    D --> E["Exit 0 or fail + reason"]
    E --> F["Tear down — no state left"]
```

**Caption:** The clean-laptop integration test lifecycle: start from zero state, inject a controlled event, verify it traverses the full pipeline, exit with a clear pass/fail signal, leave no state behind. Each step is automation — no manual intervention, no pre-existing dependencies.

---

## Post Metadata JSON Block

```json
{
  "slug": "day-28-integration-tests-launch-criteria",
  "title": "Integration Tests — The Only Launch Criteria I Trust",
  "subtitle": "How staging discipline at Agoda shaped the LensAI quickstart smoke test",
  "series": "experience",
  "day": 28,
  "employer": "Agoda",
  "date": "2026-06-12",
  "url": "https://akshantvats.github.io/Profile/blog/series/experience/day-28-integration-tests-launch-criteria.html",
  "coverImage": "blog/assets/covers/day-28-integration-tests-launch-criteria.png",
  "ogImage": "blog/assets/og/day-28-integration-tests-launch-criteria.png",
  "tags": ["DistributedSystems", "BackendEngineering", "Infrastructure", "Observability", "Testing", "Agoda"],
  "bridge": "Landing page demo GIF must show eBPF → ingest → flagd → Grafana or it's marketing, not engineering."
}
```

---

## Verified Numbers Table

Use ONLY these numbers from the Agoda context doc. Do not invent others.

| Metric | Value | Source |
|---|---|---|
| Events per day | 1.5T (resume) / 1.8T (Kafka forwarder) | Agoda context doc |
| Tenure | ~5 months, Senior Engineer | Agoda context doc |
| Hot tier retention | Last 3–7 days | Agoda context doc |
| Compaction cadence | Hourly → 3-hour → daily | Agoda context doc |

**Do NOT use:** team size numbers, specific query latency numbers, engineer names, business metrics.

---

## Self-Review Checklist

- [ ] `Day 28` appears in `<title>`, `<h1>`, accent tag chip, and meta line
- [ ] Series footer reads `Experience · Day 28 of 150`
- [ ] All `<div` opens and `</div>` closes are balanced
- [ ] Zero `</motion.div>` tags
- [ ] No `<a>` nested inside another `<a>`
- [ ] At least one `class="prose"` div present
- [ ] Every scale number matches the Verified Numbers table
- [ ] No invented system names beyond those in Agoda context doc
- [ ] Every paragraph is ≤ 3 sentences
- [ ] Every major section has a "so what" closing sentence
- [ ] Every major concept has one concrete non-software analogy
- [ ] Both Mermaid diagrams use the exact init block — no variations
- [ ] Every Mermaid node label is ≤ 6 words
- [ ] Each diagram has ≤ 8 nodes
- [ ] No placeholder URLs
- [ ] Cover image path: `blog/assets/covers/day-28-integration-tests-launch-criteria.png`
- [ ] OG image path: `blog/assets/og/day-28-integration-tests-launch-criteria.png`
- [ ] Previous Experience post (day-27) footer updated to link to this post
- [ ] `series-index.json` entry added with correct schema
- [ ] `pre-push-check.sh` exits 0 before any `git push`
- [ ] Commit message includes `Self-review: N issues found and fixed.`
