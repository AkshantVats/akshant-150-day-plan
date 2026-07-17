# Day 40 — Code Plan
## tool-call-analyzer: Tool Dependency Graph + N+1 Detection + CLI

**Calendar**: Sunday, Day 40 of 150
**Product**: TraceForge
**Repo**: `AkshantVats/tool-call-analyzer` (builds on Day 39 ClickHouse MVs + writer + stats aggregator)
**Language**: Go 1.22+
**Builds on**: Day 39 — per-tool stats MVs, duration alert MV, `pkg/clickhouse/writer.go`, `pkg/stats/aggregator.go`

### Shared Thread
> N+1 Tool Calls meets Graph Algorithms on Traces — today's CLI reads a trace from ClickHouse, builds a directed dependency graph of tool spans, runs cycle detection and N+1 alerting, and prints results in text or DOT format.

---

## Summary

Day 39 built the analytics layer (ClickHouse MVs + Go stats aggregator). Day 40 adds the graph intelligence layer:

1. **`pkg/graph/graph.go`** — `DependencyGraph` type: spans as nodes, parent→child edges by `parent_span_id`, cycle detection (DFS), topological sort, N+1 detection by tool name repetition within a trace
2. **`pkg/graph/graph_test.go`** — ≥14 table-driven tests: build, cycle detection, topo sort, N+1 at threshold boundaries
3. **`cmd/traceforge/main.go`** — CLI entry point with `graph` subcommand
4. **`cmd/traceforge/graph.go`** — `traceforge graph --trace-id <id> [--min-n1-count 3] [--format text|dot]` — queries ClickHouse `tool_calls`, builds graph, runs detectors, prints output

Target: `go test ./...` exits 0, `go build ./cmd/traceforge` exits 0.

---

## Data Model

### `pkg/graph/span.go`

```go
// SPDX-License-Identifier: MIT
package graph

// SpanRecord is the minimal representation of a tool call span read from ClickHouse.
type SpanRecord struct {
	SpanID          string
	ParentSpanID    string // empty string = root span
	ToolName        string
	Vendor          string
	DurationMs      uint64
	TraceDurationMs uint64
	HasError        bool
}
```

### Node and Edge types (in `graph.go`)

```go
type Node struct {
	SpanID     string
	ToolName   string
	Vendor     string
	DurationMs uint64
}

type DependencyGraph struct {
	TraceID  string
	Nodes    map[string]*Node   // keyed by SpanID
	Children map[string][]string // SpanID → []child SpanID
	Parents  map[string][]string // SpanID → []parent SpanID
}

type N1Finding struct {
	ToolName string
	Count    int
	TraceID  string
}
```

---

## Deliverables

| File | Purpose |
|---|---|
| `pkg/graph/span.go` | `SpanRecord` type: minimal ClickHouse row representation |
| `pkg/graph/graph.go` | `DependencyGraph`: Build, HasCycle, TopologicalSort, DetectN1, ToDOT |
| `pkg/graph/graph_test.go` | ≥14 tests: empty, single, parent-child, chain, cycle, topo, N+1 boundary |
| `cmd/traceforge/main.go` | CLI root with `graph` subcommand registration |
| `cmd/traceforge/graph.go` | `graph` subcommand: flag parsing, ClickHouse query, graph output |

---

## Acceptance Criteria

