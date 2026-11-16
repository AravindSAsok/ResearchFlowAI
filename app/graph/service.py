from app.graph.llm import get_chat_model
from app.graph.workflow import build_research_graph
from app.ingestion.vector_store import get_vector_store
from app.core.config import RETRIEVAL_TOP_K

def run_question(question: str):
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": RETRIEVAL_TOP_K})
    graph = build_research_graph(get_chat_model(), retriever)
    return graph.invoke({"question": question, "retry_count": 0, "workflow_steps": []})
