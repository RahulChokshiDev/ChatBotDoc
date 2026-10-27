import os, re, time, warnings
warnings.filterwarnings("ignore")

os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6KubRtdY-jkA8ESORSKdwxx3Hw5Oc62Y7ExRcQxhXNSIw"

import gradio as gr
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# ── Global state ───────────────────────────────────────────────────────────────
retriever      = None
rephrase_chain = None
answer_chain   = None
doc_meta       = {}

# ── LLM & prompts ─────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="models/gemini-3.6-flash", temperature=0)

contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Given the chat history and the latest user question, rewrite it as a standalone "
     "query. Do NOT answer. Return as-is if no rewrite needed."),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

qa_prompt = ChatPromptTemplate.from_messages([
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


def format_docs(docs):
    return "\n\n---\n\n".join(d.page_content for d in docs)


# ── Batch embedding helpers ────────────────────────────────────────────────────
_EMBED_BATCH_SIZE = 50
_BATCH_DELAY      = 1.5


def _embed_batch(texts: list, emb, max_retries: int = 5) -> list:
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


def _build_vector_store(chunks, emb):
    texts   = [c.page_content for c in chunks]
    metas   = [c.metadata     for c in chunks]
    vectors = []
    for i in range(0, len(texts), _EMBED_BATCH_SIZE):
        batch = texts[i : i + _EMBED_BATCH_SIZE]
        vectors.extend(_embed_batch(batch, emb))
        if i + _EMBED_BATCH_SIZE < len(texts):
            time.sleep(_BATCH_DELAY)
    return FAISS.from_embeddings(list(zip(texts, vectors)), emb, metadatas=metas)


# ── Backend: load + index ─────────────────────────────────────────────────────
def load_and_index(file_obj):
    global retriever, rephrase_chain, answer_chain, doc_meta

    if file_obj is None:
        return (
            _status_html("idle", "No file selected. Drop a document above."),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )

    path = file_obj.name
    ext  = Path(path).suffix.lower()

    try:
        loader      = PyPDFLoader(path) if ext == ".pdf" else TextLoader(path, encoding="utf-8")
        raw_docs    = loader.load()
        total_chars = sum(len(d.page_content) for d in raw_docs)

        chunks = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        ).split_documents(raw_docs)

        embeddings   = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        vector_store = _build_vector_store(chunks, embeddings)

        retriever      = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        rephrase_chain = contextualize_prompt | llm | StrOutputParser()
        answer_chain   = qa_prompt | llm | StrOutputParser()

        doc_meta = {
            "name":    Path(path).name,
            "pages":   len(raw_docs),
            "chars":   total_chars,
            "chunks":  len(chunks),
            "vectors": vector_store.index.ntotal,
        }

        html = _status_html("ready", None, doc_meta)
        return html, gr.update(interactive=True), gr.update(interactive=True)

    except Exception as e:
        return (
            _status_html("error", str(e)),
            gr.update(interactive=False),
            gr.update(interactive=False),
        )


def _status_html(state, message=None, meta=None):
    if state == "idle":
        return f"""
        <div class="status-card idle">
          <div class="status-icon">📄</div>
          <div class="status-text">{message or "Waiting for document…"}</div>
        </div>"""

    if state == "error":
        return f"""
        <div class="status-card error">
          <div class="status-icon">❌</div>
          <div class="status-title">Error</div>
          <div class="status-text">{message}</div>
        </div>"""

    if state == "ready" and meta:
        return f"""
        <div class="status-card ready">
          <div class="status-icon">✅</div>
          <div class="status-title">Document Ready</div>
          <table class="meta-table">
            <tr><td>File</td><td><b>{meta["name"]}</b></td></tr>
            <tr><td>Pages</td><td>{meta["pages"]}</td></tr>
            <tr><td>Characters</td><td>{meta["chars"]:,}</td></tr>
            <tr><td>Chunks</td><td>{meta["chunks"]}</td></tr>
            <tr><td>Vectors</td><td>{meta["vectors"]}</td></tr>
          </table>
          <div class="status-hint">Ask anything in the chat →</div>
        </div>"""
    return ""


# ── Backend: chat ─────────────────────────────────────────────────────────────
def chat(user_message, history):
    if not user_message.strip():
        return history, ""

    if retriever is None:
        history = history + [
            {"role": "user",      "content": user_message},
            {"role": "assistant", "content": "⚠️ Please upload and index a document first."},
        ]
        return history, ""

    lc_history = []
    for msg in history:
        if msg["role"] == "user":
            lc_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            lc_history.append(AIMessage(content=msg["content"]))

    standalone = (
        rephrase_chain.invoke({"question": user_message, "chat_history": lc_history})
        if lc_history else user_message
    )

    docs    = retriever.invoke(standalone)
    context = format_docs(docs)
    answer  = answer_chain.invoke({
        "question":    user_message,
        "chat_history": lc_history,
        "context":     context,
    })

    history = history + [
        {"role": "user",      "content": user_message},
        {"role": "assistant", "content": answer},
    ]
    return history, ""


def clear_chat():
    return [], ""


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
/* ---------- page ---------- */
body, .gradio-container { background: #0f1117 !important; color: #e2e8f0 !important; }
.gradio-container { max-width: 1200px !important; margin: 0 auto !important; padding: 24px !important; }
footer { display: none !important; }

/* ---------- header ---------- */
#header {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%);
    border-radius: 16px;
    padding: 32px 40px;
    margin-bottom: 24px;
    border: 1px solid #3730a3;
}
#header h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: #ffffff !important;
    margin: 0 0 8px 0 !important;
    letter-spacing: -0.5px;
}
#header p {
    color: #a5b4fc !important;
    font-size: 1rem !important;
    margin: 0 !important;
}
#header .badge {
    display: inline-block;
    background: rgba(99,102,241,0.3);
    border: 1px solid #6366f1;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.75rem;
    color: #c7d2fe;
    margin-top: 12px;
    margin-right: 6px;
}

