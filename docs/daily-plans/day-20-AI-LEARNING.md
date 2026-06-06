# Day 20 — AI Learning Post Outline
## "Day 20 — Prompt Engineering as Infra Optimization"
### Prompt cache and prefix reuse in dollars per million requests
### AI Learning · Day 20 of 150

**Series**: AI Learning
**Day**: 20 of 150
**Subtitle**: Prompt cache and prefix reuse in dollars per million requests
**Hook**: Calculate savings at 1M req/day — that's the slide your PM actually reads.

**Target blog URL**: `https://akshantvats.github.io/Profile/blog/series/ai-learning/day-20-prompt-engineering-infra-optimization.html`

---

## HTML File Target
`blog/series/ai-learning/day-20-prompt-engineering-infra-optimization.html`

**Title tag**: `Day 20 — Prompt Engineering as Infra Optimization | AI Learning Series`
**Accent chip**: `AI Learning · Day 20 of 150`
**H1**: `Day 20 — Prompt Engineering as Infra Optimization`
**Meta line**: `AI Learning · Day 20 of 150`
**Series footer**: `Day 20 of 150 — Prompt Engineering as Infra Optimization`

---

## Hook / Thesis

**Core thesis**: Prompt engineering is mostly discussed as a craft for getting better outputs. That framing undersells it. A well-structured prompt at 1M requests/day is a cost engineering decision worth $2,000–$15,000/month depending on your model tier. The PM reads the cost slide; the engineer writes the prompt. They should both be in the same room.

**Opening sentence**: "I started thinking about prompt engineering as a cost lever when I calculated how much a single extra sentence in a system prompt was costing us at scale — and the number was larger than I expected."

---

## Section 1 — What Prompt Caching Is (and Isn't)

**Key points**:
- Most major LLM APIs now support prompt caching: if the beginning of your prompt matches a previous request exactly, the provider reuses internal KV cache state and charges a reduced rate for those cached tokens.
- Anthropic Claude: cached input tokens cost 10% of normal input price; cache write (first time the prefix is cached) costs 125% of normal input price. Cache entries persist for up to 5 minutes.
- OpenAI: automatic prompt caching on input context >1,024 tokens; cached token discount is 50%.
- The constraint: caching only works on a **shared prefix**. If the first part of every request is identical (system prompt, few-shot examples, reference documents), those tokens can be cached. The variable part (the user query) is always freshly processed.
- What prompt caching is NOT: it doesn't cache the output. Each response is generated fresh. It only caches the computation of turning your static context into key-value attention vectors.

**Concrete analogy**: A dictionary lookup. The dictionary (your system prompt) is the same for every search. The first lookup requires loading the whole book. Every subsequent lookup reuses the loaded index — you pay only to look up the new word, not to re-read the book.

**What I didn't expect**: cache TTL is short — 5 minutes on Claude, auto-refreshed per Anthropic docs if the same prefix is used within the window. A low-traffic application that processes one request every 10 minutes gets zero cache benefit. Caching is a reward for volume.

**So what**: Prompt caching is free money if your request volume is high enough — and "high enough" is lower than most engineers think.

---

## Section 2 — The Dollar Math at 1M Requests/Day

**Purpose**: This is the PM slide. Make it concrete with real pricing numbers (current as of June 2026 — note to morning agent: verify against Anthropic pricing page before publishing).

**Setup**:
- Application: LLM-powered code review assistant
- System prompt: 2,000 tokens (coding standards, few-shot examples, output format instructions) — constant across all requests
- User query: 200 tokens average (code snippet + question) — variable per request
- Total input per request: 2,200 tokens
- Volume: 1,000,000 requests/day
- Model: Claude Sonnet (representative mid-tier pricing)

**Without caching**:
- Daily input tokens: 1M × 2,200 = 2.2B tokens
- At $3.00/MTok (input): $6,600/day → **$198,000/month**

**With caching** (assuming 90% cache hit rate after warmup):
- Cache hits (90%): 1M × 0.9 = 900k requests → pay for 200 tokens each = 180M tokens at $3.00/MTok = $540/day
- Cache misses (10%): 1M × 0.1 = 100k requests → pay full 2,200 tokens = 220M tokens at $3.00/MTok = $660/day
- Cache write cost (on miss, first cache): 100k × 2,000 tokens × $3.75/MTok = $750/day (125% of normal for cache write)
- Total: $540 + $660 + $750 = **$1,950/day → $58,500/month**
- **Savings: $139,500/month (70% reduction)**

