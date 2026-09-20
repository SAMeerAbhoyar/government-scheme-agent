import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Profile
from app.models.scheme import Scheme
from app.models.activity import SavedScheme, Notification
from app.services.matching import match_scheme_against_profile
from app.services.email_service import send_email_notification

logger = logging.getLogger(__name__)

def profile_to_dict(profile: Optional[Profile]) -> Dict[str, Any]:
    if not profile:
        return {}
    data = {}
    for col in Profile.__table__.columns:
        if col.name not in ("id", "user_id"):
            val = getattr(profile, col.name)
            if val is not None:
                if hasattr(val, '__float__'):
                    data[col.name] = float(val)
                else:
                    data[col.name] = val
    if profile.other_attributes and isinstance(profile.other_attributes, dict):
        data.update(profile.other_attributes)
    return data

async def notify_saved_scheme_changed(db: AsyncSession, scheme_id: uuid.UUID) -> int:
    """
    Trigger 1: Saved scheme changed.
    Sends notification to all users who saved this scheme.
    Deduplication: avoids creating duplicate scheme_change notification if one already exists for this scheme.
    """
    stmt_scheme = select(Scheme).where(Scheme.id == scheme_id)
    res_scheme = await db.execute(stmt_scheme)
    scheme = res_scheme.scalar_one_or_none()
    if not scheme:
        return 0

    stmt_saved = select(SavedScheme).where(SavedScheme.scheme_id == scheme_id)
    res_saved = await db.execute(stmt_saved)
    saved_entries = res_saved.scalars().all()

    created_count = 0
    for entry in saved_entries:
        # Deduplication check
        stmt_existing = select(Notification).where(
            and_(
                Notification.user_id == entry.user_id,
                Notification.scheme_id == scheme_id,
                Notification.type == "scheme_change"
            )
        )
        res_existing = await db.execute(stmt_existing)
        if res_existing.scalar_one_or_none() is not None:
            continue

        msg = f"Saved scheme '{scheme.name}' has been updated with new details."
        notif = Notification(
            user_id=entry.user_id,
            scheme_id=scheme_id,
            type="scheme_change",
            message=msg
        )
        db.add(notif)
        created_count += 1

        # Trigger email stub if email available
        stmt_user = select(User).where(User.id == entry.user_id)
        res_user = await db.execute(stmt_user)
        user = res_user.scalar_one_or_none()
        if user and user.email:
            await send_email_notification(
                to_email=user.email,
                subject=f"Update on saved scheme: {scheme.name}",
                body=msg
            )

    await db.commit()
    return created_count

async def notify_approaching_deadlines(db: AsyncSession) -> int:
    """
    Trigger 2: Saved scheme deadline within 7 days.
    Deduplication: check if deadline_approaching notification was already created within last 7 days.
    """
    now = datetime.now(timezone.utc)
    seven_days_later = now + timedelta(days=7)

    stmt = (
        select(SavedScheme, Scheme)
        .join(Scheme, SavedScheme.scheme_id == Scheme.id)
        .where(Scheme.status == "active")
        .where(Scheme.deadline_date.isnot(None))
        .where(and_(Scheme.deadline_date >= now, Scheme.deadline_date <= seven_days_later))
    )
    res = await db.execute(stmt)
    pairs = res.all()

    created_count = 0
    for saved, scheme in pairs:
        # Check deduplication
        stmt_existing = select(Notification).where(
            and_(
                Notification.user_id == saved.user_id,
                Notification.scheme_id == scheme.id,
                Notification.type == "deadline_approaching"
            )
        )
        res_existing = await db.execute(stmt_existing)
        if res_existing.scalar_one_or_none() is not None:
            continue

        days_left = max(1, (scheme.deadline_date - now).days)
        msg = f"Saved scheme '{scheme.name}' deadline is in {days_left} days."
        notif = Notification(
            user_id=saved.user_id,
            scheme_id=scheme.id,
            type="deadline_approaching",
            message=msg
        )
        db.add(notif)
        created_count += 1

    await db.commit()
    return created_count

async def notify_new_relevant_scheme(db: AsyncSession, scheme_id: uuid.UUID) -> int:
    """
    Trigger 3: A new active scheme matches a user's profile via Mode 2 engine.
    Deduplication: check if new_scheme_match notification already created for this user + scheme.
    """
    stmt_scheme = select(Scheme).where(Scheme.id == scheme_id)
    res_scheme = await db.execute(stmt_scheme)
    scheme = res_scheme.scalar_one_or_none()
    if not scheme or scheme.status != "active":
        return 0

    stmt_profiles = select(Profile)
    res_profiles = await db.execute(stmt_profiles)
    profiles = res_profiles.scalars().all()

    created_count = 0
    for p in profiles:
        # Deduplication check
        stmt_existing = select(Notification).where(
            and_(
                Notification.user_id == p.user_id,
                Notification.scheme_id == scheme_id,
                Notification.type == "new_scheme_match"
            )
        )
        res_existing = await db.execute(stmt_existing)
        if res_existing.scalar_one_or_none() is not None:
            continue

        p_dict = profile_to_dict(p)
        match_res = match_scheme_against_profile(p_dict, scheme)
        if match_res.status == "potentially_relevant":
            msg = f"New scheme '{scheme.name}' matches your profile!"
            notif = Notification(
                user_id=p.user_id,
                scheme_id=scheme_id,
                type="new_scheme_match",
                message=msg
            )
            db.add(notif)
            created_count += 1

    await db.commit()
    return created_count
