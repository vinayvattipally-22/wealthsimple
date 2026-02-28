"""Shared test fixtures: async DB, FastAPI test client, mock OpenAI."""
import os
import sys
import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from database.models import Base


@pytest_asyncio.fixture
async def async_db():
    """In-memory async SQLite session for isolated tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _mock_openai_response(content: str = "{}"):
    """Build a mock OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def mock_openai():
    """Patch OpenAI client so no real API calls are made."""
    import json
    mock_analysis = json.dumps({
        "insights": [
            {
                "id": "RRSP_BRACKET_OPTIMIZATION",
                "priority": "HIGH",
                "category": "THIS_YEAR",
                "headline": "Maximize RRSP to reduce tax bracket",
                "detail": "Contributing $12,000 to RRSP would reduce taxable income.",
                "estimated_value": 3120.0,
                "calculation_shown": "$12,000 x 26% marginal rate = $3,120",
                "action_required": "Contribute to RRSP before March 1 deadline",
                "confidence": 0.92,
            },
            {
                "id": "TFSA_GAP",
                "priority": "MEDIUM",
                "category": "LONG_TERM",
                "headline": "Utilize unused TFSA room",
                "detail": "You have $8,500 in unused TFSA contribution room.",
                "estimated_value": 425.0,
                "calculation_shown": "$8,500 x 5% estimated return = $425 tax-free",
                "action_required": "Open or top up TFSA",
                "confidence": 0.88,
            },
        ]
    })
    with patch("services.llm_service._client") as mock_client:
        mock_client.return_value.chat.completions.create.return_value = _mock_openai_response(mock_analysis)
        yield mock_client


@pytest_asyncio.fixture
async def test_client(async_db, mock_openai):
    """FastAPI test client with in-memory DB and mocked OpenAI."""
    from database.session import get_db
    from main import app

    async def override_get_db():
        yield async_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock LightRAG init to avoid real OpenAI calls
    with patch("services.lightrag_service.init_rag", return_value=MagicMock()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def advisor_headers(test_client):
    """Register an advisor user and return auth headers with JWT."""
    from database.models import User
    from services.auth_service import create_access_token, hash_password

    # Register a user first, then we need to make them advisor
    resp = await test_client.post("/api/auth/register", json={
        "email": "advisor@test.com",
        "password": "test123",
        "name": "Test Advisor",
        "province": "ON",
    })
    assert resp.status_code == 200
    token = resp.json()["token"]

    # Manually update role to ADVISOR in DB
    from database.session import get_db
    from main import app
    db_gen = app.dependency_overrides[get_db]()
    db = await db_gen.__anext__()
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.email == "advisor@test.com"))
    user = result.scalar_one()
    user.role = "ADVISOR"
    await db.commit()

    # Create new token with advisor role
    token = create_access_token({"sub": str(user.id), "role": "ADVISOR"})
    return {"Authorization": f"Bearer {token}"}
