"""Authentication endpoints: register, login, current user."""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.models import User
from services.auth_service import hash_password, verify_password, create_access_token
from middleware.auth import get_current_user

router = APIRouter()

PROVINCES = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}


def _user_response(user: User, token: str) -> dict:
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "province": user.province,
        },
    }


@router.post("/register")
async def register(body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Register a new user with email + password."""
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    name = (body.get("name") or "").strip()
    province = (body.get("province") or "").strip().upper()

    if not email or "@" not in email:
        raise HTTPException(400, "Valid email is required")
    if len(password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if province and province not in PROVINCES:
        raise HTTPException(400, f"Invalid province code: {province}")

    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name or None,
        role="USER",
        province=province or None,
    )
    db.add(user)
    await db.flush()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return _user_response(user, token)


@router.post("/login")
async def login(body: dict = Body(...), db: AsyncSession = Depends(get_db)):
    """Login with email + password, return JWT."""
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return _user_response(user, token)


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    """Return current user info."""
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "province": user.province,
        }
    }
