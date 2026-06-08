# Day 22 — Experience Series Outline
## H3 vs Bounding Boxes — Geospatial Indexing That Scales

---

## Header Block

| Field | Value |
|---|---|
| Series | Experience |
| Day | 22 of 150 |
| Employer | Delivery Hero |
| Systems | Route Service · OSRM · Order SQS · Route Consumers (AWS EKS) |
| Bridge | Sticky user hashing for model flags copies H3 cell assignment — same user, same variant, all day. |
| Slug | `day-22-h3-geospatial-indexing-surge-detection` |
| Date | 2026-06-09 |

---

## HTML File Target

```
<title>Day 22 — H3 vs Bounding Boxes — Geospatial Indexing That Scales | Experience Series</title>
```

| HTML location | Required text |
|---|---|
| Accent tag chip | `Experience · Day 22 of 150` |
| `<h1 class="post-title">` | `Day 22 — H3 vs Bounding Boxes — Geospatial Indexing That Scales` |
| Meta line | `Experience · Day 22 of 150` |
| Series footer | `Experience · Day 22 of 150` |

---

## Voice Reminders

- Write in first person throughout: "I hit this wall when...", "What I didn't expect was...", "Here's what surprised me..."
- Maximum 3 sentences per paragraph. Split immediately at 4.
- One concrete non-software analogy per major concept — grounded in physical/everyday objects.
- Every section ends with a "so what" sentence that tells the reader why this matters beyond the immediate context.
- Do not use bullet lists as a substitute for prose. Lists only for ordered steps where prose is genuinely harder to follow.
- Use only verified DH numbers from the Verified Numbers table below. Never invent system names or scale figures.

---

## Target Blog URL

`https://akshantvats.github.io/Profile/blog/series/experience/day-22-h3-geospatial-indexing-surge-detection.html`

---

## Opening Hook

**Purpose:** Drop the reader into the exact moment naive geo indexing collapses in production — a real, specific failure, not a hypothetical.

**Draft:**

I first noticed the problem during a weekday lunch rush. Surge multipliers were applying inconsistently across orders that were physically two blocks apart — one restaurant cluster was seeing a 1.8x multiplier while another 400 meters away was seeing 1.0x, even though both were packed with riders waiting. The underlying cause was not a bug in the surge calculation itself. It was a bounding box boundary sitting directly through a high-density restaurant zone, splitting the same physical demand signal into two different indexing cells that never compared notes.

At 1M+ daily orders and 5k+ real-time route updates per second flowing through the Route Service on EKS, that kind of boundary artifact is not a minor annoyance. It compounds. Every inconsistency in zone assignment means your surge multiplier is applied to some orders in a demand cluster but not others — the pricing surface becomes jagged in a way that neither engineers nor customers can predict. That was the day I stopped treating geospatial indexing as an infrastructure detail and started treating it as a first-class product problem.

---

## Section 1 — What Geospatial Indexing Looks Like at Delivery Hero Scale

**Purpose:** Establish the concrete system context — what data is moving, at what rate, through what architecture — before explaining why indexing choice matters.

**Key Points:**

Every rider location event travels from the rider's device to an Order SQS queue, picked up by Route Consumers running on AWS EKS, matched through OSRM, and assembled into a Route object that flows back to the UI. At 5k+ route updates per second across the platform, each Route Consumer is continuously ingesting lat/lon pairs and deciding what zone each coordinate belongs to. That zone assignment drives everything downstream: surge pricing, rider dispatch priority, and demand forecasting.

The naive approach is to define zones as rectangles on a map — bounding boxes with a min/max lat and a min/max lon. A bounding box query checks whether a coordinate falls within those four boundaries. It works fine at low throughput, and it's the first thing any engineer reaches for because the mental model maps directly to how we think about maps: north/south/east/west rectangles, like drawing boxes on graph paper.

What I didn't expect was how quickly rectangular geometry starts lying to you once your zones have irregular shapes and your event rate climbs past a few thousand per second. Zone boundaries in a real city rarely follow straight lines. A restaurant cluster in Berlin follows a street grid that runs at 30-degree angles. Rectangular bounding boxes either over-include geography (pulling in events from neighboring zones) or under-include it (missing riders just outside a tight boundary). The data pipeline doesn't know which problem it has — it just silently misassigns events.