/* ---------- panels ---------- */
.panel {
    background: #1a1d2e !important;
    border: 1px solid #2d3148 !important;
    border-radius: 14px !important;
    padding: 20px !important;
}
.panel-title {
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
    color: #6366f1 !important;
    margin-bottom: 14px !important;
}

/* ---------- file upload ---------- */
.upload-zone {
    border: 2px dashed #3730a3 !important;
    border-radius: 12px !important;
    background: #13162a !important;
    transition: border-color 0.2s;
}
.upload-zone:hover { border-color: #6366f1 !important; }

/* ---------- load button ---------- */
#load-btn {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    padding: 12px !important;
    width: 100% !important;
    cursor: pointer !important;
    transition: opacity 0.2s, transform 0.1s !important;
    margin-top: 10px !important;
}
#load-btn:hover { opacity: 0.9 !important; transform: translateY(-1px) !important; }
#load-btn:active { transform: translateY(0) !important; }

/* ---------- status card ---------- */
.status-card {
    border-radius: 12px;
    padding: 18px;
    margin-top: 14px;
    font-size: 0.88rem;
    line-height: 1.6;
}
.status-card.idle   { background: #1e2235; border: 1px solid #2d3148; color: #94a3b8; }
.status-card.error  { background: #2d1515; border: 1px solid #7f1d1d; color: #fca5a5; }
.status-card.ready  { background: #0f2a1a; border: 1px solid #166534; color: #86efac; }
.status-icon  { font-size: 1.8rem; margin-bottom: 8px; }
.status-title { font-weight: 700; font-size: 1rem; margin-bottom: 10px; color: #4ade80; }
.status-hint  { margin-top: 12px; color: #6ee7b7; font-style: italic; font-size: 0.82rem; }
.meta-table   { width: 100%; border-collapse: collapse; }
.meta-table td { padding: 4px 0; }
.meta-table td:first-child { color: #6b7280; width: 110px; }
.meta-table td:last-child  { color: #d1fae5; }

/* ---------- chatbot ---------- */
#chatbot {
    background: #13162a !important;
    border: 1px solid #2d3148 !important;
    border-radius: 12px !important;
}
#chatbot .message.user { background: #312e81 !important; border-radius: 12px 12px 2px 12px !important; }
#chatbot .message.bot  { background: #1e2235 !important; border-radius: 12px 12px 12px 2px !important; }

/* ---------- input row ---------- */
#msg-box textarea {
    background: #1a1d2e !important;
    border: 1px solid #3730a3 !important;
    border-radius: 10px !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    padding: 12px 14px !important;
    resize: none !important;
}
#msg-box textarea:focus { border-color: #6366f1 !important; outline: none !important; box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important; }
#msg-box label { color: #94a3b8 !important; font-size: 0.8rem !important; }

#send-btn {
    background: linear-gradient(135deg, #4f46e5, #6366f1) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 700 !important;
    min-width: 80px !important;
    transition: opacity 0.2s !important;
}
#send-btn:hover { opacity: 0.85 !important; }

#clear-btn {
    background: transparent !important;
    border: 1px solid #374151 !important;
    border-radius: 8px !important;
    color: #9ca3af !important;
    font-size: 0.82rem !important;
    transition: border-color 0.2s, color 0.2s !important;
}
#clear-btn:hover { border-color: #6b7280 !important; color: #d1d5db !important; }

/* ---------- dividers ---------- */
.gr-row { gap: 20px !important; }
"""

# ── UI ────────────────────────────────────────────────────────────────────────
with gr.Blocks(title="DocBot", css=CSS) as demo:

    # Header
    gr.HTML("""
    <div id="header">
      <h1>DocBot</h1>
      <p>Ask questions about any document. Answers come exclusively from your file — never from outside knowledge.</p>
      <span class="badge">Python</span>
      <span class="badge">LangChain</span>
      <span class="badge">Gemini</span>
      <span class="badge">RAG</span>
    </div>
    """)

    with gr.Row():

        # ── Left panel ────────────────────────────────────────────────────────
        with gr.Column(scale=1, min_width=280, elem_classes="panel"):
            gr.HTML('<div class="panel-title">Document</div>')

            file_input = gr.File(
                label="Drop a .txt or .pdf here",
                file_types=[".txt", ".pdf"],
                elem_classes="upload-zone",
            )

            load_btn = gr.Button(
                "⚡  Load & Index Document",
                elem_id="load-btn",
            )

            status_html = gr.HTML(
                _status_html("idle", "Upload a document to get started.")
            )

        # ── Right panel ───────────────────────────────────────────────────────
        with gr.Column(scale=2, elem_classes="panel"):
            gr.HTML('<div class="panel-title">Chat</div>')

            chatbot = gr.Chatbot(
                label="",
                height=440,
                elem_id="chatbot",
                placeholder="<div style='text-align:center;color:#4b5563;padding:40px 20px'>"
                            "<div style='font-size:2.5rem'>🤖</div>"
                            "<div style='font-size:1rem;margin-top:8px'>Upload any document on the left, then ask questions about it</div>"
                            "</div>",
            )

            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Type your question and press Enter…",
                    label="",
                    scale=5,
                    interactive=False,
                    elem_id="msg-box",
                    lines=1,
                    max_lines=4,
                    show_label=False,
                )
                send_btn = gr.Button("Send ➤", scale=1, elem_id="send-btn")

            clear_btn = gr.Button("🗑  Clear chat", elem_id="clear-btn", size="sm")

    # ── Wiring ────────────────────────────────────────────────────────────────
    load_btn.click(
        fn=load_and_index,
        inputs=[file_input],
        outputs=[status_html, msg_box, send_btn],
    )

    def send(msg, hist):
        return chat(msg, hist)

    send_btn.click(send, [msg_box, chatbot], [chatbot, msg_box])
    msg_box.submit(send, [msg_box, chatbot], [chatbot, msg_box])
    clear_btn.click(clear_chat, outputs=[chatbot, msg_box])



if __name__ == "__main__":
    demo.launch(share=False)
