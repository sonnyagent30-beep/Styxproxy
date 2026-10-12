"""Charon — the support agent.

This module glues together:

- Scenario matcher (deterministic regex rules)
- Knowledge base (RAG over Markdown files)
- LLM (MiniMax-M2 by default)
- Tool registry (Charon can do some things, not others)
- Conversation logging (every exchange is persisted)

When n8n comes online, swap `call_llm()` to call n8n's webhook
instead. The rest of the interface is stable.
"""
