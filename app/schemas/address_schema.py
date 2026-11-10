import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user_schema import validate_phone

AddressType = Literal["Home", "Office", "Other"]


class AddressFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_type: AddressType
    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str = Field(min_length=7, max_length=25)
    address_line_1: str = Field(min_length=3, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    country: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=3, max_length=20)

    @field_validator("full_name", "address_line_1", "city", "state", "country", "postal_code")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("This field must not be empty.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("address_type", mode="before")
    @classmethod
    def normalize_address_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().title()
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-\s]{1,18}[A-Za-z0-9]", value):
            raise ValueError("Enter a valid postal code.")
        return value


class AddressCreate(AddressFields):
    is_default: bool = False


class AddressReplace(AddressFields):
    is_default: bool = False


class AddressPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address_type: AddressType | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone_number: str | None = Field(default=None, min_length=7, max_length=25)
    address_line_1: str | None = Field(default=None, min_length=3, max_length=255)
    address_line_2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, min_length=2, max_length=100)
    state: str | None = Field(default=None, min_length=2, max_length=100)
    country: str | None = Field(default=None, min_length=2, max_length=100)
    postal_code: str | None = Field(default=None, min_length=3, max_length=20)
    is_default: bool | None = None

    @field_validator("address_type", mode="before")
    @classmethod
    def normalize_address_type(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().title()
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value) if value is not None else value

    @field_validator("full_name", "address_line_1", "city", "state", "country", "postal_code")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = " ".join(value.split())
        if not value:
            raise ValueError("This field must not be empty.")
        return value

    @field_validator("postal_code")
    @classmethod
    def validate_optional_postal_code(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-\s]{1,18}[A-Za-z0-9]", value):
            raise ValueError("Enter a valid postal code.")
        return value


class AddressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    address_type: str
    full_name: str
    phone_number: str
    address_line_1: str
    address_line_2: str | None
    city: str
    state: str
    country: str
    postal_code: str
    is_default: bool
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    message: str
