# Phase 5: Agent layer, routing, skills

**Status:** done and tested.

## Idea
An "agent" here = a **router** that picks a **skill**, plus shared retrieval and a model.

```
mode (UI) or regex intent → skill → retrieval → gate → LLMProvider
```

## Why regex routing?
No extra model call (slow on CPU), deterministic, unit-testable. An LLM router is a later upgrade.

## Skills
ask · explain · quiz · ship30 · artifact · prd. One module each (`agent/skills/`).

## Ship 30 for 30, encoded
Principles are constants in `ship30.py` (hook, for-who/so-that, rate of revelation, 1-3-1 rhythm, skimmable format, one idea, grounded claims, actionable takeaway). **Sectioned** strategy: outline, then one short call per section. Small models cannot write 1,250 words in one go but can write six 200-word parts.

## Providers
`LLMProvider` interface: Ollama, Claude (HTTP), Claude Agent SDK. The brief names the SDK but the demo must run on Ollama, so the SDK is one provider, not the whole layer. **SDK path is unverified (no key).**

## Interview questions
1. Why an interface between agent and model? (swap by config; the trade-off to present in your video) 2. Router vs LLM-as-router? 3. How would you add a tool-using agent? (skills become tools; loop on model tool calls)
