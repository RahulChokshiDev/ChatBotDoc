
# DocBot — UI Design Specification

> Hand this file to any AI or developer to rebuild or redesign the frontend from scratch.
> The backend API contract is included so the UI works without touching `server.py`.

---

## 1. What the App Does

A **document-grounded chatbot**. The user uploads a file, the backend indexes it, and then the user asks questions. The bot answers **only from the document** — if the answer is not in the document it replies with `"I don't have that information."` No hallucination, no outside knowledge.

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python · FastAPI · LangChain · Gemini · FAISS |
| Frontend (current) | Vanilla HTML + CSS + JavaScript (single file) |
| Fonts | Inter (Google Fonts) |
| Served at | `http://127.0.0.1:8000` |

The frontend is one self-contained file: `static/index.html`.
The backend serves it at `GET /` and exposes three API endpoints.

---

## 3. Backend API Contract

The UI communicates with three endpoints. Do not change these — only the frontend needs redesigning.

### `POST /upload`
Upload a document file for indexing.

**Request:** `multipart/form-data`
**Field:** `file` — a `.txt` or `.pdf` file

**Success response `200`:**
```json
{
  "name":    "invoice.pdf",
  "pages":   3,
  "chars":   4821,
  "chunks":  12,
  "vectors": 12
}
```

**Error response `400` / `422`:**
```json
{ "detail": "Only .txt and .pdf files are supported." }
```

---

### `POST /chat`
Send a question and get an answer.

**Request:** `application/json`
```json
{ "message": "What is the total amount on the invoice?" }
```

**Success response `200`:**
```json
{ "answer": "The total amount is $4,250.00." }
```

**Error response `400`** (no document loaded yet):
```json
{ "detail": "No document loaded. Please upload a file first." }
```

---

### `POST /clear`
Clear the conversation history (server-side).

**Request:** no body
**Response `200`:** `{ "ok": true }`

---

## 4. User Flow

```
1. User opens the app
2. User drops or selects a .txt or .pdf file
3. Indexing starts AUTOMATICALLY — no button click required
4. A loading spinner shows while the backend embeds the document
5. When ready, a metadata card appears (file name, pages, chunks, vectors)
6. The chat input becomes active
7. User types a question and presses Enter (or clicks Send)
8. A typing indicator (3 animated dots) appears while the bot thinks
9. The bot's answer appears as a chat bubble
10. The conversation continues — follow-up questions work via chat history
11. User can click "Clear chat" to reset the conversation
12. User can drop a new file at any time to switch documents
```

---

## 5. Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                         FULL VIEWPORT                           │
│  ┌──────────────┐  ┌───────────────────────────────────────┐   │
│  │   SIDEBAR    │  │             MAIN AREA                 │   │
│  │   320px      │  │             flex: 1                   │   │
│  │              │  │  ┌─────────────────────────────────┐  │   │
│  │  Logo        │  │  │  CHAT HEADER (doc name + clear) │  │   │
│  │  ──────────  │  │  └─────────────────────────────────┘  │   │
│  │  Drop zone   │  │  ┌─────────────────────────────────┐  │   │
│  │              │  │  │  MESSAGES (scrollable)          │  │   │
│  │  Status card │  │  │  - empty state                  │  │   │
│  │              │  │  │  - message bubbles               │  │   │
│  │              │  │  │  - typing indicator              │  │   │
│  │  Tech badges │  │  └─────────────────────────────────┘  │   │
│  └──────────────┘  │  ┌─────────────────────────────────┐  │   │
│                    │  │  INPUT BAR (sticky bottom)      │  │   │
│                    │  └─────────────────────────────────┘  │   │
│                    └───────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-page` | `#0d0f1a` | Page background |
| `bg-sidebar` | `#111827` | Sidebar + chat header + input bar |
| `bg-bubble-bot` | `#1a1d2e` | Bot message bubble |
| `bg-bubble-user` | `#312e81 → #3730a3` | User message bubble (gradient) |
| `bg-input` | `#1a1d2e` | Textarea wrapper |
| `bg-drop` | `#0d0f1a` | Drop zone fill |
| `border` | `#1f2937` | Panel borders |
| `border-hover` | `#6366f1` | Drop zone hover / input focus |
| `accent` | `#4f46e5 → #7c3aed` | Buttons, avatars (gradient) |
| `accent-light` | `#818cf8` | Labels, spinner accent |
| `text-primary` | `#e2e8f0` | Body text |
| `text-muted` | `#6b7280` | Subtitles, hints, meta keys |
| `text-faint` | `#374151` | Input hint |
| `status-ready-bg` | `#052e16` | Ready card background |
| `status-ready-border` | `#166534` | Ready card border |
| `status-ready-text` | `#4ade80` | Ready card title |
| `status-ready-val` | `#d1fae5` | Ready card values |
| `status-error-bg` | `#1c0a0a` | Error card background |
| `status-error-border` | `#7f1d1d` | Error card border |
| `status-error-text` | `#fca5a5` | Error card text |
| `status-loading-bg` | `#1a1d2e` | Loading card background |

