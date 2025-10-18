# auth/manager.py

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
        """
        Logika wywoływana PO tym, jak użytkownik poprosi o reset hasła.
        Wysyłka e-maila jest zakomentowana, aby uniknąć błędów 401.
        """
        print("--- FUNKCJA RESETOWANIA HASŁA URUCHOMIONA ---")
        print(f"Użytkownik {user.first_name or user.email} poprosił o reset.")
        print("")
        print(f"Token do resetu hasła (skopiuj go): {token}")
        print("")
        print("--------------------------------------------------")

        # === SEKCJA SENDGRID (TYMCZASOWO WYŁĄCZONA) ===
        #
        # print("Próba wysłania e-maila przez SendGrid...")
        # api_key = os.environ.get("SENDGRID_API_KEY")
        # sender_email = os.environ.get("APP_SENDER_EMAIL")
        #
        # if not api_key or not sender_email:
        #     print("BŁĄD KRYTYCZNY: Brak SENDGRID_API_KEY lub APP_SENDER_EMAIL w .env.")
        #     return
        #
        # message = Mail(
        #     from_email=sender_email,
        #     to_emails=user.email,
        #     subject='Eventer - Token do resetu hasła',
        #     html_content=f"Oto Twój token: <strong>{token}</strong>"
        # )
        #
        # try:
        #     sg = SendGridAPIClient(api_key)
        #     response = sg.send(message)
        #     print(f"E-mail z tokenem wysłany do {user.email}.")
        #     print(f"Status SendGrid: {response.status_code}")
        #
        # except Exception as e:
        #     print(f"BŁĄD podczas wysyłania e-maila przez SendGrid: {e}")
        #
        # === KONIEC SEKCJI SENDGRID ===


    async def create(
        self,
        user_create: schemas.BaseUserCreate,
        safe: bool = False,
        request: Optional[Request] = None,
        **kwargs,
    ) -> User:
        """
        Metoda do tradycyjnej rejestracji i tworzenia admina.
        """
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