**The lever**: the larger your system prompt relative to your user query, the more you save. A 2,000-token system prompt with a 200-token query is a 10:1 ratio — ideal for caching. A 100-token system prompt with a 2,000-token query is a 1:20 ratio — minimal caching benefit.

**Important caveat**: these numbers use representative pricing. Always verify against the current Anthropic pricing page before basing budget decisions on them. Pricing changes.

**Concrete analogy for the ratio**: A bus route. The bus (system prompt) travels the same 20-mile route every trip. Each passenger (user query) boards for a different stop — maybe 1 mile. If you charge per mile, the bulk of the cost is the fixed route. Caching is buying a monthly bus pass for the fixed route and paying per-stop only for the variable leg.

**So what**: A prompt optimization that reduces your system prompt by 500 tokens at 1M req/day is worth approximately $45,000/year at Sonnet pricing. That's not a writing exercise — that's an engineering project.

---

## Section 3 — Prefix Reuse: Structuring Prompts for Cache Hits

**Purpose**: The tactical section — how to actually structure prompts to maximize cache hit rate.

**Key points**:
- The cache key is the exact byte sequence of the cached prefix. A single character difference (trailing space, different punctuation) = cache miss. Treat the system prompt as immutable configuration, versioned and deployed like code.
- Structure rule: **static content first, variable content last**. System prompt → reference documents → few-shot examples → user query. Never interleave static and variable content.
- Multi-turn conversations: include the system prompt once (top of the conversation), then alternating human/assistant turns. On each new turn, the entire conversation history up to the current turn is the input. As conversation grows, early turns become the cached prefix — but they grow too, so cache benefits diminish per-turn.
- The conversation length trap: at turn N, your input is: system prompt (2k) + N previous turns (variable). Once the conversation exceeds the cache TTL window or varies significantly per user, per-conversation caching stops being useful. Solution: summarize and compress long conversations before they exceed a threshold.
- Explicit cache breakpoints (Claude `cache_control`): Anthropic's API supports explicit `cache_control: {type: "ephemeral"}` markers in the message array. Place them after your system prompt and after large reference document blocks to tell the API where to cache.

**Code pattern (Python, Anthropic SDK)**:
```python
client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": SYSTEM_PROMPT,  # 2,000 tokens — static
            "cache_control": {"type": "ephemeral"}
        }
    ],
    messages=[
        {"role": "user", "content": user_query}  # 200 tokens — variable
    ]
)
```

**What I didn't expect**: the `cache_control` marker must go on the last content block you want cached. If you have three blocks (intro + examples + format instructions), the marker goes on the third block. The cache includes everything *up to and including* the marked block. First-time readers miss this detail and wonder why caching isn't triggering.

**Concrete analogy**: A recipe book for a restaurant kitchen. The book (system prompt) sits on the counter — always open to the same page. The order ticket (user query) changes per customer. The cook doesn't re-read the whole book for each ticket. Put the order ticket at the bottom so the book stays open at the same place.

**So what**: Prompt caching is not automatic unless your prompt structure places variable content at the end — architect it correctly once and the savings compound across every request.

---

## Section 4 — Beyond Caching: Prompt Compression

**Purpose**: Caching is the most powerful lever, but token count reduction compounds with it.

**Key points**:
- Prompt compression reduces the total token count, reducing cost regardless of cache hit rate. Tools: LLMLingua (Microsoft), selective context filtering, manual trimming.
- The 80/20 rule for system prompts: most system prompts have 20% of their tokens carrying 80% of the behavioral signal. The rest is hedging, repeated instructions, and filler. Ruthless editing pays dividends.
- Structured formats over prose: `JSON schema` for output format takes fewer tokens than a paragraph describing the desired format. `Bullet list of constraints` takes fewer tokens than explaining each constraint in prose with rationale.
- Example: a prose instruction like "Please ensure that when you respond to the user, you always begin your response with a clear and concise summary of your main finding before elaborating on supporting details" = 40 tokens. Equivalent instruction: `Output format: {summary: string, details: string[]}` = 12 tokens. Same behavioral effect; 70% fewer tokens.
- At 1M requests/day, 28 tokens saved = 28M tokens/day = 28B tokens/month at $3.00/MTok input = $84,000/year saved. From editing one instruction.

**The compression-quality tradeoff**: aggressive compression can reduce output quality. Always A/B test compressed prompts against baselines on your eval set before deploying to production. Don't compress blindly.

