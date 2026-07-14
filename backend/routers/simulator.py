"""What-If Scenario Simulator endpoint with AI features."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from database.session import get_db
from database.models import User, FinancialProfile
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT, ANALYSIS_LIMIT
from services.scenario_engine import (
    simulate_scenario,
    SCENARIO_TYPES,
    generate_smart_suggestions,
    parse_natural_language_scenario,
    multi_year_projection,
)

router = APIRouter()


class ScenarioRequest(BaseModel):
    profile_id: int
    scenario_type: str
    value: float | str


class NLScenarioRequest(BaseModel):
    profile_id: int
    query: str


class MultiYearRequest(BaseModel):
    profile_id: int
    years: int = 10
    annual_rrsp: float = 0
    annual_tfsa: float = 0
    annual_fhsa: float = 0


async def _get_profile(profile_id: int, user: User, db: AsyncSession) -> FinancialProfile:
    """Fetch and validate profile ownership."""
    profile = await db.get(FinancialProfile, profile_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    if profile.user_id != user.id:
        raise HTTPException(403, "Not your profile")
    return profile


@router.post("/simulator/run")
@limiter.limit(READ_LIMIT)
async def run_scenario(
    body: ScenarioRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run a what-if scenario against a user's financial profile."""
    profile = await _get_profile(body.profile_id, user, db)

    if body.scenario_type not in SCENARIO_TYPES:
        raise HTTPException(400, f"Invalid scenario type. Must be one of: {SCENARIO_TYPES}")

    result = simulate_scenario(
        profile_data=profile.profile_data or {},
        scenario={"type": body.scenario_type, "value": body.value},
    )

    if "error" in result:
        raise HTTPException(400, result["error"])

    return result


@router.get("/simulator/suggestions/{profile_id}")
@limiter.limit(READ_LIMIT)
async def get_suggestions(
    profile_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered scenario suggestions based on the user's profile."""
    profile = await _get_profile(profile_id, user, db)
    suggestions = generate_smart_suggestions(profile.profile_data or {})
    return {"suggestions": suggestions}


@router.post("/simulator/natural-language")
@limiter.limit(ANALYSIS_LIMIT)
async def natural_language_scenario(
    body: NLScenarioRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parse a natural language scenario query and run the scenarios."""
    profile = await _get_profile(body.profile_id, user, db)
    profile_data = profile.profile_data or {}

    # Parse NL query into structured scenarios
    parsed = parse_natural_language_scenario(body.query, profile_data)
    scenarios = parsed.get("scenarios", [])

    if not scenarios:
        return {
            "parsed": parsed,
            "results": [],
            "error": "Could not parse your question into a scenario. Try being more specific.",
        }

    # Run each parsed scenario
    results = []
    for sc in scenarios:
        sc_type = sc.get("type", "")
        sc_value = sc.get("value", 0)
        if sc_type in SCENARIO_TYPES:
            result = simulate_scenario(profile_data, {"type": sc_type, "value": sc_value})
            results.append(result)

    return {
        "parsed": parsed,
        "results": results,
    }


@router.post("/simulator/multi-year")
@limiter.limit(READ_LIMIT)
async def run_multi_year(
    body: MultiYearRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Multi-year tax planning projection."""
    profile = await _get_profile(body.profile_id, user, db)
    result = multi_year_projection(
        profile_data=profile.profile_data or {},
        years=min(body.years, 30),
        annual_rrsp=body.annual_rrsp,
        annual_tfsa=body.annual_tfsa,
        annual_fhsa=body.annual_fhsa,
    )
    return result