---

## 7. Typography

- **Font family:** Inter (weights 300, 400, 500, 600, 700, 800)
- **Base size:** 16px

| Element | Size | Weight |
|---------|------|--------|
| App name (logo) | 1.3rem | 800 |
| Section labels | 0.68rem | 700, uppercase, 1.2px letter-spacing |
| Body / bubbles | 0.9rem | 400 |
| Status title | 0.88rem | 700 |
| Meta keys/values | 0.8rem | 400 / 500 |
| Timestamps | 0.68rem | 400 |
| Input text | 0.92rem | 400 |
| Input hint | 0.72rem | 400 |
| Tech badges | 0.68rem | 500 |

---

## 8. Component Specs

### Sidebar

- **Width:** 320px fixed, no collapse
- **Structure (top → bottom):**
  1. Header (logo + tagline)
  2. Body (drop zone + status card) — `flex: 1`, scrollable
  3. Footer (tech badges)
- **Border right:** 1px solid `#1f2937`

---

### Logo

```
[gradient icon 36×36 rounded-10]  DocBot
                                   Document-Grounded AI  ← subtitle, muted
```

---

### Drop Zone

- Full-width, dashed border (`#374151`), border-radius 14px
- On hover / dragover: border turns `#6366f1`, background darkens slightly
- Contains a hidden `<input type="file" accept=".txt,.pdf">`
- Centered content: icon emoji + "Click to browse or drag & drop" + formats note
- **On file select or drop → indexing starts immediately, no button**

---

### Status Card (3 states)

**Loading:**
- Background `#1a1d2e`, border `#2d3148`
- Title: "Indexing document…" in `#818cf8`
- Body: CSS spinner + "Embedding chunks with Gemini…"

**Ready:**
- Background `#052e16`, border `#166534`
- Title: "✅ Document ready" in `#4ade80`
- Body: 2-column metadata grid
  - File / Pages / Characters / Chunks / Vectors

**Error:**
- Background `#1c0a0a`, border `#7f1d1d`
- Title: "❌ Error" in `#f87171`
- Body: error message string

---

### CSS Spinner

```css
width: 18px; height: 18px;
border: 2px solid #374151;
border-top-color: #818cf8;
border-radius: 50%;
animation: spin 0.7s linear infinite;
```

---

### Tech Badges (sidebar footer)

Pill-shaped tags: `LangChain` · `Gemini` · `FAISS` · `FastAPI`
Background `#1f2937`, border `#374151`, text `#6b7280`

---

### Chat Header

- Background `#111827`, border-bottom `#1f2937`, padding 18px 28px
- Left: document name (bold) + subtitle "Answers come only from your document"
- Right: "Clear chat" ghost button

---

### Message Bubbles

**User bubble (right-aligned):**
- Background: `linear-gradient(135deg, #312e81, #3730a3)`
- Text: `#eef2ff`
- Border-radius: 16px, top-right corner 4px (speech tail effect)
- Avatar: teal gradient circle, right of bubble

