# Phase 0: Audit, plan, what we are building

**Status:** done (see `prd.md`).

## One-line idea
Open-book exam for an AI: it may only answer from Lenny's transcripts, and must show its pages.

## RAG in one picture
```
ONE TIME:  transcript → chunks → embeddings → database
EACH QUESTION: question → embedding → nearest chunks → prompt → LLM → answer + sources
```
Draw this in interviews; it is the 20% that explains 80% of the project.

## Connects to what you know
| You know | Here |
|---|---|
| Base model vs assistant | The model is general; our prompt + retrieved pages make it a "Lenny-only" assistant |
| Weights / backprop / fine-tuning | RAG changes **no weights**. Knowledge lives in the database |
| Tokens | Chunks and prompts must fit the context window (that is why we chunk) |
| Embeddings | Same idea, used for search: near vectors = similar meaning |

## Interview questions
1. Why RAG instead of fine-tuning? (cheap, updatable, citable, no GPU)
2. What does the assistant do when the corpus lacks the answer? (gate → refuse before the model)
3. What did you cut and why? (see PRD scope)
