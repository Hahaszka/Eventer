# models/oauth.py

import uuid

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseOAuthAccountTableUUID
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from database.setup import Base


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False
    )