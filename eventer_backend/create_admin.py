import asyncio
import uuid
from datetime import date

from fastapi import HTTPException

# Ważne: upewnij się, że te importy wskazują na poprawne pliki w Twoim projekcie
from auth.manager import UserManager
from database.setup import get_async_session, get_user_db
from models.user import User
from schemas.user import UserCreate

# --- DANE ADMINISTRATORA ---
# Zmień hasło na swoje własne, bardzo silne hasło.
ADMIN_EMAIL = "michalski.szkolny@gmail.com"
ADMIN_PASSWORD = "!EventerNaZaliczenieRobiony2321!"
ADMIN_USERNAME = "admin_kacper"
ADMIN_FIRST_NAME = "Kacper"
ADMIN_LAST_NAME = "Michalski"
ADMIN_DATE_OF_BIRTH = date(2000, 1, 1)


async def create_admin_user():
    """
    Główna funkcja tworząca administratora.
    """
    print("Rozpoczynam tworzenie administratora...")

    # Musimy ręcznie stworzyć kontekst dla sesji bazy danych
    async_session_generator = get_async_session()
    session = await anext(async_session_generator)
    
    user_db_generator = get_user_db(session)
    user_db = await anext(user_db_generator)

    user_manager = UserManager(user_db)

    try:
        # Przygotowujemy dane użytkownika zgodnie ze schematem UserCreate
        user_create_schema = UserCreate(
            email=ADMIN_EMAIL,
            password=ADMIN_PASSWORD,
            username=ADMIN_USERNAME,
            first_name=ADMIN_FIRST_NAME,
            last_name=ADMIN_LAST_NAME,
            date_of_birth=ADMIN_DATE_OF_BIRTH,
        )

        # Tworzymy użytkownika, ustawiając flagę superużytkownika
        # `safe=False` pozwala nam ustawić dodatkowe flagi, takie jak is_superuser
        await user_manager.create(
            user_create_schema,
            safe=False,
            is_superuser=True,
            is_verified=True,  # Możemy od razu zweryfikować admina
        )
        print("✅ Administrator został pomyślnie utworzony!")
        print(f"   Email: {ADMIN_EMAIL}")
        print(f"   Hasło: [UKRYTE]")

    except HTTPException as e:
        # Obsługa błędu, jeśli użytkownik już istnieje
        if "już istnieje" in e.detail:
            print(f"⚠️  Błąd: Administrator z emailem '{ADMIN_EMAIL}' lub nazwą '{ADMIN_USERNAME}' już istnieje.")
            print("   Nie podjęto żadnych działań.")
        else:
            print(f"Wystąpił nieoczekiwany błąd: {e.detail}")
    finally:
        # Pamiętaj, aby zamknąć sesję
        await session.close()


if __name__ == "__main__":
    asyncio.run(create_admin_user())