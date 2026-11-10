from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.database.connection import get_db
from app.schemas.address_schema import AddressCreate, AddressPatch, AddressRead, AddressReplace
from app.services import address_service

router = APIRouter(prefix="/api/users/addresses", tags=["User Addresses"])


@router.post("", response_model=AddressRead, status_code=status.HTTP_201_CREATED, summary="Add an address")
def create_address(
    payload: AddressCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return address_service.create_address(db, current_user.auth_user_id, payload)


@router.get("", response_model=list[AddressRead], summary="List current user's addresses")
def list_addresses(
    db: Session = Depends(get_db), current_user: AuthenticatedUser = Depends(get_current_user)
):
    return address_service.list_addresses(db, current_user.auth_user_id)


@router.get("/{address_id}", response_model=AddressRead, summary="Get an address owned by current user")
def get_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return address_service.get_address(db, current_user.auth_user_id, address_id)


@router.put("/{address_id}", response_model=AddressRead, summary="Replace an owned address")
def replace_address(
    address_id: int,
    payload: AddressReplace,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return address_service.update_address(db, current_user.auth_user_id, address_id, payload)


@router.patch("/{address_id}", response_model=AddressRead, summary="Partially update an owned address")
def patch_address(
    address_id: int,
    payload: AddressPatch,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return address_service.patch_address(db, current_user.auth_user_id, address_id, payload)


@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an owned address")
def remove_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    address_service.delete_address(db, current_user.auth_user_id, address_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{address_id}/default", response_model=AddressRead, summary="Set an owned address as default")
def make_default_address(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return address_service.set_default_address(db, current_user.auth_user_id, address_id)
