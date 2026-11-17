from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
import re

from app.core.config import RETRIEVAL_TOP_K
from app.graph.llm import get_chat_model, get_model_config, mark_model_unavailable
from app.ingestion.vector_store import get_vector_store

SYSTEM_INSTRUCTIONS = """You are an expert document research analyst.
Answer the user's question using ONLY the supplied document excerpts.
Be thorough, analytical, and specific. Distinguish direct evidence from interpretation.
Cite factual claims inline using [filename, p. N] when page numbers exist, or [filename, section] otherwise.
Never invent a quotation, page number, source, statistic, or fact. If the documents do not establish something, say so.
Structure substantial answers with: Direct answer, Evidence and analysis, Limitations or conflicting evidence, and Conclusion.
Explain uncertainty instead of filling gaps with outside knowledge."""


def retrieve_evidence(question: str):
    retriever = get_vector_store().as_retriever(search_kwargs={"k": RETRIEVAL_TOP_K})
    docs = retriever.invoke(question)
    if not docs or not any(len(doc.page_content.strip()) > 30 for doc in docs):
        docs = retriever.invoke(question + " key facts details")
    return docs


def _source_list(docs):
    sources, seen = [], set()
    for doc in docs:
        meta = doc.metadata or {}
        filename = str(meta.get("filename") or meta.get("source") or "uploaded document")
        page = int(meta["page"]) + 1 if meta.get("page") is not None else None
        section = meta.get("section")
        key = (filename, page, section)
        if key not in seen:
            seen.add(key)
            sources.append({"source": filename, "page": page, "section": section})
    return sources


def _answer_one(model_id: str, question: str, docs: list):
    started = perf_counter()
    model = get_chat_model(model_id)
    excerpts = []
    for index, doc in enumerate(docs, 1):
        meta = doc.metadata or {}
        filename = meta.get("filename") or meta.get("source") or "uploaded document"
        page = int(meta["page"]) + 1 if meta.get("page") is not None else None
        section = meta.get("section") or f"excerpt {index}"
        reference = f"{filename}, p. {page}" if page else f"{filename}, {section}"
        excerpts.append(f"[SOURCE: {reference}]\n{doc.page_content}")
    prompt = (
        f"{SYSTEM_INSTRUCTIONS}\n\nQUESTION:\n{question}\n\n"
        f"DOCUMENT EVIDENCE ({len(docs)} retrieved excerpts):\n"
        + ("\n\n---\n\n".join(excerpts) if excerpts else "No relevant evidence was retrieved.")
    )
    response = model.invoke(prompt)
    answer = str(response.content if hasattr(response, "content") else response).strip()
    citations = re.findall(r"\[([^\]]+)\]", answer)
    known_sources = {str((doc.metadata or {}).get("filename") or (doc.metadata or {}).get("source") or "uploaded document") for doc in docs}
    matched_citations = [citation for citation in citations if any(name.lower() in citation.lower() for name in known_sources)]
    citation_status = "matched_source_names" if matched_citations else ("missing" if not citations else "check_source_names")
    return {
        "model_id": model_id,
        "answer": answer,
        "latency_ms": round((perf_counter() - started) * 1000),
        "citation_status": citation_status,
        "status": "success",
    }


def run_multi_model_question(question: str, model_ids: list[str]):
    if not 1 <= len(model_ids) <= 5:
        raise ValueError("Select between 1 and 5 models.")
    if len(set(model_ids)) != len(model_ids):
        raise ValueError("Duplicate models are not allowed.")
    for model_id in model_ids:
        if not get_model_config(model_id):
            raise ValueError(f"Unknown model: {model_id}")

    docs = retrieve_evidence(question)
    sources = _source_list(docs)
    if not docs or not any(len(doc.page_content.strip()) > 30 for doc in docs):
        return {
            "question": question,
            "answers": [{
                "model_id": model_id,
                "model_name": get_model_config(model_id)["name"],
                "provider": get_model_config(model_id)["provider"],
                "answer": "The indexed documents did not return enough relevant evidence to answer this question reliably. Try rephrasing the question or adding a more relevant document.",
                "latency_ms": 0,
                "citation_status": "not_applicable",
                "status": "insufficient_evidence",
            } for model_id in model_ids],
            "sources": sources,
            "workflow_steps": ["query_analyzer", "shared_document_retrieval", "insufficient_evidence_guardrail"],
        }
    results = {}
    with ThreadPoolExecutor(max_workers=min(5, len(model_ids))) as pool:
        futures = {pool.submit(_answer_one, model_id, question, docs): model_id for model_id in model_ids}
        for future in as_completed(futures):
            model_id = futures[future]
            model = get_model_config(model_id)
            try:
                results[model_id] = future.result()
            except Exception as exc:
                unavailable_reason = mark_model_unavailable(model["provider"], model_id, exc)
                results[model_id] = {
                    "model_id": model_id,
                    "answer": "",
                    "latency_ms": None,
                    "status": "unavailable" if unavailable_reason else "error",
                    "error": unavailable_reason or "The provider request failed. Check this model's access and try again.",
                }
            results[model_id]["model_name"] = model["name"]
            results[model_id]["provider"] = model["provider"]
    return {
        "question": question,
        "answers": [results[model_id] for model_id in model_ids],
        "sources": sources,
        "workflow_steps": ["query_analyzer", "shared_document_retrieval", "parallel_model_generation", "source_reference_review"],
    }
