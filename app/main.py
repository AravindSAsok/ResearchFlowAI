import hashlib
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel, Field

from app.core.config import UPLOAD_DIR, MAX_UPLOAD_MB
from app.ingestion.document import load_and_split_document
from app.ingestion.vector_store import get_vector_store
from app.graph.service import run_question
from app.graph.research import run_research
from app.graph.multi_model import run_multi_model_question
from app.graph.llm import list_models, get_model_config, recommend_models, recommend_free_models, mark_model_unavailable
from app.storage.database import initialize_database, create_conversation, save_message, list_conversations, get_messages


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="ResearchFlow AI",
    version="0.2.0",
    description="Multi-model, document-grounded AI research workspace.",
    lifespan=lifespan,
)


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: int | None = None


class ResearchRequest(BaseModel):
    question: str = Field(min_length=8, max_length=2000)
    model_id: str | None = None


class CompareRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    model_ids: list[str] = Field(min_length=1, max_length=5)


class TextDocumentRequest(BaseModel):
    filename: str = Field(default="Pasted research.txt", min_length=1, max_length=180)
    text: str = Field(min_length=20, max_length=500000)


def has_indexed_documents() -> bool:
    return bool(get_vector_store().get(include=["metadatas"]).get("ids"))


def index_saved_document(saved_path: Path, original_name: str, content: bytes):
    digest = hashlib.sha256(content).hexdigest()
    store = get_vector_store()
    existing = store.get(where={"file_hash": digest}, include=["metadatas"])
    if existing.get("ids"):
        saved_path.unlink(missing_ok=True)
        meta = existing["metadatas"][0]
        return {
            "status": "already_indexed",
            "document_id": meta["document_id"],
            "filename": meta.get("filename", original_name),
            "chunks": len(existing["ids"]),
        }

    document_id = str(uuid.uuid4())
    try:
        chunks = load_and_split_document(saved_path)
        if not chunks:
            raise ValueError("No readable text was found in this document.")
        for chunk in chunks:
            chunk.metadata.update({
                "document_id": document_id,
                "filename": original_name,
                "file_hash": digest,
                "stored_filename": saved_path.name,
                "file_type": saved_path.suffix.lower().lstrip("."),
            })
        store.add_documents(chunks)
    except Exception as exc:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not process document: {exc}") from exc
    return {
        "status": "indexed",
        "document_id": document_id,
        "filename": original_name,
        "chunks": len(chunks),
        "file_type": saved_path.suffix.lower().lstrip("."),
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "ResearchFlow AI"}


@app.get("/models")
def models():
    return {
        "models": list_models(),
        "recommended_models": recommend_models(5),
        "safe_default_models": recommend_free_models(5),
        "selection_limit": 5,
        "ranking_note": "Recommendations are metadata-based heuristics, not measured benchmark winners.",
    }


@app.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required.")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".doc", ".docx", ".txt"}:
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOC, DOCX and TXT.")
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded document is empty.")
    if suffix == ".pdf" and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Document exceeds the {MAX_UPLOAD_MB} MB limit.")

    safe_name = Path(file.filename).name
    document_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}{suffix}"
    saved_path.write_bytes(content)
    return index_saved_document(saved_path, safe_name, content)


@app.post("/documents/text")
def upload_pasted_text(request: TextDocumentRequest):
    safe_name = Path(request.filename).name
    if Path(safe_name).suffix.lower() not in {"", ".txt"}:
        safe_name = f"{Path(safe_name).stem}.txt"
    content = request.text.encode("utf-8")
    if len(content) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"Text exceeds the {MAX_UPLOAD_MB} MB limit.")
    document_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{document_id}.txt"
    saved_path.write_bytes(content)
    return index_saved_document(saved_path, safe_name, content)


@app.get("/documents")
def documents():
    data = get_vector_store().get(include=["metadatas"])
    grouped = {}
    for meta in data.get("metadatas") or []:
        doc_id = meta.get("document_id")
        if not doc_id:
            continue
        item = grouped.setdefault(doc_id, {
            "document_id": doc_id,
            "filename": meta.get("filename", "document"),
            "file_type": meta.get("file_type", "pdf"),
            "chunks": 0,
        })
        item["chunks"] += 1
    return {"documents": list(grouped.values())}


@app.delete("/documents/{document_id}")
def delete_document(document_id: str):
    store = get_vector_store()
    matches = store.get(where={"document_id": document_id}, include=["metadatas"])
    if not matches.get("ids"):
        raise HTTPException(status_code=404, detail="Document not found.")
    metadata = matches["metadatas"][0] if matches.get("metadatas") else {}
    store.delete(ids=matches["ids"])
    stored_name = metadata.get("stored_filename")
    if stored_name:
        (UPLOAD_DIR / Path(stored_name).name).unlink(missing_ok=True)
    else:
        for suffix in (".pdf", ".doc", ".docx", ".txt"):
            (UPLOAD_DIR / f"{document_id}{suffix}").unlink(missing_ok=True)
    return {"status": "deleted", "document_id": document_id, "chunks_removed": len(matches["ids"])}


@app.post("/compare")
def compare(request: CompareRequest):
    if not has_indexed_documents():
        raise HTTPException(status_code=400, detail="Upload or paste a document before asking questions.")
    unknown = [model_id for model_id in request.model_ids if not get_model_config(model_id)]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown model ID(s): {', '.join(unknown)}")
    try:
        return run_multi_model_question(request.question, request.model_ids)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Model comparison failed: {exc}") from exc


@app.post("/chat")
def chat(request: ChatRequest):
    if not has_indexed_documents():
        raise HTTPException(status_code=400, detail="Upload a document before asking questions.")
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
        model = get_model_config("openrouter/free")
        if model:
            unavailable_reason = mark_model_unavailable(model["provider"], model["id"], exc)
            if unavailable_reason:
                raise HTTPException(status_code=503, detail=unavailable_reason) from exc
        raise HTTPException(status_code=500, detail="Research workflow failed. Check provider access and try again.") from exc
    conversation_id = request.conversation_id or create_conversation(request.question[:80])
    save_message(conversation_id, "user", request.question)
    save_message(conversation_id, "assistant", result.get("answer", ""))
    return {
        "conversation_id": conversation_id,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "workflow_steps": result.get("workflow_steps", []),
    }


@app.post("/research")
def research(request: ResearchRequest):
    if not has_indexed_documents():
        raise HTTPException(status_code=400, detail="Upload research documents first.")
    if request.model_id and not get_model_config(request.model_id):
        raise HTTPException(status_code=400, detail=f"Unknown model ID: {request.model_id}")
    try:
        result = run_research(request.question, model_id=request.model_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        selected_model = get_model_config(request.model_id or "openrouter/free")
        if selected_model:
            unavailable_reason = mark_model_unavailable(selected_model["provider"], selected_model["id"], exc)
            if unavailable_reason:
                raise HTTPException(status_code=503, detail=unavailable_reason) from exc
        raise HTTPException(status_code=500, detail="Research workflow failed. Check provider access and try again.") from exc
    return {
        "question": request.question,
        "report": result.get("answer", ""),
        "subquestions": result.get("subquestions", []),
        "sources": result.get("sources", []),
        "workflow_steps": result.get("workflow_steps", []),
    }


@app.get("/conversations")
def conversations():
    return {"conversations": list_conversations()}


@app.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: int):
    return {"messages": get_messages(conversation_id)}
