# JARVIS AI Workflow & Routing System

**Purpose:** Document how JARVIS routes tasks across 11 LLM providers, manages AI operations, handles failures, tracks costs, and optimizes for both quality and efficiency. This is the authoritative guide to the AI layer.

**Last Updated:** 2026-07-02  
**Owner:** JARVIS Operational Manager  
**Status:** Living Document

---

## 1. Task Classification System

Every request to JARVIS is classified into one of 7 task types. Classification determines which LLM provider handles the request.

### Task Types & Routing

```
┌─ CODE (Software Development)
│  ├─ Primary: Claude Sonnet 5
│  ├─ Fallback 1: DeepSeek Coder
│  ├─ Fallback 2: GPT-4o
│  └─ Why: Code quality and correctness > speed
│
├─ REASONING (Complex Analysis)
│  ├─ Primary: Claude Opus 4.8
│  ├─ Fallback 1: GPT-4o
│  ├─ Fallback 2: Gemini 1.5 Pro
│  └─ Why: Multi-step reasoning and inference
│
├─ STRATEGY (Business Decisions)
│  ├─ Primary: Claude Opus 4.8
│  ├─ Fallback 1: GPT-4o
│  └─ Why: Strategic thinking requires deep reasoning
│
├─ ANALYSIS (Data & Insight)
│  ├─ Primary: Claude Opus 4.8
│  ├─ Fallback 1: GPT-4o
│  ├─ Fallback 2: Gemini 1.5 Pro
│  └─ Why: Accuracy over speed
│
├─ RESEARCH (Knowledge Synthesis)
│  ├─ Primary: Gemini 1.5 Pro
│  ├─ Fallback 1: GPT-4o
│  ├─ Fallback 2: Claude Sonnet
│  └─ Why: Broad knowledge cutoff + cost-efficiency
│
├─ FAST (Speed Priority)
│  ├─ Primary: DeepSeek Flash
│  ├─ Fallback 1: Llama 3.3 (70B via Groq)
│  ├─ Fallback 2: GPT-4o Mini
│  └─ Why: Ultra-low cost + acceptable quality, speed critical
│
└─ LONG_CONTEXT (200k+ tokens)
   ├─ Primary: Gemini 1.5 Pro (2M context)
   ├─ Fallback 1: Kimi-K2 (200k context)
   ├─ Fallback 2: Claude Sonnet (200k context)
   └─ Why: Must support massive context windows
```

### Classification Rules

**CODE Detection:**
- Contains: code snippets, refactoring requests, debugging, algorithm design
- Keywords: "write code", "function", "class", "implement", "bug", "optimize"
- Trigger: Any GitHub issue, pull request, or code file reference

**REASONING Detection:**
- Contains: "why", "explain", "analyze", "evaluate", "compare"
- Requires: Multi-step logical analysis
- Complexity: 5+ inference steps

**STRATEGY Detection:**
- Contains: business decisions, roadmap, pricing, partnerships, pivots
- Keywords: "should we", "opportunity", "threat", "positioning", "market"
- Trigger: Captain involved or decisions > $100k impact

**ANALYSIS Detection:**
- Contains: data queries, trend identification, metrics, reporting
- Keywords: "what is", "how much", "breakdown by", "trending"
- Data scope: 10k+ data points or complex aggregations

**RESEARCH Detection:**
- Contains: exploratory questions, synthesis of multiple sources
- Keywords: "research", "study", "survey", "literature", "discovery"
- Scope: Broad knowledge synthesis, not just retrieval

**FAST Detection:**
- Contains: simple transformations, formatting, categorization
- Keywords: "convert", "extract", "parse", "categorize", "list"
- Time critical: Expected response <500ms

**LONG_CONTEXT Detection:**
- Input tokens: >100,000 tokens estimated
- Document: Full PDF analysis, entire book chapter, 100+ page document
- Scope: Entire codebase analysis, exhaustive search

---

## 2. LLM Provider Configuration

### 11 Supported Providers

