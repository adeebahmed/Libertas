# Phase 4: AI & Multi-Model Intelligence - Research

**Researched:** 2026-04-11
**Domain:** LLM provider abstraction, local model support, prompt/context controls
**Confidence:** HIGH

## Summary

Current state is Claude-only chat through `backend/ai.py` and `/api/insights/chat` with no provider abstraction and no model selection UX.

What exists:
- Claude API call helper and key storage fallback in settings
- Insights chat tab in frontend
- Rule-based insights already provide structured portfolio context inputs

Gaps to complete FR-7:
- No provider abstraction contract (provider registry, adapter interface)
- No OpenAI or Ollama providers
- No provider/model selection UI in settings
- No context window strategy beyond current prompt assembly
- No persisted chat sessions with clearable history controls
- No provider-cost surfacing and recommendation logic

<phase_requirements>
## Phase Requirements

| ID | Description |
|----|-------------|
| FR-7.1 | Provider abstraction and user-selected backend |
| FR-7.2 | Claude + OpenAI + Ollama implementations |
| FR-7.3 | Model/provider settings UI + cost visibility |
| FR-7.4 | Context management, persisted history, advisory disclaimer |
</phase_requirements>

## Execution Recommendation

1. Abstraction layer + schema/settings contracts
2. Claude adapter migration to new interface
3. OpenAI adapter
4. Ollama adapter and local reachability checks
5. Settings and insights chat UI upgrades
6. Context summarization and transcript persistence
7. ADR and final validation
