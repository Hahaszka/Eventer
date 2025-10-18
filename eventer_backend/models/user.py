
import enum
import uuid
from typing import List

from sqlalchemy import Boolean, Column, Date, String
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, relationship

from database.setup import Base
from .oauth import OAuthAccount


class GenderEnum(str, enum.Enum):
    male = "M"
    female = "F"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = Column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = Column(
        String(length=320), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = Column(String(length=1024), nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    is_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    username: Mapped[str] = Column(
        String(length=50), unique=True, index=True, nullable=True
    )
    first_name: Mapped[str] = Column(String(length=150), nullable=True)
    last_name: Mapped[str] = Column(String(length=150), nullable=True)
    date_of_birth: Mapped[Date] = Column(Date, nullable=True)
    
    gender: Mapped[GenderEnum] = Column(
        PgEnum(GenderEnum, name="gender_enum", create_type=True), nullable=True
    )
    deleted: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    oauth_accounts: Mapped[List["OAuthAccount"]] = relationship(
        "OAuthAccount", lazy="subquery"
    )
