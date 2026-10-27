import os, re, time, tempfile, warnings, uuid
warnings.filterwarnings("ignore")

import streamlit as st

# -- Page config ---------------------------------------------------------------
st.set_page_config(
    page_title="DocBot",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -- Custom CSS matching index.html design system ------------------------------
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

  :root {
    --surface-page: #0f1115;
    --surface-panel: #15181d;
    --surface-raised: #1c2027;
    --border: #232830;
    --border-strong: #3a4048;
    --border-subtle: #2b313b;
    --border-hover: #14b8a6;
    --border-ready: #047857;
    --accent-from: #f59e0b;
    --accent-to: #ea580c;
    --accent-light: #fbbf24;
    --on-accent: #1c1206;
    --bubble-user-from: #0f766e;
    --bubble-user-to: #115e59;
    --ink-primary: #e7e5e4;
    --ink-heading: #fafaf9;
    --ink-inverted: #ecfeff;
    --ink-muted: #a8a29e;
    --ink-faint: #8a847d;
    --ink-subtle: #c9c4bf;
    --status-ready-title: #34d399;
    --status-ready-value: #a7f3d0;
    --surface-ready: #0b2a1e;
  }

  /* Global overrides */
  .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
    background-color: var(--surface-page) !important;
    color: var(--ink-primary) !important;
    font-family: 'Inter', sans-serif !important;
  }
  section[data-testid="stSidebar"] {
    background-color: var(--surface-panel) !important;
    border-right: 1px solid var(--border) !important;
  }
  section[data-testid="stSidebar"] * {
    font-family: 'Inter', sans-serif !important;
  }
  [data-testid="stSidebarContent"] {
    background-color: var(--surface-panel) !important;
  }

  /* Hide Streamlit branding */
  #MainMenu, footer, header, [data-testid="stDecoration"],
  [data-testid="stToolbar"], .stDeployButton { display: none !important; }

  /* Sidebar divider */
  section[data-testid="stSidebar"] hr {
    border-color: var(--border) !important;
  }

  /* Buttons */
  section[data-testid="stSidebar"] button[kind="secondary"],
  section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"] {
    background-color: transparent !important;
    border: 1px solid var(--border-strong) !important;
    color: var(--ink-subtle) !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    font-weight: 500 !important;
    transition: border-color 0.2s, color 0.2s !important;
  }
  section[data-testid="stSidebar"] button[kind="secondary"]:hover,
  section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--accent-from) !important;
    color: var(--accent-light) !important;
  }

  section[data-testid="stSidebar"] button[kind="primary"],
  section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--accent-from), var(--accent-to)) !important;
    color: var(--on-accent) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
  }

  /* Active session button */
  section[data-testid="stSidebar"] button[kind="primary"] {
    border-left: 2px solid var(--accent-from) !important;
  }

  /* File uploader */
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    background-color: transparent !important;
  }
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] section {
    background-color: var(--surface-page) !important;
    border: 2px dashed var(--border-strong) !important;
    border-radius: 14px !important;
    padding: 20px 16px !important;
    transition: border-color 0.2s !important;
  }
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover {
    border-color: var(--border-hover) !important;
  }
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] span,
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] small,
  section[data-testid="stSidebar"] [data-testid="stFileUploader"] button {
    color: var(--ink-subtle) !important;
  }

  /* Captions */
  section[data-testid="stSidebar"] [data-testid="stCaption"] {
    color: var(--ink-faint) !important;
    font-size: 0.72rem !important;
  }

  /* Success message */
  section[data-testid="stSidebar"] [data-testid="stAlert"] {
    background-color: var(--surface-ready) !important;
    border: 1px solid var(--border-ready) !important;
    color: var(--status-ready-value) !important;
    border-radius: 12px !important;
  }

  /* Main area header */
  .main-header {
    padding: 18px 28px;
    background: var(--surface-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .main-header-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--ink-heading);
  }
  .main-header-sub {
    font-size: 0.78rem;
    color: var(--ink-muted);
    margin-top: 2px;
  }

  /* Chat container */
  [data-testid="stChatMessageContainer"] {
    background-color: transparent !important;
  }

  /* Chat messages */
  [data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 8px 0 !important;
  }

  /* Bot message bubble */
  .bot-bubble {
    max-width: 72%;
    padding: 13px 17px;
    border-radius: 16px;
    border-top-left-radius: 4px;
    background: var(--surface-raised);
    border: 1px solid var(--border-subtle);
    color: var(--ink-primary);
    font-size: 0.9rem;
    line-height: 1.65;
  }

  /* User message bubble */
  .user-bubble {
    max-width: 72%;
    padding: 13px 17px;
    border-radius: 16px;
    border-top-right-radius: 4px;
    background: linear-gradient(135deg, #0f766e, #115e59);
    color: var(--ink-inverted);
    font-size: 0.9rem;
    line-height: 1.65;
    margin-left: auto;
  }

  .bubble-time {
    font-size: 0.68rem;
    color: var(--ink-faint);
    margin-top: 5px;
  }
  .user-time {
    text-align: right;
  }

  /* Avatar overrides */
  [data-testid="stChatMessage"] [data-testid="stAvatar"],
  [data-testid="stChatMessage"] .stAvatar {
    width: 34px !important;
    height: 34px !important;
    border-radius: 50% !important;
  }

  /* Chat input */
  [data-testid="stChatInput"] {
    background-color: var(--surface-panel) !important;
    border-top: 1px solid var(--border) !important;
  }
  [data-testid="stChatInput"] textarea {
    background-color: var(--surface-raised) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 14px !important;
    color: var(--ink-primary) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
  }
  [data-testid="stChatInput"] textarea:focus {
    border-color: var(--border-hover) !important;
    box-shadow: 0 0 0 3px rgba(20,184,166,0.18) !important;
  }
  [data-testid="stChatInput"] textarea::placeholder {
    color: var(--ink-faint) !important;
  }
  [data-testid="stChatInput"] button {
    background: linear-gradient(135deg, var(--accent-from), var(--accent-to)) !important;
    border: none !important;
    border-radius: 10px !important;
    color: var(--on-accent) !important;
  }

  /* Clear chat button in main */
  .clear-btn {
    padding: 7px 14px;
    background: transparent;
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    color: var(--ink-subtle);
    cursor: pointer;
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    transition: border-color 0.2s, color 0.2s;
    text-decoration: none;
  }
  .clear-btn:hover {
    border-color: var(--ink-muted);
    color: #f5f5f4;
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    max-width: 420px;
    padding: 20px;
    margin: 80px auto;
  }
  .empty-icon {
    color: var(--ink-muted);
    margin-bottom: 16px;
    font-size: 3rem;
  }
  .empty-title {
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--ink-heading);
    margin-bottom: 8px;
  }
  .empty-sub {
    font-size: 0.88rem;
    color: var(--ink-muted);
    line-height: 1.6;
  }
  .empty-steps {
    margin-top: 24px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    text-align: left;
  }
  .empty-step {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface-panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
    color: var(--ink-subtle);
    font-size: 0.83rem;
  }
  .step-num {
    width: 24px;
    height: 24px;
    background: var(--border);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--accent-light);
    flex-shrink: 0;
  }

  /* Logo in sidebar */
  .logo-container {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0 18px;
  }
  .logo-mark {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #f59e0b, #ea580c);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
    color: #1c1206;
  }
  .logo-name {
    font-size: 1.3rem;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: var(--ink-heading);
  }
  .logo-tag {
    font-size: 0.72rem;
    color: var(--ink-muted);
    margin-top: 2px;
  }

  /* Section labels */
  .section-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    color: var(--ink-faint);
    margin-bottom: 10px;
  }

  /* Powered-by badges */
  .powered-by {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    padding: 14px 0;
    border-top: 1px solid var(--border);
    margin-top: 16px;
  }
  .badge {
    display: inline-block;
    background: var(--border);
    border: 1px solid var(--border-strong);
    border-radius: 20px;
    padding: 3px 10px;
    color: var(--ink-muted);
    font-size: 0.68rem;
    font-weight: 500;
  }

  /* Model info */
  .model-info {
    padding: 14px 0;
    border-top: 1px solid var(--border);
    margin-top: 12px;
  }
  .model-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }
  .model-label {
    font-size: 0.72rem;
    color: var(--ink-faint);
  }
  .model-value {
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--ink-subtle);
  }
  .model-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 0.68rem;
    font-weight: 500;
    padding: 3px 8px;
    border-radius: 20px;
    border: 1px solid var(--border-strong);
    background: var(--surface-raised);
    color: var(--ink-muted);
    margin-top: 4px;
  }
  .model-chip.active {
    border-color: var(--border-ready);
    background: var(--surface-ready);
    color: var(--status-ready-value);
  }
  .model-chip-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--border-strong);
    display: inline-block;
  }
  .model-chip.active .model-chip-dot {
    background: var(--status-ready-title);
  }

  /* Doc status card */
  .doc-ready-card {
    background: var(--surface-ready);
    border: 1px solid var(--border-ready);
    border-radius: 12px;
    padding: 12px;
    margin-top: 12px;
  }
  .doc-ready-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--status-ready-title);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .meta-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
  }
  .meta-key {
    font-size: 0.8rem;
    color: var(--ink-muted);
  }
  .meta-val {
    font-size: 0.8rem;
    font-weight: 500;
    color: var(--status-ready-value);
  }

  /* Warning message override */
  [data-testid="stAlert"][data-baseweb] {
    background-color: var(--surface-raised) !important;
    border: 1px solid var(--border-strong) !important;
    border-radius: 10px !important;
  }

  /* Spinner */
  [data-testid="stSpinner"] {
    color: var(--accent-light) !important;
  }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }

  /* Hide default streamlit padding */
  .block-container {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }

  /* Message animation */
  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bot-bubble, .user-bubble {
    animation: fadeUp 0.25s ease;
  }
