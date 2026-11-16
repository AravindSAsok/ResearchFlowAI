import os
import requests
import streamlit as st

st.set_page_config(page_title="ResearchFlow AI", page_icon="🔎", layout="wide")
API_URL = st.sidebar.text_input("Backend URL", os.getenv("RESEARCHFLOW_API", "http://localhost:8000")).rstrip("/")
st.markdown("""<style>
.stApp {background: #0b1120; color: #e5e7eb;}
[data-testid="stSidebar"] {background: #111827;}
.block-container {max-width: 1100px; padding-top: 2rem;}
</style>""", unsafe_allow_html=True)
st.title("🔎 ResearchFlow AI")
st.caption("Document intelligence • LangChain RAG • LangGraph workflows")
page = st.sidebar.radio("Workspace", ["Dashboard", "Document Library", "AI Chat", "Research Workspace", "Workflow Execution"])

def api_get(path):
    return requests.get(f"{API_URL}{path}", timeout=30)

def api_post(path, **kwargs):
    return requests.post(f"{API_URL}{path}", timeout=180, **kwargs)

if page == "Dashboard":
    st.subheader("Your research workspace")
    try:
        health = api_get("/health").json()
        docs = api_get("/documents").json().get("documents", [])
        a, b, c = st.columns(3)
        a.metric("Backend", health.get("status", "unknown"))
        b.metric("Indexed documents", len(docs))
        c.metric("AI workflow", "LangGraph")
        st.info("Upload PDFs in Document Library, then ask evidence-based questions in AI Chat.")
    except requests.RequestException as exc:
        st.error(f"Cannot reach backend at {API_URL}. Start FastAPI first. Details: {exc}")

elif page == "Document Library":
    st.subheader("Upload research documents")
    uploaded = st.file_uploader("Choose a PDF", type=["pdf"])
    if uploaded and st.button("Upload and index", type="primary"):
        with st.spinner("Extracting, splitting and indexing PDF..."):
            try:
                response = api_post("/documents/upload", files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")})
                if response.ok:
                    st.success(response.json())
                else:
                    st.error(response.text)
            except requests.RequestException as exc:
                st.error(str(exc))
    st.divider()
    try:
        docs = api_get("/documents").json().get("documents", [])
        for doc in docs:
            left, right = st.columns([5, 1])
            left.write(f"**{doc['filename']}** · {doc['chunks']} chunks")
            if right.button("Delete", key=doc["document_id"]):
                result = requests.delete(f"{API_URL}/documents/{doc['document_id']}", timeout=30)
                st.toast(result.text)
                st.rerun()
    except requests.RequestException as exc:
        st.error(str(exc))

elif page == "AI Chat":
    st.subheader("Ask your documents")
    try:
        saved = api_get("/conversations").json().get("conversations", [])
        choices = {"＋ New conversation": None}
        for item in saved:
            choices[f"#{item['id']} · {item['title']}"] = item["id"]
        current_id = st.session_state.get("conversation_id")
        labels = list(choices.keys())
        default_index = next((i for i, label in enumerate(labels) if choices[label] == current_id), 0)
        selected_label = st.selectbox(
            "Conversation", labels, index=default_index,
            key=f"conversation_picker_{current_id or 'new'}",
        )
        selected_id = choices[selected_label]
        if selected_id is None:
            st.session_state.pop("conversation_id", None)
        else:
            st.session_state["conversation_id"] = selected_id
    except requests.RequestException:
        st.caption("Conversation history is temporarily unavailable.")

    question = st.text_area("Your question", placeholder="What are the main findings in these papers?")
    if st.button("Ask ResearchFlow", type="primary", disabled=not question.strip()):
        with st.spinner("Running LangGraph research workflow..."):
            try:
                response = api_post("/chat", json={
                    "question": question,
                    "conversation_id": st.session_state.get("conversation_id"),
                })
                if response.ok:
                    result = response.json()
                    st.session_state["conversation_id"] = result["conversation_id"]
                    st.markdown("### Answer")
                    st.write(result["answer"])
                    st.markdown("### Sources")
                    for source in result.get("sources", []):
                        st.caption(f"{source.get('source')} · page {source.get('page')}")
                    st.session_state["last_steps"] = result.get("workflow_steps", [])
                else:
                    st.error(response.text)
            except requests.RequestException as exc:
                st.error(str(exc))

elif page == "Research Workspace":
    st.subheader("Structured research report")
    question = st.text_area("Research question", placeholder="Compare the approaches and identify limitations...")
    if st.button("Generate report", type="primary", disabled=len(question.strip()) < 8):
        with st.spinner("Researching indexed documents..."):
            try:
                response = api_post("/research", json={"question": question})
                if response.ok:
                    result = response.json()
                    st.markdown(result["report"])
                    st.markdown("#### Evidence sources")
                    for source in result.get("sources", []):
                        st.caption(f"{source.get('source')} · page {source.get('page')}")
                else:
                    st.error(response.text)
            except requests.RequestException as exc:
                st.error(str(exc))

else:
    st.subheader("Workflow execution trace")
    steps = st.session_state.get("last_steps", [])
    if steps:
        for index, step in enumerate(steps, 1):
            st.write(f"{index}. {step}")
    else:
        st.info("Run a question in AI Chat to see the LangGraph execution trace.")
    try:
        conversations = api_get("/conversations").json().get("conversations", [])
        st.markdown("### Recent conversations")
        for conversation in conversations:
            st.write(f"**#{conversation['id']}** — {conversation['title']} · {conversation['created_at']}")
            messages = api_get(f"/conversations/{conversation['id']}/messages").json().get("messages", [])
            with st.expander("View messages"):
                for message in messages:
                    st.markdown(f"**{message['role'].title()}:** {message['content']}")
    except requests.RequestException as exc:
        st.error(str(exc))
