from langchain_core.documents import Document
import pytest

from app.graph import multi_model


class FakeRetriever:
    def __init__(self):
        self.calls = []
    def invoke(self, query):
        self.calls.append(query)
        return [Document(
            page_content="The paper reports that retrieval-augmented generation grounds answers in retrieved evidence.",
            metadata={"filename": "paper.pdf", "page": 0},
        )]


class FakeStore:
    def __init__(self, retriever):
        self.retriever = retriever
    def as_retriever(self, search_kwargs):
        assert search_kwargs["k"] >= 1
        return self.retriever


class FakeModel:
    def __init__(self, model_id):
        self.model_id = model_id
    def invoke(self, prompt):
        assert "paper.pdf, p. 1" in prompt
        assert "ONLY the supplied document excerpts" in prompt
        return type("Response", (), {"content": f"Answer from {self.model_id} [paper.pdf, p. 1]"})()


def test_multi_model_uses_shared_evidence_and_returns_selected_order(monkeypatch):
    retriever = FakeRetriever()
    monkeypatch.setattr(multi_model, "get_vector_store", lambda: FakeStore(retriever))
    monkeypatch.setattr(multi_model, "get_chat_model", lambda model_id: FakeModel(model_id))

    result = multi_model.run_multi_model_question(
        "What does the paper say about RAG?",
        ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"],
    )

    assert len(retriever.calls) == 1
    assert [answer["model_id"] for answer in result["answers"]] == [
        "openai/gpt-oss-120b", "qwen/qwen3.8-27b"
    ]
    assert all(answer["status"] == "success" for answer in result["answers"])
    assert all(answer["citation_status"] == "matched_source_names" for answer in result["answers"])
    assert result["sources"] == [{"source": "paper.pdf", "page": 1, "section": None}]


def test_multi_model_rejects_more_than_five_models():
    with pytest.raises(ValueError, match="between 1 and 5"):
        multi_model.run_multi_model_question("Explain the finding", ["a", "b", "c", "d", "e", "f"])


def test_billing_rejection_marks_model_unavailable(monkeypatch):
    class PaymentRequiredError(Exception):
        status_code = 402

    retriever = FakeRetriever()
    monkeypatch.setattr(multi_model, "get_vector_store", lambda: FakeStore(retriever))
    monkeypatch.setattr(multi_model, "get_model_config", lambda model_id: {
        "id": model_id, "name": "Test paid model", "provider": "groq"
    })
    monkeypatch.setattr(multi_model, "get_chat_model", lambda model_id: (_ for _ in ()).throw(PaymentRequiredError("payment required")))

    result = multi_model.run_multi_model_question("What does the paper say about RAG?", ["test-paid-model"])

    assert result["answers"][0]["status"] == "unavailable"
    assert "billing" in result["answers"][0]["error"].lower()
    assert "payment required" not in result["answers"][0]["error"].lower()
    from app.graph import llm
    llm._MODEL_BLOCKS.pop(("groq", "test-paid-model"), None)
