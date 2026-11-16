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
        response = client.post("/chat", json={"question": "What is in my PDF?"})
        assert response.status_code == 400

def test_upload_rejects_non_pdf():
    with TestClient(app) as client:
        response = client.post("/documents/upload", files={"file": ("notes.txt", b"not a pdf", "text/plain")})
        assert response.status_code == 400
