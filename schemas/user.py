import re
import uuid
from datetime import date
from typing import Optional

from fastapi_users import schemas
from pydantic import Field, validator

class UserRead(schemas.BaseUser[uuid.UUID]):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    bio: Optional[str] = None

class UserReadPublic(schemas.BaseUser[uuid.UUID]):
    id: uuid.UUID
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    bio: Optional[str]
    gender: Optional[str]
    date_of_birth: Optional[date]
    
    class Config:
        from_attributes = True

class UserCreate(schemas.BaseUserCreate):
    username: Optional[str] = Field(
        None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None

    @validator("password")
    def validate_password_strength(cls, value):
        if len(value) < 8:
            raise ValueError("Hasło musi mieć co najmniej 8 znaków.")
        if not re.search(r"[A-Z]", value):
            raise ValueError("Hasło musi zawierać co najmniej jedną dużą literę.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Hasło musi zawierać co najmniej jedną małą literę.")
        if not re.search(r"\d", value):
            raise ValueError("Hasło musi zawierać co najmniej jedną cyfrę.")
        return value

class UserUpdate(schemas.BaseUserUpdate):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    bio: Optional[str] = None

class UserAdminUpdate(UserUpdate):
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    is_verified: Optional[bool] = None