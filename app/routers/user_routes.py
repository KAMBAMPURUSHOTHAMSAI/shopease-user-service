from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.database.connection import get_db
from app.schemas.user_schema import ProfileCreate, ProfilePatch, ProfileRead, ProfileReplace
from app.schemas.address_schema import MessageResponse
from app.services import user_service

router = APIRouter(prefix="/api/users", tags=["User Profiles"])


@router.post("/profile", response_model=ProfileRead, status_code=status.HTTP_201_CREATED, summary="Create current user's profile")
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return user_service.create_profile(db, current_user.auth_user_id, payload)


@router.get("/profile", response_model=ProfileRead, summary="Get current user's profile")
def get_profile(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    return user_service.get_profile_by_auth_id(db, current_user.auth_user_id)


@router.put("/profile", response_model=ProfileRead, summary="Replace current user's profile")
def replace_profile(
    payload: ProfileReplace,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return user_service.update_profile(db, current_user.auth_user_id, payload)


@router.patch("/profile", response_model=ProfileRead, summary="Partially update current user's profile")
def patch_profile(
    payload: ProfilePatch,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return user_service.patch_profile(db, current_user.auth_user_id, payload)


@router.delete("/profile", status_code=status.HTTP_204_NO_CONTENT, summary="Delete current user's profile")
def remove_profile(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    user_service.delete_profile(db, current_user.auth_user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/profile/deactivate", response_model=ProfileRead, summary="Deactivate profile in User Service only")
def deactivate_profile(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    return user_service.deactivate_profile(db, current_user.auth_user_id)


@router.get("/account", response_model=ProfileRead, summary="Get current user's account/profile information")
def get_account(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    return user_service.get_profile_by_auth_id(db, current_user.auth_user_id)


@router.get("/account/status", response_model=MessageResponse, summary="Check local profile status")
def get_account_status(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    profile = user_service.get_profile_by_auth_id(db, current_user.auth_user_id, require_active=False)
    return MessageResponse(message="active" if profile.is_active else "deactivated")
