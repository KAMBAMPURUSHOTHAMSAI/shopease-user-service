import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Gender = Literal["Male", "Female", "Other", "Prefer not to say"]


def validate_phone(value: str) -> str:
    cleaned = value.strip()
    if not re.fullmatch(r"\+?[0-9][0-9\s()\-]{5,22}", cleaned):
        raise ValueError("Enter a valid phone number (7–23 characters).")
    return cleaned


class ProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=150)
    phone_number: str = Field(min_length=7, max_length=25)
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image: str | None = Field(default=None, max_length=500)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("Full name must not be empty.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_must_be_past(cls, value: date | None) -> date | None:
        if value is not None and value >= date.today():
            raise ValueError("Date of birth must be in the past.")
        return value


class ProfileReplace(ProfileCreate):
    """Full profile replacement. Required fields remain full_name and phone_number."""


class ProfilePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone_number: str | None = Field(default=None, min_length=7, max_length=25)
    date_of_birth: date | None = None
    gender: Gender | None = None
    profile_image: str | None = Field(default=None, max_length=500)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = " ".join(value.split())
        if not value:
            raise ValueError("Full name must not be empty.")
        return value

    @field_validator("phone_number")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        return validate_phone(value) if value is not None else value

    @field_validator("date_of_birth")
    @classmethod
    def birth_date_must_be_past(cls, value: date | None) -> date | None:
        if value is not None and value >= date.today():
            raise ValueError("Date of birth must be in the past.")
        return value


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    auth_user_id: int
    full_name: str
    phone_number: str
    date_of_birth: date | None
    gender: str | None
    profile_image: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
