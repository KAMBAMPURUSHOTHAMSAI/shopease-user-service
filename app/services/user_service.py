from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user_model import UserProfile
from app.schemas.user_schema import ProfileCreate, ProfilePatch, ProfileReplace


def get_profile_by_auth_id(db: Session, auth_user_id: int, *, require_active: bool = True) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.auth_user_id == auth_user_id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found.")
    if require_active and not profile.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User profile is deactivated.")
    return profile


def create_profile(db: Session, auth_user_id: int, payload: ProfileCreate) -> UserProfile:
    existing = db.query(UserProfile.id).filter(UserProfile.auth_user_id == auth_user_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A profile already exists for this account.")
    profile = UserProfile(auth_user_id=auth_user_id, **payload.model_dump())
    db.add(profile)
    try:
        db.commit()
        db.refresh(profile)
        return profile
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A profile already exists for this account.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to create user profile.") from exc


def update_profile(db: Session, auth_user_id: int, payload: ProfileReplace) -> UserProfile:
    profile = get_profile_by_auth_id(db, auth_user_id)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    try:
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update user profile.") from exc


def patch_profile(db: Session, auth_user_id: int, payload: ProfilePatch) -> UserProfile:
    profile = get_profile_by_auth_id(db, auth_user_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="At least one profile field must be supplied.")
    for required in ("full_name", "phone_number"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} cannot be null.")
    for key, value in changes.items():
        setattr(profile, key, value)
    try:
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update user profile.") from exc


def delete_profile(db: Session, auth_user_id: int) -> None:
    profile = get_profile_by_auth_id(db, auth_user_id, require_active=False)
    try:
        db.delete(profile)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete user profile.") from exc


def deactivate_profile(db: Session, auth_user_id: int) -> UserProfile:
    profile = get_profile_by_auth_id(db, auth_user_id, require_active=False)
    if not profile.is_active:
        return profile
    profile.is_active = False
    try:
        db.commit()
        db.refresh(profile)
        return profile
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to deactivate user profile.") from exc