| Provider | Model | Cost/1M Tokens | Quality | Speed | Context | Reliability |
|----------|-------|----------------|---------|-------|---------|-------------|
| **Anthropic** | Claude Opus 4.8 | $15 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 200k | 99.9% |
| **Anthropic** | Claude Sonnet 5 | $3 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 200k | 99.9% |
| **OpenAI** | GPT-4o | $5 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 128k | 99.8% |
| **Google** | Gemini 1.5 Pro | $3.50 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 2M | 99.7% |
| **DeepSeek** | DeepSeek V3 | $0.27 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 64k | 99.5% |
| **DeepSeek** | DeepSeek Flash | $0.27 | ⭐⭐ | ⭐⭐⭐⭐⭐ | 64k | 99.5% |
| **Groq** | Llama 3.3 (70B) | $0.59 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 8k | 99.6% |
| **Mistral** | Large | $0.81 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 128k | 99.5% |
| **Moonshot (Kimi)** | Kimi-K2 | $1 | ⭐⭐⭐ | ⭐⭐⭐ | 200k | 99% |
| **ZhipuAI** | GLM-4 | $0.50 | ⭐⭐⭐ | ⭐⭐⭐ | 128k | 98% |
| **NVIDIA** | NIM | $2 | ⭐⭐⭐ | ⭐⭐⭐ | 64k | 98% |

### Provider Health Monitoring

**Health Check Interval:** Every 30 seconds  
**Signals Monitored:**
- Response latency (alert if >5s for FAST requests)
- Error rate (alert if >1%)
- Rate limit status (track usage vs. quota)
- Model availability (check if model is deprecated or unavailable)

**Health Status Enum:**
- ✅ **HEALTHY:** <1% errors, <2s latency, quota available
- ⚠️ **DEGRADED:** 1-5% errors, 2-5s latency, quota 70%+ utilized
- ❌ **UNAVAILABLE:** >5% errors, >5s latency, or rate limited

**Automatic Degradation Policy:**
```
Provider HEALTHY          → Route 100% of requests
Provider DEGRADED         → Route 50% of requests, failover 50%
Provider UNAVAILABLE      → Route 0%, failover all requests
Provider RECOVERING       → Increase load gradually (10% per minute)
```

---

## 3. Request Routing Flow

### Step-by-Step Routing Process

```
┌─ User Request Arrives
│  └─ Extract: task_type, priority, timeout, context
│
├─ Task Classification
│  └─ If unclear: Ask user or default to REASONING
│
├─ Select Primary Provider
│  └─ Look up in routing table for task_type
│
├─ Check Provider Health
│  ├─ If HEALTHY → Route request
│  ├─ If DEGRADED → Route to fallback
│  └─ If UNAVAILABLE → Skip to fallback
│
├─ Generate Provider-Specific Prompt
│  └─ Adapt prompt to provider capabilities/limitations
│
├─ Rate Limit Check
│  ├─ Check quota: requests/minute, tokens/day
│  ├─ If available: Allow request
│  └─ If blocked: Queue or failover
│
├─ Send API Request
│  ├─ Timeout: 30s (standard), 10s (FAST), 60s (LONG_CONTEXT)
│  ├─ Retries: Up to 3 attempts with exponential backoff
│  └─ Request ID: Generate UUID for tracing
│
├─ Parse Response
│  ├─ Extract: tokens_used, finish_reason, cost
│  ├─ Validate: Output matches expected format
│  └─ Error handling: Malformed responses trigger fallback
│
├─ Log to AIRequestLog
│  └─ Record: provider, model, tokens, cost, latency, tenant_id, status
│
└─ Return to User
   └─ Stream response or batch return (depends on integration)
```

### Code Example: Task Routing

**Location:** `backend/app/services/ai/router.py`

