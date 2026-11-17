from app.graph import research as research_module

class FakeResponse:
    def __init__(self, content):
        self.content = content

class FakeLLM:
    def __init__(self):
        self.calls = 0
    def invoke(self, prompt):
        self.calls += 1
        if self.calls == 1:
            return FakeResponse("What is retrieval augmented generation?\nHow does LangGraph orchestrate workflows?\nWhat does a vector database do?")
        return FakeResponse("## Executive summary\nResearchFlow combines retrieval and graph orchestration.")

def test_research_decomposes_and_synthesizes(monkeypatch):
    fake_llm = FakeLLM()
    monkeypatch.setattr(research_module, "get_chat_model", lambda model_id=None: fake_llm)
    monkeypatch.setattr(research_module, "run_question", lambda q, model_id=None: {
        "answer": f"Evidence for: {q}",
        "sources": [{"source": "guide.pdf", "page": 1}],
        "workflow_steps": ["retrieve", "answer"],
    })
    result = research_module.run_research("Explain the architecture of a document research assistant")
    assert len(result["subquestions"]) == 3
    assert fake_llm.calls == 2
    assert "Executive summary" in result["answer"]
    assert result["sources"] == [{"source": "guide.pdf", "page": 1}]
    assert result["workflow_steps"][-1] == "research_synthesis"
