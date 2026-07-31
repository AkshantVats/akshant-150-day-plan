# Day 47 — AI Learning Blog Plan

**Title**: Day 47 — Diff Semantics — Structural vs Textual
**Subtitle**: First divergence detection on spans
**Hook**: Git diff for trees — stop at first changed tool output.
**day_index**: 47

## Angle

Clone the GOLD post's depth (`day-2-continuous-batching-vllm.html`) and the most recent AI
Learning post's structure. Reader already knows Unix `diff`/line-based comparison; new concept
is why that breaks down for structured, non-deterministic-serialization data like agent traces,
and how a composite-key comparison fixes it.

Cover, in order:

1. **Hook**: "Git diff for trees — stop at first changed tool output," then why a textual diff
   of two agent traces reports near-total disagreement even when the traces made identical
   decisions (timestamps, span IDs, JSON key order all differ regardless).
2. **DS analogy (attr-box team)**: two witness statements describing the same event in different
   words — a word-for-word diff flags nearly every sentence, but an investigator compares facts
   (make, color, direction), not phrasing, and finds the one fact that actually disagrees.
3. **The composite key already solved half this problem**: `pkg/diff` reuses the exact
   `ToolName` + `InputHash` key `pkg/mocker` (Day 44/46) already used for replay lookups — one
   design decision paying for two tools. Mermaid diagram: Trace A/B → Compare per step → match or
   divergence.
4. **Why ToolName wins the tie-break**: when both fields differ at once, reporting "different
   tool" is more informative than "different input" — the more fundamental divergence wins.
5. **Why a length mismatch still counts**: a trace that ran further took an action the shorter
   one never took; that's not agreement, it's an untested divergence.
6. **Closer**: the hard part of a diff algorithm is deciding what counts as "the same," not the
   walk-and-compare loop itself.

Required: mermaid init block (CLAUDE.md section 4.5), labels ≤6 words, attr-box DS analogy,
ai.hook opening line, `<strong>So what:</strong>` inline (not a separate CSS class) matching Day
46 AI Learning's convention.

Kicker: `AI Learning · Day 47 of 150`. Max 3 sentences/paragraph.
