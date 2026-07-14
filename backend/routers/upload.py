"""Document upload — POST /api/upload: PDF/image, size validation, extraction, persist to DB, return fields + confidence.
Also: GET /api/documents/{id}/view — serve redacted PDF from DB for advisor review."""
import io
import json
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, File, UploadFile, HTTPException, Request, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from services.ocr_service import extract_t4, extract_document
from middleware.rate_limiter import limiter, UPLOAD_LIMIT, READ_LIMIT
from middleware.auth import get_current_user_optional
from services.auth_service import decode_token
from database.session import get_db
from database.models import Document, User

router = APIRouter()

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_CONTENT = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}


def _create_redacted_pdf_bytes(source_path: str) -> bytes | None:
    """Create a redacted copy of a PDF and return the bytes."""
    try:
        import fitz
        from services.redaction_service import redact_pdf_page_for_form

        doc = fitz.open(source_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            redact_pdf_page_for_form(page)
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception:
        return None


@router.post("/upload")
@limiter.limit(UPLOAD_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Accept PDF or image; validate size (10MB max); run extraction; persist Document; return structured fields + confidence."""
    if file.content_type and file.content_type not in ALLOWED_CONTENT:
        raise HTTPException(400, f"Unsupported type: {file.content_type}. Use PDF or image.")
    size = 0
    chunks = []
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_BYTES:
            raise HTTPException(400, f"File too large. Max {MAX_FILE_SIZE_MB}MB.")
        chunks.append(chunk)
    content = b"".join(chunks)
    suffix = Path(file.filename or "upload").suffix or ".pdf"
    if "pdf" in (file.content_type or ""):
        suffix = ".pdf"
    elif "png" in (file.content_type or ""):
        suffix = ".png"
    elif "jpeg" in (file.content_type or "") or "jpg" in (file.content_type or ""):
        suffix = ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = extract_document(tmp_path)

        # Persist Document in DB
        doc_type = result.get("doc_type", "T4")
        # Build safe extracted_data (exclude raw file content)
        extracted_data = {k: v for k, v in result.items() if k not in ("raw_text",)}
        doc = Document(
            user_id=user.id if user else None,
            doc_type=doc_type,
            file_name=file.filename,
            extracted_data=extracted_data,
        )
        db.add(doc)
        await db.flush()

        # Save redacted PDF bytes in DB for advisor review
        if suffix == ".pdf":
            redacted_bytes = _create_redacted_pdf_bytes(tmp_path)
            if redacted_bytes:
                doc.redacted_file_data = redacted_bytes
                await db.flush()

        await db.commit()

        result["document_id"] = doc.id
        return result
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.get("/upload/status")
def upload_status():
    return {"message": "Upload router ready"}


@router.get("/documents/{document_id}/view")
@limiter.limit(READ_LIMIT)
async def view_document(
    request: Request,
    document_id: int,
    token: str | None = None,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Serve the redacted PDF for a document. Used by the advisor to review source documents.
    Accepts auth via Authorization header OR ?token= query param (needed for iframe loading)."""
    # Fallback: if no user from header, try query param token (iframe can't set headers)
    if not user and token:
        payload = decode_token(token)
        if payload and "sub" in payload:
            user = await db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "Authentication required")

    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    if not doc.redacted_file_data:
        raise HTTPException(404, "No redacted PDF available for this document")

    filename = f"{doc.file_name or 'document'}_redacted.pdf"
    return Response(
        content=doc.redacted_file_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
