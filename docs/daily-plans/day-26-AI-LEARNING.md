# Day 26 — Fine-Tuning vs RAG vs Prompting — Infra Cost View
## Blog Outline — AI Learning Series

---

## Header Block

| Field | Value |
|---|---|
| Series | AI Learning · Day 26 of 150 |
| Day | 26 |
| Topic | Fine-Tuning vs RAG vs Prompting — Infra Cost View |
| Subtitle | When to buy GPUs vs buy vectors vs buy nothing |
| Hook | "Staff engineers pick the cheapest path that meets SLO — not the coolest paper." |
| DS Analogy | Choosing between fine-tuning, RAG, and prompting is like choosing between buying a specialized lathe, renting a warehouse catalogue, or just hiring someone who already knows the answer. The right choice depends entirely on how often you need the capability and what it costs to maintain each option over time. |
| Target URL | `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-26-fine-tuning-rag-prompting-infra-cost.html` |
| Thread Connection | infra-ai-streaming's cost attribution model (ClickHouse + resolved_model_id) gives you the data to make this decision empirically — not from a blog post. |

---

## HTML File Target Block

All of the following must use "Day 26" — never an episode ordinal.

| HTML Location | Required Text |
|---|---|
| `<title>` | `Day 26 — Fine-Tuning vs RAG vs Prompting — Infra Cost View \| AI Learning Series` |
| Accent chip | `AI Learning · Day 26 of 150` |
| `<h1 class="post-title">` | `Day 26 — Fine-Tuning vs RAG vs Prompting — Infra Cost View` |
| Meta line | `AI Learning · Day 26 of 150` |
| Series footer | `Day 26 of 150 — Fine-Tuning vs RAG vs Prompting — Infra Cost View` |

---

## Voice Reminders

- Write in first person throughout: "I hit this wall when...", "Here's what surprised me...", "What I didn't expect was..."
- Maximum 3 sentences per paragraph. If a paragraph hits 4 sentences, split it.
- One concrete analogy per major concept — grounded in physical or everyday objects, never another software concept.
- Every section ends with a "so what" sentence that lands the practical takeaway.
- No bullet lists as a substitute for prose. Lists only for ordered steps where prose is genuinely harder to follow.

---

## Opening Hook

**Purpose:** Pull the reader into the core tension — there are three ways to inject knowledge into an LLM, and the engineering decision between them is almost entirely a cost accounting problem, not a capability problem.

### Paragraph 1 (The incident frame)
Open with the hook verbatim: "Staff engineers pick the cheapest path that meets SLO — not the coolest paper." Expand: six months into working with LLM-backed systems, I watched a team spend three months fine-tuning a 7B-parameter model to answer product questions — GPU time, CUDA engineering, checkpoint management, the full stack — when a 200-line RAG pipeline with a $20/month vector database would have produced equivalent answer quality for the specific task. The fine-tuning project felt like engineering. The RAG approach felt like plumbing. The output for the user was identical. The cost difference was two orders of magnitude.

### Paragraph 2 (What the rest of this post covers)
This post is a cost accounting framework for choosing between the three main knowledge injection approaches: prompting (put the knowledge in the context window directly), RAG (retrieve relevant knowledge chunks at request time), and fine-tuning (bake the knowledge into the model weights). Each has a different cost structure, a different maintenance burden, and a different failure mode. The framework doesn't tell you which to pick — it gives you the questions that produce the right answer for your specific system.

### Concrete Non-Software Analogy
A restaurant kitchen faces the same decision when adding a new dish. It can train the chef to cook it from memory (fine-tuning), keep a laminated reference card in the kitchen for the chef to consult (RAG), or just list the dish only when the chef who already knows it is working that day (prompting). The right choice depends on how often the dish is ordered, how complex it is, and how much it costs to train, store, or schedule accordingly.

### Core Frame
The core frame for this post: prompting is free but token-limited, RAG trades vector infrastructure cost for token savings, and fine-tuning trades GPU training cost and ongoing maintenance for the lowest per-request cost at very high volume. The decision is a volume and consistency trade-off, not a capability trade-off.

---

## Section 1 — Prompting: The Cheapest Path When It Works

**Purpose:** Establish what prompting is good for, where its limits are, and why it's the right default to reach for first.

### Key Points

