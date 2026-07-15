# Day 38 — Experience Blog Outline
## Golden Files — How Platforms Survive API Drift

**Calendar**: Friday, 17 July 2026 · Day 38 of 150
**Series**: Experience
**Slug**: `day-38-golden-files-api-drift`
**Live URL**: `https://akshantvats.github.io/Profile/blog/series/experience/day-38-golden-files-api-drift.html`

---

## Post Metadata

| Field | Value |
|---|---|
| Title | `Day 38 — Golden Files — How Platforms Survive API Drift` |
| Subtitle | Wayfair · contract tests · supplier APIs |
| Series chip | `Experience · Day 38 of 150` |
| Cover image | `blog/assets/covers/day-38-golden-files-api-drift.png` |
| OG image | `blog/assets/og/day-38-golden-files-api-drift.png` |
| Estimated read time | 8 min |
| Format | incident + design (hybrid) |
| Employer | Wayfair (PAS team, Nov 2024 – Mar 2026) |

---

## Bridge to Today's Code

> "Recorded JSON fixtures are supplier sandbox responses for AI APIs. Today's code in tool-call-analyzer implements that lesson."

The adapter pattern and golden file testing I built today in `tool-call-analyzer` isn't a new idea. I first used this exact approach at Wayfair — building a client library against 20k+ supplier APIs that could change their response format without warning. What worked then works now, applied to OpenAI and Anthropic instead of furniture suppliers.

---

## Hook

At Wayfair, the PAS (Price Adjustment System) team owned a client library that talked to supplier cost APIs. Each of those suppliers was a separate company with their own engineering team, their own release schedule, and their own ideas about what a "valid API response" looked like.

We had 20,000+ active suppliers. Some changed their response format with a major version and a migration guide. Some changed it in a hotfix at 3am ET without telling anyone. Both kinds of change looked identical to our system: JSON that parsed fine but produced wrong pricing until someone's margin alert fired.

The answer wasn't better supplier onboarding. It was golden files.

---

## Outline

### Section 1: The Problem — 20k Suppliers, One Client Library (600 words)

- **Scale context**: 250k+ SKU updates per supplier in near real-time across 20k+ active suppliers
- **Architecture**: GCP event-driven global pricing engine; supplier cost APIs are upstream of the PAS pipeline
- **The fragile coupling**: our client library (`ucms-partner-home`) called supplier APIs and expected specific response shapes — `net_cost`, `currency`, `effective_date` in predictable positions
- **What drift looked like**: a supplier engineer updated their API to return `netCost` (camelCase) instead of `net_cost` (snake_case). Their sandbox still returned the old format. Our integration tests passed. Production failed on the first live request after their deploy.
- **What the failure looked like**: no exception, no error log. The `net_cost` field deserialized to 0.0 (zero value). A $0 cost produces a very high profit margin. The margin optimizer picked up the SKU immediately and set a price $40 below cost. First alarm was a Slack message from the pricing manager: "why are these SKUs all at a 95% margin?"

**Paragraph ends with "so what"**: A silent deserialization failure is worse than a crash. A crash stops traffic. A wrong zero costs money for every transaction it touches until someone notices the margin report looks wrong.

### Section 2: The Golden File Approach (650 words)

- **What we built**: a `testdata/fixtures/` directory in the `ucms-partner-home` client library, one JSON file per supplier, recorded from the supplier's sandbox at integration time
- **What each golden file contained**: the exact sandbox response, including all fields — even ones we didn't use. No manual cleanup. Raw response, saved to file.
- **How tests used them**: table-driven Go tests loaded each golden file, ran it through the client library's deserializer, and asserted on the fields we cared about. `net_cost`, `currency`, `effective_date` all checked.
- **The key insight**: the golden file is the supplier's sandbox talking to our code at a specific point in time. When they change their API and don't update their sandbox, our golden file still catches it on the next test run — because we've recorded what the response used to look like.
- **What the drift test looks like**: after a supplier updates their sandbox, we update their golden file. The diff in the PR shows exactly what changed. A rename from `net_cost` to `netCost` becomes a visible, reviewed change — not a runtime surprise.

**Paragraph ends with "so what"**: The golden file is a contract snapshot. Not a formal contract (we had no SLA enforcement with suppliers), but an observable record of what the API actually returned. Diffs in golden files are the earliest possible warning that something upstream changed.

### Section 3: What Made It Work at Scale (500 words)

