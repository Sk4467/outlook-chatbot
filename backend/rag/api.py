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
    print(f"[INGEST] Attachment: {req.filename} ({req.contentType})")
    data = _download_bytes(req.blob_uri)
    print(f"[INGEST] Downloaded {len(data)} bytes")
    
    # Cache the downloaded data
    from .data_cache import cache_blob_data
    cache_blob_data(req.blob_uri, req.filename, data)
    
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
    print(f"[INGEST] Processing {fn} ({ct})")

    if "pdf" in ct or fn.endswith(".pdf"):
        print(f"[INGEST] PDF processing: {filename}")
        pages = parse_pdf_bytes(data)
        print(f"[INGEST] Extracted {len(pages)} pages")
        
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
            print(f"[INGEST] No chunks extracted from PDF")
            return {"chunks": 0}
        
        print(f"[INGEST] Creating {len(docs)} embeddings")
        embs = embed_texts(docs)
        ATTACHMENTS_SEMANTIC.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
        print(f"[INGEST] PDF stored: {len(docs)} chunks")
        return {"chunks": len(docs), "kind": "pdf"}

    if "spreadsheetml" in ct or fn.endswith((".xlsx", ".xlsm")) or fn.endswith(".csv"):
        print(f"[INGEST] Tabular processing: {filename}")
        entries = []
        if fn.endswith(".csv"):
            text = f"CSV file: {filename} (ingest for tabular questions)."
            entries.append({"text": text, "sheet": None})
            print(f"[INGEST] CSV index entry created")
        else:
            summaries = xlsx_summary_from_bytes(data)
            print(f"[INGEST] Excel summaries: {len(summaries)} sheets")
            for s in summaries:
                entries.append({"text": s["text"], "sheet": s["sheet"], "columns": s["columns"], "row_count": s["row_count"]})
        
        if not entries:
            print(f"[INGEST] No tabular entries created")
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
                "blob_uri": str(blob_uri or ""),
                "cached_data_available": "true",  # Flag that data was successfully processed
            })
        
        print(f"[INGEST] Creating {len(docs)} tabular embeddings")
        embs = embed_texts(docs)
        ATTACHMENTS_TABULAR_IDX.add(documents=docs, embeddings=embs, ids=ids, metadatas=metas)
        print(f"[INGEST] Tabular stored: {len(docs)} index entries")
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

# ---------- Enhanced Analysis Endpoints ----------

@router.post("/ask/enhanced-pdf")
async def ask_enhanced_pdf(req: AskRequest) -> Dict[str, Any]:
    """Enhanced PDF analysis using PandaAGI with cross-document synthesis"""
    # Get PDF chunks
    pdf_chunks = topk_from_collection(ATTACHMENTS_SEMANTIC, req.question, k=req.k)
    if not pdf_chunks:
        return {"answer": "No relevant PDF attachments found.", "sources": []}
    
    # Optionally get related mail context
    mail_context = topk_from_collection(MAIL_BODIES, req.question, k=2)
    
    try:
        from .enhanced_agent import get_enhanced_rag_manager
        manager = get_enhanced_rag_manager()
        result = await manager.enhanced_document_analysis(req.question, pdf_chunks, mail_context)
        return {
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "analysis_type": result.get("analysis_type", "enhanced_pdf"),
            "total_chunks": result.get("total_chunks", len(pdf_chunks))
        }
    except Exception as e:
        return {
            "answer": f"Enhanced PDF analysis failed: {str(e)}",
            "sources": [{"filename": chunk.get('meta', {}).get('filename', 'Unknown'), 
                       "page": chunk.get('meta', {}).get('page', 'Unknown')} for chunk in pdf_chunks],
            "error": str(e)
        }