</style>
""", unsafe_allow_html=True)

# -- API key -------------------------------------------------------------------
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    api_key = os.getenv("GOOGLE_API_KEY", "")

if not api_key:
    st.error("GOOGLE_API_KEY not found. Add it in Streamlit secrets or as an environment variable.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = api_key

# -- LangChain imports ---------------------------------------------------------
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage


# -- Cached resources ----------------------------------------------------------
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)


@st.cache_resource
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")


# -- Batch embedding -----------------------------------------------------------
_EMBED_BATCH_SIZE = 50
_BATCH_DELAY      = 1.5


def _embed_batch(texts: list, emb, max_retries: int = 8) -> list:
    for attempt in range(max_retries):
        try:
            return emb.embed_documents(texts)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                m = re.search(r"retry in (\d+)", msg)
                wait = int(m.group(1)) + 5 if m else 60
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Embedding failed after max retries.")


def build_vector_store(chunks, emb) -> FAISS:
    texts   = [c.page_content for c in chunks]
    metas   = [c.metadata     for c in chunks]
    vectors = []

    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        vectors.extend(_embed_batch(batch, emb))
        if i + _EMBED_BATCH_SIZE < len(texts):
            time.sleep(_BATCH_DELAY)

    return FAISS.from_embeddings(list(zip(texts, vectors)), emb, metadatas=metas)


@st.cache_resource
def get_prompts():
    contextualize = ChatPromptTemplate.from_messages([
        ("system",
         "Given the chat history and the latest user question, rewrite it as a standalone "
         "query. Do NOT answer. Return as-is if no rewrite needed."),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])
    qa = ChatPromptTemplate.from_messages([
        ("system", """\
