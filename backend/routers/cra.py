"""CRA API connector endpoints — placeholder for CRA authorization flow."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/cra/status")
def cra_status():
    """Placeholder for CRA connection status."""
    return {"message": "CRA router ready"}