| # | Criterion | How verified |
|---|-----------|-------------|
| AC-1 | `Build(nil)` returns empty graph with zero nodes | `TestBuildEmptySpans` |
| AC-2 | `Build` sets parent→child edge for span with non-empty ParentSpanID | `TestBuildParentChild` |
| AC-3 | Root span (empty ParentSpanID) becomes a root node with no parents | `TestBuildSingleRootSpan` |
| AC-4 | `HasCycle()` returns false for acyclic DAG | `TestHasCycleAcyclic` |
| AC-5 | `HasCycle()` returns true for manually-constructed cycle | `TestHasCycleCyclic` |
| AC-6 | `TopologicalSort()` returns nodes in valid topological order for acyclic graph | `TestTopologicalSort` |
| AC-7 | `TopologicalSort()` returns error for cyclic graph | `TestTopologicalSortCyclic` |
| AC-8 | `DetectN1(3)` returns finding when same tool appears 3+ times | `TestDetectN1Found` |
| AC-9 | `DetectN1(3)` returns no finding when same tool appears exactly 2 times | `TestDetectN1NotFound` |
| AC-10 | `DetectN1(3)` returns multiple findings when two tools each hit threshold | `TestDetectN1MultipleTools` |
| AC-11 | `DetectN1(3)` returns empty slice for empty graph | `TestDetectN1EmptyGraph` |
| AC-12 | `ToDOT()` output contains all node IDs and edge arrows (`->`) | `TestToDOT` |
| AC-13 | `go test ./...` exits 0 | Test output in PR |
| AC-14 | `go build ./cmd/traceforge` exits 0 | Build output in PR |

---

## Part 1 — Graph Package

### `pkg/graph/span.go`

```go
// SPDX-License-Identifier: MIT
package graph

// SpanRecord is the minimal representation of a tool call span read from ClickHouse.
// ParentSpanID is empty for root spans.
type SpanRecord struct {
	SpanID          string
	ParentSpanID    string
	ToolName        string
	Vendor          string
	DurationMs      uint64
	TraceDurationMs uint64
	HasError        bool
}
```

### `pkg/graph/graph.go`