@router.post("/ask/multi-modal")
async def ask_multi_modal(req: AskRequest) -> Dict[str, Any]:
    """Multi-modal analysis across all content types"""
    # Get content from all collections
    mail_hits = topk_from_collection(MAIL_BODIES, req.question, k=2)
    pdf_hits = topk_from_collection(ATTACHMENTS_SEMANTIC, req.question, k=3)
    tabular_idx_hits = topk_from_collection(ATTACHMENTS_TABULAR_IDX, req.question, k=2)
    
    if not any([mail_hits, pdf_hits, tabular_idx_hits]):
        return {"answer": "No relevant content found across mail bodies and attachments.", "sources": []}
    
    try:
        from .enhanced_agent import get_enhanced_rag_manager
        manager = get_enhanced_rag_manager()
        
        # Combine PDF and mail content for document analysis
        all_docs = mail_hits + pdf_hits
        
        # If we have tabular data, load and analyze it separately
        tabular_analysis = None
        if tabular_idx_hits:
            specs = []
            for h in tabular_idx_hits:
                m = h["meta"]
                specs.append({
                    "blob_uri": m.get("blob_uri"),
                    "filename": m.get("filename"),
                    "sheet": m.get("sheet"),
                })
            tables = load_dataframes(specs)
            if tables:
                tabular_analysis = await manager.analyze_tabular_data(req.question, tables)
        
        # Enhanced document analysis
        doc_result = await manager.enhanced_document_analysis(req.question, pdf_hits, mail_hits)
        
        # Combine results
        combined_answer = doc_result.get("answer", "")
        if tabular_analysis and tabular_analysis.get("answer"):
            combined_answer += f"\n\nTabular Data Analysis:\n{tabular_analysis.get('answer', '')}"
        
        return {
            "answer": combined_answer,
            "sources": doc_result.get("sources", []),
            "analysis_type": "multi_modal",
            "document_chunks": len(all_docs),
            "tabular_data": tabular_analysis.get("tables_used", []) if tabular_analysis else [],
            "previews": tabular_analysis.get("previews", []) if tabular_analysis else []
        }
        
    except Exception as e:
        return {
            "answer": f"Multi-modal analysis failed: {str(e)}",
            "sources": [],
            "error": str(e)
        }

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
async def ask(req: AskRequest) -> Dict[str, Any]:
    print(f"[ASK] Question: {req.question[:100]}...")
    route, conf = classify_intent(req.question)
    print(f"[ASK] Route: {route} (conf: {conf:.2f})")

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
        
        # Try PandasAI enhanced PDF analysis
        try:
            from .enhanced_agent import analyze_pdf_with_agent
            result = await analyze_pdf_with_agent(req.question, top)
            return {
                "answer": result.get("answer", ""),
                "route": route,
                "sources": result.get("sources", []),
                "analysis_type": result.get("analysis_type", "pdf_agentic"),
                "chunks_analyzed": result.get("chunks_analyzed", len(top))
            }
        except Exception as e:
            # Fallback to traditional approach
            print(f"PandasAI PDF analysis failed: {e}")
            prompt = _build_prompt(req.question, top)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            sources = [{"filename": t["meta"].get("filename"), "page": t["meta"].get("page")} for t in top]
            return {
                "answer": (resp.text or "").strip(), 
                "route": route, 
                "sources": sources,
                "analysis_type": "pdf_fallback"
            }

    if route == "attachment_tabular":
        print(f"[TABULAR] Query: {req.question[:50]}...")
        idx_hits = topk_from_collection(ATTACHMENTS_TABULAR_IDX, req.question, k=min(3, req.k))
        
        if not idx_hits:
            print("[TABULAR] No index hits")
            return {"answer": "No relevant tabular attachments found.", "route": route, "sources": []}
        
        print(f"[TABULAR] Found {len(idx_hits)} hits")
        specs = []
        for i, h in enumerate(idx_hits):
            m = h["meta"]
            filename = m.get("filename", "unknown")
            blob_uri = m.get("blob_uri", "")
            specs.append({
                "blob_uri": blob_uri,
                "filename": filename,
                "sheet": m.get("sheet"),
            })
            print(f"[TABULAR] {i+1}: {filename} ({len(blob_uri)} chars)")
        
        try:
            tables = load_dataframes(specs)
            print(f"[TABULAR] Loaded {len(tables)} tables")
            
            tab_ans = answer_with_pandasai(req.question, tables)
            print(f"[TABULAR] Analysis: {tab_ans.get('analysis_type', 'unknown')}")
            
            sources = [{"filename": s["filename"], "sheet": s.get("sheet")} for s in specs]
            return {
                "answer": tab_ans.get("answer", ""),
                "route": route,
                "sources": sources,
                "tables_used": tab_ans.get("tables_used", []),
                "previews": tab_ans.get("previews", []),
                "analysis_type": tab_ans.get("analysis_type", "tabular_enhanced")
            }
            
        except Exception as e:
            print(f"[TABULAR] ERROR: {str(e)}")
            return {
                "answer": f"Tabular analysis failed: {str(e)}",
                "route": route,
                "sources": [],
                "error": str(e),
                "analysis_type": "tabular_error"
            }

    return {"answer": "I couldn't determine how to answer this question.", "route": route, "sources": []}
