import os
import requests
import streamlit as st

st.set_page_config(
    page_title="ResearchFlow AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = st.sidebar.text_input(
    "Backend endpoint",
    os.getenv("RESEARCHFLOW_API", "http://127.0.0.1:8001"),
    help="FastAPI backend URL",
).rstrip("/")

# --- Visual system ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {
  --rf-bg: #080b14; --rf-panel: #101625; --rf-panel-2: #141d2e;
  --rf-line: rgba(148,163,184,.14); --rf-text: #edf2ff; --rf-muted: #91a0b8;
  --rf-cyan: #63e6e2; --rf-violet: #9b8cff; --rf-green: #8be0b0;
}
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background:
  radial-gradient(ellipse at 80% -10%, rgba(99,102,241,.16), transparent 36%),
  radial-gradient(ellipse at 0% 35%, rgba(20,184,166,.08), transparent 32%), var(--rf-bg); color:var(--rf-text); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#0e1422 0%,#0a0f1b 100%); border-right:1px solid var(--rf-line); }
[data-testid="stSidebar"] > div { padding-top:1.2rem; }
.block-container { max-width:1420px; padding:2rem 2.5rem 3.5rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.035em; color:var(--rf-text); }
h1 { font-size:2.25rem !important; }
p, label, .stMarkdown { color:#d7dfef; }
[data-testid="stMetric"] { background:linear-gradient(145deg,rgba(20,29,46,.96),rgba(13,19,32,.96)); border:1px solid var(--rf-line); border-radius:18px; padding:18px 20px; }
[data-testid="stMetricLabel"] { color:var(--rf-muted) !important; }
[data-testid="stMetricValue"] { color:var(--rf-text) !important; font-family:'Space Grotesk',sans-serif; }
.stButton > button { border-radius:12px; border:1px solid var(--rf-line); background:#172238; color:var(--rf-text); font-weight:600; min-height:2.65rem; transition:all .18s ease; }
.stButton > button:hover { border-color:rgba(99,230,226,.65); color:#fff; background:#1b2c43; transform:translateY(-1px); }
.stButton > button[kind="primary"] { background:linear-gradient(105deg,#5eead4,#8b80ff); color:#07111b; border:0; box-shadow:0 8px 28px rgba(99,102,241,.18); }
.stButton > button[kind="primary"]:hover { filter:brightness(1.08); color:#07111b; }
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div { background:#111a2b !important; color:var(--rf-text) !important; border-color:var(--rf-line) !important; border-radius:12px !important; }
[data-testid="stChatInput"] { border-color:rgba(99,230,226,.28) !important; background:#111a2b !important; border-radius:18px !important; box-shadow:0 12px 40px rgba(0,0,0,.24); }
[data-testid="stChatMessage"] { background:rgba(17,26,43,.7); border:1px solid var(--rf-line); border-radius:18px; padding:1rem 1.1rem; }
[data-testid="stExpander"] { border:1px solid var(--rf-line); border-radius:14px; background:rgba(16,22,37,.72); }
hr { border-color:var(--rf-line) !important; }
.eyebrow { color:var(--rf-cyan); text-transform:uppercase; letter-spacing:.16em; font-size:.72rem; font-weight:700; }
.hero { padding:26px 30px; border:1px solid rgba(148,163,184,.18); border-radius:24px;
  background:linear-gradient(115deg,rgba(25,39,62,.95),rgba(20,22,48,.88) 58%,rgba(35,26,67,.78));
  box-shadow:0 18px 55px rgba(0,0,0,.22); margin:8px 0 24px; }
.hero h1 { margin:.3rem 0 .45rem; }
.hero p { color:#aab8cf; margin:0; max-width:760px; }
.panel { padding:20px 22px; border:1px solid var(--rf-line); border-radius:18px; background:linear-gradient(145deg,rgba(20,29,46,.88),rgba(13,19,32,.88)); }
.muted { color:var(--rf-muted); }
.brand { font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.25rem; letter-spacing:-.04em; }
.brand-mark { display:inline-flex; width:34px; height:34px; align-items:center; justify-content:center; border-radius:11px; margin-right:9px; color:#07111b; background:linear-gradient(135deg,#5eead4,#a78bfa); }
[data-testid="stSidebar"] .stButton > button { min-height:3.35rem; width:100%; text-align:left; justify-content:flex-start; padding:.75rem 1rem; border-radius:14px; font-size:.98rem; font-weight:600; background:rgba(23,34,56,.72); }
[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:linear-gradient(105deg,rgba(94,234,212,.20),rgba(139,128,255,.22)); color:#f4f7ff; border:1px solid rgba(99,230,226,.55); box-shadow:inset 3px 0 0 #63e6e2; }
[data-testid="stSidebar"] .stCaption { color:var(--rf-muted); }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

def api_get(path):
    response = requests.get(f"{API_URL}{path}", timeout=30)
    response.raise_for_status()
    return response

def api_post(path, timeout=180, **kwargs):
    response = requests.post(f"{API_URL}{path}", timeout=timeout, **kwargs)
    response.raise_for_status()
    return response

def error_detail(exc):
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            return exc.response.json().get("detail", exc.response.text)
        except ValueError:
            return exc.response.text
    return str(exc)

def hero(kicker, title, description):
    st.markdown(
        f'<section class="hero"><div class="eyebrow">{kicker}</div>'
        f'<h1>{title}</h1><p>{description}</p></section>',
        unsafe_allow_html=True,
    )

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "last_steps" not in st.session_state:
    st.session_state.last_steps = []

# --- Sidebar navigation ---
def navigate_to(page_name):
    # Streamlit runs this callback before rebuilding the navigation widget.
    st.session_state.workspace_page = page_name

st.sidebar.markdown(
    '<div class="brand"><span class="brand-mark">✦</span>ResearchFlow <span style="color:#8b80ff">AI</span></div>',
    unsafe_allow_html=True,
)
st.sidebar.caption("YOUR PERSONAL RESEARCH WORKSPACE")
st.sidebar.divider()
if "workspace_page" not in st.session_state:
    st.session_state.workspace_page = "Overview"

st.sidebar.caption("WORKSPACE")
workspace_pages = ["Overview", "Documents", "Model Library", "AI Chat", "Research Studio", "Workflow Trace"]
for workspace_option in workspace_pages:
    st.sidebar.button(
        workspace_option,
        key=f"nav_{workspace_option.lower().replace(' ', '_')}",
        type="primary" if st.session_state.workspace_page == workspace_option else "secondary",
        use_container_width=True,
        on_click=navigate_to,
        args=(workspace_option,),
    )
page = st.session_state.workspace_page
st.sidebar.divider()
try:
    health = api_get("/health").json()
    st.sidebar.markdown("🟢 **Backend connected**")
except requests.RequestException:
    st.sidebar.markdown("🔴 **Backend offline**")
st.sidebar.caption(API_URL)

# --- Overview ---
if page == "Overview":
    hero("YOUR KNOWLEDGE, CONNECTED", "Research at the speed of thought.",
         "A focused workspace to explore your PDFs, ask evidence-backed questions, and turn scattered papers into clear research.")
    try:
        health_data = api_get("/health").json()
        docs = api_get("/documents").json().get("documents", [])
        conversations = api_get("/conversations").json().get("conversations", [])
        a, b, c = st.columns(3)
        a.metric("Indexed documents", len(docs), help="PDFs available for retrieval")
        b.metric("Conversations", len(conversations), help="Saved research chats")
        c.metric("AI engine", "LangGraph", help="Retrieval and evidence workflow")
        st.markdown("### Your workspace")
        left, right = st.columns([1.15, .85], gap="large")
        with left:
            st.markdown('<div class="panel"><div class="eyebrow">START HERE</div><h3>Ask better questions.</h3><p class="muted">Chat with your indexed documents, trace the evidence, and keep every conversation organised.</p></div>', unsafe_allow_html=True)
            st.button(
                "Open AI Chat →",
                type="primary",
                use_container_width=True,
                on_click=navigate_to,
                args=("AI Chat",),
            )
        with right:
            st.markdown('<div class="panel"><div class="eyebrow">QUICK TIP</div><h3>Ground every answer.</h3><p class="muted">Upload PDFs first. ResearchFlow retrieves relevant passages and shows the source document and page.</p></div>', unsafe_allow_html=True)
    except requests.RequestException as exc:
        st.error(f"Cannot reach the backend: {error_detail(exc)}")

# --- Documents ---
elif page == "Documents":
    hero("KNOWLEDGE LIBRARY", "Your research, in one place.",
         "Upload PDF, Word or TXT files, or paste copied text. ResearchFlow extracts and indexes the content for document-grounded answers.")
    uploaded = st.file_uploader(
        "Upload a document",
        type=["pdf", "doc", "docx", "txt"],
        help="Supported: PDF, legacy DOC (Microsoft Word or Antiword required), DOCX and TXT.",
    )
    if uploaded and st.button("Upload and index document", type="primary"):
        content_type = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
        }.get(os.path.splitext(uploaded.name)[1].lower(), "application/octet-stream")
        with st.spinner("Extracting text and building the searchable index..."):
            try:
                result = api_post(
                    "/documents/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), content_type)},
                ).json()
                st.success(f"{result.get('filename')} · {result.get('chunks')} chunks · {result.get('status')}")
                st.rerun()
            except requests.RequestException as exc:
                st.error(error_detail(exc))

    with st.expander("＋ Paste copied text"):
        pasted_name = st.text_input("Document name", value="Copied research.txt")
        pasted_text = st.text_area("Paste text to index", height=180, placeholder="Copy text from a paper, website, notes, or report and paste it here...")
        if st.button("Index pasted text", type="primary", disabled=len(pasted_text.strip()) < 20):
            try:
                result = api_post("/documents/text", json={
                    "filename": pasted_name,
                    "text": pasted_text,
                }).json()
                st.success(f"{result.get('filename')} · {result.get('chunks')} chunks indexed")
                st.rerun()
            except requests.RequestException as exc:
                st.error(error_detail(exc))

    st.markdown("### Indexed documents")
    try:
        docs = api_get("/documents").json().get("documents", [])
        if not docs:
            st.info("Your library is empty. Upload a PDF, Word or TXT file, or paste text to get started.")
        for doc in docs:
            left, middle, right = st.columns([5, 2, 1])
            left.markdown(f"**📄 {doc['filename']}**")
            middle.caption(f"{doc.get('file_type', 'file').upper()} · {doc['chunks']} chunks")
            if right.button("Delete", key=f"delete_{doc['document_id']}"):
                result = requests.delete(f"{API_URL}/documents/{doc['document_id']}", timeout=30)
                if result.ok:
                    st.toast("Document removed from the index.")
                    st.rerun()
                else:
                    st.error(error_detail(requests.HTTPError(response=result)))
    except requests.RequestException as exc:
        st.error(error_detail(exc))

# --- Model library ---
elif page == "Model Library":
    hero("MODEL DISCOVERY", "Find your best research models.",
         "Browse the chat-capable models listed by your connected providers, including paid models. Providers may reject requests when billing, credits, permissions or quotas are unavailable.")
    try:
        model_payload = api_get("/models").json()
        catalogue = model_payload.get("models", [])
        recommendations = model_payload.get("recommended_models", [])
        if catalogue:
            configured = sum(1 for item in catalogue if item["configured"])
            provider_count = len({item["provider"] for item in catalogue})
            a, b, c = st.columns(3)
            a.metric("Live models", len(catalogue))
            b.metric("Providers connected", provider_count)
            c.metric("Routes with API keys", configured)
            st.info("Research-fit score is a metadata heuristic, not a measured accuracy score. This catalogue includes free and paid models. ResearchFlow does not add credits, enable billing, or switch to another provider automatically; a provider may reject a paid request if your account has no billing or credits.")
            if recommendations:
                st.markdown("### ✦ Recommended starting shortlist")
                st.caption("The recommender prioritises high-fit candidates and provider diversity. These are suggested starting points, not guaranteed winners.")
                cols = st.columns(len(recommendations))
                for col, item in zip(cols, recommendations):
                    with col:
                        st.markdown(f"**{item['name']}**")
                        st.caption(item["provider_name"])
                        st.metric("Fit", f"{item['fit_score']}/100")
                        st.caption(item.get("cost_label", "Provider pricing varies"))
            st.divider()
            filter_left, filter_right = st.columns([2, 1])
            with filter_left:
                search_text = st.text_input("Search models", placeholder="Search model name or model ID...")
            with filter_right:
                provider_names = ["All providers"] + sorted({item["provider_name"] for item in catalogue})
                provider_filter = st.selectbox("Provider", provider_names)
            filtered = [
                item for item in catalogue
                if (not search_text or search_text.lower() in (item["name"] + " " + item["id"]).lower())
                and (provider_filter == "All providers" or item["provider_name"] == provider_filter)
            ]
            st.markdown(f"### Model catalogue · {len(filtered)}")
            for item in filtered:
                left, middle, right = st.columns([4, 1, 2])
                with left:
                    st.markdown(f"**{item['name']}** · {item['provider_name']}")
                    context_label = f"{item['context_window']:,} tokens" if item.get("context_window") else "Context not published"
                    st.caption(f"{context_label} · {item.get('cost_label', 'Provider pricing varies')}")
                    st.caption(" · ".join(item.get("recommendation_reasons", [])))
                with middle:
                    st.metric("Fit score", f"{item['fit_score']}/100")
                with right:
                    st.caption(item.get("access_label", "Provider key status unknown"))
                    if item.get("availability_reason"):
                        st.warning(item["availability_reason"])
                    else:
                        st.caption("Provider-listed candidate; endpoint support can vary")
                st.divider()
        else:
            st.warning("No model catalogue returned by the backend.")
    except requests.RequestException as exc:
        st.error(f"Could not load model catalogue: {error_detail(exc)}")

# --- Multi-model chat ---
elif page == "AI Chat":
    hero("MULTI-MODEL RESEARCH", "One question. Up to five expert answers.",
         "Every selected model receives the same retrieved document evidence. Compare the answers side by side by switching between model tabs.")
    try:
        model_payload = api_get("/models").json()
        model_data = model_payload.get("models", [])
        recommended_models = model_payload.get("recommended_models", [])
        safe_default_models = model_payload.get("safe_default_models", [])
        docs = api_get("/documents").json().get("documents", [])
    except requests.RequestException as exc:
        model_data, docs = [], []
        st.error(f"Could not load models or documents: {error_detail(exc)}")

    if not docs:
        st.warning("Upload or paste a document in Documents before starting a comparison.")
    if model_data:
        model_lookup = {item["id"]: item for item in model_data}
        selectable_models = [item for item in model_data if item.get("available", item["configured"])]
        selectable_ids = {item["id"] for item in selectable_models}
        initial_recommendations = [item["id"] for item in safe_default_models[:5] if item["id"] in selectable_ids]
        if "selected_model_ids" in st.session_state:
            st.session_state.selected_model_ids = [model_id for model_id in st.session_state.selected_model_ids if model_id in selectable_ids]
        st.caption("Only models explicitly listed at zero token price are preselected. Paid models remain selectable manually. Models rejected by a provider for billing, quota or access reasons are temporarily hidden from selection; retry after 30 minutes or restart the backend.")
        if not selectable_models:
            st.warning("No models are currently selectable. Check provider keys, billing/credits, quotas or access permissions.")
        selected_models = st.multiselect(
            "Choose models (maximum 5)",
            options=[item["id"] for item in selectable_models],
            default=initial_recommendations,
            format_func=lambda model_id: (
                f"{model_lookup[model_id]['name']} · {model_lookup[model_id]['provider_name']} · fit {model_lookup[model_id]['fit_score']}/100"
                + ("" if model_lookup[model_id]["configured"] else " · API key needed")
            ),
            max_selections=5,
            key="selected_model_ids",
            help="The catalogue includes free and paid models. Provider billing, quotas and endpoint permissions determine whether a request succeeds.",
        )
        configured_count = sum(1 for model_id in selected_models if model_lookup[model_id]["configured"])
        st.caption(f"{len(selected_models)}/5 selected · {configured_count} selected model(s) configured")
        unavailable = [model_lookup[model_id]["name"] for model_id in selected_models if not model_lookup[model_id]["configured"]]
        if unavailable:
            st.info("Add the required provider keys to .env and restart the backend: " + ", ".join(unavailable))
    else:
        selected_models = []
        configured_count = 0
        st.warning("Model catalogue is unavailable. Check the backend connection.")

    prompt = st.chat_input(
        "Ask a question about your indexed documents…",
        key="multi_model_prompt",
        max_chars=2000,
        disabled=not docs or not selected_models or configured_count != len(selected_models),
    )
    if prompt and prompt.strip():
        clean_prompt = prompt.strip()
        st.session_state.last_comparison = None
        st.markdown(f"**Your question:** {clean_prompt}")
        with st.spinner(f"Retrieving document evidence and querying {configured_count} model(s) in parallel..."):
            try:
                result = api_post("/compare", timeout=240, json={
                    "question": clean_prompt,
                    "model_ids": selected_models,
                }).json()
                st.session_state.last_comparison = result
                st.session_state.last_steps = result.get("workflow_steps", [])
            except requests.HTTPError as exc:
                st.error(f"Comparison failed: {error_detail(exc)}")
            except requests.Timeout:
                st.error("The comparison timed out. Try fewer models or a shorter question.")
            except requests.RequestException as exc:
                st.error(f"Could not reach ResearchFlow API: {error_detail(exc)}")

    comparison = st.session_state.get("last_comparison")
    if comparison:
        st.markdown("### Model answers")
        answers = comparison.get("answers", [])
        displayable = [item for item in answers if item.get("status") in {"success", "insufficient_evidence"}]
        if displayable:
            tabs = st.tabs([f"{item['model_name']} · {item['latency_ms']} ms" for item in displayable])
            for tab, item in zip(tabs, displayable):
                with tab:
                    st.markdown(f"**{item['provider'].title()}**")
                    if item.get("status") == "insufficient_evidence":
                        st.warning(item["answer"])
                    else:
                        st.caption(f"Citation check: {item.get('citation_status', 'not checked')} · Response time: {item['latency_ms']} ms")
                        st.markdown(item["answer"])
        for item in answers:
            if item.get("status") == "unavailable":
                st.warning(f"{item.get('model_name', item['model_id'])}: {item.get('error', 'Temporarily unavailable')}. It has been hidden from model selection temporarily.")
            elif item.get("status") == "error":
                st.error(f"{item.get('model_name', item['model_id'])}: {item.get('error', 'Model request failed')}")
        if comparison.get("sources"):
            with st.expander(f"Shared document evidence · {len(comparison['sources'])} source reference(s)", expanded=True):
                for source in comparison["sources"]:
                    location = f"page {source['page']}" if source.get("page") else source.get("section") or "text section"
                    st.caption(f"{source.get('source')} · {location}")
        st.caption("All answers use the same retrieved excerpts. Model responses may differ; verify important claims against the cited source text.")

# --- Research studio ---
elif page == "Research Studio":
    hero("DEEP RESEARCH", "Go beyond a quick answer.",
         "Choose one model to decompose your question, investigate the indexed documents, and synthesize a structured report.")
    try:
        research_payload = api_get("/models").json()
        research_models = [item for item in research_payload.get("models", []) if item.get("available", item["configured"])]
        safe_default_ids = {item["id"] for item in research_payload.get("safe_default_models", [])}
        research_models.sort(key=lambda item: item["id"] not in safe_default_ids)
    except requests.RequestException:
        research_models = []
    if research_models:
        research_model_id = st.selectbox(
            "Research model",
            options=[item["id"] for item in research_models],
            format_func=lambda model_id: next(
                f"{item['name']} · {item['provider_name']}" for item in research_models if item["id"] == model_id
            ),
            key="research_model_id",
        )
    else:
        research_model_id = None
        st.warning("No currently available model. Check provider keys, billing/credits, quotas or access permissions.")
    question = st.text_area("Research question", placeholder="Compare the approaches in these papers and identify their limitations...", height=110)
    if st.button("Generate research report", type="primary", disabled=len(question.strip()) < 8 or not research_model_id):
        with st.spinner("Decomposing the question, gathering evidence and synthesising findings..."):
            try:
                result = api_post("/research", timeout=240, json={
                    "question": question.strip(),
                    "model_id": research_model_id,
                }).json()
                st.markdown(result["report"])
                st.markdown("### Evidence sources")
                for source in result.get("sources", []):
                    location = f"page {source['page']}" if source.get("page") else source.get("section") or "text section"
                    st.caption(f"{source.get('source')} · {location}")
                st.session_state.last_steps = result.get("workflow_steps", [])
            except requests.RequestException as exc:
                st.error(error_detail(exc))

# --- Workflow trace ---
else:
    hero("UNDER THE HOOD", "See how the answer was built.",
         "Follow the LangGraph workflow from query analysis through retrieval, evidence evaluation and answer review.")
    steps = st.session_state.last_steps
    if steps:
        for index, step in enumerate(steps, 1):
            st.markdown(f'<div class="panel" style="margin:8px 0"><span class="eyebrow">STEP {index:02d}</span><h3 style="margin:.35rem 0">{step.replace("_", " ").title()}</h3></div>', unsafe_allow_html=True)
    else:
        st.info("Run a question in AI Chat or Research Studio to populate the workflow trace.")
    try:
        conversations = api_get("/conversations").json().get("conversations", [])
        if conversations:
            st.markdown("### Recent research sessions")
            for conversation in conversations[:8]:
                with st.expander(f"#{conversation['id']} · {conversation['title']}"):
                    messages = api_get(f"/conversations/{conversation['id']}/messages").json().get("messages", [])
                    for message in messages:
                        st.markdown(f"**{message['role'].title()}**")
                        st.write(message["content"])
    except requests.RequestException as exc:
        st.error(error_detail(exc))