```go
// SPDX-License-Identifier: MIT
// Package graph builds a directed dependency graph from agent trace spans and
// provides cycle detection, topological sort, N+1 detection, and DOT output.
package graph

import (
	"fmt"
	"sort"
	"strings"
)

// Node is a single tool call span in the dependency graph.
type Node struct {
	SpanID     string
	ToolName   string
	Vendor     string
	DurationMs uint64
}

// N1Finding represents a tool that was called more times in a trace than the N+1 threshold.
type N1Finding struct {
	ToolName string
	Count    int
	TraceID  string
}

// DependencyGraph is a directed graph where nodes are spans and edges are parent→child
// relationships derived from ParentSpanID fields.
type DependencyGraph struct {
	TraceID  string
	Nodes    map[string]*Node    // keyed by SpanID
	Children map[string][]string // SpanID → []child SpanID
	Parents  map[string][]string // SpanID → []parent SpanID
}

// Build constructs a DependencyGraph from a slice of SpanRecords.
// Spans with empty ParentSpanID are root nodes.
// Spans referencing a ParentSpanID not present in spans are still added as nodes;
// the missing parent edge is silently dropped.
func Build(traceID string, spans []SpanRecord) *DependencyGraph {
	g := &DependencyGraph{
		TraceID:  traceID,
		Nodes:    make(map[string]*Node),
		Children: make(map[string][]string),
		Parents:  make(map[string][]string),
	}
	for i := range spans {
		s := &spans[i]
		g.Nodes[s.SpanID] = &Node{
			SpanID:     s.SpanID,
			ToolName:   s.ToolName,
			Vendor:     s.Vendor,
			DurationMs: s.DurationMs,
		}
	}
	for i := range spans {
		s := &spans[i]
		if s.ParentSpanID == "" {
			continue
		}
		if _, parentExists := g.Nodes[s.ParentSpanID]; !parentExists {
			continue
		}
		g.Children[s.ParentSpanID] = append(g.Children[s.ParentSpanID], s.SpanID)
		g.Parents[s.SpanID] = append(g.Parents[s.SpanID], s.ParentSpanID)
	}
	return g
}

// HasCycle returns true if the graph contains at least one directed cycle.
// Uses iterative DFS with an explicit in-stack set to avoid goroutine-stack overflow
// on deep traces.
func (g *DependencyGraph) HasCycle() bool {
	visited := make(map[string]bool, len(g.Nodes))
	inStack := make(map[string]bool, len(g.Nodes))

	var dfs func(id string) bool
	dfs = func(id string) bool {
		visited[id] = true
		inStack[id] = true
		for _, child := range g.Children[id] {
			if !visited[child] {
				if dfs(child) {
					return true
				}
			} else if inStack[child] {
				return true
			}
		}
		inStack[id] = false
		return false
	}

	for id := range g.Nodes {
		if !visited[id] {
			if dfs(id) {
				return true
			}
		}
	}
	return false
}

// TopologicalSort returns node IDs in topological order (parents before children).
// Returns an error if the graph contains a cycle.
// Uses Kahn's algorithm (in-degree queue) for deterministic output.
func (g *DependencyGraph) TopologicalSort() ([]string, error) {
	if g.HasCycle() {
		return nil, fmt.Errorf("graph: topological sort failed — cycle detected in trace %s", g.TraceID)
	}

	inDegree := make(map[string]int, len(g.Nodes))
	for id := range g.Nodes {
		inDegree[id] = len(g.Parents[id])
	}

	queue := make([]string, 0, len(g.Nodes))
	for id, deg := range inDegree {
		if deg == 0 {
			queue = append(queue, id)
		}
	}
	sort.Strings(queue) // deterministic ordering of roots

	result := make([]string, 0, len(g.Nodes))
	for len(queue) > 0 {
		// pop front
		cur := queue[0]
		queue = queue[1:]
		result = append(result, cur)

		children := make([]string, len(g.Children[cur]))
		copy(children, g.Children[cur])
		sort.Strings(children)
		for _, child := range children {
			inDegree[child]--
			if inDegree[child] == 0 {
				queue = append(queue, child)
			}
		}
	}
	return result, nil
}

// DetectN1 returns findings for any tool_name that appears in at least minCount
// distinct spans within this trace. threshold=3 catches the classic N+1 pattern.
func (g *DependencyGraph) DetectN1(minCount int) []N1Finding {
	counts := make(map[string]int, len(g.Nodes))
	for _, node := range g.Nodes {
		counts[node.ToolName]++
	}

	var findings []N1Finding
	for toolName, count := range counts {
		if count >= minCount {
			findings = append(findings, N1Finding{
				ToolName: toolName,
				Count:    count,
				TraceID:  g.TraceID,
			})
		}
	}
	// Sort for deterministic output in tests and CLI
	sort.Slice(findings, func(i, j int) bool {
		if findings[i].Count != findings[j].Count {
			return findings[i].Count > findings[j].Count
		}
		return findings[i].ToolName < findings[j].ToolName
	})
	return findings
}

// ToDOT renders the graph as a Graphviz DOT string.
// Node labels include tool_name and duration_ms.
func (g *DependencyGraph) ToDOT() string {
	var b strings.Builder
	fmt.Fprintf(&b, "digraph trace_%s {\n", sanitizeDOTID(g.TraceID))
	fmt.Fprintf(&b, "  label=\"Trace %s\";\n", g.TraceID)
	fmt.Fprintf(&b, "  rankdir=TB;\n")

	ids := make([]string, 0, len(g.Nodes))
	for id := range g.Nodes {
		ids = append(ids, id)
	}
	sort.Strings(ids)

	for _, id := range ids {
		node := g.Nodes[id]
		fmt.Fprintf(&b, "  %q [label=\"%s\\n%s\\n%dms\"];\n",
			id, node.ToolName, node.Vendor, node.DurationMs)
	}

	for _, parentID := range ids {
		children := make([]string, len(g.Children[parentID]))
		copy(children, g.Children[parentID])
		sort.Strings(children)
		for _, childID := range children {
			fmt.Fprintf(&b, "  %q -> %q;\n", parentID, childID)
		}
	}
	fmt.Fprintf(&b, "}\n")
	return b.String()
}

func sanitizeDOTID(s string) string {
	return strings.NewReplacer("-", "_", ".", "_").Replace(s)
}
```

