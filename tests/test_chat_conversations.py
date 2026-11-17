from fastapi.testclient import TestClient

from app.main import app
from app.storage import database


def test_first_chat_message_creates_conversation_and_followup_reuses_it(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "chat-test.db")
    database.initialize_database()
    monkeypatch.setattr("app.main.has_indexed_documents", lambda: True)

    seen_history = []

    def fake_run_question(question, history=None):
        seen_history.append(history or [])
        return {
            "answer": f"Answer for: {question}",
            "sources": [{"source": "paper.pdf", "page": 1}],
            "workflow_steps": ["query_analyzer", "answer_generator"],
        }

    monkeypatch.setattr("app.main.run_question", fake_run_question)

    with TestClient(app) as client:
        first = client.post("/chat", json={"question": "What is the main finding?"})
        assert first.status_code == 200
        conversation_id = first.json()["conversation_id"]
        assert conversation_id

        second = client.post("/chat", json={
            "question": "Can you explain that further?",
            "conversation_id": conversation_id,
        })
        assert second.status_code == 200
        assert second.json()["conversation_id"] == conversation_id

        messages = client.get(f"/conversations/{conversation_id}/messages").json()["messages"]
        assert [message["role"] for message in messages] == [
            "user", "assistant", "user", "assistant"
        ]
        assert messages[0]["content"] == "What is the main finding?"
        assert messages[2]["content"] == "Can you explain that further?"
        assert seen_history[0] == []
        assert len(seen_history[1]) == 2
        assert seen_history[1][0]["content"] == "What is the main finding?"
