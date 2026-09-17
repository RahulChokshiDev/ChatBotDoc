import os, time, tempfile, warnings, uuid
warnings.filterwarnings("ignore")

import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocBot",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── API key ────────────────────────────────────────────────────────────────────
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    api_key = os.getenv("GOOGLE_API_KEY", "")

if not api_key:
    st.error("⚠️ GOOGLE_API_KEY not found. Add it in Streamlit secrets or as an environment variable.")
    st.stop()

os.environ["GOOGLE_API_KEY"] = api_key

# ── LangChain imports ──────────────────────────────────────────────────────────
from pathlib import Path
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage


# ── Cached resources ───────────────────────────────────────────────────────────
@st.cache_resource
def get_llm():
    return ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)


@st.cache_resource
def get_embeddings():
    return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")


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

Rules — no exceptions:
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


# ── Session state init ─────────────────────────────────────────────────────────
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
        "name":          f"Chat {st.session_state.session_counter}",
        "retriever":     None,
        "rephrase_chain": None,
        "answer_chain":  None,
        "chat_history":  [],   # LangChain messages (for memory)
        "messages":      [],   # Display messages [{role, content}]
        "doc_meta":      None,
    }
    st.session_state.active_id = sid


# Ensure at least one session exists
if not st.session_state.sessions:
    new_session()

sessions  = st.session_state.sessions
active_id = st.session_state.active_id


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:

    # Logo
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 18px">
      <div style="width:38px;height:38px;border-radius:10px;
                  background:linear-gradient(135deg,#f59e0b,#ea580c);
                  display:flex;align-items:center;justify-content:center;
                  font-size:18px;flex-shrink:0">✦</div>
      <div>
        <div style="font-size:1.15rem;font-weight:800;letter-spacing:-0.5px">DocBot</div>
        <div style="font-size:0.72rem;color:#a8a29e">Document-Grounded AI</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Conversations header
    col_label, col_new = st.columns([3, 2])
    with col_label:
        st.markdown(
            '<p style="font-size:0.65rem;font-weight:700;letter-spacing:1px;'
            'text-transform:uppercase;color:#8a847d;margin:6px 0 8px">Conversations</p>',
            unsafe_allow_html=True,
        )
    with col_new:
        if st.button("＋ New Chat", use_container_width=True, key="new_chat_btn"):
            new_session()
            st.rerun()

    # Session list
    for sid, s in list(sessions.items()):
        is_active  = sid == active_id
        msg_count  = len(s["messages"])
        sub_text   = f"{msg_count} msg{'s' if msg_count != 1 else ''}" if msg_count else "Empty"
        doc_label  = f"  ·  {s['doc_meta']['name']}" if s.get("doc_meta") else ""
        btn_label  = s["name"]

        col_btn, col_del = st.columns([5, 1])
        with col_btn:
            if st.button(
                btn_label,
                key=f"sess_{sid}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.active_id = sid
                st.rerun()

        with col_del:
            if st.button("✕", key=f"del_{sid}", help="Delete this chat"):
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
    st.markdown(
        '<p style="font-size:0.65rem;font-weight:700;letter-spacing:1px;'
        'text-transform:uppercase;color:#8a847d;margin-bottom:8px">Upload to Current Chat</p>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Drop a .txt or .pdf",
        type=["txt", "pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        if st.button("⚡ Load & Index", use_container_width=True, type="primary"):
            with st.spinner("Embedding chunks with Gemini…"):
                try:
                    cur_id = st.session_state.active_id
                    suffix = Path(uploaded_file.name).suffix.lower()

                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    loader   = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path, encoding="utf-8")
                    raw_docs = loader.load()
                    total_chars = sum(len(d.page_content) for d in raw_docs)

                    chunks = RecursiveCharacterTextSplitter(
                        chunk_size=800, chunk_overlap=150,
                        separators=["\n\n", "\n", ". ", " ", ""],
                    ).split_documents(raw_docs)

                    vector_store = FAISS.from_documents(chunks, get_embeddings())
                    time.sleep(3)

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
                    os.unlink(tmp_path)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error indexing document: {e}")

    # Show doc status for active session
    active = sessions.get(st.session_state.active_id, {})
    if active.get("doc_meta"):
        m = active["doc_meta"]
        st.success(f"**{m['name']}** ready")
        st.caption(f"{m['pages']} page(s)  ·  {m['chunks']} chunks  ·  {m['vectors']} vectors")


# ── Main chat area ─────────────────────────────────────────────────────────────
active_id = st.session_state.active_id
active    = sessions.get(active_id, {})

# Chat header
doc_name = active.get("doc_meta", {}).get("name", "No document loaded") if active.get("doc_meta") else "No document loaded"
h_col, btn_col = st.columns([5, 1])
with h_col:
    st.markdown(f"## {active.get('name', 'Chat')}")
    st.caption(f"📄 {doc_name}  ·  Answers come only from your document")
with btn_col:
    st.write("")
    if st.button("Clear chat", key="clear_chat"):
        active["messages"]     = []
        active["chat_history"] = []
        st.rerun()

st.divider()

# Display messages
if not active.get("messages"):
    st.markdown("""
    <div style="text-align:center;padding:80px 20px;color:#8a847d">
      <div style="font-size:3rem">💬</div>
      <div style="font-size:1.1rem;font-weight:600;margin-top:12px;color:#c9c4bf">
        Ask anything about your document
      </div>
      <div style="font-size:0.88rem;margin-top:8px">
        Upload a .txt or .pdf in the sidebar, then start chatting.
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for msg in active["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask anything about your document…"):
    if not active.get("retriever"):
        st.warning("Please upload and index a document first using the sidebar.")
    else:
        # Store and display user message
        active["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display bot answer
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
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
            st.markdown(answer)

        # Persist
        active["messages"].append({"role": "assistant", "content": answer})
        active["chat_history"].append(HumanMessage(content=prompt))
        active["chat_history"].append(AIMessage(content=answer))
        st.rerun()
