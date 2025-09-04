import io
from typing import List, Dict, Any, Tuple
from bs4 import BeautifulSoup
from openpyxl import load_workbook
import fitz  # PyMuPDF

def html_to_text(html: str) -> str:
    return BeautifulSoup(html or "", "html.parser").get_text(separator=" ", strip=True)

def chunk_text(text: str, max_words: int = 900, overlap: int = 80) -> List[str]:
    words = (text or "").split()
    if not words:
        return []
    chunks, start = [], 0
    while start < len(words):
        end = min(len(words), start + max_words)
        chunks.append(" ".join(words[start:end]))
        if end == len(words): break
        start = max(0, end - overlap)
    return chunks

def parse_pdf_bytes(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    out: List[Dict[str, Any]] = []
    for i in range(len(doc)):
        page = doc[i]
        text = page.get_text("text") or ""
        out.append({"text": text, "page": i + 1})
    doc.close()
    return out

def xlsx_summary_from_bytes(xlsx_bytes: bytes, sample_rows: int = 50) -> List[Dict[str, Any]]:
    """
    Return summary entries suitable for an index (NOT full-row embeddings).
    Each entry gets sheet name, columns, row_count, and a short sample preview.
    """
    wb = load_workbook(io.BytesIO(xlsx_bytes), data_only=True)
    summaries: List[Dict[str, Any]] = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [(str(h).strip() if h is not None else "") for h in (rows[0] or [])]
        data_rows = rows[1:]
        row_count = len(data_rows)
        sample = data_rows[:sample_rows]
        # Render a compact preview (first few rows)
        preview_lines = []
        for r in sample:
            pairs = []
            for i, val in enumerate(r):
                col = headers[i] if i < len(headers) else f"Col{i+1}"
                pairs.append(f"{col}: {'' if val is None else str(val)}")
            preview_lines.append(" | ".join(pairs))
        text = f"Sheet: {ws.title}\nColumns: {', '.join(h for h in headers if h)}\nRows: {row_count}\nPreview:\n" + "\n".join(preview_lines[:5])
        summaries.append({
            "sheet": ws.title,
            "columns": headers,
            "row_count": row_count,
            "text": text,
        })
    return summaries