# backend/rag/retriever.py
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from config_loader import load_config_to_env as _cfg  # ensure GOOGLE_API_KEY set

_cfg()  # no-op if already loaded

def embed_text(text: str) -> List[float]:
    resp = genai.embed_content(model="models/text-embedding-004", content=text)
    return resp["embedding"]

def embed_texts(texts: List[str]) -> List[List[float]]:
    return [embed_text(t) for t in texts]

def topk_from_collection(collection, query: str, k: int = 6, where: Optional[Dict[str, Any]] = None):
    q_emb = embed_text(query)
    # chroma query rejects empty where={}; omit where when not provided
    kwargs: Dict[str, Any] = {"query_embeddings": [q_emb], "n_results": k}
    if where:
        kwargs["where"] = where
    res = collection.query(**kwargs)
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    return [{"text": d, "meta": m} for d, m in zip(docs, metas)]
