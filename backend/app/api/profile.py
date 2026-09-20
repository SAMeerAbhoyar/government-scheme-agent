from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.api.auth import get_current_user
from app.models.user import User, Profile
from app.schemas.profile import ProfileOut, ProfileUpdate

router = APIRouter(tags=["Profile"])

@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

    return profile

@router.put("/profile", response_model=ProfileOut)
async def update_profile(
    profile_in: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile

@router.post("/profile/answers", response_model=ProfileOut)
async def submit_profile_answers(
    answers: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Profile).where(Profile.user_id == current_user.id)
    result = await db.execute(stmt)
    profile = result.scalar_one_or_none()

    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)

    valid_cols = {col.name for col in Profile.__table__.columns}
    other_attrs = profile.other_attributes or {}

    for field, val in answers.items():
        if field in valid_cols and field not in ("id", "user_id"):
            setattr(profile, field, val)
        else:
            other_attrs[field] = val

    profile.other_attributes = other_attrs
    await db.commit()
    await db.refresh(profile)
    return profile

@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account and all associated user data permanently deleted."}