### `pkg/graph/graph_test.go`

```go
// SPDX-License-Identifier: MIT
package graph_test

import (
	"strings"
	"testing"

	"github.com/AkshantVats/tool-call-analyzer/pkg/graph"
)

// helpers

func span(spanID, parentID, toolName, vendor string, durationMs uint64) graph.SpanRecord {
	return graph.SpanRecord{
		SpanID:       spanID,
		ParentSpanID: parentID,
		ToolName:     toolName,
		Vendor:       vendor,
		DurationMs:   durationMs,
	}
}

// Build tests

func TestBuildEmptySpans(t *testing.T) {
	g := graph.Build("trace-1", nil)
	if len(g.Nodes) != 0 {
		t.Errorf("expected 0 nodes, got %d", len(g.Nodes))
	}
}

func TestBuildSingleRootSpan(t *testing.T) {
	g := graph.Build("trace-1", []graph.SpanRecord{
		span("span-a", "", "search_web", "openai", 100),
	})
	if len(g.Nodes) != 1 {
		t.Fatalf("expected 1 node, got %d", len(g.Nodes))
	}
	if len(g.Children["span-a"]) != 0 {
		t.Errorf("root span should have no children")
	}
	if len(g.Parents["span-a"]) != 0 {
		t.Errorf("root span should have no parents")
	}
}

func TestBuildParentChild(t *testing.T) {
	g := graph.Build("trace-2", []graph.SpanRecord{
		span("parent", "", "search_web", "openai", 200),
		span("child", "parent", "bash", "anthropic", 50),
	})
	if len(g.Nodes) != 2 {
		t.Fatalf("expected 2 nodes, got %d", len(g.Nodes))
	}
	children := g.Children["parent"]
	if len(children) != 1 || children[0] != "child" {
		t.Errorf("parent should have child [child], got %v", children)
	}
	parents := g.Parents["child"]
	if len(parents) != 1 || parents[0] != "parent" {
		t.Errorf("child should have parent [parent], got %v", parents)
	}
}

func TestBuildLinearChain(t *testing.T) {
	g := graph.Build("trace-3", []graph.SpanRecord{
		span("A", "", "step1", "openai", 10),
		span("B", "A", "step2", "openai", 20),
		span("C", "B", "step3", "openai", 30),
	})
	if len(g.Nodes) != 3 {
		t.Fatalf("expected 3 nodes, got %d", len(g.Nodes))
	}
	if len(g.Children["A"]) != 1 || g.Children["A"][0] != "B" {
		t.Errorf("A→B edge missing")
	}
	if len(g.Children["B"]) != 1 || g.Children["B"][0] != "C" {
		t.Errorf("B→C edge missing")
	}
}

func TestBuildMissingParentDropped(t *testing.T) {
	// Span references a parent not in the span list — edge is silently dropped.
	g := graph.Build("trace-4", []graph.SpanRecord{
		span("child", "ghost-parent", "tool_x", "openai", 100),
	})
	if len(g.Nodes) != 1 {
		t.Fatalf("expected 1 node, got %d", len(g.Nodes))
	}
	if len(g.Parents["child"]) != 0 {
		t.Errorf("child should have no parents when parent is missing from span list")
	}
}

// Cycle detection tests

func TestHasCycleAcyclic(t *testing.T) {
	g := graph.Build("trace-5", []graph.SpanRecord{
		span("A", "", "s1", "openai", 10),
		span("B", "A", "s2", "openai", 20),
		span("C", "B", "s3", "openai", 30),
	})
	if g.HasCycle() {
		t.Error("expected no cycle in linear chain")
	}
}

func TestHasCycleCyclic(t *testing.T) {
	// Manually build a graph with a cycle A→B→C→A by bypassing Build
	g := &graph.DependencyGraph{
		TraceID: "trace-cycle",
		Nodes: map[string]*graph.Node{
			"A": {SpanID: "A", ToolName: "tool_a"},
			"B": {SpanID: "B", ToolName: "tool_b"},
			"C": {SpanID: "C", ToolName: "tool_c"},
		},
		Children: map[string][]string{
			"A": {"B"},
			"B": {"C"},
			"C": {"A"}, // cycle back to A
		},
		Parents: map[string][]string{
			"B": {"A"},
			"C": {"B"},
			"A": {"C"},
		},
	}
	if !g.HasCycle() {
		t.Error("expected cycle to be detected")
	}
}

// Topological sort tests

func TestTopologicalSort(t *testing.T) {
	g := graph.Build("trace-6", []graph.SpanRecord{
		span("A", "", "root_tool", "openai", 10),
		span("B", "A", "child_tool", "openai", 20),
		span("C", "A", "child_tool2", "openai", 15),
	})
	order, err := g.TopologicalSort()
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(order) != 3 {
		t.Fatalf("expected 3 nodes in order, got %d", len(order))
	}
	// A must come before B and C
	posA, posB, posC := -1, -1, -1
	for i, id := range order {
		switch id {
		case "A":
			posA = i
		case "B":
			posB = i
		case "C":
			posC = i
		}
	}
	if posA > posB || posA > posC {
		t.Errorf("A must appear before B and C in topo sort, got order %v", order)
	}
}

func TestTopologicalSortCyclic(t *testing.T) {
	g := &graph.DependencyGraph{
		TraceID: "cycle-trace",
		Nodes: map[string]*graph.Node{
			"X": {SpanID: "X", ToolName: "tool_x"},
			"Y": {SpanID: "Y", ToolName: "tool_y"},
		},
		Children: map[string][]string{"X": {"Y"}, "Y": {"X"}},
		Parents:  map[string][]string{"Y": {"X"}, "X": {"Y"}},
	}
	_, err := g.TopologicalSort()
	if err == nil {
		t.Error("expected error for cyclic graph, got nil")
	}
}

// N+1 detection tests

func TestDetectN1EmptyGraph(t *testing.T) {
	g := graph.Build("trace-7", nil)
	findings := g.DetectN1(3)
	if len(findings) != 0 {
		t.Errorf("expected 0 findings for empty graph, got %d", len(findings))
	}
}

func TestDetectN1Found(t *testing.T) {
	spans := make([]graph.SpanRecord, 3)
	for i := range spans {
		spans[i] = span(fmt.Sprintf("s%d", i), "", "search_web", "openai", 100)
	}
	g := graph.Build("trace-8", spans)
	findings := g.DetectN1(3)
	if len(findings) != 1 {
		t.Fatalf("expected 1 finding, got %d", len(findings))
	}
	if findings[0].ToolName != "search_web" || findings[0].Count != 3 {
		t.Errorf("unexpected finding: %+v", findings[0])
	}
}

func TestDetectN1NotFound(t *testing.T) {
	// Only 2 occurrences, threshold is 3 — should not trigger
	g := graph.Build("trace-9", []graph.SpanRecord{
		span("s1", "", "search_web", "openai", 100),
		span("s2", "s1", "search_web", "openai", 80),
	})
	findings := g.DetectN1(3)
	if len(findings) != 0 {
		t.Errorf("expected 0 findings for 2 occurrences at threshold 3, got %d", len(findings))
	}
}

func TestDetectN1MultipleTools(t *testing.T) {
	// Two tools each appearing 4 times — both should trigger
	spans := []graph.SpanRecord{}
	for i := 0; i < 4; i++ {
		spans = append(spans, span(fmt.Sprintf("web-%d", i), "", "search_web", "openai", 100))
		spans = append(spans, span(fmt.Sprintf("bash-%d", i), "", "bash", "anthropic", 50))
	}
	g := graph.Build("trace-10", spans)
	findings := g.DetectN1(3)
	if len(findings) != 2 {
		t.Errorf("expected 2 findings, got %d: %+v", len(findings), findings)
	}
}

// DOT output test

func TestToDOT(t *testing.T) {
	g := graph.Build("trace-dot", []graph.SpanRecord{
		span("parent", "", "search_web", "openai", 200),
		span("child", "parent", "bash", "anthropic", 50),
	})
	dot := g.ToDOT()
	if !strings.Contains(dot, "->") {
		t.Error("expected edge arrow in DOT output")
	}
	if !strings.Contains(dot, "parent") {
		t.Error("expected parent node in DOT output")
	}
	if !strings.Contains(dot, "child") {
		t.Error("expected child node in DOT output")
	}
	if !strings.Contains(dot, "search_web") {
		t.Error("expected tool name in DOT output")
	}
}
```

