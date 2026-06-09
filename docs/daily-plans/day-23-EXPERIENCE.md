# Day 23 — Experience Blog Plan

## Title: OSRM at 5000 Events/sec — When ETA Becomes Infrastructure
## Subtitle: Delivery Hero · route recompute budget
## Series: Experience · Day 23 of 150
## Employer: Delivery Hero

## Hook
At 5k+ route updates per second, OSRM stops being a routing library and becomes a resource allocation problem.

## Key employer facts (from context docs)
- 1M+ daily orders
- 5k+ real-time route updates/sec (from resume: "5k map adjustments/sec")
- End-to-end rider tracking using OSRM
- AWS EKS (10k+ concurrent requests, zero downtime)
- Route Service + Route Consumers on EKS
- Order SQS → Route Consumers → OSRM cluster

## Sections
1. What 5k/sec looks like as an infrastructure problem (not just a routing one)
2. The route recompute budget — not every event needs a fresh route
3. OSRM as a stateful cluster: the map data load, warm-up time, rolling restarts
4. The queue depth / recompute rate balance: KEDA on Route Consumer lag (connecting to prior posts)
5. What I learned about capacity planning for route engines

## Attribution boundary
- Delivery Hero team built the Route Service and OSRM cluster
- My contributions: scaling Route Consumers on EKS, lag-based autoscaling, KEDA integration (referenced in Day 20 post)
- "I worked on the consumer layer" not "I built OSRM"

## Bridge to Day 23 AI
CRD + Helm for flags is how platform teams let app engineers self-serve rollouts without SSH — same separation of concerns that makes OSRM updates deployable without touching the consumer code.
