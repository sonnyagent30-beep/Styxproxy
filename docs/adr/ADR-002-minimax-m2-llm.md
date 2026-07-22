# ADR-002: MiniMax M2 as LLM Provider

**Date:** 2026-06-26
**Status:** Accepted
**Deciders:** Sonny (agent), Dannion

---

## Context

Styxproxy uses an LLM to parse customer WhatsApp messages and extract intent. We need to decide which LLM to use — this is a foundational choice that affects cost, latency, reliability, and code.

Initial approach was Ollama (local, free). Ollama works but has problems at scale: requires a GPU or heavy CPU, needs model downloads and updates, and adds operational complexity.

---

## Decision

**Use MiniMax M2 Cloud API** as the LLM provider, replacing Ollama.

---

## Why MiniMax M2

| Factor | Decision |
|--------|---------|
| **n8n native** | OpenAI-compatible API — works with n8n's HTTP Request node without custom code |
| **No local infra** | No GPU needed, no model downloads, no Ollama server to maintain |
| **Cost** | ~$0.001/msg at normal usage — ~$10/month at 500 customers |
| **Speed** | Cloud-hosted, typically < 1s response |
| **Reliability** | MiniMax SLA, not dependent on VPS uptime |
| **Context window** | 256K tokens — sufficient for conversation history |

**Alternatives considered:**

| Alternative | Why Not |
|-------------|---------|
| Ollama (local) | Requires GPU on VPS; adds RAM/CPU load; model updates are manual |
| OpenAI GPT-4o | 10x more expensive; overkill for simple intent parsing |
| Anthropic Claude | More expensive; slower for simple parsing tasks |
| Google Gemini | Good but MiniMax M2 is cheaper and simpler for this use case |
| Local Llama | Too slow on CPU; quality insufficient for intent parsing |

---

## Consequences

**Positive:**
- No local LLM infrastructure to maintain
- Cost is predictable and low
- Response quality sufficient for intent parsing (not creative writing)
- OpenAI-compatible = easy to swap to GPT-4o later if needed

**Negative:**
- Adds external API dependency (MiniMax)
- Cost accumulates with message volume — need to monitor
- Privacy: customer messages go to MiniMax (standard for LLM APIs)

**Mitigation:** Redis caching for LLM responses (80% cache hit rate expected for repeated intents). Minimize context sent — only send the current message, not full history.

---

## Cost Estimate

| Volume | Msgs/Month | Cost |
|--------|-----------|------|
| 50 customers, 10 msgs/day | 15,000 | ~$15/mo |
| 100 customers, 10 msgs/day | 30,000 | ~$30/mo |
| 500 customers, 10 msgs/day | 150,000 | ~$100/mo |

At 500 customers and 500 cached responses (80% hit rate), actual cost ~$20/mo.

---

## Implementation

```javascript
// n8n HTTP Request node
{
  "method": "POST",
  "url": "https://api.minimax.chat/v1/chat/completions",
  "headers": {
    "Authorization": "Bearer {{ $env.MINIMAX_API_KEY }}",
    "Content-Type": "application/json"
  },
  "body": {
    "model": "MiniMax-M2",
    "messages": [...]
  }
}
```

Base URL: `https://api.minimax.chat/v1`
Model: `MiniMax-M2`

---

## Rollback

If MiniMax is unavailable, fall back to a keyword-based intent parser (simple if/else on message text). Quality degrades but service continues.