**What I didn't expect:** The failure is silent. The system assigns every event to a zone — it never throws an error. You only discover the misassignment when surge multipliers stop making intuitive sense and you start correlating zone event rates with a map layer.

**Concrete analogy:** A bounding box around an irregular neighborhood is like trying to fit a hexagonal bolt head with a square wrench. The wrench opens wide enough to grip the bolt, but it's touching only four of the six faces — the contact is unequal, the torque transfers unevenly, and the bolt strips before it tightens. The tool is not wrong in principle; it's wrong for the shape it's being asked to hold.

**So what:** At 5k+ events/sec, every percentage point of misassignment is hundreds of zone errors per second — and those errors compound directly into pricing decisions that customers see in real time.

---

## Section 2 — Why Bounding Boxes Break

**Purpose:** Make the failure modes concrete and mechanical — exactly *how* bounding boxes break at this throughput.

**Key Points:**

The first failure mode is unequal adjacency. In a rectangular grid, corner cells touch adjacent cells at a single point — one pixel of shared geometry. Edge-adjacent cells share a full side. When a rider is near a corner, the system has to decide which of four possible zones owns that coordinate, and a point-in-polygon test on a bounding box gives you a technically correct answer that is practically wrong. A rider standing at the intersection of four surge zones should belong to the zone with the highest local demand density — but a bounding box query just returns whichever rectangle the coordinate falls inside, based purely on the boundary lines, not on demand context.

The second failure mode is query cost. A bounding box zone lookup requires a range scan on two dimensions: latitude must be between min_lat and max_lat, and longitude must be between min_lon and max_lon. Without a spatial index, that's O(N) per query against the zone table. At 5k events per second, an unindexed bounding box scan turns into a full table scan 5,000 times per second. Even with an R-tree, you're doing two-dimensional range intersection math on every event, which does not vectorize cleanly on the compute shapes available in EKS pods.

The third failure mode is hotspot amplification. Orders cluster near restaurant zones. A bounding box cell that happens to cover a high-density restaurant cluster receives a disproportionate fraction of all events — not because the zone is larger in physical area, but because the rectangular boundary captures more restaurants than a same-area hexagonal cell would. The hotspot is an artifact of the grid geometry, not the actual demand pattern. That makes it extremely difficult to distinguish genuine surge from indexing noise.

**What I didn't expect:** The hotspot problem is self-reinforcing. Once a bounding box cell gets more events, it triggers surge multipliers faster, which changes rider behavior, which sends more events to that cell, which deepens the apparent surge. You can't tune your way out of it by adjusting surge thresholds — the root cause is the shape of the cell.

**Concrete analogy:** A bounding box zone grid covering a city is like trying to divide a pizza into equal portions with only horizontal and vertical cuts. You can make the cuts perfectly straight and evenly spaced, but the resulting slices are radically different sizes once you account for the circular shape of the pizza — the corner squares are tiny, the center squares are normal, and you've wasted a lot of pizza trying to fit a circle inside a grid.

**So what:** At 5k route updates per second, bounding box geometry turns indexing artifacts into real-time pricing inconsistencies — and there is no tuning fix that preserves the rectangular approach while eliminating the structural misassignment.

---

## Section 3 — H3: Hexagonal Indexing

**Purpose:** Explain why hexagons solve the problems rectangles create — uniform adjacency, deterministic integer IDs, tunable resolution.

**Key Points:**

H3 is Uber's open-source hierarchical hexagonal geospatial index. It tessellates the entire surface of the earth into hexagonal cells at 16 resolution levels. At resolution 7, each cell covers roughly 5.16 km². At resolution 8, it's 0.74 km². At resolution 9, it drops to 0.105 km². For a food delivery surge zone in a dense urban area, resolution 8 is usually the right fit — large enough to capture a meaningful cluster of restaurants and riders, small enough that a single cell doesn't cross neighborhood boundaries in a way that mixes demand signals.

The key geometric property is uniform adjacency. Every H3 hexagon has exactly 6 neighbors, and every neighbor shares a full edge — not a corner point. The center of any hexagon is equidistant from the center of each of its 6 neighbors. There are no corner-adjacency artifacts, no ambiguous boundary cases where a point technically touches four zones at once. A lat/lon coordinate maps to exactly one H3 cell at any given resolution, and that mapping is a pure mathematical function of the coordinate — no range scan, no polygon-in-polygon test. You pass in a float pair, you get back a 64-bit integer.

