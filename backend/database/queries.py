"""Reusable query helpers that enforce the advisor-approval boundary.

Rule: No AI-generated insight reaches a customer without advisor approval.
All user-facing code MUST use these helpers instead of querying Insight directly.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Insight, ActionItem


def approved_insights_query(profile_id: int | None = None, profile_ids: list[int] | None = None):
    """Return a select() for approved insights only.

    Use profile_id for a single profile, or profile_ids for multiple.
    """
    query = select(Insight).where(Insight.review_status == "APPROVED")
    if profile_id is not None:
        query = query.where(Insight.profile_id == profile_id)
    elif profile_ids is not None:
        query = query.where(Insight.profile_id.in_(profile_ids))
    return query


async def has_pending_insights(db: AsyncSession, profile_id: int) -> bool:
    """Check whether a profile has any PENDING insights (under review)."""
    result = await db.execute(
        select(Insight.id).where(
            Insight.profile_id == profile_id,
            Insight.review_status == "PENDING",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def has_pending_insights_bulk(db: AsyncSession, profile_ids: list[int]) -> bool:
    """Check whether ANY of the given profiles have PENDING insights."""
    if not profile_ids:
        return False
    result = await db.execute(
        select(Insight.id).where(
            Insight.profile_id.in_(profile_ids),
            Insight.review_status == "PENDING",
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


def approved_action_items_query(profile_ids: list[int]):
    """Return action items whose linked insight is approved, or that have no linked insight."""
    return (
        select(ActionItem)
        .outerjoin(Insight, ActionItem.insight_id == Insight.id)
        .where(
            ActionItem.profile_id.in_(profile_ids),
            (ActionItem.insight_id.is_(None)) | (Insight.review_status == "APPROVED"),
        )
    )
