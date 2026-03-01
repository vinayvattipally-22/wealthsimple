"""Create financial profile from upload/extraction result."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import FinancialProfile, Document, User
from middleware.auth import get_current_user_optional

router = APIRouter()


@router.post("/profiles")
async def create_profile(
    body: dict = Body(...),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a financial profile from extracted T4/upload data.
    Expects: tax_year, province_code (or employment.province_of_employment), and employment totals or box values.
    """
    tax_year = body.get("tax_year", 2024)
    province = body.get("province_code") or (body.get("employment") or {}).get("province_of_employment") or "ON"
    # Fall back to user's province if not in document
    if province == "ON" and user and user.province:
        province = user.province
    employment = body.get("employment") or {}
    box_values = body.get("box_values") or body
    income = employment.get("total_employment_income")
    if income is None:
        income = float(box_values.get("14") or box_values.get(14) or 0)
    cpp = employment.get("total_cpp_contributions") or float(box_values.get("16") or box_values.get(16) or 0)
    ei = employment.get("total_ei_premiums") or float(box_values.get("18") or box_values.get(18) or 0)
    tax_withheld = employment.get("total_income_tax_withheld") or float(box_values.get("22") or box_values.get(22) or 0)
    employment_data = {
        "num_employers": employment.get("num_employers", 1),
        "total_employment_income": income,
        "total_cpp_contributions": cpp,
        "total_ei_premiums": ei,
        "total_income_tax_withheld": tax_withheld,
        "province_of_employment": province,
    }
    # Personal details (marital status, dependents, housing costs, etc.)
    personal = body.get("personal_details") or {}
    personal_details = {
        "date_of_birth": personal.get("date_of_birth"),
        "marital_status": personal.get("marital_status"),
        "num_children_under_18": personal.get("num_children_under_18", 0),
        "spouse_income": personal.get("spouse_income"),
        "rent_paid": personal.get("rent_paid", 0),
        "property_tax_paid": personal.get("property_tax_paid", 0),
    }
    profile_data = {
        "tax_year": tax_year,
        "province_code": province,
        "employment": employment_data,
        "structured_t4": box_values,
        "registered_accounts": body.get("registered_accounts") or {},
        "carryforwards": body.get("carryforwards") or {},
        "personal_details": personal_details,
        "derived": {},
    }
    profile = FinancialProfile(
        user_id=user.id if user else None,
        tax_year=tax_year,
        province_code=province,
        profile_data=profile_data,
        review_status="PENDING",
    )
    db.add(profile)
    await db.flush()

    # Link document to profile if document_id provided
    document_id = body.get("document_id")
    if document_id:
        doc = await db.get(Document, document_id)
        if doc:
            doc.profile_id = profile.id

    await db.commit()
    return {"profile_id": profile.id, "tax_year": tax_year, "province": province}


@router.patch("/profiles/{profile_id}")
async def update_profile(
    profile_id: int,
    body: dict = Body(...),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Update a financial profile — primarily for adding personal details after initial creation."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if user and profile.user_id and profile.user_id != user.id:
        raise HTTPException(403, "Not your profile")

    data = profile.profile_data or {}

    # Merge personal_details if provided
    personal = body.get("personal_details")
    if personal:
        existing = data.get("personal_details") or {}
        existing.update({k: v for k, v in personal.items() if v is not None})
        data["personal_details"] = existing

    # Allow updating registered_accounts too
    reg = body.get("registered_accounts")
    if reg:
        existing_reg = data.get("registered_accounts") or {}
        existing_reg.update(reg)
        data["registered_accounts"] = existing_reg

    profile.profile_data = data
    # Force SQLAlchemy to detect the JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(profile, "profile_data")
    await db.commit()

    return {"ok": True, "profile_id": profile_id}
