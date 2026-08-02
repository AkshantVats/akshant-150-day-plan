# Day 53 — Code Plan
## agent-benchmark-runner: Report Generator — Markdown + JSON + Timeline SVG

**Calendar**: Saturday, Day 53 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-benchmark-runner/` (builds on Day 51's
`pkg/compare` and Day 52's orchestrator/store packages)
**Language**: Go 1.25
**Builds on**: Day 51 fixed the scenario (Task YAML) and the bar (typed criteria) as data,
and produces a `compare.Result` comparing two agents. Day 53 answers "what does a human
actually read" — a `compare.Result` is a Go struct, not a report.

### Shared Thread
> `agent-benchmark-runner report generator — "14 calls vs 9, diverged step 5" markdown +
> JSON + timeline SVG.`
> Comparison markdown is the executive summary of a trace — dollars and steps, not vibes.
> A benchmark result only earns a reviewer's attention if it can be read in one line
> before anything else: how many tool calls each agent made, and where they stopped
> agreeing.

---

## Summary

1. **`pkg/report/report.go`** — `Report` (reshapes a `compare.Result` plus both agents'
   raw tool call sequences), `Build`, `Headline` formatting (`"14 calls vs 9, diverged at
   step 5"` or `"N calls vs N, sequences matched"`), `RenderMarkdown`, `RenderJSON`.
2. **`pkg/report/report_test.go`** — 7 tests: divergent headline, matched headline,
   pass/fail carry-through, markdown headline+table content, markdown sequence-match note,
   JSON round-trip, JSON indentation.
3. **`pkg/report/timeline.go`** — `RenderTimelineSVG`: two-row SVG timeline, one box per
   tool call, divergence step highlighted, boxes after the divergence point muted, a
   sequence that ended early drawn as a dashed empty slot rather than omitted.
4. **`pkg/report/timeline_test.go`** — 6 tests: well-formed SVG, dashed-placeholder count
   for the shorter sequence, divergence color present, no divergence color when sequences
   matched, empty-sequence edge case, label truncation.
5. **`DESIGN.md`** — Day 53 addendum: why the headline leads with divergence instead of
   pass/fail, why the SVG is hand-rolled instead of a charting dependency, Day 53 scope
   note, updated file layout and series navigation.
6. **`README.md`** — `pkg/report` package table row + a "Generating a Report" usage
   section.

Target: `go test -race ./...` exits 0 (52 tests total, module-wide), `go vet ./...` exits
0, `gofmt -l .` empty. CI already runs these three steps for `agent-benchmark-runner`
(wired Day 51) — no workflow changes needed.

---

## Key Design Decisions

- **The headline leads with divergence, not pass/fail.** Day 51 already reports
  `PassedA`/`PassedB` per agent; a report that opens with two independent pass/fail badges
  makes a reviewer hunt for where the runs actually differ. `"14 calls vs 9, diverged at
  step 5"` answers the question a reviewer opens the report to ask, before a single
  criterion result.
- **`Report` carries the raw tool call sequences; `compare.Result` deliberately does not.**
  Day 51's `compare.Result` intentionally omits the outcomes it was computed from (see
  DESIGN.md's "Comparing Two Agents"). A report needs the sequences themselves to render a
  timeline, so `Build` takes them as separate parameters rather than reaching back into
  `compare.Result` for data it was never designed to carry.
- **Three renderers, not one format with options.** Markdown, JSON, and SVG serve three
  different consumers (a PR/Slack summary, a dashboard or alerting rule, a visual diff) —
  keeping them as separate functions over the same `Report` value keeps each renderer
  simple instead of growing one function with format-switch branches.
- **Hand-rolled SVG, not a charting library dependency.** The visual is a small, fixed
  shape (two rows of colored boxes) that a few dozen lines of `fmt.Fprintf` render exactly
  as well as a general-purpose charting library, without adding a dependency and its
  transitive tree for one narrow chart shape.
- **A sequence that ended early is drawn, not omitted.** The shorter agent's timeline gets
  dashed empty-slot boxes for the steps it never reached, so "stopped here" is visible
  instead of reading as an unexplained gap.

---

## Acceptance Criteria

```bash
gofmt -l .           # empty
go vet ./...         # exits 0
go test -race ./...  # exits 0, 52 tests pass
```

## Series Navigation

Previous: Day 52 — agent-benchmark-runner: Orchestrator — Parallel Runs, ClickHouse `benchmark_runs`, Seed Control
Next: Day 54 — TBD
