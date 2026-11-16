# Development Status — ResearchFlow AI

Updated: 2026-11-16

## Implemented
- [x] Project layout, configuration and secret-safe .gitignore
- [x] Python 3.14 virtual environment and dependency installation
- [x] FastAPI health, PDF upload/list/delete, chat, research and conversation endpoints
- [x] PDF extraction, page metadata and recursive chunking
- [x] Persistent Chroma vector storage with local ONNX embeddings
- [x] LangChain retrieval and OpenRouter ChatOpenAI integration
- [x] LangGraph StateGraph with query analysis, retrieval, evidence evaluation, one retry, answer generation and review
- [x] Multi-question research decomposition and synthesis
- [x] SQLite conversation and message persistence
- [x] Streamlit dashboard, document library, chat, research workspace and workflow trace
- [x] Conversation selection and continuation in the chat UI
- [x] README, Mermaid architecture diagram and developer documentation
- [x] Sample PDF fixture and reproducible fixture generator

## Verification completed
- [x] Dependencies installed successfully on Python 3.14
- [x] Python compileall check passed
- [x] Pytest: 8 passed
- [x] FastAPI health endpoint returned HTTP 200
- [x] Streamlit frontend returned HTTP 200
- [x] Local ONNX embedding smoke test passed (384-dimensional vector)
- [x] Sample PDF extraction and chunk metadata verified
- [x] PDF upload/index API returned HTTP 200 and one chunk indexed
- [x] Chroma semantic retrieval returned the indexed sample document
- [x] Chat correctly returns HTTP 503 when the OpenRouter key is not configured

## Pending / requires user input
- [ ] Add OPENROUTER_API_KEY to local .env
- [ ] Verify live LLM chat and multi-step research with the user's OpenRouter account
- [ ] Browser-level visual review of the Streamlit UI
- [ ] Confirm GitHub repository name/URL before creating a remote or pushing

## Known limitations
- Research mode searches only the local PDF knowledge base; no external web search provider is configured.
- The answer reviewer currently applies deterministic output/source checks, not a separate LLM-based factuality judge.
- Authentication, multi-user isolation and production deployment hardening are not included in this local MVP.

## Next
Configure the API key, run live chat/research tests, inspect the UI, then prepare a clean local Git commit and confirm the GitHub destination.
