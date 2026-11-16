from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

INSUFFICIENT_EVIDENCE = "I couldn't find enough information in the uploaded documents to answer this reliably."

class ResearchState(TypedDict, total=False):
    question: str
    search_query: str
    documents: list
    context: str
    answer: str
    sources: list[dict[str, Any]]
    sufficient: bool
    retry_count: int
    workflow_steps: list[str]

def build_research_graph(llm, retriever):
    """Build a real LangGraph workflow. Dependencies are injected for easy testing."""

    def analyze_query(state: ResearchState):
        question = state["question"].strip()
        return {"search_query": question, "workflow_steps": state.get("workflow_steps", []) + ["query_analyzer"]}

    def retrieve(state: ResearchState):
        docs = retriever.invoke(state["search_query"])
        return {"documents": docs, "retry_count": state.get("retry_count", 0),
                "workflow_steps": state.get("workflow_steps", []) + ["document_retriever"]}

    def evaluate_context(state: ResearchState):
        docs = state.get("documents", [])
        sufficient = bool(docs) and any(len(d.page_content.strip()) > 30 for d in docs)
        return {"sufficient": sufficient,
                "context": "\n\n".join(d.page_content for d in docs),
                "workflow_steps": state.get("workflow_steps", []) + ["context_evaluator"]}

    def route_after_evaluation(state: ResearchState):
        if state.get("sufficient"):
            return "generate"
        if state.get("retry_count", 0) < 1:
            return "retry"
        return "finish"

    def retry_retrieval(state: ResearchState):
        query = state["question"] + " key facts details"
        docs = retriever.invoke(query)
        return {"search_query": query, "documents": docs, "retry_count": 1,
                "workflow_steps": state.get("workflow_steps", []) + ["retrieval_retry"]}

    def evaluate_retry(state: ResearchState):
        docs = state.get("documents", [])
        sufficient = bool(docs) and any(len(d.page_content.strip()) > 30 for d in docs)
        return {"sufficient": sufficient, "context": "\n\n".join(d.page_content for d in docs),
                "workflow_steps": state.get("workflow_steps", []) + ["context_recheck"]}

    def generate_answer(state: ResearchState):
        prompt = (
            "You are ResearchFlow AI. Answer ONLY from the supplied document context. "
            "If the context does not support a claim, say so. Do not invent sources. "
            "Use concise, clear language.\n\n"
            f"QUESTION:\n{state['question']}\n\nDOCUMENT CONTEXT:\n{state['context']}"
        )
        response = llm.invoke(prompt)
        answer = response.content if hasattr(response, "content") else str(response)
        return {"answer": answer, "workflow_steps": state.get("workflow_steps", []) + ["answer_generator"]}

    def review_answer(state: ResearchState):
        # Deterministic guardrail: only return generated text when evidence exists.
        answer = state.get("answer", "").strip()
        if not answer:
            answer = INSUFFICIENT_EVIDENCE
        sources = []
        seen = set()
        for doc in state.get("documents", []):
            meta = doc.metadata or {}
            source = str(meta.get("filename") or meta.get("source") or "uploaded document")
            page_index = meta.get("page")
            page = int(page_index) + 1 if page_index is not None else None
            key = (source, page)
            if key not in seen:
                seen.add(key)
                sources.append({"source": source, "page": page})
        return {"answer": answer, "sources": sources,
                "workflow_steps": state.get("workflow_steps", []) + ["answer_reviewer"]}

    def finish(state: ResearchState):
        return {"answer": INSUFFICIENT_EVIDENCE, "sources": [],
                "workflow_steps": state.get("workflow_steps", []) + ["final_response"]}

    graph = StateGraph(ResearchState)
    graph.add_node("analyze_query", analyze_query)
    graph.add_node("retrieve", retrieve)
    graph.add_node("evaluate_context", evaluate_context)
    graph.add_node("retry_retrieval", retry_retrieval)
    graph.add_node("evaluate_retry", evaluate_retry)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("review_answer", review_answer)
    graph.add_node("finish", finish)

    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "retrieve")
    graph.add_edge("retrieve", "evaluate_context")
    graph.add_conditional_edges("evaluate_context", route_after_evaluation,
        {"generate": "generate_answer", "retry": "retry_retrieval", "finish": "finish"})
    graph.add_edge("retry_retrieval", "evaluate_retry")
    graph.add_conditional_edges("evaluate_retry",
        lambda state: "generate" if state.get("sufficient") else "finish",
        {"generate": "generate_answer", "finish": "finish"})
    graph.add_edge("generate_answer", "review_answer")
    graph.add_edge("review_answer", END)
    graph.add_edge("finish", END)
    return graph.compile()
