"""Action Items — trackable tasks generated from tax insights."""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.models import User, ActionItem, FinancialProfile
from middleware.auth import get_current_user
from middleware.rate_limiter import limiter, READ_LIMIT

router = APIRouter()


class UpdateActionItem(BaseModel):
    status: str  # pending, in_progress, completed, skipped


@router.get("/action-items")
@limiter.limit(READ_LIMIT)
async def list_action_items(
    request: Request,
    profile_id: int = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List action items for a specific profile or all user profiles."""
    # Get all user profile IDs for authorization
    prof_result = await db.execute(
        select(FinancialProfile.id).where(FinancialProfile.user_id == user.id)
    )
    user_profile_ids = [row[0] for row in prof_result]

    if not user_profile_ids:
        return {"action_items": [], "summary": {"pending": 0, "completed": 0, "total_savings": 0}}

    # Filter to specific profile or all
    if profile_id:
        if profile_id not in user_profile_ids:
            raise HTTPException(403, "Not your profile")
        target_ids = [profile_id]
    else:
        target_ids = user_profile_ids

    from database.queries import approved_action_items_query

    result = await db.execute(
        approved_action_items_query(target_ids)
        .order_by(ActionItem.deadline.asc().nullslast(), ActionItem.priority.asc())
    )
    items = result.scalars().all()

    items_out = []
    pending_count = 0
    completed_count = 0
    total_savings = 0

    for item in items:
        items_out.append({
            "id": item.id,
            "profile_id": item.profile_id,
            "insight_id": item.insight_id,
            "title": item.title,
            "description": item.description,
            "deadline": item.deadline.isoformat() if item.deadline else None,
            "priority": item.priority,
            "status": item.status,
            "estimated_value": item.estimated_value,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
        if item.status in ("pending", "in_progress"):
            pending_count += 1
            total_savings += item.estimated_value or 0
        elif item.status == "completed":
            completed_count += 1

    return {
        "action_items": items_out,
        "summary": {
            "pending": pending_count,
            "completed": completed_count,
            "total_savings": round(total_savings, 2),
        },
    }


@router.patch("/action-items/{item_id}")
@limiter.limit(READ_LIMIT)
async def update_action_item(
    item_id: int,
    body: UpdateActionItem,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update action item status."""
    item = await db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(404, "Action item not found")

    # Verify ownership
    profile = await db.get(FinancialProfile, item.profile_id)
    if not profile or profile.user_id != user.id:
        raise HTTPException(403, "Not your action item")

    valid_statuses = {"pending", "in_progress", "completed", "skipped"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Must be one of: {valid_statuses}")

    item.status = body.status
    await db.commit()

    return {
        "id": item.id,
        "status": item.status,
        "updated": True,
    }