```python
class AIRouter:
    async def route_task(self, 
        task_type: TaskType,  # CODE, REASONING, STRATEGY, etc.
        prompt: str,
        tenant_id: UUID,
        priority: Priority = Priority.NORMAL,
        timeout_seconds: int = 30
    ) -> AIResponse:
        
        # 1. Get routing config for task_type
        routing = self.routing_table[task_type]
        providers = [routing.primary] + routing.fallbacks
        
        # 2. Filter by health status
        healthy_providers = [p for p in providers 
                            if self.health_check.is_healthy(p)]
        
        if not healthy_providers:
            # All providers down - emergency mode
            return AIResponse(
                error="All providers unavailable",
                status="EMERGENCY_FALLBACK"
            )
        
        # 3. Try each provider in order
        for provider in healthy_providers:
            try:
                response = await self.call_provider(
                    provider=provider,
                    prompt=prompt,
                    timeout=timeout_seconds,
                    max_retries=3
                )
                
                # 4. Log the call
                await self.cost_tracker.log_call(
                    tenant_id=tenant_id,
                    provider=provider.name,
                    model=response.model,
                    tokens_used=response.tokens,
                    cost_usd=response.cost,
                    latency_ms=response.latency_ms
                )
                
                return AIResponse(
                    content=response.content,
                    provider=provider.name,
                    tokens=response.tokens,
                    cost_usd=response.cost,
                    latency_ms=response.latency_ms
                )
            
            except ProviderError as e:
                # Log failure, try next provider
                self.logger.warning(
                    f"Provider {provider.name} failed: {e}",
                    extra={"request_id": request_id}
                )
                continue
        
        # Should not reach here
        raise AllProvidersFailedError()
```

---

## 4. Cost Optimization Strategy

### Intelligent Provider Selection

**Rule 1: Match Provider to Task Complexity**
```
Task Complexity         Primary Provider        Cost/Response
─────────────────────────────────────────────────────────────
Simple (categorize)     DeepSeek Flash          $0.0001
Medium (analysis)       Claude Sonnet           $0.0025
Complex (reasoning)     Claude Opus             $0.0075
Strategic (thinking)    Claude Opus + Opus 4.8  $0.0100
```

**Rule 2: Prefer Cheap Providers for Equivalent Quality**
```
If DeepSeek produces acceptable output for task_type → use DeepSeek
If Groq Llama (99¢/M tokens) ≈ Claude Sonnet (3¢/M) → use Groq
```

**Rule 3: Batch Similar Requests**
```
If 10 customers need "categorize this lead" → batch process
Send all 10 to Gemini 1.5 (cheapest batch processor)
Cost: $0.0003 × 10 = $0.003 (vs $0.001 each = $0.010)
Savings: 70%
```

**Rule 4: Long Context When Relevant**
```
If document > 100k tokens AND task_type = RESEARCH
→ Use Gemini 1.5 Pro (2M context) in single call
Cost: ~$0.15 for entire document
Alternative: Chunk into 5 × 200k calls to Claude = $0.375
Savings: 60% + faster
```

### Cost Tracking & Attribution

**Real-time Cost Tracking:**
```
For every API call:
  tenant_id          → Which client to bill
  provider           → Anthropic, OpenAI, DeepSeek, etc.
  model              → claude-opus, gpt-4o, deepseek-v3
  tokens_used        → input + output tokens
  cost_estimate_usd  → Provider API cost × (1 + markup)
  created_at         → Exact timestamp for daily aggregation
```

**Cost Aggregation:**
```
SELECT 
  DATE(created_at) as day,
  provider,
  SUM(cost_estimate_usd) as daily_cost,
  COUNT(*) as request_count,
  AVG(latency_ms) as avg_latency
FROM ai_request_log
WHERE tenant_id = {tenant_id}
GROUP BY 1, 2
ORDER BY 1 DESC
```

**Monthly Invoice Generation:**
```
AI Usage (raw costs):     $1,200.00  ← Actual provider costs
Markup (40%):             $480.00    ← Aliyar operations + margin
─────────────────────────
Total AI Costs:           $1,680.00

+ Base Retainer:          $4,000.00  ← Fixed service cost
─────────────────────────
Total Monthly Bill:       $5,680.00
```

