# Outlook RAG Prototype — React + Graph (Runtime Only)

## Objectives
- Show an end-to-end demo: fetch Outlook emails/attachments via Graph, ingest to in-memory vectors, and chat with Gemini over that context.
- No persistence, no background jobs: everything lives only in memory during the session.
- Minimal React UI for sign-in, email selection, ingest, and chat.

## Constraints
- Runtime-only: no DB, no files persisted; ephemeral Chroma in backend memory.
- Frontend handles Microsoft login and Graph calls; backend never stores tokens.
- Supported content: email body, PDF, and XLSX attachments.

## Architecture (ultra-light)
- Frontend: React + MSAL (PKCE) + Microsoft Graph client
  - Sign in, list recent messages, view selected email, list attachments
  - Download body and chosen attachments and POST them to backend for ingest
  - Chat box that calls backend `/chat` and streams answer + citations
- Backend: FastAPI (Python)
  - `/ingest` accepts body text + attachments (multipart), parses and chunks, embeds to Chroma (in-memory)
  - `/chat` retrieves top-k, builds prompt, calls Gemini, returns answer + sources
  - No persistence; Chroma collection exists only for the process lifetime

## Tech Choices
- UI: React + Vite + `@azure/msal-browser` and `@azure/msal-react`
- Graph: Microsoft Graph REST via `@microsoft/microsoft-graph-client`
- Backend: Python FastAPI + Uvicorn
- Parsing: `pymupdf` (PDF), `openpyxl` (XLSX)
- Vectors: `chromadb` (ephemeral, no `persist_directory`)
- LLM/Embeddings: `google-generativeai` (`text-embedding-004`, Gemini 1.5 Flash/Pro)

## Data Flow
1) User signs in (MSAL) in React.
2) React lists last N messages; user selects one.
3) React fetches email body and selected attachments via Graph.
4) React posts payload to backend `/ingest` (body text + files) for parsing and in-memory indexing.
5) User asks a question; React calls `/chat` with query.
6) Backend retrieves top chunks from Chroma, calls Gemini, returns streamed answer + citations.

## Minimal API Contracts
- POST `/ingest` (multipart/form-data):
  - fields: `emailSubject`, `emailFrom`, `receivedAt`, `bodyText` (string)
  - files: `attachments[]` (PDF/XLSX)
  - returns: `{ chunks: number, attachments: number }`
- POST `/chat` (json): `{ query: string, k?: number }` → streams or returns
  - returns: `{ answer: string, sources: Array<{subject, filename?, page?, sheet?, range?, receivedAt}> }`

## Chunking Defaults
- Target ~800–1000 tokens, 10–15% overlap
- Keep provenance: `page` (PDF), `sheet` + `row range` (XLSX), and `email` metadata

## Milestones
- M1 — Outlook API in React
  - Sign-in with MSAL (SPA), request `Mail.Read` + `offline_access`
  - List last N messages; view selected body (plain text from HTML)
  - Show attachments (PDF/XLSX) and allow selecting which to ingest
  - Acceptance: can fetch and display body + download attachment bytes client-side
- M2 — Ingestion (Backend)
  - Implement `/ingest` to accept body + files, parse PDF/XLSX, chunk, embed to in-memory Chroma
  - Idempotent within session (simple content hash) to avoid duplicate chunks
  - Acceptance: after ingest, collection size reflects chunks; can re-ingest same email without duplication
- M3 — RAG Chat
  - Implement `/chat` retrieval (top-k) and Gemini answer with citations
  - React chat UI: input box, send, stream/display answer, show Sources list
  - Acceptance: ask questions grounded in the selected email/attachments with clear citations

## Deliverables
- `frontend/` (React + Vite)
  - Auth + message list + message view + attachments UI
  - Ingest button and Chat screen
- `backend/` (FastAPI)
  - `main.py` (endpoints `/ingest`, `/chat`)
  - `parsers/pdf_parser.py`, `parsers/xlsx_parser.py`
  - `rag/vector.py` (Chroma setup), `rag/retriever.py`, `rag/prompt.py`
  - `requirements.txt` (fastapi, uvicorn, chromadb, google-generativeai, pymupdf, openpyxl)
- `README_quick_graph.md` with run instructions and required env vars

## Env Vars
- Frontend: MSAL config (tenant/clientId, redirect URI)
- Backend: `GOOGLE_API_KEY`

## Notes & Limits
- Attachments size: cap to e.g., 10–20 MB per file in prototype
- HTML → text: basic sanitization only (strip signatures optionally)
- No reranker/hybrid; pure dense retrieval
- All state cleared on server restart

## Open Decisions
- Gemini model: 1.5 Flash (default) vs 1.5 Pro
- Retrieval `k` (default 6) and max prompt tokens
- Time window for messages list (e.g., last 7–30 days)