You are a document assistant. Answer ONLY from the document excerpts in <context>.

Rules -- no exceptions:
1. Base your answer exclusively on <context>.
2. Do NOT use training knowledge or outside information.
3. If the answer is not in <context>, respond with exactly: "I don't have that information."
4. Do not guess or extrapolate beyond what is explicitly stated.

<context>
{context}
</context>"""),
        MessagesPlaceholder("chat_history"),
        ("human", "{question}"),
    ])
    return contextualize, qa


# -- Session state init --------------------------------------------------------
if "sessions" not in st.session_state:
    st.session_state.sessions = {}
if "active_id" not in st.session_state:
    st.session_state.active_id = None
if "session_counter" not in st.session_state:
    st.session_state.session_counter = 0


def new_session():
    st.session_state.session_counter += 1
    sid = str(uuid.uuid4())
    st.session_state.sessions[sid] = {
        "name":           f"Chat {st.session_state.session_counter}",
        "retriever":      None,
        "rephrase_chain": None,
        "answer_chain":   None,
        "chat_history":   [],
        "messages":       [],
        "doc_meta":       None,
    }
    st.session_state.active_id = sid


if not st.session_state.sessions:
    new_session()

sessions  = st.session_state.sessions
active_id = st.session_state.active_id


# -- Sidebar -------------------------------------------------------------------
with st.sidebar:

    # Logo
    st.markdown("""
    <div class="logo-container">
      <div class="logo-mark">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path d="M12 3l1.8 6.2L20 11l-6.2 1.8L12 19l-1.8-6.2L4 11l6.2-1.8L12 3z" fill="currentColor"/>
        </svg>
      </div>
      <div>
        <div class="logo-name">DocBot</div>
        <div class="logo-tag">Document-Grounded AI</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Conversations header
    col_label, col_new = st.columns([3, 2])
    with col_label:
        st.markdown('<p class="section-label">Conversations</p>', unsafe_allow_html=True)
    with col_new:
        if st.button("+ New Chat", use_container_width=True, key="new_chat_btn"):
            new_session()
            st.rerun()

    # Session list
    for sid, s in list(sessions.items()):
        is_active  = sid == active_id
        msg_count  = len(s["messages"])
        sub_text   = f"{msg_count} msg{'s' if msg_count != 1 else ''}" if msg_count else "Empty"
        doc_label  = f"  ·  {s['doc_meta']['name']}" if s.get("doc_meta") else ""

        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            if st.button(
                s["name"],
                key=f"sess_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_id = sid
                st.rerun()

        with col_del:
            if st.button("x", key=f"del_{sid}", help="Delete this chat"):
                del sessions[sid]
                remaining = list(sessions.keys())
                if not remaining:
                    new_session()
                elif active_id == sid:
                    st.session_state.active_id = remaining[-1]
                st.rerun()

        st.caption(f"{sub_text}{doc_label}")

    st.divider()

    # Upload section
    st.markdown('<p class="section-label">Upload to Current Chat</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop a .txt or .pdf",
        type=["txt", "pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        if st.button("Load & Index", use_container_width=True, type="primary"):
            with st.spinner("Embedding chunks with Gemini..."):
                try:
                    cur_id = st.session_state.active_id
                    suffix = Path(uploaded_file.name).suffix.lower()

                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    try:
                        loader   = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path, encoding="utf-8")
                        raw_docs = loader.load()
                        total_chars = sum(len(d.page_content) for d in raw_docs)

                        chunks = RecursiveCharacterTextSplitter(
                            chunk_size=2000, chunk_overlap=200,
                            separators=["\n\n", "\n", ". ", " ", ""],
                        ).split_documents(raw_docs)

                        vector_store = build_vector_store(chunks, get_embeddings())
                    finally:
                        os.unlink(tmp_path)

                    llm = get_llm()
                    ctx_prompt, qa_prompt = get_prompts()

                    sessions[cur_id].update({
                        "name":           uploaded_file.name,
                        "retriever":      vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4}),
                        "rephrase_chain": ctx_prompt | llm | StrOutputParser(),
                        "answer_chain":   qa_prompt  | llm | StrOutputParser(),
                        "chat_history":   [],
                        "messages":       [],
                        "doc_meta": {
                            "name":    uploaded_file.name,
                            "pages":   len(raw_docs),
                            "chars":   total_chars,
                            "chunks":  len(chunks),
                            "vectors": vector_store.index.ntotal,
                        },
                    })
                    st.rerun()

                except Exception as e:
                    st.error(f"Error indexing document: {e}")

    # Doc status card
    active = sessions.get(st.session_state.active_id, {})
    if active.get("doc_meta"):
        m = active["doc_meta"]
        st.markdown(f"""
        <div class="doc-ready-card">
          <div class="doc-ready-title">
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            Document ready
          </div>
          <div class="meta-grid">
            <span class="meta-key">File</span><span class="meta-val">{m['name']}</span>
            <span class="meta-key">Pages</span><span class="meta-val">{m['pages']}</span>
            <span class="meta-key">Characters</span><span class="meta-val">{m['chars']:,}</span>
            <span class="meta-key">Chunks</span><span class="meta-val">{m['chunks']}</span>
            <span class="meta-key">Vectors</span><span class="meta-val">{m['vectors']}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Model info
    embed_model = "gemini-embedding-2"
    llm_model = "gemini-3.6-flash"
    st.markdown(f"""
    <div class="model-info">
      <p class="section-label">Models</p>
      <div class="model-row">
        <span class="model-label">LLM</span>
        <span class="model-value">{llm_model}</span>
      </div>
      <div class="model-row">
        <span class="model-label">Embedding</span>
        <span class="model-value">{embed_model}</span>
      </div>
      <div style="margin-top:8px">
        <span class="model-label">Active embedding</span>
        <div style="margin-top:4px">
          <span class="model-chip active">
            <span class="model-chip-dot"></span>{embed_model}
          </span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Powered-by badges
    st.markdown("""
    <div class="powered-by">
      <span class="badge">LangChain</span>
      <span class="badge">Gemini</span>
      <span class="badge">FAISS</span>
      <span class="badge">Streamlit</span>
    </div>
    """, unsafe_allow_html=True)


# -- Main chat area ------------------------------------------------------------
active_id = st.session_state.active_id
active    = sessions.get(active_id, {})

# Chat header
doc_name = active.get("doc_meta", {}).get("name", "No document loaded") if active.get("doc_meta") else "No document loaded"
st.markdown(f"""
<div class="main-header">
  <div>
    <div class="main-header-title">{doc_name}</div>
    <div class="main-header-sub">Answers come only from your document</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Clear chat button
h_col, btn_col = st.columns([6, 1])
with btn_col:
    if st.button("Clear chat", key="clear_chat"):
        active["messages"]     = []
        active["chat_history"] = []
        st.rerun()

# Display messages or empty state
if not active.get("messages"):
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">
        <svg width="40" height="40" viewBox="0 0 24 24">
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4H6.5A2.5 2.5 0 0 1 4 13.5v-8z"
            fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="empty-title">Ask anything about your document</div>
      <div class="empty-sub">Upload a file on the left and start asking questions. The bot answers only from your document.</div>
      <div class="empty-steps">
        <div class="empty-step"><span class="step-num">1</span>Drop a .txt or .pdf in the sidebar</div>
        <div class="empty-step"><span class="step-num">2</span>Click "Load & Index" to process</div>
        <div class="empty-step"><span class="step-num">3</span>Type any question about your file</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in active["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(f'<div class="user-bubble">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            with st.chat_message("assistant"):
                st.markdown(f'<div class="bot-bubble">{msg["content"]}</div>', unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask anything about your document..."):
    if not active.get("retriever"):
        st.warning("Please upload and index a document first using the sidebar.")
    else:
        active["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(f'<div class="user-bubble">{prompt}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                lc_history = active["chat_history"]

                standalone = (
                    active["rephrase_chain"].invoke({"question": prompt, "chat_history": lc_history})
                    if lc_history else prompt
                )

                docs    = active["retriever"].invoke(standalone)
                context = "\n\n---\n\n".join(d.page_content for d in docs)
                answer  = active["answer_chain"].invoke({
                    "question":     prompt,
                    "chat_history": lc_history,
                    "context":      context,
                })
            st.markdown(f'<div class="bot-bubble">{answer}</div>', unsafe_allow_html=True)

        active["messages"].append({"role": "assistant", "content": answer})
        active["chat_history"].append(HumanMessage(content=prompt))
        active["chat_history"].append(AIMessage(content=answer))
        st.rerun()
