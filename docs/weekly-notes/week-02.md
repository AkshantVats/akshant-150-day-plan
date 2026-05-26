# Week 02 notes

## OSS-01 (Day 11)

| Item | Link |
|------|------|
| Issue | https://github.com/vectordotdev/vector/issues/25455 |
| Maintainer ping | https://github.com/vectordotdev/vector/issues/25455#issuecomment-4540643593 |
| Upstream PR | https://github.com/vectordotdev/vector/pull/25496 |
| Fork branch | `fix/memory-enrichment-counters-total-suffix` on `AkshantVats/vector` |
| Commit | `3133039` — `fix(metrics): add _total suffix to memory enrichment counters` |

**Outcome:** Renamed three memory enrichment table counter metrics to end with `_total` per Vector instrumentation spec (`docs/specs/instrumentation.md`). Breaking change for direct scrapers; noted in PR body.

**Proof:** `cargo test -p vector-common` — 29 passed, 0 failed.

**Out of scope honored:** No G-09 / `ai_anomalies`; no `run_chaos.sh` re-run.
