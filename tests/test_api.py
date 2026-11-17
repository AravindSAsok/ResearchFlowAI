from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_chat_rejects_short_question():
    with TestClient(app) as client:
        response = client.post("/chat", json={"question": "hi"})
        assert response.status_code == 422


def test_chat_requires_indexed_documents(monkeypatch):
    monkeypatch.setattr("app.main.has_indexed_documents", lambda: False)
    with TestClient(app) as client:
        response = client.post("/chat", json={"question": "What is in my document?"})
        assert response.status_code == 400


def test_upload_rejects_unsupported_file():
    with TestClient(app) as client:
        response = client.post("/documents/upload", files={"file": ("notes.csv", b"not supported", "text/csv")})
        assert response.status_code == 400


def test_model_catalog_returns_five_selection_limit():
    with TestClient(app) as client:
        response = client.get("/models")
        assert response.status_code == 200
        payload = response.json()
        assert payload["selection_limit"] == 5
        assert len(payload["models"]) >= 5
        assert {item["provider"] for item in payload["models"]} == {
            "openrouter", "groq", "gemini", "nvidia"
        }
        assert all("configured" in item for item in payload["models"])


def test_compare_endpoint_returns_model_answers(monkeypatch):
    monkeypatch.setattr("app.main.has_indexed_documents", lambda: True)
    monkeypatch.setattr("app.main.run_multi_model_question", lambda question, model_ids: {
        "question": question,
        "answers": [{"model_id": model_id, "status": "success", "answer": f"Answer {model_id}"} for model_id in model_ids],
        "sources": [{"source": "paper.pdf", "page": 1}],
        "workflow_steps": ["shared_document_retrieval", "parallel_model_generation"],
    })
    with TestClient(app) as client:
        response = client.post("/compare", json={
            "question": "Explain the paper's key finding",
            "model_ids": ["openai/gpt-oss-120b", "gemini-3.8-flash"],
        })
        assert response.status_code == 200
        assert len(response.json()["answers"]) == 2
        assert response.json()["answers"][1]["model_id"] == "gemini-3.8-flash"


def test_compare_rejects_more_than_five_models(monkeypatch):
    monkeypatch.setattr("app.main.has_indexed_documents", lambda: True)
    with TestClient(app) as client:
        response = client.post("/compare", json={
            "question": "Explain the paper's key finding",
            "model_ids": ["a", "b", "c", "d", "e", "f"],
        })
        assert response.status_code == 422


def test_pasted_text_document_is_saved_and_indexed(monkeypatch, tmp_path):
    monkeypatch.setattr("app.main.UPLOAD_DIR", tmp_path)

    def fake_index(path, filename, content):
        assert path.suffix == ".txt"
        assert path.read_text(encoding="utf-8") == content.decode("utf-8")
        return {"status": "indexed", "filename": filename, "chunks": 1}

    monkeypatch.setattr("app.main.index_saved_document", fake_index)
    with TestClient(app) as client:
        response = client.post("/documents/text", json={
            "filename": "copied notes.txt",
            "text": "This is copied research text with enough detail to index.",
        })
        assert response.status_code == 200
        assert response.json()["filename"] == "copied notes.txt"
