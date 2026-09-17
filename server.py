import os, time, shutil, tempfile, warnings, uuid
warnings.filterwarnings("ignore")

os.environ["GOOGLE_API_KEY"] = "AQ.Ab8RN6KubRtdY-jkA8ESORSKdwxx3Hw5Oc62Y7ExRcQxhXNSIw"

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# ── Per-session state ──────────────────────────────────────────────────────────
sessions: dict = {}

# ── Shared LLM + prompts ───────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)

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


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI()


# ── Session management ─────────────────────────────────────────────────────────
@app.get("/sessions")
def list_sessions():
    return [
        {"id": sid, "doc_meta": s["doc_meta"], "message_count": len(s["chat_history"])}
        for sid, s in sessions.items()
    ]


@app.post("/sessions")
def create_session():
    sid = str(uuid.uuid4())
    sessions[sid] = {
        "retriever":      None,
        "rephrase_chain": None,
        "answer_chain":   None,
        "chat_history":   [],
        "doc_meta":       None,
    }
    return {"id": sid}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    del sessions[session_id]
    return {"ok": True}


# ── Upload ─────────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload(session_id: str = Query(...), file: UploadFile = File(...)):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".txt", ".pdf"}:
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        loader      = PyPDFLoader(tmp_path) if suffix == ".pdf" else TextLoader(tmp_path, encoding="utf-8")
        raw_docs    = loader.load()
        total_chars = sum(len(d.page_content) for d in raw_docs)

        chunks = RecursiveCharacterTextSplitter(
            chunk_size=800, chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        ).split_documents(raw_docs)

        embeddings   = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")
        vector_store = FAISS.from_documents(chunks, embeddings)
        time.sleep(3)

        retriever      = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        rephrase_chain = contextualize_prompt | llm | StrOutputParser()
        answer_chain   = qa_prompt | llm | StrOutputParser()

        doc_meta = {
            "name":    file.filename,
            "pages":   len(raw_docs),
            "chars":   total_chars,
            "chunks":  len(chunks),
            "vectors": vector_store.index.ntotal,
        }

        sessions[session_id].update({
            "retriever":      retriever,
            "rephrase_chain": rephrase_chain,
            "answer_chain":   answer_chain,
            "chat_history":   [],
            "doc_meta":       doc_meta,
        })
        return doc_meta

    finally:
        os.unlink(tmp_path)


# ── Chat ───────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    s = sessions[req.session_id]
    if s["retriever"] is None:
        raise HTTPException(status_code=400, detail="No document loaded. Please upload a file first.")

    question = req.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    standalone = (
        s["rephrase_chain"].invoke({"question": question, "chat_history": s["chat_history"]})
        if s["chat_history"] else question
    )

    docs    = s["retriever"].invoke(standalone)
    context = format_docs(docs)
    answer  = s["answer_chain"].invoke({
        "question":     question,
        "chat_history": s["chat_history"],
        "context":      context,
    })

    s["chat_history"].append(HumanMessage(content=question))
    s["chat_history"].append(AIMessage(content=answer))

    return {"answer": answer}


# ── Clear ──────────────────────────────────────────────────────────────────────
class ClearRequest(BaseModel):
    session_id: str


@app.post("/clear")
async def clear(req: ClearRequest):
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")
    sessions[req.session_id]["chat_history"] = []
    return {"ok": True}


# ── Static + root ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
