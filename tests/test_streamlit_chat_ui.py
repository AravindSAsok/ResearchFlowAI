from streamlit.testing.v1 import AppTest
import requests


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def fake_catalogue():
    return {"models": [{
        "id": "openai/gpt-oss-120b",
        "name": "GPT-OSS 120B",
        "provider": "groq",
        "provider_name": "Groq",
        "configured": True,
        "available": True,
        "strengths": ["reasoning", "analysis"],
        "context_window": 131072,
        "fit_score": 92,
        "fit_note": "Test model",
    }]}


def test_multi_model_chat_renders_answer_without_forced_refresh(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if url.endswith("/documents"):
            return FakeResponse({"documents": [{"document_id": "doc-1", "filename": "paper.pdf", "chunks": 2}]})
        if url.endswith("/models"):
            return FakeResponse(fake_catalogue())
        if url.endswith("/conversations"):
            return FakeResponse({"conversations": []})
        raise AssertionError(f"Unexpected GET: {url}")

    def fake_post(url, **kwargs):
        assert url.endswith("/compare")
        assert kwargs["json"]["question"] == "Explain the main finding."
        assert kwargs["json"]["model_ids"] == ["openai/gpt-oss-120b"]
        return FakeResponse({
            "question": "Explain the main finding.",
            "answers": [{
                "model_id": "openai/gpt-oss-120b",
                "model_name": "GPT-OSS 120B",
                "provider": "groq",
                "answer": "UI_MULTI_MODEL_REPLY_VISIBLE",
                "latency_ms": 120,
                "status": "success",
            }],
            "sources": [{"source": "paper.pdf", "page": 2}],
            "workflow_steps": ["shared_document_retrieval", "parallel_model_generation"],
        })

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "post", fake_post)

    app = AppTest.from_file("../frontend/streamlit_app.py", default_timeout=30).run()
    next(button for button in app.button if button.label == "AI Chat").click().run()
    app.multiselect[0].set_value(["openai/gpt-oss-120b"]).run()
    app.chat_input[0].set_value("Explain the main finding.").run()

    assert len(app.exception) == 0
    assert any("UI_MULTI_MODEL_REPLY_VISIBLE" in str(item.value) for item in app.markdown)
    assert len(app.chat_input) == 1


def test_overview_quick_action_navigates_without_widget_state_error(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if url.endswith("/documents"):
            return FakeResponse({"documents": []})
        if url.endswith("/models"):
            return FakeResponse(fake_catalogue())
        if url.endswith("/conversations"):
            return FakeResponse({"conversations": []})
        raise AssertionError(f"Unexpected GET: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    app = AppTest.from_file("../frontend/streamlit_app.py", default_timeout=30).run()
    assert len(app.exception) == 0

    next(button for button in app.button if button.label == "Open AI Chat →").click().run()

    assert len(app.exception) == 0
    assert app.session_state["workspace_page"] == "AI Chat"
    assert any("One question. Up to five expert answers." in str(item.value) for item in app.markdown)

def test_model_library_lists_provider_models(monkeypatch):
    def fake_get(url, **kwargs):
        if url.endswith("/health"):
            return FakeResponse({"status": "ok"})
        if url.endswith("/models"):
            return FakeResponse(fake_catalogue())
        if url.endswith("/documents"):
            return FakeResponse({"documents": []})
        if url.endswith("/conversations"):
            return FakeResponse({"conversations": []})
        raise AssertionError(f"Unexpected GET: {url}")

    monkeypatch.setattr(requests, "get", fake_get)
    app = AppTest.from_file("../frontend/streamlit_app.py", default_timeout=30).run()
    next(button for button in app.button if button.label == "Model Library").click().run()

    assert len(app.exception) == 0
    assert any("Find your best research models." in str(item.value) for item in app.markdown)
    assert any("GPT-OSS 120B" in str(item.value) for item in app.markdown)
