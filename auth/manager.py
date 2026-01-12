import os
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request, status
from fastapi_users import BaseUserManager, UUIDIDMixin, schemas
from sqlalchemy import select

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from database.setup import get_user_db
from models.user import User

load_dotenv()
SECRET = os.environ.get("SECRET")


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
       
        print("--- FUNKCJA RESETOWANIA HASŁA URUCHOMIONA ---")
        print(f"Użytkownik {user.first_name or user.email} poprosił o reset.")
        print("")
        print(f"Token do resetu hasła (skopiuj go): {token}")
        print("")
        print("--------------------------------------------------")

    async def create(
        self,
        user_create: schemas.BaseUserCreate,
        safe: bool = False,
        request: Optional[Request] = None,
        **kwargs,
    ) -> User:
        statement = select(User).where(
            (User.email == user_create.email) | (User.username == user_create.username)
        )
        existing_user_results = await self.user_db.session.execute(statement)
        existing_user = existing_user_results.scalars().first()

        if existing_user:
            if existing_user.email == user_create.email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Użytkownik z tym adresem e-mail już istnieje.",
                )
            if user_create.username and existing_user.username == user_create.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Użytkownik z taką nazwą użytkownika już istnieje.",
                )

        special_flags = {
            "is_superuser": kwargs.get("is_superuser", False),
            "is_verified": kwargs.get("is_verified", False),
        }

        created_user = await super().create(user_create, safe, request)

        if any(special_flags.values()):
            created_user = await self.user_db.update(created_user, special_flags)

        return created_user


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)