# Day 56 — Experience Blog Plan

**Title**: Org Boundaries — Public Platform Identity
**Subtitle**: Wayfair · leading teams · ownership
**Employer context**: `docs/context/pricing-system-architecture.md` (Cost Aggregation
Layer's per-team ownership boundaries) + `docs/context/resume-extracted.md` (role scope).
Relevant facts only:
- Wayfair, Bengaluru, Nov 2024 – Mar 2026, Sr. Software Engineer III — led PAS (Price
  Adjustment System) and Pricing, Promotions & Discounts teams simultaneously.
- Architecture doc: every subsystem in the Cost Aggregation Layer is explicitly labeled
  with an owning team — UCMS/SPCS ("Team: Supplier Cost and Promotions" / "Team: PPD
  Supplier Cost"), Hydros/EdenReader ("Team: Estimated Costs"), PAS Cost Adjustments
  ("Team: PAS"), ScheduledReader ("Team: Total Cost"). A production system at this scale
  makes ownership an explicit, visible property of the architecture diagram itself, not an
  implicit assumption.
- Do NOT invent org-chart specifics, headcounts, or reporting lines beyond "led PAS and
  Pricing Promotion Teams" from the resume line and the "Team:" labels the architecture
  doc already documents.

**Format**: `patterns` (per `docs/BLOG-FORMAT-MIX.md`'s signal table: "leading teams" is
listed explicitly as a `patterns` trigger). Last-10 Experience posts: rollout(46),
deep-dive(47), design(49), patterns(50), design(51), design(52), patterns(53), design(54),
feature(55) — `patterns` appears twice in ten, well under any incident-heavy pattern, and
matches today's topic better than forcing a design/tradeoff frame onto what is genuinely a
synthesized-lesson post about ownership signaling, not one decision with rejected
alternatives.

**Bridge**: creating a `traceforge-dev` GitHub org (rather than leaving four components as
personal-account repos) is how public OSS work signals "maintained product," the same way
Wayfair's architecture diagram signals ownership by labeling every subsystem with a team,
not leaving it implicit. Today's code in `agent-benchmark-runner` — its first CLI, wired
into a root `docker-compose.yml` alongside the other three TraceForge components — is what
an org actually has to back up: a "platform," not four weekend repos that happen to share
a theme.

## Angle

At Wayfair, every box in the Cost Aggregation Layer's architecture diagram carries a
"Team:" label — UCMS is Team Supplier Cost and Promotions, ScheduledReader is Team Total
Cost, PAS Cost Adjustments is Team PAS. That's not decoration; it's how a large
organization keeps four independently-evolving subsystems from becoming four
unaccountable black boxes. When a Total Cost number looks wrong, the diagram itself tells
you which team's pager to page. Leading PAS and Pricing Promotions simultaneously meant
living on both sides of exactly that boundary: two roadmaps, two on-call rotations, one
person accountable for how they fit together.

Four solo repos under a personal GitHub account have the opposite problem: nothing in
`github.com/akshantvats/agent-replay-engine` signals that it's part of anything, or that
anyone is accountable for keeping it working alongside the other three. A `traceforge-dev`
org — even a small one, even for a solo project — is the equivalent move at a much smaller
scale: it says these four repos are one platform with one maintainer, not four unrelated
side projects that happen to share a README template.

But a name on an org page doesn't make four repos a platform any more than a "Team:"
label alone would make Wayfair's Cost Aggregation Layer coherent if the four systems it
labels couldn't actually be operated together. The org boundary has to be backed by
something a user can run. That's what today's code is: agent-benchmark-runner's first CLI
(it had no `cmd/` at all through Day 55 — library only) and a root `docker-compose.yml`
that boots all four components together. The org signals "platform"; the compose file is
what makes that true instead of aspirational.

## Section Outline

1. **What a "Team:" label buys you** — ground this in the architecture doc's explicit
   per-subsystem ownership labels (UCMS, Hydros, PAS Cost Adjustments, ScheduledReader),
   and what leading two of those teams simultaneously actually meant day to day.
2. **Four repos, no boundary** — the honest starting state: agent-replay-engine,
   agent-benchmark-runner, tool-call-analyzer, and traceforge as four separate personal
   repos with no signal that they're one platform or that anyone maintains the seams
   between them.
3. **The org is the label; the compose file is the proof** — a `traceforge-dev` org name
   is cheap to create and easy to leave hollow; the unified `docker-compose.yml` (all four
   components, one command) is the part that has to actually be true, the same way
   Wayfair's team labels only mean something because ScheduledReader really does aggregate
   what UCMS, Hydros, and PAS Cost Adjustments produce.
4. **What still isn't proven** — honest gap: no Docker daemon was available to actually
   run `docker compose up` end to end in the environment this was built in, so the compose
   file is validated (`docker compose config`) but not yet proven to boot cleanly — the
   same gap as claiming a team boundary without yet paging through an incident on it.

## Diagram

One Mermaid diagram: four labeled component boxes (traceforge, agent-replay-engine,
agent-benchmark-runner, tool-call-analyzer) inside one dashed "traceforge-dev" boundary
box, each with an arrow into one "docker compose up" box. Max 8 nodes, labels ≤6 words,
required init block from CLAUDE.md §4.5.