- **Automation**: the fixture refresh script (`scripts/refresh_fixtures.sh`) pulled fresh sandbox responses for all suppliers daily. Suppliers that changed their API showed up as changed golden files in the next CI run.
- **Strict but narrow assertions**: we only asserted on fields we actually used. Unknown new fields were ignored. This meant a supplier adding `new_field_v2` to their response didn't break our tests — only a rename or removal of a field we depended on did.
- **Separation of concerns**: the golden file tests lived in the client library, not in the integration test suite. This meant they ran on every PR — not just once a week on the integration schedule.
- **Team discipline**: updating a golden file required a PR. The diff was the documentation. When a supplier changed their API, the PR showed before/after. Two engineers reviewed it. The change was traceable.

**Paragraph ends with "so what"**: Golden file testing at scale is less about the technical pattern and more about the discipline. The pattern is simple — record, test, update. The discipline is: treat a changed golden file as a signal that deserves human attention before it deploys.

### Section 4: How This Maps to AI APIs Today (500 words)

- **The parallel**: OpenAI is a supplier. Their `/v1/chat/completions` response is a supplier API. `tool_calls[].function.arguments` is a field we depend on.
- **What changed in 18 months**: OpenAI deprecated `functions` in favor of `tool_calls`. Added `parallel_tool_calls`. Changed the finish reason field name once.
- **The same discipline applies**: record golden fixtures from the API at the time you write the adapter. Add a drift simulation fixture that includes unknown fields. Update fixtures when you upgrade the SDK.
- **The `tool_call_unknown_fields.json` fixture** in today's `tool-call-analyzer` commit is exactly the Wayfair golden file philosophy applied to AI: a recorded response with extra unknown fields added, to verify the adapter doesn't break when the vendor adds fields we haven't seen yet.
- **What's different**: supplier APIs were mostly stable (changes quarterly). AI APIs change monthly. The golden file refresh discipline has to be faster. This is why the fixtures live next to the adapter code, not in a separate fixtures repo — the adapter and its fixtures are a single unit of change.

**Paragraph ends with "so what"**: The AI API landscape in 2026 looks a lot like the supplier API landscape at Wayfair in 2024: dozens of vendors, each with their own format, each updating on their own schedule. The lesson from Wayfair isn't specific to furniture or pricing — it's about any system that depends on external APIs it doesn't control.

### Section 5: The Silent Failure Problem (350 words)

- The Wayfair incident with the `netCost` rename had a specific failure mode: zero-value deserialization
- This failure mode is especially dangerous in AI cost attribution: if `cost_usd` silently becomes 0.0, your cost dashboard lies to you — you think agents are cheap when they're not
- The fix is active assertions in adapter tests: `if tc.Cost.CostUSD == 0 { t.Error(...) }` for known models
- An adapter that returns zero cost for a known model is wrong. Make the test say so.

**Paragraph ends with "so what"**: Zeroes are the enemy of observability. A zero can mean "genuinely free" or "we lost the data." Distinguishing between them is the job of the adapter layer — and the only way to do it is to check.

### Section 6: One Lesson Carried Forward (250 words)

The Wayfair pricing platform had 77 Bigtable endpoints, 20k+ supplier integrations, and a real-time pricing pipeline that touched $20B+ of annual GMV. The golden file approach didn't protect all of it — there were incidents from sources we didn't think to golden-file (CloudSQL schema changes, Pub/Sub message shape changes). But for supplier API drift, it worked well enough that we stopped having surprise pricing incidents from that source.

When I started building `tool-call-analyzer`, I didn't think of it as "applying the Wayfair lesson." I thought of it as "the obvious way to test an adapter." The obvious way became obvious because of Wayfair. That's how context compounds.

---

## Series Nav (sidebar)

Previous: Day 37 — LangChain Is Four Vendors in a Trenchcoat
Next: Day 39 — (coming)

---

## Tags for social sharing

`#DistributedSystems #BackendEngineering #Infrastructure #OSS #Observability #AIInference #Wayfair`

---

## Accuracy checkpoint (verify against context docs before writing)

- Wayfair tenure: Nov 2024 – Mar 2026 ✓
- Scale: 250k+ SKU updates per supplier, 20k+ suppliers ✓ (resume-extracted.md)
- GCP event-driven pricing engine: reduces price propagation from hours to sub-seconds ✓
- UCMS (`ucms-partner-home`): Supplier Cost Management, HPA 10-35, FastAPI, 4 CloudSQL proxy replicas ✓ (pricing-system-architecture.md)
- PAS: Price Adjustment System — Bigtable `pricing-cost-adjustment-bt`, 3 clusters × 3 nodes ✓
- 99.99% availability bulk processing framework ✓ (resume-extracted.md)
- Do NOT invent: specific supplier names, exact incident dates, internal ticket numbers, budget figures beyond GMV
