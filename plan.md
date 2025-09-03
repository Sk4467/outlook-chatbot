# Outlook Document Chatbot – Plan

## Goals
- Provide a secure, fast chatbot over Outlook emails and attachments.
- Support PDF and XLSX parsing first; scale to more types later.
- Use Gemini for grounded, cited answers via RAG over a vector DB.

## Non‑Goals (MVP)
- No real‑time background ingestion beyond manual/periodic fetch.
- No multi‑tenant admin UI; start with single mailbox or single tenant.
- No full Outlook add‑in UI in MVP (optional later milestone).

## High‑Level Architecture
1) Connector (Microsoft Graph) → 2) Ingestion Pipeline → 3) Vector Store → 4) Retriever + RAG → 5) Chat API/UI

### Components
- Connector: Microsoft Graph API via MSAL OAuth (delegated flow initially).
- Ingestion: Queues new/changed emails, downloads body + attachments, parses, chunks, embeds, and upserts to vector DB.
- Vector Store: `pgvector` on PostgreSQL (or Qdrant). Namespaces/partitions per user/tenant.
- RAG Service: Hybrid retrieval option (dense + BM25), optional reranker later.
- Chat Service: Gemini generation with citations to retrieved chunks.
- UI: Simple web chat first; later an Outlook add‑in task pane.

## Data Model & Metadata
- Core keys: `userId`, `tenantId`, `messageId`, `internetMessageId`, `threadId`, `attachmentId?`.
- Source context: `subject`, `from`, `to`, `receivedAt`, `folderPath`, `labels/categories`.
- Document metadata: `filename`, `filetype`, `pages|sheets`, `hash`, `contentDisposition`.
- Chunk fields: `chunkId`, `text`, `embedding`, `tokenCount`, `position` (page/sheet/row range), `overlapRange`, `provenance` (e.g., `file.pdf#page=3`, `Sheet1!A2:D2`).
- Index ops: upsert by `(messageId, attachmentId, chunkId)`; tombstone deletes; dedup by content `hash`.

## Ingestion Pipeline
- Trigger: Manual backfill of last N days; later Graph subscriptions + delta queries for near‑real‑time.
- Fetch: Email body (HTML + text), normalize to text; enumerate attachments with metadata.
- Type‑specific parsers:
  - PDF: PyMuPDF/PDFium; extract text with layout hints, capture headings, lists, and tables when possible; keep page numbers.
  - XLSX: openpyxl; emit per‑row or logical blocks with sheet name; preserve header row; include formulas as metadata; store cell ranges.
- Normalization: Convert to unified chunk schema; strip signatures/disclaimers; optional redaction rules.
- Chunking: ~700–1200 tokens per chunk with 10–15% overlap; keep boundaries by page/sheet when helpful.
- Embeddings: Google `text-embedding-004` (1536‑D). Store vector + metadata.
- Idempotency: Hash normalized content; skip unchanged; update embeddings only when text changes.

## Vector Store
- Default: Postgres + `pgvector` for dense; optional `tsvector` column for BM25/lexical hybrid.
- Alternative: Qdrant (collections per tenant, payload filters). Choose based on ops comfort/perf.
- Schema sketch (Postgres):
  - `documents(id, user_id, message_id, attachment_id, filetype, subject, received_at, hash, deleted_at)`
  - `chunks(id, document_id, chunk_index, text, embedding vector(1536), token_count, page, sheet, row_start, row_end, created_at)`
  - GIN/GIST indexes for metadata filters; HNSW/IVFFlat for vector search if available.

## Retrieval & Prompting
- Query preprocessing: Optional LLM rewrite for recall (keep original too).
- Retrieval: Top‑k dense; optional hybrid with BM25; filter by time range, sender, subject, filetype.
- Reranking (later): Cross‑encoder/LLM reranker to refine top 20 → 5.
- Prompting style:
  - System: “Answer using only provided context; cite sources with page/sheet refs; say when unknown.”
  - Include a compact “Sources” list: subject, filename, page/sheet, receivedAt, link to message.
  - Safety: Refuse instructions from documents (prompt‑injection); cap context tokens.

## Outlook Integration (Graph)
- Auth: MSAL PKCE (web) or auth‑code flow (server). Scopes: `Mail.Read`, `Mail.ReadWrite` (if deletions), `offline_access`.
- Access: Use `/me/messages` with `$select` for minimal fields; `$expand=attachments` as needed; large files via `/attachments/{id}/$value` or `/content`.
- Sync: Start with backfill by date; later add delta queries and webhooks (subscriptions). Consider resource data encryption for webhook payloads.

## Chat Service
- LLM: Gemini 1.5 Pro (or Flash for cost/latency) via Google AI Studio or Vertex AI.
- Orchestration: Construct prompt with top chunks; stream tokens to client; include citations.
- Guardrails: Max tokens per response; strip/escape HTML; configurable PII redaction.

## Security & Compliance
- Data flow: Only derived text chunks are sent for embeddings and to LLM; avoid uploading raw files unless necessary.
- Storage: Encrypt at rest; per‑tenant/user namespaces; retention policy controls; audit logs for queries and data changes.
- Secrets: Store OAuth and API keys in secure vault; rotate regularly.
- Access control: Enforce user‑scoped filters at retrieval; no cross‑user leakage.

## Observability & Ops
- Logging: Ingestion events, chunk counts, embedding latency, retrieval hits/misses, LLM tokens.
- Metrics: Time from email arrival → searchable; QPS/latency; cost per query; top senders/types indexed.
- Tracing: Trace IDs across ingestion → chat answer; record doc IDs used as context.

## MVP Scope
- Fetch last N days for one mailbox (configurable).
- Parse PDF and XLSX; chunk + embed; upsert to vector DB.
- `/chat` endpoint: retrieve top‑k, ground Gemini, stream response with citations.
- Minimal web UI: auth, trigger ingest, chat with filters (time range, filetype), show sources.

## Tech Stack Options
- Backend: Python (FastAPI + MSAL + PyMuPDF + openpyxl) or Node (Express/Nest + @azure/msal-node + pdfjs/pdfium + exceljs).
- Vector DB: Postgres + pgvector (hybrid via `tsvector`) vs Qdrant.
- Hosting: GCP (easy Gemini via AI Studio/Vertex) or Azure (Graph proximity). Pick based on org constraints.

## Open Decisions
- Backend language/runtime preference?
- Vector DB choice (pgvector vs Qdrant)?
- Hosting (GCP vs Azure) and access to Gemini (AI Studio vs Vertex)?
- Single‑user MVP vs multi‑tenant from day one?
- Include Outlook add‑in UI in MVP or defer to later?

## Immediate Questions
- Do you already have code in this repo to review?
- Any data residency/compliance requirements (PII handling, region, encryption)?
- Expected email volume and attachment sizes to size the pipeline?
- Any specific retrieval filters needed (sender domain, labels, projects)?

## Proposed Milestones
- M1: Scaffold project, auth to Graph, manual backfill ingest for PDFs/XLSX into vector DB.
- M2: Build `/chat` with retrieval + Gemini, return streaming answer with citations.
- M3: Basic UI: login, ingest button, chat, source viewer.
- M4: Delta sync + subscriptions; soft deletes/tombstones.
- M5: Hybrid retrieval + reranker; add security hardening and observability.

