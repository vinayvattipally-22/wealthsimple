"""LightRAG service: graph-based RAG for Canadian tax law knowledge."""
import os
from pathlib import Path
from typing import Optional

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete, openai_embed

# Storage directory for graph + vector data (relative to backend/)
_WORKING_DIR = str(Path(__file__).resolve().parent.parent / "lightrag_data")
_rag: Optional[LightRAG] = None


async def init_rag() -> LightRAG:
    """Initialize LightRAG with OpenAI models. Call once at startup."""
    global _rag
    os.makedirs(_WORKING_DIR, exist_ok=True)

    _rag = LightRAG(
        working_dir=_WORKING_DIR,
        llm_model_func=openai_complete,
        llm_model_name="gpt-4o-mini",
        embedding_func=openai_embed,
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        enable_llm_cache=True,
    )
    await _rag.initialize_storages()
    return _rag


def _get_rag() -> LightRAG:
    if _rag is None:
        raise RuntimeError("LightRAG not initialized — call init_rag() first")
    return _rag


async def ingest_documents(texts: list[str]) -> dict:
    """Insert documents into the knowledge graph.

    LightRAG auto-chunks, extracts entities/relations, and builds the graph.
    """
    rag = _get_rag()
    inserted = 0
    for text in texts:
        if text.strip():
            await rag.ainsert(text)
            inserted += 1
    return {"inserted": inserted, "status": "ok"}


async def query_tax_guidance(question: str, mode: str = "hybrid") -> dict:
    """Query the tax knowledge graph.

    Modes:
        local  — entity-focused, specific facts
        global — theme-focused, broad patterns
        hybrid — combines local + global
        mix    — knowledge graph + vector retrieval (default LightRAG)
        naive  — basic vector search only
    """
    rag = _get_rag()
    param = QueryParam(mode=mode, top_k=10, stream=False)
    answer = await rag.aquery(question, param)
    return {"answer": answer, "mode": mode}
