# Architecture

ResearchFlow AI separates ingestion, retrieval, workflow orchestration, API transport and presentation.

- **Ingestion:** PyPDFLoader extracts pages; RecursiveCharacterTextSplitter creates chunks while retaining page metadata.
- **Embeddings:** Sentence Transformers runs locally and creates vector representations.
- **Vector storage:** Chroma persists chunks and metadata on disk.
- **RAG:** LangChain retriever fetches the most relevant chunks.
- **Orchestration:** LangGraph controls query analysis, retrieval, evidence checks, one retry, generation and answer review.
- **LLM:** ChatOpenAI uses the OpenRouter-compatible API endpoint.
- **API:** FastAPI exposes document, chat, research and conversation endpoints.
- **UI:** Streamlit calls the API.
- **Persistence:** SQLite stores conversation and message records.

See the Mermaid architecture diagram in the root README.
