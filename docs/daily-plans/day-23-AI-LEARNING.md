# Day 23 — AI Learning Blog Plan

## Title: Day 23 — Evaluations as Event Streams
## Subtitle: Eval harnesses are Kafka topics with scores
## Series: AI Learning · Day 23 of 150
## Hook: "LLM-as-judge output is just another event type — store it like you store metrics."

## Core frame
Evaluations are not a test suite you run before deploy. They are a continuous stream of scored events emitted alongside production inference. Treat them as a Kafka topic.

## DS analogy (mandatory, per DS engineer framing)
A CI test suite gates a build. An evaluation stream monitors a production process. The difference is not technical — it is temporal. CI is point-in-time; eval streams are continuous. The right mental model is not "test runner" but "anomaly detector with a quality signal."

## Sections
1. Why batch eval suites lie (point-in-time scoring over samples misses distribution shift)
2. Eval events as a first-class schema: `eval_run_id`, `model_id`, `prompt_hash`, `judge_model`, `score`, `latency_ms`, `timestamp`
3. LLM-as-judge as a producer: one inference call produces one scored event
4. Kafka topic design: `llm-eval-events` with partition key = `model_id:tenant_id` for per-model scoring windows
5. ClickHouse aggregations: rolling 1h quality score by model version, joined to `inference_events` for cost-quality tradeoff

## attr-box examples
- Team: "LLM-as-judge is a probability estimator, not a ground truth oracle"
- Mine: "Storing eval scores in the same pipeline as inference events was the insight that made quality-cost tradeoff visible"

## Mermaid diagrams
1. Inference → eval producer → Kafka llm-eval-events → ClickHouse
2. ClickHouse join: inference_events × eval_events × flag_audit → cost-quality-flag report
