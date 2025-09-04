# backend/rag/api.py
from typing import List, Dict, Any, Optional
import hashlib
import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

import google.generativeai as genai

from .vector_store import MAIL_BODIES, ATTACHMENTS_SEMANTIC, ATTACHMENTS_TABULAR_IDX
from .parsers import chunk_text, parse_pdf_bytes, xlsx_summary_from_bytes
from .retriever import embed_texts, topk_from_collection
from .router import classify_intent
from .tabular_agent import load_dataframes, answer_with_pandasai

router = APIRouter(tags=["RAG"])

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def _download_bytes(url: str) -> bytes:
    with httpx.Client(timeout=90.0) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.content

# ---------- Models ----------

class IngestMailBody(BaseModel):
    messageId: str
    subject: str = ""
    sender: str = ""
    receivedAt: str = ""
    bodyText: str

class IngestAttachment(BaseModel):
    messageId: str
    attachmentId: str
    filename: str
    contentType: str
    blob_uri: str  # presigned URL

class AskRequest(BaseModel):
    question: str
    k: int = 6
    # optional filters later (sender, time, subject, etc.)

# ---------- Ingestion ----------

@router.post("/ingest/mail")
def ingest_mail(req: IngestMailBody) -> Dict[str, Any]:
    chunks = chunk_text(req.bodyText)
    if not chunks:
        return {"chunks": 0}
    ids = []
    metas = []
    for i, c in enumerate(chunks):
        ids.append(f"{req.messageId}:body:{i}")
        metas.append({
            "type": "mail_body",
            "messageId": req.messageId,
            "subject": req.subject,
            "sender": req.sender,
            "receivedAt": req.receivedAt,
        })
    embs = embed_texts(chunks)
    MAIL_BODIES.add(documents=chunks, embeddings=embs, ids=ids, metadatas=metas)
    return {"chunks": len(chunks)}

@router.post("/ingest/attachment")
def ingest_attachment(req: IngestAttachment) -> Dict[str, Any]:
    data = _download_bytes(req.blob_uri)
    return _ingest_attachment_bytes_core(
        data=data,
        message_id=req.messageId,
        attachment_id=req.attachmentId,
        filename=req.filename,
        content_type=req.contentType,
        blob_uri=req.blob_uri,
    )


def _ingest_attachment_bytes_core(
    *,
    data: bytes,
    message_id: str,
    attachment_id: str,
    filename: str,
    content_type: str,
    blob_uri: Optional[str] = None,
) -> Dict[str, Any]:
    ct = (content_type or "").lower()
    fn = (filename or "").lower()

    if "pdf" in ct or fn.endswith(".pdf"):
        pages = parse_pdf_bytes(data)
        # chunk per page text
        docs, ids, metas = [], [], []
        for p in pages:
            for i, c in enumerate(chunk_text(p["text"])):
                docs.append(c)
                ids.append(f"{message_id}:{attachment_id}:pdf:{p['page']}:{i}")
                metas.append({
                    "type": "attachment_pdf",
                    "messageId": message_id,
                    "attachmentId": attachment_id,
                    "filename": filename,
                    "page": p["page"],
                })
        if not docs:
            return {"chunks": 0}
        embs = embed_texts(docs)
        ATTACHMENTS_SEMANTIC.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
        return {"chunks": len(docs), "kind": "pdf"}

    if "spreadsheetml" in ct or fn.endswith((".xlsx", ".xlsm")) or fn.endswith(".csv"):
        # Build index entries (not full embeddings of all rows)
        entries = []
        if fn.endswith(".csv"):
            # simple index text
            text = f"CSV file: {filename} (ingest for tabular questions)."
            entries.append({"text": text, "sheet": None})
        else:
            for s in xlsx_summary_from_bytes(data):
                entries.append({"text": s["text"], "sheet": s["sheet"], "columns": s["columns"], "row_count": s["row_count"]})
        if not entries:
            return {"chunks": 0}

        docs, ids, metas = [], [], []
        for i, e in enumerate(entries):
            docs.append(e["text"])
            ids.append(f"{message_id}:{attachment_id}:tabular:{i}")
            metas.append({
                "type": "attachment_tabular",
                "messageId": message_id or "",
                "attachmentId": attachment_id or "",
                "filename": filename or "",
                "sheet": str(e.get("sheet") or ""),
                "blob_uri": str(blob_uri or ""),  # used later to load DF
            })
        embs = embed_texts(docs)
        ATTACHMENTS_TABULAR_IDX.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
        return {"chunks": len(docs), "kind": "tabular-index"}

    # Unsupported
    return {"chunks": 0, "skipped": True, "reason": f"Unsupported contentType {ct}"}


