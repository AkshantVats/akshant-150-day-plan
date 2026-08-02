# Day 54 — Code Plan
## agent-benchmark-runner: Flame Graph Timeline — Colored by Cost

**Calendar**: Sunday, Day 54 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/infra-ai-streaming` → `agent-benchmark-runner/` (builds on Day 53's
`pkg/report` — `Report`, `RenderTimelineSVG`)
**Language**: Go 1.25
**Builds on**: Day 53 gave a reader a divergence-colored timeline — where two agents'
sequences stopped agreeing. It says nothing about which tool calls were expensive. Day 54
adds a second, orthogonal signal: dollar cost per tool call, rendered as a flame-graph-style
timeline where box width is cost and box color is a cost heat gradient.

### Shared Thread
> Flame graph timeline meets Flame Graphs — CPU Profile for Agents in today's
> `agent-benchmark-runner` commit.
> Color by cost is control-loop tuning — which actuator spends the energy. Wide bars are
> where budget died.

---

## Summary

1. **`pkg/report/flame.go`** — `CostReport` (embeds `Report`, adds `CostsA`, `CostsB
   []float64` parallel to `ToolCallsA`/`ToolCallsB`), `BuildCostReport` (validates cost
   slice lengths against the tool call slices), `RenderFlameGraphSVG` (renders each row as
   a contiguous flame-graph strip — box width proportional to that call's cost, box color
   on a cool-to-hot gradient scaled to the report's most expensive call, the single most
   expensive call per row marked with a heavier stroke).
2. **`pkg/report/flame_test.go`** — well-formed SVG, width proportional to cost (a $0.40
   call renders wider than a $0.01 call), color gradient present at both ends (cheapest
   and most expensive fills differ), peak-cost call gets the marker stroke, empty cost
   slice degenerates to minimum-width boxes without dividing by zero, `BuildCostReport`
   rejects a cost slice whose length doesn't match its tool call slice.
3. **`DESIGN.md`** — Day 54 addendum: why cost is a second axis instead of folding into
   the Day 53 timeline's existing color scheme, why width is linear in cost rather than
   log-scaled, why a `CostReport` wraps `Report` instead of adding optional fields to it.
4. **`README.md`** — `pkg/report` table row update + a "Cost Flame Graph" usage section.

Target: `go test -race ./...` exits 0 (module-wide, previous day counts plus new flame
tests), `go vet ./...` exits 0, `gofmt -l .` empty. CI already runs these three steps for
`agent-benchmark-runner` — no workflow changes needed.

---

## Key Design Decisions

- **`CostReport` wraps `Report` instead of adding cost fields to it.** Day 53's `Report` is
  already serialized (JSON) and rendered (markdown, SVG) without any notion of cost; every
  caller that built a `Report` from a `compare.Result` before today keeps compiling
  unchanged. A wrapper type that wants cost data opts in explicitly instead of every
  existing `Report` value gaining two always-empty slices.
- **Width is linear in cost, clamped to a floor, not log-scaled.** A true flame graph's
  width is proportional to the resource it measures, and a reader's first read of "which
  bar is biggest" has to match "which call cost the most" without a scale transform in
  between. A floor width (not zero) keeps a $0.00 call visible as a box instead of a
  zero-width sliver that reads as a rendering bug.
- **Rows are independent horizontal strips, not aligned by step index.** Day 53's timeline
  aligns agent A and agent B by tool-call index because it's answering "where did they
  diverge." Day 54 is answering "where did the budget go," and forcing two cost-weighted
  rows into the same column grid would make identical-cost calls at different step indices
  look different width for no cost-related reason. Each row lays its own boxes out
  contiguously, the way a real flame graph does.
- **One peak marker per row, not a top-N list.** "Wide bars are where budget died" is a
  single-glance claim — marking every call above some threshold would turn the graphic
  back into a table. A heavier stroke on the single most expensive call per row answers
  "where did the money go" without requiring a legend.
- **Cost is dollars (`float64`), not a duration.** Day 54's plan bridge ties this directly
  to "which actuator spends the energy" — a dollar figure, not a latency number Day 53
  already has no data for. `agent-benchmark-runner` has no live cost telemetry yet, so
  `BuildCostReport` takes costs as an explicit parameter (mirroring how Day 53's `Build`
  takes tool call sequences as a parameter rather than reaching into `compare.Result` for
  data it doesn't carry) — a future runner supplies real per-call cost once one exists.

---

## Acceptance Criteria

```bash
gofmt -l .           # empty
go vet ./...         # exits 0
go test -race ./...  # exits 0, all tests pass including new pkg/report/flame_test.go
```

---

## Series Navigation

- Previous: Day 53 — Report Generator (`pkg/report` markdown/JSON/SVG)
- Next: Day 55 — LensAI integration, benchmark completion emits ingest events
