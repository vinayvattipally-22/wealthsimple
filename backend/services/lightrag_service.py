"""LightRAG service: graph-based RAG for Canadian tax law knowledge."""
import asyncio
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import openai_complete, openai_embed

log = logging.getLogger(__name__)

# Storage directory for graph + vector data (relative to backend/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_WORKING_DIR = str(_BACKEND_DIR / "lightrag_data")
_KNOWLEDGE_BASE_DIR = _BACKEND_DIR / "knowledge_base"
_INGEST_MARKER = _BACKEND_DIR / "lightrag_data" / ".ingest_marker.json"
_rag: Optional[LightRAG] = None


async def init_rag() -> LightRAG:
    """Initialize LightRAG with OpenAI. Call once at startup."""
    global _rag
    os.makedirs(_WORKING_DIR, exist_ok=True)

    # Use gpt-4o-mini for entity extraction (higher rate limits)
    # Use gpt-4o for queries via query_tax_guidance
    llm_model = os.getenv("LLM_MODEL_RAG", "gpt-4o-mini")

    _rag = LightRAG(
        working_dir=_WORKING_DIR,
        llm_model_func=openai_complete,
        llm_model_name=llm_model,
        embedding_func=openai_embed,
        chunk_token_size=1200,
        chunk_overlap_token_size=100,
        enable_llm_cache=True,
    )
    await _rag.initialize_storages()

    # Auto-ingest knowledge base if new or changed
    await _auto_ingest_knowledge_base()

    return _rag


async def _auto_ingest_knowledge_base():
    """Ingest knowledge_base/*.md files if they are new or changed since last ingest."""
    if not _KNOWLEDGE_BASE_DIR.exists():
        log.info("No knowledge_base/ directory found — skipping auto-ingest.")
        return

    md_files = sorted(_KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not md_files:
        log.info("No .md files in knowledge_base/ — skipping auto-ingest.")
        return

    # Build a hash of all file contents to detect changes
    current_hashes = {}
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        current_hashes[f.name] = hashlib.sha256(content.encode()).hexdigest()

    # Load previous ingest marker
    previous_hashes = {}
    if _INGEST_MARKER.exists():
        try:
            previous_hashes = json.loads(_INGEST_MARKER.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            previous_hashes = {}

    # Find files that are new or changed
    files_to_ingest = []
    for f in md_files:
        if f.name not in previous_hashes or previous_hashes[f.name] != current_hashes[f.name]:
            files_to_ingest.append(f)

    if not files_to_ingest:
        log.info("Knowledge base unchanged (%d files) — skipping re-ingest.", len(md_files))
        return

    log.info("Auto-ingesting %d new/changed knowledge base files: %s",
             len(files_to_ingest), [f.name for f in files_to_ingest])

    rag = _get_rag()
    ingested = 0
    for i, f in enumerate(files_to_ingest):
        content = f.read_text(encoding="utf-8").strip()
        if content:
            try:
                await rag.ainsert(content)
                ingested += 1
                log.info("  Ingested: %s (%d/%d)", f.name, ingested, len(files_to_ingest))
                # Brief pause between files to avoid rate limits
                if i < len(files_to_ingest) - 1:
                    await asyncio.sleep(5)
            except Exception as e:
                log.error("  Failed to ingest %s: %s", f.name, e)

    # Update marker with all current hashes
    _INGEST_MARKER.write_text(json.dumps(current_hashes, indent=2), encoding="utf-8")
    log.info("Knowledge base auto-ingest complete: %d/%d files ingested.", ingested, len(files_to_ingest))


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
