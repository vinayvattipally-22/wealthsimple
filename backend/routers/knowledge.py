"""Knowledge base endpoints: ingest tax documents, query the graph, check status."""
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from services.lightrag_service import ingest_documents, query_tax_guidance

router = APIRouter()

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parent.parent / "knowledge_base"


class QueryRequest(BaseModel):
    question: str
    mode: str = "hybrid"


@router.post("/knowledge/ingest")
async def ingest_knowledge_base(request: Request):
    """Read all .md files from knowledge_base/ and ingest into LightRAG."""
    if not KNOWLEDGE_BASE_DIR.exists():
        raise HTTPException(404, "knowledge_base/ directory not found")

    md_files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not md_files:
        raise HTTPException(404, "No .md files found in knowledge_base/")

    texts = []
    file_names = []
    for f in md_files:
        content = f.read_text(encoding="utf-8")
        if content.strip():
            texts.append(content)
            file_names.append(f.name)

    result = await ingest_documents(texts)
    return {**result, "files": file_names}


@router.get("/knowledge/status")
async def knowledge_status(request: Request):
    """Return knowledge base status: files available and storage info."""
    md_files = sorted(KNOWLEDGE_BASE_DIR.glob("*.md")) if KNOWLEDGE_BASE_DIR.exists() else []
    storage_dir = Path(__file__).resolve().parent.parent / "lightrag_data"
    storage_exists = storage_dir.exists()
    storage_files = list(storage_dir.glob("*")) if storage_exists else []

    return {
        "knowledge_base_files": [f.name for f in md_files],
        "knowledge_base_count": len(md_files),
        "storage_initialized": storage_exists,
        "storage_files": [f.name for f in storage_files],
    }


@router.post("/knowledge/query")
async def query_knowledge(body: QueryRequest):
    """Query the tax knowledge graph directly."""
    if not body.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    result = await query_tax_guidance(body.question, mode=body.mode)
    return result