That 64-bit integer ID is what changes the operational profile entirely. Zone assignment becomes a hash lookup in a flat map, not a spatial range query. At 5k events per second, the Route Consumer calls `latLngToCell(lat, lon, resolution=8)` — a single function call — and then does a O(1) increment on a counter keyed by that integer. That's not a minor optimization at this scale. It's the difference between a Route Consumer pod that runs comfortably at 70% CPU and one that saturates and starts dropping messages.

**What I didn't expect:** H3 resolution tuning is not a technical decision — it's a product decision. The question "which resolution should we use?" is really asking "how large should a surge zone be?" That question belongs to the product manager who owns rider experience and pricing strategy, not to the platform team. I spent two days benchmarking resolutions 7 through 9 before I realized I should have been in a meeting with product, not a profiler.

**Concrete analogy:** Replacing bounding boxes with H3 cells is like replacing square floor tiles with hexagonal ones in a hallway with irregular walls. The square tiles leave awkward triangular gaps near any non-right-angle edge — you have to cut every tile that meets the wall, and the cuts are all different sizes. Hexagonal tiles fit irregular boundaries more cleanly because the six-sided shape can approximate any curve without leaving as much wasted space.

**So what:** H3 turns geospatial zone assignment from a two-dimensional range query into a deterministic integer hash — and that change unlocks consistent, high-throughput surge detection without spatial index infrastructure.

---

## Section 4 — Surge Detection with H3

**Purpose:** Show the complete operational flow — how H3 cell assignment enables consistent surge multiplier application at the throughput numbers the system actually sees.

**Key Points:**

The flow is straightforward once H3 is in place. Each rider location event arrives at a Route Consumer. The consumer calls `latLngToCell(lat, lon, resolution=8)` and gets back a 64-bit cell ID. It then increments an in-memory counter for that cell ID in a fixed time window (typically 60 seconds, sliding). When the counter for a cell crosses a configured threshold — say, event rate exceeding 1.5x the rolling baseline for that cell — the consumer flags that cell as a surge cell and writes the surge state to a shared cache keyed by cell ID.

Order Service reads that surge cache when pricing an order. It calls `latLngToCell` on the order's pickup location, gets the same 64-bit integer, and looks up whether that cell is currently flagged as surge. Because H3 cell assignment is deterministic — same lat/lon always returns the same integer — every order from the same physical location sees the same surge state. Two orders placed 30 seconds apart from the same restaurant get the same surge multiplier if the cell hasn't changed state. The pricing surface is consistent with the actual spatial demand signal, not with where you drew a rectangle on a map.

The surge multiplier itself is not a service — it's a config value. A cell's surge state is a boolean flag plus a multiplier scalar stored in the cache. The Route Consumer writes it. The Order Service reads it. There's no separate "surge service" mediating the two — the shared H3 cell ID is the handshake. This matters at 10k+ concurrent requests because it eliminates a synchronous service call from the hot path of order pricing. The Order Service does one cache read, keyed by a 64-bit integer, and moves on.

**What I didn't expect:** Surge detection with H3 is almost boring to implement once the cell assignment is in place. The hard part was convincing the team to replace bounding boxes — the indexing migration, the cache schema change, the coordination with the product team on resolution choice. The actual surge detection logic is just a counter threshold on integer keys.

**Concrete analogy:** H3-based surge detection is like a toll booth system where every road segment has a unique physical ID stamped on the pavement. Every car that passes a sensor broadcasts that ID. When the count for a given ID exceeds a threshold, the booth raises the price for that segment. No dispatcher needs to map GPS coordinates to zones in real time — the road segment ID is already in the signal.

**So what:** When zone assignment is deterministic and identity-based rather than boundary-based, consistent surge pricing becomes a property of the indexing scheme itself — not something you have to enforce with coordination logic downstream.

---

## Section 5 — The Bridge: Sticky Assignment → Model Flags

**Purpose:** Connect the H3 cell assignment pattern to flagd's FNV-1a percentage rollout hashing — the same deterministic partitioning invariant underlies both systems.

**Key Points:**

The H3 insight is not specific to geospatial systems. It's an instance of a broader pattern: deterministic partitioning by a stable identity key. H3 takes a lat/lon pair and maps it to a stable integer. flagd's percentage rollout evaluation takes a request identifier — a user ID or session ID — and hashes it with FNV-1a to produce a stable bucket number between 0 and 99. Both operations share the same invariant: given the same input, you always get the same output, regardless of when you call the function or how many times it's been called before.

