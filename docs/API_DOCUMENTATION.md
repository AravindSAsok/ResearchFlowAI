# API Documentation

Interactive OpenAPI docs are available at /docs while FastAPI is running.

| Method | Path | Request | Purpose |
|---|---|---|---|
| GET | /health | — | Health check |
| POST | /documents/upload | multipart: file | Validate, split, embed and index PDF |
| GET | /documents | — | List indexed PDFs and chunk counts |
| DELETE | /documents/{document_id} | — | Delete a PDF and its vector chunks |
| POST | /chat | question, optional conversation_id | Run document-grounded LangGraph RAG |
| POST | /research | question | Decompose, research and synthesize a report |
| GET | /conversations | — | List conversations |
| GET | /conversations/{id}/messages | — | Read a conversation's messages |

Chat responses include answer, source filename/page metadata, conversation ID and workflow step names. Research responses include the generated sub-questions, report, source references and workflow steps.
