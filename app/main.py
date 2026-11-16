import hashlib
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.ingestion.pdf import load_and_split_pdf
from app.ingestion.vector_store import get_vector_store
from app.graph.service import run_question
from app.graph.research import run_research
from app.storage.database import initialize_database, create_conversation, save_message, list_conversations, get_messages

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield

app = FastAPI(title="ResearchFlow AI", version="0.1.0",
    description="Document-grounded AI research assistant powered by LangChain and LangGraph.",
    lifespan=lifespan)

class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: int | None = None

class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)

def has_indexed_documents() -> bool:
    return bool(get_vector_store().get(include=["metadatas"]).get("ids"))

@app.get("/health")
def health():
    return {"status": "ok", "service": "ResearchFlow AI"}

@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"PDF exceeds the {MAX_UPLOAD_MB} MB limit.")

    digest = hashlib.sha256(content).hexdigest()
    store = get_vector_store()
    existing = store.get(where={"file_hash": digest}, include=["metadatas"])
    if existing.get("ids"):
        return {"status": "already_indexed", "document_id": existing["metadatas"][0]["document_id"],
                "filename": file.filename, "chunks": len(existing["ids"])}

    document_id = str(uuid.uuid4())
    safe_name = Path(file.filename).name
    saved_path = UPLOAD_DIR / f"{document_id}.pdf"
    saved_path.write_bytes(content)
    try:
        chunks = load_and_split_pdf(saved_path)
        if not chunks:
            raise ValueError("No readable text was found in this PDF.")
        for chunk in chunks:
            chunk.metadata.update({"document_id": document_id, "filename": safe_name, "file_hash": digest})
        store.add_documents(chunks)
    except Exception as exc:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not process PDF: {exc}") from exc
    return {"status": "indexed", "document_id": document_id, "filename": safe_name, "chunks": len(chunks)}

@app.get("/documents")
def documents():
    data = get_vector_store().get(include=["metadatas"])
    grouped = {}
    for meta in data.get("metadatas") or []:
        doc_id = meta.get("document_id")
        if not doc_id:
            continue
        item = grouped.setdefault(doc_id, {"document_id": doc_id, "filename": meta.get("filename", "document.pdf"), "chunks": 0})
        item["chunks"] += 1
    return {"documents": list(grouped.values())}

@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    store = get_vector_store()
    matches = store.get(where={"document_id": document_id}, include=["metadatas"])
    if not matches.get("ids"):
        raise HTTPException(status_code=404, detail="Document not found.")
    store.delete(ids=matches["ids"])
    (UPLOAD_DIR / f"{document_id}.pdf").unlink(missing_ok=True)
    return {"status": "deleted", "document_id": document_id, "chunks_removed": len(matches["ids"])}

@app.post("/chat")
def chat(request: ChatRequest):
    if not has_indexed_documents():
        raise HTTPException(status_code=400, detail="Upload a PDF before asking questions.")
    history = []
    if request.conversation_id is not None:
        existing = next((item for item in list_conversations() if item["id"] == request.conversation_id), None)
        if existing is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")
        history = get_messages(request.conversation_id)[-8:]
    try:
        result = run_question(request.question, history=history)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research workflow failed: {exc}") from exc
    conversation_id = request.conversation_id or create_conversation(request.question[:80])
    save_message(conversation_id, "user", request.question)
    save_message(conversation_id, "assistant", result.get("answer", ""))
    return {"conversation_id": conversation_id, "answer": result.get("answer", ""),
            "sources": result.get("sources", []), "workflow_steps": result.get("workflow_steps", [])}

@app.post("/research")
def research(request: ResearchRequest):
    if not has_indexed_documents():
        raise HTTPException(status_code=400, detail="Upload research PDFs first.")
    try:
        result = run_research(request.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research workflow failed: {exc}") from exc
    return {"question": request.question, "report": result.get("answer", ""),
            "subquestions": result.get("subquestions", []),
            "sources": result.get("sources", []), "workflow_steps": result.get("workflow_steps", [])}

@app.get("/conversations")
def conversations():
    return {"conversations": list_conversations()}

@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int):
    return {"messages": get_messages(conversation_id)}
