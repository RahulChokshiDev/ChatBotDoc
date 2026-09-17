# DocBot — Document-Grounded RAG Chatbot

A multi-session RAG (Retrieval-Augmented Generation) chatbot that answers questions strictly from uploaded documents. Built with FastAPI, LangChain, Google Gemini, and FAISS.

---

## Features

- **Multi-session chat** — create multiple independent conversations, each with its own document and memory
- **Session history** — switch between chats and restore full conversation history
- **RAG pipeline** — answers are grounded exclusively in the uploaded document; no hallucination
- **Multi-format support** — upload `.txt` or `.pdf` files
- **Conversational memory** — follow-up questions are understood using chat history
- **Clean UI** — dark-themed chat interface with real-time typing indicator

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| LLM | Google Gemini (`gemini-3.6-flash`) |
| Embeddings | Google Gemini Embedding (`gemini-embedding-2`) |
| Vector Store | FAISS (in-memory) |
| RAG Framework | LangChain (LCEL) |
| Frontend | Vanilla HTML/CSS/JS |

---

## Project Structure

```
ChatBotDoc/
├── server.py           # FastAPI backend — sessions, upload, chat endpoints
├── static/
│   └── index.html      # Single-page frontend (no framework)
├── chatbot.ipynb       # Jupyter notebook — original RAG prototype (6 steps)
├── sample_doc.txt      # Sample document for testing (ACME employee handbook)
└── requirements.txt    # Python dependencies
```

---

## How It Works

### RAG Pipeline

```
User question
     │
     ▼
[Rephrase chain] ── uses chat history to rewrite follow-up as standalone query
     │
     ▼
[FAISS retriever] ── finds top-4 similar chunks from the document
     │
     ▼
[QA chain] ── Gemini LLM answers using only retrieved context
     │
     ▼
Answer (grounded in document)
```

### Session Architecture

Each conversation is an isolated session on the server:
- Has its own FAISS vector store (from the uploaded document)
- Has its own LangChain message history for multi-turn memory
- Sessions are identified by UUID and stored in-memory

---

## Setup & Run

### 1. Clone the repository

```bash
git clone <repo-url>
cd ChatBotDoc
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install fastapi uvicorn langchain langchain-google-genai \
            langchain-community langchain-text-splitters \
            faiss-cpu pypdf python-dotenv
```

### 4. Set your Google API key

Get a free key from [Google AI Studio](https://aistudio.google.com/).

Option A — set in `server.py` directly (already done):
```python
os.environ["GOOGLE_API_KEY"] = "your-key-here"
```

Option B — use a `.env` file (recommended):
```
GOOGLE_API_KEY=your-key-here
```
Then load it in `server.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

### 5. Start the server

```bash
python3 server.py
```

Open your browser at **http://127.0.0.1:8000**

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sessions` | Create a new chat session |
| `GET` | `/sessions` | List all sessions |
| `DELETE` | `/sessions/{id}` | Delete a session |
| `POST` | `/upload?session_id=<id>` | Upload a document to a session |
| `POST` | `/chat` | Send a message `{session_id, message}` |
| `POST` | `/clear` | Clear chat history `{session_id}` |

---

## How to Extend

### Swap the LLM

Replace `ChatGoogleGenerativeAI` with any LangChain-compatible LLM:

```python
# OpenAI
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Ollama (local)
from langchain_ollama import ChatOllama
llm = ChatOllama(model="llama3", temperature=0)
```

### Persist sessions to disk

Replace the in-memory `sessions` dict with a database:

```python
# SQLite example with SQLAlchemy
# Store doc_meta in DB, reload FAISS index from saved files
import faiss
faiss.write_index(vector_store.index, f"indexes/{session_id}.index")
```

### Add persistent vector store

Replace FAISS with a hosted vector DB:

```python
# Chroma (local)
from langchain_chroma import Chroma
vector_store = Chroma.from_documents(chunks, embeddings, persist_directory="./chroma_db")

# Pinecone (cloud)
from langchain_pinecone import PineconeVectorStore
vector_store = PineconeVectorStore.from_documents(chunks, embeddings, index_name="docbot")
```

### Support more file types

Add loaders in the `upload` endpoint:

```python
from langchain_community.document_loaders import (
    Docx2txtLoader,      # .docx
    UnstructuredCSVLoader,  # .csv
    WebBaseLoader,       # URLs
)
```

### Stream responses

Use LangChain streaming with FastAPI `StreamingResponse`:

```python
from fastapi.responses import StreamingResponse

async def stream_answer():
    async for chunk in answer_chain.astream({...}):
        yield f"data: {chunk}\n\n"

return StreamingResponse(stream_answer(), media_type="text/event-stream")
```

---

## Notes

- The free tier of Google AI Studio has a daily request quota per model
- FAISS runs in-memory — all sessions are lost on server restart
- The system prompt explicitly forbids the LLM from using outside knowledge
