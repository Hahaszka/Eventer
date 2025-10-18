# schemas/user.py

import re
import uuid
from datetime import date
from typing import Optional

from fastapi_users import schemas
from pydantic import Field, validator


class UserRead(schemas.BaseUser[uuid.UUID]):
    # ZMIANA: username może być teraz pusty
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None


class UserCreate(schemas.BaseUserCreate):
    # Bez zmian - przy tradycyjnej rejestracji nadal wymagamy wszystkiego
    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    first_name: str
    last_name: str
    date_of_birth: date
    gender: Optional[str] = None

    @validator("password")
    def validate_password_strength(cls, value):
        # ... (walidacja hasła bez zmian) ...
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
    # ZMIANA: Pozwalamy użytkownikowi ustawić swój username
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None