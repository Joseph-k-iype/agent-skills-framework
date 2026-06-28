"""Auth router — login / refresh / me."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user, get_db
from app.auth.service import AuthService
from app.core.envelope import success
from app.schemas.auth import LoginRequest, RefreshRequest

router = APIRouter()


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await AuthService(db).login(body.username, body.password)
    return success(result.model_dump())


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    tokens = await AuthService(db).refresh(body.refresh_token)
    return success(tokens.model_dump())


@router.get("/me")
async def me(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await AuthService(db).me(user.id)
    return success(profile.model_dump())
