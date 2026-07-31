# Day 49 — AI Learning Blog Plan

**Title**: Day 49 — Streaming Parsers — OOM-Safe Debugging
**Subtitle**: Iterators over multi-MB traces
**Hook**: Replay must work on laptop RAM — stream everything.
**day_index**: 49

## Angle

Clone the GOLD post's depth (`day-2-continuous-batching-vllm.html`) and the most recent AI
Learning post's structure (Day 47). Reader already knows "just read the file into memory and
loop over it" as the default parsing instinct; new concept is why that instinct breaks at scale
for a shared, multi-tenant log file, and what an iterator-style parser buys instead — including
the part where it doesn't buy what you'd expect.

Cover, in order:

1. **Hook**: "Replay must work on laptop RAM — stream everything," then the concrete failure
   mode: a shared trace log holding every recorded agent run ever, and a debugging session that
   only needs one of them.
2. **DS analogy (attr-box team)**: reading a phone book to find one number. You don't photocopy
   the whole book first — you flip pages one at a time and stop the moment you find the entry,
   which is also why you can't binary-search a book that isn't alphabetized (the ordering
   assumption streaming leans on).
3. **`eventlog.Scanner`**: a `bufio.Scanner`-style line-at-a-time reader — one line in memory at
   a time instead of the whole file. Mermaid diagram: Log File → Scanner.Scan() loop → one
   AgentEvent → discard or keep.
4. **The benchmark's honest result**: streaming used ~20% less peak memory on a 51-trace shared
   log but was ~40% slower and allocated 2x more than the batch path — two single-pass scans
   each paying JSON-decode cost per line beat one batched `ReadJSONL` pass on raw throughput.
   Bounded memory is not the same prize as "faster," and a real design write-up says so.
5. **Where streaming wins outright**: `--stop-at-step` on a large file reads only what it needs
   — measured 3.7% of a 1.78MB file to answer a first-step question — because the scanner never
   reads past the point where the caller stopped asking.
6. **Closer**: an iterator's job is to make "I don't need the rest of this" a real decision the
   code can act on, not just a place the loop happens to stop.

Required: mermaid init block (CLAUDE.md section 4.5), labels ≤6 words, attr-box DS analogy,
ai.hook opening line, `<strong>So what:</strong>` inline (not a separate CSS class) matching Day
47 AI Learning's convention.

Kicker: `AI Learning · Day 49 of 150`. Max 3 sentences/paragraph.