---

## 5. Failure Handling & Resilience

### Circuit Breaker Pattern

**State Machine:**
```
┌─ CLOSED (healthy)
│  ├─ Normal request routing
│  ├─ Error count < threshold (5 errors/minute)
│  └─ On threshold: Switch to OPEN
│
├─ OPEN (failing)
│  ├─ Stop routing to this provider
│  ├─ All requests failover to next provider
│  ├─ Monitor recovery (health check every 5s)
│  └─ If recovers: Switch to HALF_OPEN
│
└─ HALF_OPEN (recovering)
   ├─ Allow 10% of requests to provider
   ├─ If healthy: Switch to CLOSED
   └─ If still failing: Switch back to OPEN
```

**Example: OpenAI Rate Limit**
```
Time 0s:  Request to GPT-4o succeeds
Time 5s:  Request to GPT-4o rate limited (429)
Time 10s: Error count = 2, OK
Time 15s: Error count = 5 → Circuit OPEN
Time 20s: All GPT-4o requests failover to Claude Sonnet
Time 25s: Health check shows OpenAI recovering
Time 30s: Allow 1 test request to GPT-4o → succeeds
Time 35s: Health check 10 tests → all succeed → Circuit CLOSED
         Normal routing to GPT-4o resumes
```

### Automatic Retry Strategy

**Retry Rules:**
```
Error Type              Retries    Delay          Backoff
───────────────────────────────────────────────────────────
Network timeout         3          1s, 2s, 4s     Exponential
Rate limit (429)        5          5s, 10s, 20s   Exponential
Temporary error (5xx)   3          1s, 2s, 4s     Exponential
Invalid input (4xx)     0          N/A            (Don't retry)
Token limit exceeded    0          N/A            (Switch provider)
```

**Example Retry Flow:**
```
Request to Claude → Timeout
  ├─ Wait 1s
  ├─ Retry to Claude → Timeout
  ├─ Wait 2s
  ├─ Retry to Claude → Timeout
  └─ Switch to fallback (GPT-4o) → Success
Total latency: ~5s
Customer never sees error (fallback is transparent)
```

### Error Handling Strategy

**Tier 1: Silent Failover (No Error to User)**
```
Primary provider fails → Automatically use fallback
Example: Claude Opus timeout → GPT-4o handles request
User never knows: Request succeeds, cost is tracked, all transparent
```

**Tier 2: Degraded Response (Warning but Usable)**
```
All providers slow → Return partial response with cache
Example: All LLMs taking >10s → Return cached previous response
User knows: "Showing cached result from 2 hours ago; live update in progress"
```

**Tier 3: User-Facing Error (Retry & Escalate)**
```
All providers unavailable > 10 minutes → Error to user
Example: Stripe/OpenAI/Gemini all down (rare)
User action: Retry, or contact support
Internal action: Auto-escalate to Captain via Slack/SMS
```

---

## 6. Performance Optimization

### Request Batching

**When to Batch:**
- Multiple independent requests of same type
- Requests can tolerate 1-5 second delay
- Cost savings > latency cost

**Batching Strategy:**
```
System detects: 50 lead categorization requests in queue
    ├─ Estimated tokens/request: 100 input + 20 output
    ├─ Single request cost: $0.0018 (Claude Sonnet)
    ├─ Batch cost (50 requests): $0.055 (single Gemini 1.5 call)
    ├─ Individual cost total: $0.09
    └─ Savings: 40%

Action: Batch process all 50 in one call
Response time: +2 seconds (batching delay)
Cost saved: $0.035
ROI: 17.5x the latency cost
```