**Point 1 — Prompting is zero infrastructure.**
System prompts, few-shot examples, and chain-of-thought instructions are text. They cost nothing to deploy, nothing to maintain, and nothing to update. You change the system prompt and the behavior changes on the next request. There is no training pipeline, no vector store, no embedding model, no index refresh. For tasks where the required knowledge fits in the context window and the latency of larger context windows is acceptable, prompting is strictly dominant.

**Point 2 — Context window size is the hard limit.**
The fundamental constraint on prompting is that everything you need the model to know must fit in the context window at request time. For a 128k token context window, that's roughly 100,000 words — a short novel. For many enterprise knowledge bases, product catalogues, or codebase-grounded QA tasks, the relevant knowledge is larger than any context window. When the knowledge that matters doesn't fit, prompting breaks.

**Point 3 — Retrieval quality degrades in long contexts.**
Even when the knowledge technically fits in the context window, models become less reliable at retrieving specific facts from very long contexts. This is the "lost in the middle" problem — information near the beginning and end of a context window is retrieved more reliably than information in the middle. A 100k-token context with the relevant answer buried at position 50k is less reliable than a 4k-token context where the answer is in the first 1k tokens.

**Point 4 — When to use prompting.**
Prompting is the right choice when: the task is well-defined and the required context is small; you're prototyping and need to iterate quickly; the knowledge you're injecting changes frequently (a model retrained monthly can't keep up with a knowledge base updated hourly); or you need zero operational overhead.

**"What I didn't expect" insight**
What I didn't expect was how often prompting is sufficient for production use cases. The engineering instinct is to reach for a more sophisticated solution. In practice, the majority of tasks I've seen that were solved with RAG or fine-tuning were also solvable with carefully constructed prompts — the more sophisticated solution was chosen because it felt more like engineering, not because it produced better outcomes.

**Concrete Non-Software Analogy**
Prompting is like briefing a consultant before a meeting — you hand them the relevant documents, they read them before walking in, and they answer questions based on what you just gave them. It works well when the briefing packet is small and well-organized. It breaks down when the briefing packet is a filing cabinet.

**"So what" sentence**
Prompting should be your first attempt for any new task — not because it's simpler, but because the cost of being wrong is zero and the cost of over-engineering with RAG or fine-tuning is measurable in infrastructure and maintenance hours.

---

## Section 2 — RAG: Buying a Catalogue Instead of a Memory

**Purpose:** Explain RAG's cost model, when it wins over prompting, and what the actual infrastructure footprint is.

### Key Points

**Point 1 — RAG is a retrieval problem dressed as an AI problem.**
Retrieval-Augmented Generation is architecturally simple: chunk your knowledge base into fixed-size or semantic chunks, embed each chunk with an embedding model, store the embeddings in a vector database, and at query time embed the question and retrieve the top-k most similar chunks. Those chunks are then injected into the context window as a smaller, more relevant subset of the full knowledge base. The LLM never sees the whole knowledge base — it sees the three to ten chunks most relevant to this specific query.

**Point 2 — The infrastructure is real but manageable.**
RAG requires three components that prompting doesn't: an embedding model (to convert text to vectors), a vector database (to store and query embeddings), and an indexing pipeline (to keep the embeddings fresh when the knowledge base changes). At moderate scale, the cost is $20–$200/month for managed vector store (Pinecone, Weaviate, pgvector on Postgres) plus the embedding API cost (~$0.0001/1k tokens for most providers). The indexing pipeline is an engineering investment — typically a few days to build, a few hours/week to maintain.

**Point 3 — RAG wins when knowledge is dynamic or large.**
RAG is the right choice when: the knowledge base is too large for the context window; the knowledge base changes frequently and you need updates to take effect immediately (re-embedding a document takes seconds; retraining a model takes days); or the task requires retrieving specific facts from a large corpus where brute-force prompting would saturate the context window.

**Point 4 — RAG's failure mode is retrieval quality, not model quality.**
Most RAG failures are retrieval failures, not generation failures. If the wrong chunks are retrieved, the model generates a hallucinated or irrelevant answer from locally plausible but globally wrong context. The debugging loop for a RAG system is: is the right content in the index? Is the embedding model capturing the relevant semantic similarity? Is the chunk size appropriate for the query type? These are information retrieval problems, not machine learning problems.

**"What I didn't expect" insight**
What I didn't expect was how much chunk design matters. The intuition is that semantic search will find the right content regardless of how it's chunked. In practice, a document chunked at 512 tokens with 50-token overlap produces dramatically better retrieval results than the same document chunked at 2048 tokens with no overlap, for question-answering tasks. The chunk design is where most of the work actually lives.

**Concrete Non-Software Analogy**
RAG is like a research librarian. You don't need to read the entire library before the meeting — you ask the librarian to pull the three most relevant papers. The librarian's filing system (the vector index) determines how quickly and accurately they can find the right material. A badly organized filing system means the librarian pulls the wrong papers, and the meeting goes poorly.

**"So what" sentence**
RAG is the right default when prompting breaks — it trades a manageable infrastructure investment for the ability to ground the model in a knowledge base that's too large or too dynamic for the context window.

---

## Section 3 — Fine-Tuning: When Nothing Else Works

**Purpose:** Establish the actual use cases where fine-tuning is justified, and the full cost model including the hidden costs.

### Key Points

**Point 1 — Fine-tuning changes model behavior, not model knowledge.**
The common misconception about fine-tuning is that it's a way to inject new factual knowledge into a model. In practice, fine-tuning is better understood as a way to change model behavior — to adjust tone, format, reasoning style, or domain-specific patterns. A fine-tuned model doesn't necessarily "know" more facts than its base model. It behaves more consistently in a specific domain. This distinction matters because most tasks people try to solve with fine-tuning are actually knowledge retrieval tasks that RAG solves more effectively.

**Point 2 — The cost model is front-loaded and ongoing.**
Fine-tuning a 7B-parameter model for a domain-specific task costs $50–$500 in GPU time depending on dataset size and training duration (at cloud GPU rates). But training cost is the smallest line item. Data curation — collecting, cleaning, and formatting a high-quality training dataset — typically costs 10–50x the training compute in engineering hours. Evaluation — measuring whether the fine-tuned model actually performs better on the target task — requires a test harness and a human evaluation budget. And every time the base model provider releases a new version, the fine-tuning work must be partially or fully repeated.

**Point 3 — Fine-tuning wins at high-volume, stable tasks.**
Fine-tuning is genuinely the right choice when: the task is well-defined, high-volume, and unlikely to change; the behavior change required cannot be achieved reliably through prompting; the per-request cost reduction at scale justifies the training investment; and the team has the operational capacity to maintain a custom model checkpoint. Code completion assistance, structured data extraction from fixed-format documents, and domain-specific classification are tasks where fine-tuning consistently outperforms prompting and RAG at scale.

**Point 4 — The hidden cost is model versioning.**
When the base model provider releases a new version — GPT-4o to GPT-4o-mini, Llama 3 to Llama 3.1 — the fine-tuned checkpoint based on the old version does not automatically benefit from the improvements. You have a choice: stay on the old version (missing improvements), or re-run the fine-tuning pipeline on the new base model (paying the full training cost again). This is the ongoing maintenance cost that never appears in the initial "should we fine-tune?" calculation.

**"What I didn't expect" insight**
What I didn't expect was how often fine-tuning is proposed as the solution to a prompting problem. I've seen three separate projects where the proposed solution was "fine-tune a model to do X" and the actual solution was "write a better system prompt and add three examples." The better prompt took two hours. The fine-tuning project would have taken three months. The projects that legitimately required fine-tuning were a small minority — and they all had one thing in common: they needed a behavioral change that no amount of prompting could reliably produce.

**Concrete Non-Software Analogy**
Fine-tuning is like custom manufacturing a specialized tool for a specific job. A custom lathe built for one specific part runs faster and more accurately than a general-purpose lathe for that exact part. But it costs ten times as much to build, it can't adapt to a different part without significant rework, and every time the part design changes, the tool needs to be rebuilt. General-purpose tools win unless the volume and consistency of the specific task justifies the custom manufacturing cost.

**"So what" sentence**
Fine-tuning is the right answer for a narrow class of high-volume, stable, behavior-change tasks — and the engineers who reach for it as the default solution to every knowledge injection problem are paying a ten-month amortization cost for a problem a better prompt would have solved in two hours.

---

## Section 4 — The Decision Framework

**Purpose:** Give a concrete, opinionated decision procedure — not a comparison chart, but a sequence of questions with answers that point to a decision.

### Key Points

**The framework is four questions:**

First question: does the task require knowledge that fits in the context window and changes slowly? If yes, start with prompting and measure. Don't build RAG or fine-tune until you've tried a well-crafted prompt with few-shot examples and measured its failure rate on a representative eval set. Most teams skip this step because it doesn't feel like engineering.

Second question: does prompting fail because of context window size or dynamic knowledge? If yes, build RAG. The vector store investment is the cheapest form of "the model knows about our stuff." The indexing pipeline is the only ongoing engineering cost.

Third question: does RAG fail because the retrieval quality is insufficient for the required precision, even with optimized chunking and embedding models? Now you have a harder choice — either improve the RAG pipeline (reranking, hybrid search, better chunking) or accept that fine-tuning is required.

Fourth question: is the task volume and stability high enough to justify fine-tuning's training and maintenance cost? Calculate the cost crossover point: at what request volume does the per-request cost savings from fine-tuning exceed the amortized training + maintenance cost? Below that volume, fine-tuning loses on economics regardless of quality.

**The default path:** Prompting → RAG → Fine-tuning. You should have a strong reason to skip each step before advancing to the next. "Fine-tuning feels more robust" is not a strong reason. "Prompting and RAG both failed at X% accuracy on the eval set and fine-tuning achieves Y%" is a strong reason.

**"What I didn't expect" insight**
What I didn't expect was how rarely teams measure the failure rate on a representative eval set before deciding to fine-tune. The decision is usually made based on intuition or peer pressure from a paper that demonstrated fine-tuning gains on a different task. Without an eval set, you can't know whether the task actually requires fine-tuning or whether prompting would have been sufficient.

**Concrete Non-Software Analogy**
This decision framework is like a heating system diagnostic. First question: is the thermostat set correctly? (Prompting.) Second question: is the radiator clear and the pipes unblocked? (RAG — clear the path between knowledge and the model.) Third question: is the furnace actually working? (Fine-tuning — the base capability needs adjustment.) You don't replace the furnace before checking the thermostat. Most problems are solved at the cheapest layer.

**"So what" sentence**
The decision between prompting, RAG, and fine-tuning is an economics calculation with a default order — and the default order is the cheapest path first, with a measured eval set at each step before advancing to the next.

---

## Section 5 — Infra Cost View: What the Numbers Actually Look Like

**Purpose:** Give concrete cost numbers for each approach, not as absolutes but as ratios that hold across different scales.

### Key Points

**Prompting cost model:**
Cost = (input tokens + output tokens) × price per token. At gpt-4o pricing, a 4k-token context window request costs roughly $0.01. At 100k requests/day, that's $1,000/day or ~$30,000/month. Optimizing the prompt to reduce token count is direct cost reduction — every 1,000 tokens removed from the average context saves $0.01 per request.

**RAG cost model:**
Cost = (embedding cost) + (vector store cost) + (reduced context window cost). Embedding cost: $0.0001/1k tokens for ada-002; a 100k-document knowledge base embedded once costs ~$1. Monthly re-embedding on change: depends on update rate, typically $10–$100/month. Vector store: $20–$500/month depending on index size and managed vs self-hosted. Reduced context window: RAG typically injects 2k–4k tokens of retrieved context instead of a 20k–50k token full knowledge base, saving 80–95% of context tokens. At scale, the RAG infrastructure cost is dominated by the context token savings.

**Fine-tuning cost model:**
Training: $50–$500 one-time per training run. Data curation: 10–50x training cost in engineering hours. Evaluation harness: 2–5 days engineering. Inference: fine-tuned models typically use smaller base models (7B vs 70B), reducing per-request cost by 4–10x. Break-even point: at the reduced per-request cost, calculate how many requests it takes to recover the training + data curation investment. For a $5,000 total investment and $0.005/request savings, break-even is at 1,000,000 requests. Below that volume, fine-tuning is more expensive than prompting over the model's lifetime.

**The cost crossover table (illustrative ratios, not absolutes):**
```
Requests/day | Prompting cost | RAG cost | Fine-tuning cost
1,000        | $10/day        | $12/day  | $16/day (amortized)
10,000       | $100/day       | $80/day  | $30/day (amortized)
100,000      | $1,000/day     | $600/day | $100/day (amortized)
```
The crossover points are approximate — they depend on the specific task, model, and cost of the training data. But the shape of the curve is consistent: prompting wins at low volume, RAG wins at medium volume, fine-tuning wins at very high volume with stable tasks.

**"What I didn't expect" insight**
What I didn't expect was how much the data curation cost dominates fine-tuning economics. Every fine-tuning project I've seen has underestimated this. The team budgets for GPU time and ignores the engineering hours required to collect, clean, format, and validate a training dataset. A realistic fine-tuning project budget allocates 70% of total cost to data, 10% to training, and 20% to evaluation and iteration.

**Concrete Non-Software Analogy**
The cost crossover between prompting and fine-tuning is like the decision between renting a car and buying one. Renting is more expensive per trip for frequent travelers. Buying is more expensive upfront and requires maintenance, insurance, and depreciation. The crossover point — the number of trips at which buying becomes cheaper than renting — is calculable. Below that crossover, rent. Above it, buy. The mistake is buying a car before you know how often you'll need it.

**"So what" sentence**
Running the cost crossover calculation before committing to fine-tuning is not optional — it's the single most useful thing you can do before starting a three-month fine-tuning project that would have cost less as a well-tuned prompt.

---

## Section 6 — The infra-ai-streaming Connection

**Purpose:** Connect the cost framework to the LensAI observability stack — specifically how resolved_model_id and ClickHouse enable empirical cost comparison between approaches.

**Thread connection:** infra-ai-streaming's cost attribution model (ClickHouse + resolved_model_id) gives you the data to make the fine-tuning vs RAG vs prompting decision empirically.

### Key Points

**Point 1 — The decision needs data, not intuition.**
The framework in Section 4 is useful for making the initial choice. But the ongoing decision — should we migrate from RAG to fine-tuning as volume grows? Should we simplify from fine-tuning back to prompting as the task changes? — requires empirical data. Specifically, it requires per-request cost data broken down by model version and context size.

**Point 2 — resolved_model_id closes the attribution loop.**
`resolved_model_id` in infra-ai-streaming's inference events table is the field that makes this possible. Each inference event records not just the model family but the exact model version — `gpt-4o-2024-08-06` vs `ft:gpt-4o-2024-08-06:my-org::abc123`. When you run a cost attribution query against ClickHouse grouped by `resolved_model_id`, you can see the exact cost distribution across your prompting, RAG, and fine-tuned model variants. The query is the same as any other cost attribution query — the fine-tuned model is just another `resolved_model_id` value.

**Point 3 — The query that answers "is fine-tuning worth it?"**
```sql
SELECT
  resolved_model_id,
  count() AS request_count,
  sum(prompt_tokens) AS prompt_tokens,
  sum(completion_tokens) AS completion_tokens,
  sum(total_cost_usd) AS total_cost
FROM inference_events
WHERE toDate(ingested_at) BETWEEN '2026-06-01' AND '2026-06-30'
GROUP BY resolved_model_id
ORDER BY total_cost DESC
```
This query shows the monthly cost by model version. Compare the fine-tuned model's row (lower per-request cost, potentially) against the base model + RAG rows (higher per-request cost, potentially). Add the amortized training cost to the fine-tuned model's row. If the fine-tuned model is cheaper after amortization, fine-tuning was worth it. If it's more expensive, you know the answer.

**Point 4 — The loop is empirical, not theoretical.**
The cost framework in Sections 1–5 tells you which path is likely cheaper before you have data. The ClickHouse query tells you which path is actually cheaper after you have data. The right engineering process is: use the framework to make the initial choice, collect 30–90 days of real cost data via infra-ai-streaming, then re-evaluate the choice empirically. Most teams skip the re-evaluation step and lock in an architecture decision based on pre-production estimates that turned out to be wrong.

**"What I didn't expect" insight**
What I didn't expect was that the most valuable output of building infra-ai-streaming's cost attribution model was not the dashboards. It was the conversations it enabled. "Here's the cost by model version for the last 30 days" is a factual statement that ends debates that would otherwise run for weeks on intuition and conference blog posts.

**Concrete Non-Software Analogy**
A fuel economy monitor in a car is the right analogy. You can estimate whether hypermiling or a hybrid engine would save more money based on EPA ratings and driving patterns. But the fuel economy monitor tells you what's actually happening with your specific car, on your specific routes, under your specific driving habits. The monitor is the infra-ai-streaming cost attribution layer. The EPA ratings are the framework from Sections 1–5.

**"So what" sentence**
Building cost observability into your LLM infrastructure from day one converts the fine-tuning vs RAG vs prompting decision from a one-time architectural guess into an ongoing empirical optimization — and that's worth more than any amount of upfront analysis.

---

## Mermaid Diagrams

### Diagram 1 — Cost vs Volume: Three Approaches

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
    A["Start: new task"] --> B{"Fits context window?"}
    B -->|"Yes"| C["Try prompting first"]
    B -->|"No"| D["Build RAG"]
    C --> E{"Meets eval threshold?"}
    E -->|"Yes"| F["Ship it"]
    E -->|"No"| D
    D --> G{"Volume high + stable?"}
    G -->|"Yes"| H["Evaluate fine-tuning"]
    G -->|"No"| F
```

**Caption:** The decision sequence starts at the cheapest layer (prompting) and advances only when the current layer fails to meet the evaluation threshold. Volume and stability gate the fine-tuning decision — high-volume, stable tasks are the only cases where fine-tuning's upfront investment can be recovered.

### Diagram 2 — Cost Attribution Loop via infra-ai-streaming

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
    A["Inference request"] --> B["resolved_model_id written"]
    B --> C["Kafka ingest"]
    C --> D["ClickHouse inference_events"]
    D --> E["Cost by model query"]
    E --> F["Fine-tune vs RAG decision"]
    F --> A
```

**Caption:** resolved_model_id written at evaluation time flows through Kafka into ClickHouse. The cost-by-model query closes the loop — it converts the theoretical fine-tuning vs RAG decision framework into an empirical comparison against real traffic data.

---

## Post Metadata JSON Block

```json
{
  "day": 26,
  "series": "ai-learning",
  "slug": "day-26-fine-tuning-rag-prompting-infra-cost",
  "title": "Day 26 — Fine-Tuning vs RAG vs Prompting — Infra Cost View",
  "subtitle": "When to buy GPUs vs buy vectors vs buy nothing",
  "date": "2026-06-11",
  "tags": ["fine-tuning", "rag", "prompting", "llm-cost", "ai-infrastructure", "clickhouse"],
  "url": "https://akshantvats.github.io/Profile/blog/series/ai-learning/day-26-fine-tuning-rag-prompting-infra-cost.html",
  "coverImage": "blog/assets/covers/day-26-fine-tuning-rag-prompting-infra-cost.png",
  "ogImage": "blog/assets/og/day-26-fine-tuning-rag-prompting-infra-cost.png",
  "seriesFooter": "Day 26 of 150 — Fine-Tuning vs RAG vs Prompting — Infra Cost View"
}
```

---

## Format Diversity Check

Before writing the final HTML post, count the last 10 posts by format:
- incident / feature / design / deep-dive / rollout / patterns

**This post's format: deep-dive (cost framework walkthrough with decision procedure).**

If deep-dive count is ≥ 4 in the last 10 posts, reframe as a "patterns" post — narrative arc shifts from "here's the cost framework" to "here are the three patterns I've seen, and when each one fails." Reference `docs/BLOG-FORMAT-MIX.md` from `akshant-150-day-plan` for current counts.

---

## Self-Review Checklist

Run through every item before `git add`. Record the count in commit message: `Self-review: N issues found and fixed.`

- [ ] **Unexplained jargon**: RAG, FNV-1a, resolved_model_id, vector database each get a 1-sentence definition on first use
- [ ] **Paragraph length**: every paragraph ≤ 3 sentences — scan each `<p>` tag manually
- [ ] **HTML validity**: count `<div` opens vs `</div>` closes — must match exactly
- [ ] **No motion tags**: zero `</motion.div>` occurrences
- [ ] **No nested anchors**: no `<a>` inside another `<a>`
- [ ] **Diagram labels**: no label text exceeds 6 words
- [ ] **Diagram node count**: each diagram ≤ 8 nodes
- [ ] **Mermaid init block**: present verbatim in both diagrams
- [ ] **No placeholder URLs**: no `example.com`, `TODO`, `localhost`, `placeholder`
- [ ] **Cover image path**: `blog/assets/covers/day-26-fine-tuning-rag-prompting-infra-cost.png` referenced
- [ ] **Day 26 in all four locations**: `<title>`, `<h1>`, accent chip, meta line
- [ ] **Series footer text**: `Day 26 of 150 — Fine-Tuning vs RAG vs Prompting — Infra Cost View`
- [ ] **Voice check**: first person throughout — no passives like "one might expect"
- [ ] **Analogy check**: each major section has exactly one physical/everyday analogy
- [ ] **"So what" check**: every section ends with a "so what" sentence
- [ ] **pre-push-check.sh**: `bash -e .agent/pre-push-check.sh blog/series/ai-learning/day-26-fine-tuning-rag-prompting-infra-cost.html` exits 0