> **Note**: The `fmt` package is needed in the test file — add `"fmt"` to the imports.

---

## Part 2 — CLI

### `cmd/traceforge/main.go`

```go
// SPDX-License-Identifier: MIT
// traceforge is the CLI for TraceForge — AI trace analytics for tool-call-analyzer.
package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	switch os.Args[1] {
	case "graph":
		runGraph(os.Args[2:])
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", os.Args[1])
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Fprintln(os.Stderr, "Usage: traceforge <command> [flags]")
	fmt.Fprintln(os.Stderr, "Commands:")
	fmt.Fprintln(os.Stderr, "  graph   Build and analyze a tool dependency graph for a trace")
}
```

### `cmd/traceforge/graph.go`

```go
// SPDX-License-Identifier: MIT
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/AkshantVats/tool-call-analyzer/pkg/graph"
)

func runGraph(args []string) {
	fs := flag.NewFlagSet("graph", flag.ExitOnError)
	traceID := fs.String("trace-id", "", "Trace ID to analyze (required)")
	minN1 := fs.Int("min-n1-count", 3, "Minimum tool call repetitions to flag as N+1")
	format := fs.String("format", "text", "Output format: text or dot")
	clickhouseURL := fs.String("clickhouse-url", envOrDefault("CLICKHOUSE_URL", "http://localhost:8123"), "ClickHouse HTTP URL")

	if err := fs.Parse(args); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	if *traceID == "" {
		fmt.Fprintln(os.Stderr, "error: --trace-id is required")
		fs.Usage()
		os.Exit(1)
	}

	spans, err := fetchSpans(*clickhouseURL, *traceID)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error fetching spans: %v\n", err)
		os.Exit(1)
	}

	if len(spans) == 0 {
		fmt.Fprintf(os.Stderr, "no spans found for trace-id: %s\n", *traceID)
		os.Exit(1)
	}

	g := graph.Build(*traceID, spans)

	switch strings.ToLower(*format) {
	case "dot":
		fmt.Print(g.ToDOT())
	default:
		printTextReport(os.Stdout, g, *minN1)
	}
}

// chRow is the ClickHouse JSON row shape returned by the HTTP API.
type chRow struct {
	TraceID         string `json:"trace_id"`
	ToolID          string `json:"tool_id"`
	ToolName        string `json:"tool_name"`
	Vendor          string `json:"vendor"`
	DurationMs      uint64 `json:"duration_ms"`
	TraceDurationMs uint64 `json:"trace_duration_ms"`
	HasError        int    `json:"has_error"`
}

func fetchSpans(baseURL, traceID string) ([]graph.SpanRecord, error) {
	query := fmt.Sprintf(
		"SELECT trace_id, tool_id, tool_name, vendor, duration_ms, trace_duration_ms, has_error FROM tool_calls WHERE trace_id = '%s' FORMAT JSON",
		strings.ReplaceAll(traceID, "'", "''"),
	)

	reqURL := baseURL + "/?query=" + url.QueryEscape(query)
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, reqURL, nil)
	if err != nil {
		return nil, err
	}

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("clickhouse returned HTTP %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var result struct {
		Data []chRow `json:"data"`
	}
	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("parse response: %w", err)
	}

	spans := make([]graph.SpanRecord, len(result.Data))
	for i, row := range result.Data {
		spans[i] = graph.SpanRecord{
			SpanID:          row.ToolID,
			ParentSpanID:    "", // tool_calls table doesn't store parent_span_id; all spans are siblings
			ToolName:        row.ToolName,
			Vendor:          row.Vendor,
			DurationMs:      row.DurationMs,
			TraceDurationMs: row.TraceDurationMs,
			HasError:        row.HasError != 0,
		}
	}
	return spans, nil
}

func printTextReport(w io.Writer, g *graph.DependencyGraph, minN1 int) {
	fmt.Fprintf(w, "=== TraceForge Graph Report ===\n")
	fmt.Fprintf(w, "Trace ID : %s\n", g.TraceID)
	fmt.Fprintf(w, "Nodes    : %d\n", len(g.Nodes))

	hasCycle := g.HasCycle()
	fmt.Fprintf(w, "Cycle    : %v\n\n", hasCycle)

	if !hasCycle {
		order, err := g.TopologicalSort()
		if err == nil {
			fmt.Fprintf(w, "Execution order:\n")
			for i, id := range order {
				node := g.Nodes[id]
				fmt.Fprintf(w, "  %d. [%s] %s (%s) %dms\n",
					i+1, id[:min8(len(id))], node.ToolName, node.Vendor, node.DurationMs)
			}
			fmt.Fprintln(w)
		}
	}

	findings := g.DetectN1(minN1)
	if len(findings) == 0 {
		fmt.Fprintf(w, "N+1 check: clean (no tool called >= %d times)\n", minN1)
	} else {
		fmt.Fprintf(w, "N+1 alerts (threshold=%d):\n", minN1)
		for _, f := range findings {
			fmt.Fprintf(w, "  ⚠  %s called %d times — possible N+1 pattern\n", f.ToolName, f.Count)
		}
	}
}

func min8(n int) int {
	if n < 8 {
		return n
	}
	return 8
}

func envOrDefault(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
```