**Concrete analogy**: A legal contract vs. a term sheet. Both convey the same deal. The contract is 80 pages; the term sheet is 3. For a first internal review, the term sheet communicates everything relevant at a fraction of the reading time. For a court, you need the contract. Know your use case before you compress.

**So what**: Token count is a variable you control — and every token is a cost you choose to pay at every request. Review your system prompt with the same scrutiny you'd apply to an N+1 query.

---

## Section 5 — The Request Volume Threshold: When Does This Matter?

**Purpose**: Calibrate when these optimizations are worth the engineering investment.

**Key points**:
- At 1,000 requests/day: optimizing a 2,000-token system prompt saves ~$0.18/day at Sonnet pricing. Not worth an engineering sprint.
- At 100,000 requests/day: same optimization saves ~$18/day = ~$540/month. Worth a half-day of work.
- At 1,000,000 requests/day: ~$5,400/month savings from prompt compression alone; another $139,500/month from caching. Worth a team sprint.
- The crossover point: roughly 10k–50k requests/day is where prompt optimization transitions from "nice to have" to "line item in the budget."
- Multi-model cost comparison: the per-token price difference between Claude Haiku, Claude Sonnet, and Claude Opus is 10x–100x. Before optimizing token count on a cheaper model, check whether a faster/cheaper model meets your quality bar — the model choice is usually a larger lever than prompt compression.

**Concrete analogy**: Optimizing fuel efficiency on a bicycle vs. a cargo truck. A cyclist can squeeze out 5% more miles-per-calorie through technique. A truck fleet operator who cuts fuel consumption by 5% saves $2M/year across the fleet. Same percentage gain, wildly different dollar impact. Know your fleet size before deciding which lever to pull.

**So what**: Do the math before the optimization. Two minutes with a calculator will tell you whether prompt engineering is worth one sprint or one afternoon.

---

## Section 6 — The Infra Engineer's Mental Model

**Purpose**: Reframe prompt engineering as a systems engineering discipline.

**Key points**:
- Prompt → input to the LLM inference pipeline. Token count → data volume. Cache hit rate → equivalent to cache hit rate in any other caching system. Cost per request → cost per API call in any other service.
- A prompt is a configuration file that executes at runtime. Version it. Review it in code review. Instrument cache hit rate as a metric alongside latency and error rate.
- The distributed systems parallel from today's Experience post: CPU utilization on Route Consumers was the wrong signal. Input token count without cache hit rate is the wrong signal for LLM cost. Both look fine on the surface while the real problem accumulates invisibly.
- A `prompt_cache_hit_rate` Prometheus metric + Grafana panel costs one afternoon to build. It will tell you whether your prompt structure is correct before you see it in the monthly AWS/Anthropic bill.
- Token budgeting: treat the context window like disk. You wouldn't write code that fills disk arbitrarily — you'd set retention policies. For LLM conversations, set a context compression policy: summarize after N turns, drop oldest turns beyond M tokens.

**The thread back to the tracer**: ebpf-llm-tracer captures the raw HTTP request to the LLM API — including the full prompt body. That means you can compute prompt token count, cache control markers, and response token count at the kernel level without touching the application code. The comparison table in today's README is the argument for this visibility. Cache hit rate is one of the metrics it enables.

**Concrete analogy**: Bandwidth billing on a CDN. A DevOps engineer who caches static assets aggressively pays 90% less bandwidth cost than one who serves everything from origin. The application teams say "we write code, not cache configs." The infra engineer says "cache configs are code." Prompt engineering is the LLM equivalent of cache policy management — infra owns it whether they claim it or not.

**So what**: Add `prompt_cache_hit_rate` to your LLM observability stack before the first production request. It will pay for the engineering time within weeks.

---

## Section 7 — Bridge to Day 20 Code

**Draft bridge**:
Today's ebpf-llm-tracer README comparison table argues that eBPF gives you visibility into token-level traffic without SDK changes. Prompt cache hit rate is exactly the kind of metric that requires that visibility — it's not exposed by default in application logs, but it's in the response headers from every API call. The tracer captures those headers. The README is the buyer's guide that explains why. The prompt cache math above is the CFO's guide that explains what that visibility is worth. Same product, two audiences, one afternoon's work on the README.

---

## Mermaid Diagrams

