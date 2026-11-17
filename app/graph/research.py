from app.graph.llm import get_chat_model
from app.graph.service import run_question

def run_research(question: str, model_id: str | None = None):
    """Decompose a broad question, gather evidence for each part, then synthesize."""
    llm = get_chat_model(model_id)
    decomposition_prompt = (
        "Break this research question into 3 focused, non-overlapping questions. "
        "Return only the questions, one per line, without numbering or commentary.\n\n"
        f"Research question: {question}"
    )
    response = llm.invoke(decomposition_prompt)
    raw = response.content if hasattr(response, "content") else str(response)
    subquestions = [line.strip(" -•\t") for line in raw.splitlines() if line.strip()]
    subquestions = [q for q in subquestions if len(q) > 8][:3]
    if not subquestions:
        subquestions = [question]

    findings = []
    all_sources = []
    steps = ["research_decomposer"]
    for index, subquestion in enumerate(subquestions, start=1):
        result = run_question(subquestion, model_id=model_id)
        findings.append(f"Research question {index}: {subquestion}\nFinding: {result.get('answer', '')}")
        all_sources.extend(result.get("sources", []))
        steps.extend(result.get("workflow_steps", []))

    unique_sources = []
    seen = set()
    for source in all_sources:
        key = (source.get("source"), source.get("page"))
        if key not in seen:
            seen.add(key)
            unique_sources.append(source)

    evidence = "\n\n".join(findings)
    synthesis_prompt = (
        "Write a structured research report using ONLY the findings below. "
        "Include: Executive summary, Key findings, Comparison and contradictions, "
        "Evidence limitations, and Open questions. Do not invent facts or citations. "
        "If evidence is missing or conflicting, state that explicitly. "
        "Refer to the provided source names and page numbers where relevant.\n\n"
        f"Original question: {question}\n\nFindings:\n{evidence}\n\n"
        f"Available sources: {unique_sources}"
    )
    final = llm.invoke(synthesis_prompt)
    answer = final.content if hasattr(final, "content") else str(final)
    steps.append("research_synthesis")
    return {"answer": answer, "sources": unique_sources, "workflow_steps": steps,
            "subquestions": subquestions}
