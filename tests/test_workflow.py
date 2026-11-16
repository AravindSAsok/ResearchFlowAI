from langchain_core.documents import Document
from app.graph.workflow import build_research_graph, INSUFFICIENT_EVIDENCE

class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.queries = []
    def invoke(self, query):
        self.queries.append(query)
        return self.docs

class FakeResponse:
    content = "The document states that retrieval improves answer grounding."

class FakeLLM:
    def __init__(self):
        self.prompts = []
    def invoke(self, prompt):
        self.prompts.append(prompt)
        assert "DOCUMENT CONTEXT" in prompt
        return FakeResponse()

def test_graph_generates_answer_and_sources():
    doc = Document(page_content="Retrieval augmented generation uses external context to ground answers.", metadata={"source":"paper.pdf", "page":1})
    retriever = FakeRetriever([doc])
    llm = FakeLLM()
    graph = build_research_graph(llm, retriever)
    result = graph.invoke({"question":"What is RAG?", "retry_count":0, "workflow_steps":[]})
    assert "grounding" in result["answer"]
    assert result["sources"] == [{"source":"paper.pdf", "page":2}]
    assert "answer_generator" in result["workflow_steps"]
    assert len(retriever.queries) == 1
    assert "No earlier messages." in llm.prompts[0]

def test_graph_uses_prior_conversation_for_follow_up():
    doc = Document(page_content="The paper describes vector databases as semantic indexes.", metadata={"filename":"vectors.pdf", "page":0})
    llm = FakeLLM()
    graph = build_research_graph(llm, FakeRetriever([doc]))
    graph.invoke({
        "question":"What does it say about their benefits?",
        "retry_count":0,
        "workflow_steps":[],
        "history":[{"role":"user","content":"Explain vector databases."},{"role":"assistant","content":"They store embeddings."}],
    })
    assert "Explain vector databases." in llm.prompts[0]
    assert "They store embeddings." in llm.prompts[0]

def test_graph_retries_once_then_returns_insufficient_evidence():
    retriever = FakeRetriever([])
    graph = build_research_graph(FakeLLM(), retriever)
    result = graph.invoke({"question":"Explain an unsupported topic", "retry_count":0, "workflow_steps":[]})
    assert result["answer"] == INSUFFICIENT_EVIDENCE
    assert len(retriever.queries) == 2
    assert "retrieval_retry" in result["workflow_steps"]
    assert result["sources"] == []