### Diagram 1 — Prompt Structure for Maximum Cache Hit Rate

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
    SP["System Prompt\n2000 tokens · static\ncache_control: ephemeral"]
    FEW["Few-shot Examples\noptional · static\ncache_control: ephemeral"]
    REF["Reference Docs\nif needed · static\ncache_control: ephemeral"]
    UQ["User Query\n200 tokens · variable\nno cache marker"]
    RESP["LLM Response\nalways fresh"]

    SP --> FEW --> REF --> UQ --> RESP

    style SP fill:#1e3a5f,color:#f0f4f8
    style FEW fill:#1e3a5f,color:#f0f4f8
    style REF fill:#1e3a5f,color:#f0f4f8
    style UQ fill:#4a90d9,color:#0a1a2e
    style RESP fill:#0d2137,color:#f0f4f8
```

### Diagram 2 — Cost at 1M Requests/Day: With vs. Without Caching

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
    subgraph nocache ["No Caching"]
        NC_IN["2,200 tokens input\nper request"]
        NC_COST["$6,600/day\n$198k/month"]
        NC_IN --> NC_COST
    end
    subgraph cache ["With Caching (90% hit rate)"]
        C_HIT["Cache hit: 200 tokens\n(user query only)"]
        C_MISS["Cache miss: 2,200 tokens\n(10% of requests)"]
        C_WRITE["Cache write: +25%\non missed tokens"]
        C_COST["$1,950/day\n$58.5k/month"]
        C_HIT --> C_COST
        C_MISS --> C_COST
        C_WRITE --> C_COST
    end
    SAVE["70% cost reduction\n~$140k/month saved"]
    nocache --> SAVE
    cache --> SAVE
```

---

## Post Metadata

```json
{
  "slug": "day-20-prompt-engineering-infra-optimization",
  "title": "Day 20 — Prompt Engineering as Infra Optimization",
  "subtitle": "Prompt cache and prefix reuse in dollars per million requests",
  "series": "ai-learning",
  "day": 20,
  "date": "2026-06-08",
  "tags": ["PromptEngineering", "PromptCaching", "LLMCost", "AIInfrastructure", "TokenOptimization"],
  "coverImage": "/blog/assets/covers/day-20-prompt-engineering-infra-optimization.png",
  "url": "/blog/series/ai-learning/day-20-prompt-engineering-infra-optimization.html"
}
```

---

## Key References (for fact-checking before publish)

- Anthropic prompt caching docs: verify cache TTL (5 min), cached token pricing (10% of input), write surcharge (125%) at time of post
- OpenAI prompt caching: verify 50% discount threshold (>1024 tokens), automatic vs explicit
- LLMLingua paper: Microsoft Research, 2023 — selective context compression
- Claude API `cache_control` parameter: Anthropic API reference, messages endpoint

**Note to morning agent**: pricing numbers in Section 2 use representative values from knowledge cutoff. Verify `claude-sonnet-4-5` input pricing at `https://www.anthropic.com/pricing` before publishing. Update the worked example with live numbers if they differ.

---

## Cover Image Notes

AI Learning cover concept: abstract visualization of a cost curve dropping sharply after a cache hit threshold — a line graph that bends at the 10k requests/day mark, showing the "crossover point" where caching becomes meaningful. Dark background, LensAI brand colors (#1e3a5f, #4a90d9).

---

## Self-Review Checklist (before pushing)

- [ ] `Day 20` appears in `<title>`, `<h1>`, accent chip, meta line, series footer
- [ ] Pricing numbers verified against live Anthropic pricing page
- [ ] Every paragraph ≤ 3 sentences
- [ ] At least one concrete non-software analogy per major concept: dictionary lookup (caching), bus route (ratio), recipe book (prefix placement), legal contract vs term sheet (compression tradeoff), bicycle vs truck (scale threshold), CDN bandwidth (infra mental model)
- [ ] Every section ends with a "so what" sentence
- [ ] Both Mermaid diagrams have the correct init block
- [ ] No nested `<a>` tags
- [ ] Div open/close count balanced
- [ ] No `</motion.div>` tags
- [ ] No placeholder URLs (example.com, TODO, localhost)
- [ ] Code snippet (Python, cache_control) is syntactically valid
- [ ] Thread connection to Day 20 code work present in closing bridge
- [ ] Cover image exists at `blog/assets/covers/day-20-prompt-engineering-infra-optimization.png`
- [ ] `pre-push-check.sh` exits 0
- [ ] `series-index.json` updated in Profile
- [ ] Previous AI Learning post (Day 19) retrofix applied