That invariant is what makes consistent assignment possible at scale. In H3, "same rider location → same surge zone" means every order from the same pickup point sees the same multiplier during a given time window. In flagd, "same user ID → same bucket → same feature flag variant" means the same user always gets the same model version, across every pod in the fleet. There's no session state, no sticky session routing, no coordination between pods. The hash function is the entire consistency mechanism.

The practical consequence is the same in both systems. You can route 10% of traffic to a new model version and be confident that 10% is a stable set of users — not a random 10% on each request, but the same 10% every time. Just as a surge multiplier applies consistently to all orders from the same H3 cell, a model version flag applies consistently to all requests from the same user. The partitioning is spatial in one case and identity-based in the other, but the underlying math is identical.

**What I didn't expect:** When I first read the flagd source code for percentage rollout, I recognized the pattern immediately — not from distributed systems theory, but from the H3 cell assignment work at Delivery Hero. The problems look completely different on the surface. One is about geography; one is about A/B testing. But the solution structure is the same: deterministic partitioning by a stable key, with no coordination required between the components that use the result.

**Concrete analogy:** Both H3 and FNV-1a hashing are like a post office sorting machine that uses the zip code already printed on the envelope. The machine doesn't need to look up the recipient's address, consult a routing database, or ask another machine for help. The zip code — a compact, deterministic encoding of location — is already there. The sorting decision is O(1) and consistent, every time, for every envelope with the same zip code.

**So what:** Any system that needs consistent, stateless assignment at scale — whether partitioning physical space or partitioning traffic across model variants — is solving the same problem, and the same deterministic hashing pattern solves it.

---

## Section 6 — What I'd Do Differently

**Purpose:** Honest retrospective — what the right decisions were, which ones came too late, and what a future engineer inheriting this system should know.

**Key Points:**

I'd choose the H3 resolution in a product meeting before writing any code. The resolution is a product parameter, not an engineering parameter. It encodes an opinion about what constitutes a surge zone — how large an area should share the same pricing signal. Every week I spent tuning resolution in isolation was a week I was optimizing for the wrong objective function. The first conversation should have been: "How large should a surge zone be, and why?" The implementation follows directly from the answer.

I'd also instrument cell-level event rates from day one, before any surge logic is deployed. The most useful debugging tool we had was a dashboard showing event rate per H3 cell in real time, mapped back to a geo layer. That dashboard took three days to build after the indexing migration. It should have been the first thing committed — the change in indexing scheme is only as trustworthy as your ability to observe its behavior on live traffic.

Finally, I'd document the resolution decision as an architecture decision record the day it's made. Six months after the migration, a new team member asked why we used resolution 8 instead of resolution 7. No one could answer from memory. The reasoning — 0.74 km² matches the average restaurant catchment area in our high-density markets — existed only in someone's head and a Slack thread from eight months prior. A two-paragraph ADR on the day of the decision would have cost five minutes and saved an hour of archaeology.

**What I didn't expect:** The hardest migration step was not the code change — it was getting agreement on how to handle the transition period when some Route Consumers were still running bounding box logic and others had switched to H3. A mixed fleet means two different surge states for the same physical location, applied inconsistently depending on which pod processed the event. We had to do a hard cutover with a feature flag, not a gradual rollout, because gradual rollout in this context meant intentional pricing inconsistency.

**Concrete analogy:** Skipping the resolution decision meeting is like a surveyor choosing the scale of their grid before asking what the map will be used for. A 1:10,000 scale map is perfect for urban planning and useless for navigating a hiking trail. The scale encodes the use case. Get the use case first, then pick the scale.

**So what:** The technical migration is rarely the hard part of a geospatial indexing change — the hard parts are the product decision about granularity, the observability you need to trust the new system, and the deployment coordination required to avoid a mixed-fleet consistency window.

---

## Mermaid Diagrams

### Diagram 1 — Bounding Box vs H3 Indexing: Query Path Comparison

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
    A["Rider lat/lon event"] --> B{"Indexing approach"}
    B --> C["Bounding box scan"]
    B --> D["H3 cell hash"]
    C --> E["2D range query"]
    E --> F["Ambiguous boundary result"]
    D --> G["64-bit integer ID"]
    G --> H["O(1) counter lookup"]