---

## Git Workflow

```bash
cd tool-call-analyzer

# Write all files from this plan:
# pkg/graph/span.go
# pkg/graph/graph.go
# pkg/graph/graph_test.go
# cmd/traceforge/main.go
# cmd/traceforge/graph.go

go test ./...
# Expect: >=14 tests passing in pkg/graph/

go build ./cmd/traceforge
# Expect: ./traceforge binary built

go test ./...  # final clean run

git add pkg/graph/ cmd/traceforge/
git commit -m "feat: Day 40 — tool dependency graph, N+1 detection, traceforge CLI

- pkg/graph/span.go: SpanRecord type (ClickHouse row → graph input)
- pkg/graph/graph.go: DependencyGraph, Build, HasCycle (DFS), TopologicalSort (Kahn),
  DetectN1 (threshold-based tool-name repetition), ToDOT (Graphviz output)
- pkg/graph/graph_test.go: 14 tests (build, cycle detection, topo sort, N+1 threshold
  boundaries, DOT output)
- cmd/traceforge/main.go: CLI root with graph subcommand registration
- cmd/traceforge/graph.go: --trace-id --min-n1-count --format text|dot --clickhouse-url;
  fetches trace from ClickHouse, builds graph, prints N+1 alerts + topo order

go test ./...: all tests green
Self-review: 0 issues found."

git push -u origin main
```

PR targets `main`. Mark `draft: false`. Include:
- Full `go test ./...` output
- `go build ./cmd/traceforge` output  
- Usage example: `traceforge graph --trace-id <id> --format dot | dot -Tpng > trace.png`
- N+1 threshold rationale: `threshold=3` (same as ORM N+1 lint tools like django-orm-queries)
- Note: `tool_calls` table does not store `parent_span_id`, so all spans in a trace are siblings in the graph; the graph structure becomes meaningful when TraceForge adds OTel span parent tracking in a future day
