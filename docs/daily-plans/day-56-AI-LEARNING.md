# Day 56 — AI Learning Blog Plan

**Title**: Day 56 — Monorepo vs Multi-Repo — Platform Packaging
**Subtitle**: Compose files as integration contract
**Hook**: Buyers install compose, not git clone four times.
**day_index**: 56

**Format**: `design` (tradeoff essay, per `docs/BLOG-FORMAT-MIX.md`) — this is a genuine
monorepo-vs-multi-repo packaging decision with an options table and a rejected
alternative, following Day 55's `design` framing but on a different axis (repo topology +
integration contract, not join-key/schema). Days 51-52 ran a design/deep-dive hybrid and
53-54 ran pure deep-dive, so `design` here varies the run without repeating either.

**Bridge**: today's code puts all four TraceForge components — `traceforge`,
`agent-replay-engine`, `agent-benchmark-runner` (which gets its first CLI today via
`pkg/subprocess`), and `tool-call-analyzer` — inside one `infra-ai-streaming` monorepo and
ties them together with one root `docker-compose.yml`. The post explains why monorepo +
compose won over four separate repos + a docs page telling users how to wire them
together by hand.

## Angle

A platform made of N independently-versioned components has to answer one packaging
question before it has any users: does a person installing it clone one thing or N
things? Four separate repos (`agent-replay-engine`, `agent-benchmark-runner`,
`tool-call-analyzer`, `traceforge`) each with their own `go.mod`, their own CI, their own
release cadence is the more "correct" separation of concerns on paper — each component
can version independently, and a consumer who only wants one of the four doesn't pay for
the others. But it pushes the integration cost onto every single user: four `git clone`s,
four READMEs to reconcile, and no single artifact that proves the four pieces actually
work together, only four sets of docs asserting they should.

The monorepo choice made on Day 44 (when `agent-replay-engine` landed inside
`infra-ai-streaming` rather than as its own repo) already answered the "one clone or four"
question for source code. Day 56's actual decision is one level up: given one monorepo,
does `docker-compose.yml` become the integration contract, or does each component ship its
own Dockerfile and leave composition as an exercise for the reader? A Dockerfile per
component proves that component builds in isolation; it proves nothing about whether
`agent-benchmark-runner`'s container can actually reach the `traceforge` collector it's
supposed to benchmark against, or whether Redpanda's topic names match what
`tool-call-analyzer` expects. A single root compose file that wires all four together,
with the CLI-only components under a `--profile tools` flag so they don't block on
`docker compose up`, is the thing a user can actually run and see fail (or pass) as one
system.

The honest engineering tradeoff, not just a rhetorical one: `agent-benchmark-runner` had
zero `cmd/` entrypoint through Day 55 — it was a library only, exercised entirely through
`go test`. Today's `pkg/subprocess` + `cmd/traceforge` work exists *because* the compose
file needed something runnable to point a `benchmark:` service at. Packaging decisions are
not free of implementation debt: choosing "compose file as integration contract" forced a
real feature (a CLI, and the process-group-kill bug fix that came with wrapping a shell
command safely) that a docs-only, four-separate-repos world would never have surfaced.

Sections: the packaging question every multi-component platform answers whether or not it
says so out loud (one clone/one command, or N clones/N docs pages) | why the monorepo
choice from Day 44 only solved half the problem, and what compose solves that a
per-component Dockerfile alone doesn't | the concrete cost this decision imposed —
agent-benchmark-runner needed a real CLI to have anything to containerize | the honest gap:
no Docker daemon was available to actually run the composed stack end to end in this
environment, so the integration claim is validated by `docker compose config`, not yet by
`docker compose up`.

## Attr-box DS analogy

A shipping container versus a pallet of loose boxes: loose boxes (four separate repos)
each survive the trip fine on their own, but nothing about them proves they'll stack
together at the destination — that's a property of the container (the compose file), not
of any one box.

## Diagram

One Mermaid diagram: four component boxes (traceforge, agent-replay-engine,
agent-benchmark-runner, tool-call-analyzer) each with an arrow into one
"docker-compose.yml" box, which fans out to "core services" (collector, redpanda,
clickhouse) and "tools profile" (replay, benchmark, analyzer). Max 8 nodes, labels ≤6
words, required init block from CLAUDE.md §4.5.
