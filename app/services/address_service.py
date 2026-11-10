from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.address_model import UserAddress
from app.models.user_model import UserProfile
from app.schemas.address_schema import AddressCreate, AddressPatch, AddressReplace
from app.services.user_service import get_profile_by_auth_id


def _lock_profile(db: Session, auth_user_id: int) -> UserProfile:
    profile = (
        db.query(UserProfile)
        .filter(UserProfile.auth_user_id == auth_user_id)
        .with_for_update()
        .first()
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile not found.")
    if not profile.is_active:
        raise HTTPException(status_code=403, detail="User profile is deactivated.")
    return profile


def _get_owned_address(db: Session, auth_user_id: int, address_id: int) -> tuple[UserProfile, UserAddress]:
    profile = get_profile_by_auth_id(db, auth_user_id)
    address = db.query(UserAddress).filter(UserAddress.id == address_id).first()
    if address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found.")
    if address.user_id != profile.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to access this address.")
    return profile, address


def list_addresses(db: Session, auth_user_id: int) -> list[UserAddress]:
    profile = get_profile_by_auth_id(db, auth_user_id)
    return (
        db.query(UserAddress)
        .filter(UserAddress.user_id == profile.id)
        .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc(), UserAddress.id.desc())
        .all()
    )


def get_address(db: Session, auth_user_id: int, address_id: int) -> UserAddress:
    return _get_owned_address(db, auth_user_id, address_id)[1]


def create_address(db: Session, auth_user_id: int, payload: AddressCreate) -> UserAddress:
    profile = _lock_profile(db, auth_user_id)
    data = payload.model_dump()
    requested_default = data.pop("is_default")
    if requested_default:
        db.query(UserAddress).filter(UserAddress.user_id == profile.id).update(
            {UserAddress.is_default: False}, synchronize_session=False
        )
    address = UserAddress(user_id=profile.id, is_default=requested_default, **data)
    db.add(address)
    try:
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to create address.") from exc


def update_address(db: Session, auth_user_id: int, address_id: int, payload: AddressReplace) -> UserAddress:
    profile, address = _get_owned_address(db, auth_user_id, address_id)
    data = payload.model_dump()
    requested_default = data.pop("is_default")
    if requested_default:
        _lock_profile(db, auth_user_id)
        db.query(UserAddress).filter(
            UserAddress.user_id == profile.id, UserAddress.id != address.id
        ).update({UserAddress.is_default: False}, synchronize_session=False)
    for key, value in data.items():
        setattr(address, key, value)
    address.is_default = requested_default
    try:
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to update address.") from exc


def patch_address(db: Session, auth_user_id: int, address_id: int, payload: AddressPatch) -> UserAddress:
    profile, address = _get_owned_address(db, auth_user_id, address_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="At least one address field must be supplied.")
    required_fields = {
        "address_type", "full_name", "phone_number", "address_line_1", "city", "state", "country", "postal_code", "is_default"
    }
    for field in required_fields.intersection(changes):
        if changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null.")
    if changes.get("is_default") is True:
        _lock_profile(db, auth_user_id)
        db.query(UserAddress).filter(
            UserAddress.user_id == profile.id, UserAddress.id != address.id
        ).update({UserAddress.is_default: False}, synchronize_session=False)
    for key, value in changes.items():
        setattr(address, key, value)
    try:
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to partially update address.") from exc


def delete_address(db: Session, auth_user_id: int, address_id: int) -> None:
    _, address = _get_owned_address(db, auth_user_id, address_id)
    try:
        db.delete(address)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to delete address.") from exc


def set_default_address(db: Session, auth_user_id: int, address_id: int) -> UserAddress:
    profile, address = _get_owned_address(db, auth_user_id, address_id)
    _lock_profile(db, auth_user_id)
    try:
        db.query(UserAddress).filter(UserAddress.user_id == profile.id).update(
            {UserAddress.is_default: False}, synchronize_session=False
        )
        address.is_default = True
        db.commit()
        db.refresh(address)
        return address
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to set default address.") from exc