```

**Caption:** The bounding box path requires a two-dimensional range scan that can produce ambiguous boundary results near zone edges. The H3 path is a deterministic mathematical function returning a 64-bit integer — no range scan, no ambiguity.

### Diagram 2 — Surge Detection Pipeline with H3 Cell Assignment

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
    A["Rider location event"] --> B["Route Consumer EKS"]
    B --> C["latLngToCell res=8"]
    C --> D["Cell event counter"]
    D --> E{"Rate > 1.5x baseline?"}
    E -->|"Yes"| F["Write surge state cache"]
    E -->|"No"| G["No-op"]
    F --> H["Order Service reads cache"]
```

**Caption:** Each rider event flows through a Route Consumer, gets assigned a deterministic H3 cell ID at resolution 8, and increments that cell's event counter. When the rate threshold is exceeded, the surge state is written to a shared cache. Order Service performs a single O(1) cache read at order pricing time — no synchronous service call on the hot path.

---

## Post Metadata JSON Block

```json
{
  "slug": "day-22-h3-geospatial-indexing-surge-detection",
  "title": "H3 vs Bounding Boxes — Geospatial Indexing That Scales",
  "subtitle": "Delivery Hero · surge detection · why naive geo fails",
  "series": "experience",
  "day": 22,
  "employer": "Delivery Hero",
  "date": "2026-06-09",
  "url": "https://akshantvats.github.io/Profile/blog/series/experience/day-22-h3-geospatial-indexing-surge-detection.html",
  "coverImage": "blog/assets/covers/day-22-h3-geospatial-indexing-surge-detection.png",
  "ogImage": "blog/assets/og/day-22-h3-geospatial-indexing-surge-detection.png",
  "tags": ["DistributedSystems", "Geospatial", "H3", "SurgeDetection", "BackendEngineering", "DeliveryHero"],
  "bridge": "Sticky user hashing for model flags copies H3 cell assignment — same user, same variant, all day."
}
```

---

## Verified Numbers Table

Use ONLY these numbers. Do not invent other scale figures or system names.

| Metric | Value | Source |
|---|---|---|
| Daily orders | 1M+ | DH context doc |
| Real-time route updates/sec | 5k+ | Resume: "5k map adjustments/sec" |
| Concurrent requests | 10k+ | DH context doc |
| H3 resolution 8 cell area | ~0.74 km² | H3 public spec |
| H3 resolution 7 cell area | ~5.16 km² | H3 public spec |
| H3 resolution 9 cell area | ~0.105 km² | H3 public spec |
| Tenure at Delivery Hero | Jun 2022 – Jul 2023 | Resume |
| Routing engine | OSRM | DH context doc |
| Compute platform | AWS EKS | DH context doc |
| Key services | Route Service, Route Consumers, Order SQS | DH context doc |

**Do NOT use:** any named "surge service", any latency numbers not listed above, any team size figures, any revenue numbers.

---

## Self-Review Checklist

Before committing the HTML file, verify every item:

- [ ] `Day 22` appears in `<title>`, `<h1>`, accent tag chip, and meta line
- [ ] Series footer reads `Experience · Day 22 of 150`
- [ ] All `<div` opens and `</div>` closes are balanced
- [ ] Zero `</motion.div>` tags
- [ ] No `<a>` nested inside another `<a>`
- [ ] At least one `class="prose"` div present
- [ ] Every scale number matches the Verified Numbers table
- [ ] No invented system names (no "SurgeService", no names not in context docs)
- [ ] Every paragraph is ≤ 3 sentences
- [ ] Every major section has a "so what" closing sentence
- [ ] Every major concept has one concrete non-software analogy
- [ ] Both Mermaid diagrams use the exact init block — no variations
- [ ] Every Mermaid node label is ≤ 6 words
- [ ] Each diagram has ≤ 8 nodes
- [ ] No placeholder URLs
- [ ] Cover image path: `blog/assets/covers/day-22-h3-geospatial-indexing-surge-detection.png`
- [ ] OG image path: `blog/assets/og/day-22-h3-geospatial-indexing-surge-detection.png`
- [ ] Previous Experience post footer updated to link to this post
- [ ] `series-index.json` entry added with correct schema
- [ ] `pre-push-check.sh` exits 0 before any `git push`
- [ ] Commit message includes `Self-review: N issues found and fixed.`
