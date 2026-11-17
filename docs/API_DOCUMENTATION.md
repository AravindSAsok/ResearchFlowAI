# API Documentation

Interactive OpenAPI docs are available at /docs while FastAPI is running.

| Method | Path | Request | Purpose |
|---|---|---|---|
| GET | /health | — | Health check |
| GET | /models | — | Live provider catalogue, heuristic research-fit scores and provider-diverse five-model recommendations |
| POST | /documents/upload | multipart: file | Index PDF, DOC, DOCX or TXT |
| POST | /documents/text | filename, text | Index pasted/copied text |
| GET | /documents | — | List indexed documents and chunk counts |
| DELETE | /documents/{document_id} | — | Delete a document and its vector chunks |
| POST | /compare | question, model_ids (1–5) | Retrieve evidence once and query selected models in parallel |
| POST | /chat | question, optional conversation_id | Existing single-model LangGraph RAG conversation |
| POST | /research | question, optional model_id | Decompose, research and synthesize using one selected model |
| GET | /conversations | — | List conversations |
| GET | /conversations/{id}/messages | — | Read a conversation's messages |

## Compare request

```json
{
  "question": "What do these documents conclude about the intervention?",
  "model_ids": ["openai/gpt-oss-120b", "gemini-2.5-flash"]
}
```

The compare response contains one answer object per selected model, including model/provider IDs, answer text, response time, status and a basic citation-name check. The same retrieved document excerpts are sent to every selected model. Shared source metadata and workflow steps are returned once.

## Pasted text request

```json
{
  "filename": "Meeting notes.txt",
  "text": "Pasted document content..."
}
```

The GET /models response contains `models`, `recommended_models` (up to five provider-diverse candidates), `safe_default_models` (only explicitly zero-priced OpenRouter models), `selection_limit` and `ranking_note`. Each model includes provider, ID, context metadata when published, heuristic fit score and breakdown, recommendation reasons, key-configuration status, availability state and a provider-specific cost/quota label. The catalogue includes free and paid chat models. Provider billing/quota/access errors mark the affected model temporarily unavailable for 30 minutes; unavailable models remain visible in the library but are excluded from chat/research selection. The score is not a measured quality benchmark. ResearchFlow does not purchase credits or automatically fall back to another provider. Provider keys are read only from backend environment variables: OPENROUTER_API_KEY, GROQ_API_KEY, GEMINI_API_KEY and NVIDIA_API_KEY. The API never returns key values.