@router.post("/ingest/attachment-bytes")
async def ingest_attachment_bytes(
    messageId: str = Form(...),
    attachmentId: str = Form(...),
    filename: str = Form(...),
    contentType: str = Form(...),
    file: UploadFile = File(...),
):
    data = await file.read()
    return _ingest_attachment_bytes_core(
        data=data,
        message_id=messageId,
        attachment_id=attachmentId,
        filename=filename,
        content_type=contentType,
        blob_uri=None,
    )

# ---------- Ask ----------

def _build_prompt(question: str, contexts: List[Dict[str, Any]]) -> str:
    header = (
        "You are a helpful assistant. Answer using ONLY the provided context.\n"
        "If the answer isn't in the context, say you don't know.\n"
        "Cite sources with page/sheet info if present.\n\n"
    )
    blocks = []
    for i, ctx in enumerate(contexts, start=1):
        m = ctx.get("meta", {})
        src = m.get("filename") or m.get("subject") or "source"
        loc = ""
        if m.get("page"):
            loc = f"(page {m['page']})"
        elif m.get("sheet"):
            loc = f"(sheet {m['sheet']})"
        blocks.append(f"[{i}] {src} {loc}\n{ctx.get('text','')}\n")
    return f"{header}Context:\n" + "\n".join(blocks) + f"\nQuestion: {question}\nAnswer:"

@router.post("/ask")
def ask(req: AskRequest) -> Dict[str, Any]:
    route, conf = classify_intent(req.question)

    if route == "mail_body_semantic":
        top = topk_from_collection(MAIL_BODIES, req.question, k=req.k)
        if not top:
            return {"answer": "I don't know based on the available mail bodies.", "route": route, "sources": []}
        prompt = _build_prompt(req.question, top)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        sources = [{"subject": t["meta"].get("subject"), "sender": t["meta"].get("sender")} for t in top]
        return {"answer": (resp.text or "").strip(), "route": route, "sources": sources}

    if route == "attachment_semantic":
        top = topk_from_collection(ATTACHMENTS_SEMANTIC, req.question, k=req.k)
        if not top:
            return {"answer": "I don't know based on the available attachments.", "route": route, "sources": []}
        prompt = _build_prompt(req.question, top)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        sources = [{"filename": t["meta"].get("filename"), "page": t["meta"].get("page")} for t in top]
        return {"answer": (resp.text or "").strip(), "route": route, "sources": sources}

    if route == "attachment_tabular":
        # Use index to select the right table(s)
        idx_hits = topk_from_collection(ATTACHMENTS_TABULAR_IDX, req.question, k=min(3, req.k))
        if not idx_hits:
            return {"answer": "No relevant tabular attachments found.", "route": route, "sources": []}
        specs = []
        for h in idx_hits:
            m = h["meta"]
            specs.append({
                "blob_uri": m.get("blob_uri"),
                "filename": m.get("filename"),
                "sheet": m.get("sheet"),
            })
        tables = load_dataframes(specs)
        tab_ans = answer_with_pandasai(req.question, tables)
        sources = [{"filename": s["filename"], "sheet": s.get("sheet")} for s in specs]
        return {
            "answer": tab_ans.get("answer", ""),
            "route": route,
            "sources": sources,
            "tables_used": tab_ans.get("tables_used", []),
            "previews": tab_ans.get("previews", []),
        }

    return {"answer": "I couldn't determine how to answer this question.", "route": route, "sources": []}
