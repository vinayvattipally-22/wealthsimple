"""What-If Scenario Simulator endpoint."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import User, FinancialProfile
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT
from services.scenario_engine import simulate_scenario, SCENARIO_TYPES

router = APIRouter()


class ScenarioRequest(BaseModel):
    profile_id: int
    scenario_type: str
    value: float | str


@router.post("/simulator/run")
@limiter.limit(READ_LIMIT)
async def run_scenario(
    body: ScenarioRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a what-if scenario against a user's financial profile."""
    profile = await db.get(FinancialProfile, body.profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if profile.user_id != user.id:
        raise HTTPException(403, "Not your profile")

    if body.scenario_type not in SCENARIO_TYPES:
        raise HTTPException(400, f"Invalid scenario type. Must be one of: {SCENARIO_TYPES}")

    result = simulate_scenario(
        profile_data=profile.profile_data or {},
        scenario={"type": body.scenario_type, "value": body.value},
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    return result