**Batch Processing Conditions:**
- Minimum batch size: 10 items
- Maximum wait time: 5 seconds (don't hold requests indefinitely)
- Provider support: Must support batch/structured output
- Suitable providers: Gemini 1.5, Claude, GPT-4o

### Caching Strategy

**Cache Layers:**

1. **Request-Level Cache** (5 minutes)
   - Identical request → identical response
   - Example: "What is Aliyar's pricing?" asked twice in 5min
   - Skip LLM call, return cached response
   - Cost saved: 100%

2. **Semantic Cache** (24 hours)
   - Similar requests → similar answers
   - Example: "What is Aliyar's pricing?" vs "How much does Aliyar cost?"
   - Embed both, check cosine similarity >0.95
   - If similar: Return cached response with flag "cached_similar"
   - Cost saved: 100%

3. **Response Prediction Cache** (24 hours)
   - Common answers pre-computed
   - Example: "What are your hours?" → Always 9AM-6PM IST
   - No LLM needed, instant response
   - Cost saved: 100%

**Cache Invalidation:**
```
If customer updates their pricing:
  → Invalidate /pricing cache entries
  → Next query re-computes

If new product launched:
  → Invalidate /product queries
  → Next query fetches fresh data
```

### Token Optimization

**Prompt Compression:**
```
Original prompt: 500 tokens
Compressed prompt: 300 tokens
Cost reduction: 40%
Quality impact: <1%

Techniques:
- Remove examples (customer knows format)
- Abbreviate instructions (use bullets vs prose)
- Summarize context (not full transcript)
```

**Output Optimization:**
```
Requested: Full essay (1,000+ tokens)
Actual needed: Summary (100 tokens)

Cost reduction: 90%

Technique: Ask for summary upfront, not essay then summarize
```

---

## 7. AI Operations Monitoring

### Real-Time Metrics

**Dashboard: System Health**
```
Provider Status
  ├─ Claude Opus: ✅ HEALTHY (500 req/hr, 2% cost of capacity)
  ├─ GPT-4o:      ✅ HEALTHY (300 req/hr, 5% cost of capacity)
  ├─ Gemini 1.5:   ⚠️ DEGRADED (100 req/hr, 85% cost of capacity)
  ├─ DeepSeek:    ✅ HEALTHY (1000 req/hr, 1% cost of capacity)
  └─ Groq:        ✅ HEALTHY (5000 req/hr, unlimited)

Cost Summary (Today)
  ├─ Claude: $12.50
  ├─ OpenAI: $8.75
  ├─ DeepSeek: $0.30
  ├─ Gemini: $5.20
  └─ Total: $27.25 (est)

Task Distribution
  ├─ CODE: 25% (Claude)
  ├─ REASONING: 20% (Claude Opus)
  ├─ ANALYSIS: 15% (Claude)
  ├─ FAST: 30% (DeepSeek)
  └─ RESEARCH: 10% (Gemini)
```

### Cost Analysis

**Daily Cost Report:**
```
Date: 2026-07-02

Provider        Requests    Tokens      Cost    %        Change
────────────────────────────────────────────────────────────────
Claude Opus        1,200    2.5M      $37.50    38%      ↑5%
Claude Sonnet      2,800    3.2M      $9.60     10%      ↓2%
GPT-4o             1,000    1.8M      $9.00     9%       →
DeepSeek V3        5,000    4.1M      $1.11     1%       ↑10%
Gemini 1.5         2,200    5.5M      $19.25    20%      ↓3%
Groq Llama            800    0.8M      $0.47     <1%      ↑15%
Mistral              300    0.4M      $0.32     <1%      →
────────────────────────────────────────────────────────────────
TOTAL             13,300   18.3M     $77.25   100%

Efficiency Metrics:
  ├─ Avg cost/request: $0.0058
  ├─ Avg tokens/request: 1,376
  ├─ Avg cost/token: $0.00000422
  └─ vs. last week: ↓3% (improved by switching more to DeepSeek)
```

### Performance Optimization Opportunities

**System recommends:**
1. **Switch 200 RESEARCH requests to DeepSeek** (from Gemini)
   - Estimated savings: $2.50/day = $912.50/year
   - Quality impact: Low (both can handle research)
   - Action: Adjust routing weights

2. **Batch 50+ requests during off-hours**
   - Estimated savings: $1.20/day = $438/year
   - Latency impact: +2 seconds (acceptable for background jobs)
   - Action: Implement batch scheduler

3. **Use cached responses for 30% of requests**
   - Estimated savings: $23.25/day = $8,486.25/year
   - Accuracy: No loss (responses are deterministic)
   - Action: Enable semantic cache for common queries

---

## 8. Multi-Provider Orchestration

### Provider Coordination During Outages

**Scenario: OpenAI API Down**

```
Time 0:00  OpenAI service page shows 100% availability
           (Actually, internal issue not yet reported)

Time 0:05  JARVIS health check detects 15% error rate on GPT-4o
           Circuit breaker opens (state → OPEN)

Time 0:06  JARVIS health check: Claude Opus healthy
           → All GPT-4o requests redirect to Claude Opus
           → Cost increase: +15% (more expensive provider)

Time 0:15  OpenAI reports incident on status page
           → Captain receives SMS alert

Time 0:30  OpenAI health checks show recovery (<1% errors)
           → Circuit breaker moves to HALF_OPEN
           → 10% of requests attempt GPT-4o
           → All succeed

Time 1:00  Circuit breaker fully CLOSED
           → Normal routing to GPT-4o resumes
           → Cost returns to baseline

Total Impact:
  - Customer requests: 100% success (zero failures)
  - Latency: +200ms average (due to fallback)
  - Cost: +$1.50 (premium fallback provider during outage)
  - Downtime: 0 minutes (transparent failover)
```

---

## 9. AI Workflow Examples

### Example 1: Lead Qualification (FAST Task)

**Input:** Lead profile (company name, industry, employee count)  
**Output:** ICP score (0-100) + qualification recommendation

**Routing:**
```
1. Classify: FAST (simple categorization)
2. Primary: DeepSeek Flash ($0.27/M tokens)
3. Context: Keep prompt <200 tokens
4. Parallel batch: 50 leads in single call
5. Cost: $0.0002 per lead
```

### Example 2: Strategic Business Analysis (STRATEGY Task)

**Input:** Market research + competitive data  
**Output:** Strategic recommendation (pricing, positioning, go-to-market)

**Routing:**
```
1. Classify: STRATEGY (business decision)
2. Primary: Claude Opus 4.8
3. Context: Full market data + historical decisions
4. Prompting: Multi-turn conversation, refinement loops
5. Cost: $0.015-0.050 per analysis
```

### Example 3: 200k-Token Document Analysis (LONG_CONTEXT Task)

**Input:** 500-page technical specification (200k tokens)  
**Output:** Executive summary + recommendations

**Routing:**
```
1. Classify: LONG_CONTEXT (>100k tokens)
2. Primary: Gemini 1.5 Pro (2M context window)
3. Fallback: Kimi-K2 (200k context)
4. Cost: $0.15 (single call vs $0.40 if chunked)
5. Speed: 8 seconds (vs 30 seconds if chunked)
```

---

## 10. Cost Transparency & Billing

### Customer-Facing Cost Dashboard

**API Endpoint:** `/api/v1/billing/costs/summary/{tenant_id}`

```json
{
  "tenant_id": "794d9b02-2dd6-49f0-b5c1-9f7c0b3af4b1",
  "period_days": 30,
  "total_cost_usd": 2100.00,
  "avg_daily_usd": 70.00,
  "daily_breakdown": [
    {
      "date": "2026-07-02",
      "total_cost_usd": 75.00,
      "by_provider": {
        "claude": 45.00,
        "openai": 20.00,
        "deepseek": 10.00
      }
    }
  ]
}
```

**Real-time Cost Monitoring:**
- Update frequency: Every 1 minute
- Granularity: Per provider, per day
- Transparency: Customer sees exact costs before invoicing
- Optimization suggestions: Automated recommendations

---

**Document Authority:** JARVIS AI Operations  
**Last Updated:** 2026-07-02  
**Next Review:** 2026-08-02  
**Maintained by:** AI Routing & Cost Optimization Team
