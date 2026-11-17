# Development Status — ResearchFlow AI

Updated: 2026-11-16

## Implemented

- [x] FastAPI health, upload/list/delete, chat, research, compare, model catalogue and conversation endpoints
- [x] PDF, DOC, DOCX and TXT extraction plus pasted/copied text ingestion
- [x] PDF page metadata and document/section metadata for Word and text files
- [x] Persistent Chroma vector storage with local ONNX embeddings
- [x] OpenRouter, Groq, Gemini and NVIDIA NIM provider configuration through environment variables
- [x] Live provider model discovery for all four providers, including free and paid text/chat models, with common non-chat model-family filtering
- [x] OpenRouter catalogue pricing metadata surfaced; other providers clearly label account-dependent pricing/quotas
- [x] Provider billing/quota/access failures temporarily hide the affected model from selection for 30 minutes; no paid fallback or credit purchase
- [x] Only OpenRouter models explicitly listed at $0 are preselected by default; paid models remain manually selectable
- [x] Model selection up to five entries with parallel generation using the same retrieved excerpts
- [x] Switchable model answer tabs, response-time display, source references and citation-name checks
- [x] Research Studio model selector for one configured model
- [x] Evidence-first prompt instructions and insufficient-evidence guardrail
- [x] Streamlit Model Library with live model search/provider filter, research-fit scores and a provider-diverse recommended shortlist; AI Chat preselects only explicitly zero-priced models
- [x] SQLite conversation and message persistence for the existing chat path
- [x] README, API docs, architecture and ranking methodology documentation

## Verification completed

- [x] Python 3.14 compileall passed
- [x] Pytest suite: 30 passed, 15 third-party deprecation warnings
- [x] TXT and DOCX extraction tests passed
- [x] Legacy DOC extraction verified using local Microsoft Word automation
- [x] Multi-model parallel orchestration tested with mocked providers and shared evidence
- [x] API tests cover model catalogue, five-model request limit and pasted text ingestion
- [x] Streamlit AppTest verifies multi-model answer rendering
- [x] Playwright verified Model Library shortlist, provider search, AI Chat selector and five recommended models preselected; no browser page errors
- [x] Existing Playwright navigation checks cover Overview, Documents, Model Library, AI Chat, Research Studio and Workflow Trace
- [x] Playwright browser page errors: none
- [x] Live /models returned 466 candidates in this check: OpenRouter 420, Groq 4, Gemini 24, NVIDIA 18; catalogue counts are dynamic.
- [x] Streamlit frontend returned HTTP 200

## Pending

- [x] Added all four provider keys to the private .env and restarted backend; all four live model catalogue endpoints responded
- [ ] Validate live answer generation for each provider using a non-sensitive sample document; no real paid generation has been run
- [x] Fresh Playwright check: paid OpenRouter model visible, AI Chat loads, and no browser page errors; provider billing rejection and temporary blocking covered by unit tests
- [ ] Build the fixed document-question evaluation dataset and measured model leaderboard
- [ ] Verify citations semantically against source passages, not just source filenames
- [ ] Git remote and push destination have not been configured

## Known limitations

- Provider catalogue discovery is cached for the lifetime of the backend process; restart backend to refresh.
- Model fit scores and the recommended five-model shortlist are metadata heuristics, not independent benchmark scores; free quotas and paid credits vary by provider/model. Missing payment details are not a universal no-charge guarantee if an account has credits or other billing enabled.
- The citation check confirms source-name matching only; it cannot prove claim-level support.
- Research Studio uses the local document library and does not perform public web search.
- This remains a local single-user prototype without authentication or production hardening.
