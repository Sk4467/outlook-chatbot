# backend/rag/vector_store.py
import chromadb
from chromadb.config import Settings

# One in-memory client for the runtime
_client = chromadb.Client(Settings(anonymized_telemetry=False))

# Three separate collections
MAIL_BODIES = _client.get_or_create_collection(
    name="mail_bodies", metadata={"hnsw:space": "cosine"}
)
ATTACHMENTS_SEMANTIC = _client.get_or_create_collection(
    name="attachments_semantic", metadata={"hnsw:space": "cosine"}
)
ATTACHMENTS_TABULAR_IDX = _client.get_or_create_collection(
    name="attachments_tabular_idx", metadata={"hnsw:space": "cosine"}
)

def reset_all():
    for coll in (MAIL_BODIES, ATTACHMENTS_SEMANTIC, ATTACHMENTS_TABULAR_IDX):
        ids = coll.get(ids=None, where={}, limit=10_000).get("ids", [])
        if ids:
            coll.delete(ids=ids)