**Bot bubble (left-aligned):**
- Background: `#1a1d2e`, border `#2d3148`
- Text: `#e2e8f0`
- Border-radius: 16px, top-left corner 4px
- Avatar: indigo gradient circle, left of bubble

**Both bubbles:**
- Max-width: 72% of chat area
- Timestamp below in `#4b5563` at 0.68rem
- Fade-up entrance animation (opacity 0→1, translateY 8px→0, 0.25s ease)

---

### Typing Indicator

Shown while waiting for the API response.

```
[🤖 avatar]  [● ● ●]   ← 3 dots bouncing in sequence
```

- Dots: 7px circles, `#6366f1`, bounce animation staggered by 0.2s each
- Bubble styled the same as bot bubble

---

### Empty State

Shown in the message area before the first message.

```
        💬
  Ask anything about your document
  Upload a file on the left and start asking questions.

  [1]  Drop a .txt or .pdf in the sidebar
  [2]  Indexing starts automatically
  [3]  Type any question about your file
```

---

### Input Bar

- Sticky to bottom, background `#111827`, border-top `#1f2937`
- Wrapper: `#1a1d2e` background, border `#374151`, border-radius 14px
- On focus: border `#6366f1`, box-shadow `0 0 0 3px rgba(99,102,241,0.15)`
- Textarea: auto-grows (min 1 line, max 4 lines / 120px), no resize handle
- Send button: 38×38px, indigo gradient, border-radius 10px, `▶` icon
- Hint below: "Press Enter to send · Shift+Enter for new line"
- **Disabled state** (no document loaded): textarea + send button opacity 0.4, cursor not-allowed

---

## 9. Interactions & Behaviour

| Trigger | Action |
|---------|--------|
| File selected via click | `selectFile()` → `indexDocument()` immediately |
| File dropped on drop zone | `selectFile()` → `indexDocument()` immediately |
| `/upload` returns success | Show ready card, enable chat, clear messages |
| `/upload` returns error | Show error card, keep chat disabled |
| Enter key in textarea | Send message (unless Shift held) |
| Shift+Enter in textarea | Insert newline |
| Send button click | Send message |
| "Clear chat" button | `POST /clear`, remove all bubbles, show empty state |
| New file dropped while chatting | Re-index, clear chat, start fresh |

---

## 10. States Summary

| State | Drop zone | Status card | Chat input | Chat area |
|-------|-----------|-------------|-----------|-----------|
| Initial | idle | hidden | disabled | empty state |
| Indexing | locked | loading spinner | disabled | empty state |
| Ready | active | green metadata | **enabled** | empty state |
| Chatting | active | green metadata | enabled | messages |
| Error | active | red error | disabled | empty state |

---

## 11. Files

```
ChatBotDoc/
├── server.py          ← FastAPI backend (RAG pipeline) — do not modify
├── static/
│   └── index.html     ← Entire frontend (HTML + CSS + JS in one file)
├── sample_doc.txt     ← Test document
├── requirements.txt   ← Python dependencies
└── UI_DESIGN.md       ← This file
```

---

## 12. Redesign Notes for AI

If you are rebuilding this UI, follow these rules:

1. **Keep the API calls identical** — `POST /upload` (multipart), `POST /chat` (JSON), `POST /clear`. Only URLs and payload keys matter, not the UI.
2. **Auto-index on file select** — do not add a separate "Upload" button. The moment a file is chosen, call `/upload`.
3. **No hardcoded example questions** — the app works with any document (invoices, manuals, contracts, etc.).
4. **Strictly show "I don't have that information."** — the bot will return this phrase verbatim when the answer is not in the document. The UI should display it as a normal bot bubble without any special treatment.
5. **Chat history lives on the server** — the frontend does not need to track or replay history. Just display messages in order.
6. **Single user, single session** — no authentication, no multi-user support needed.
7. You may use any frontend framework (React, Vue, Svelte) or keep it vanilla.
8. You may change colors, fonts, layout — just preserve the interaction model above.
