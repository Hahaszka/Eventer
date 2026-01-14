import asyncio
from datetime import date
from fastapi import HTTPException
from auth.manager import UserManager
from database.setup import get_async_session, get_user_db
from models.user import User
from schemas.user import UserCreate

async def create_admin_user(email, password, username, first_name, last_name):
    print(f"--- INIT: Próba utworzenia administratora ({email}) ---")

    async_session_generator = get_async_session()
    session = await anext(async_session_generator)
    
    user_db_generator = get_user_db(session)
    user_db = await anext(user_db_generator)

    user_manager = UserManager(user_db)

    try:
        user_create_schema = UserCreate(
            email=email,
            password=password,
            username=username,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date(2000, 1, 1),
        )

        await user_manager.create(
            user_create_schema,
            safe=False,
            is_superuser=True,
            is_verified=True,
        )
        print("✅ Administrator został pomyślnie utworzony!")

    except HTTPException as e:
        if "już istnieje" in e.detail:
            print(f"ℹ️  Info: Administrator {email} już istnieje. Pomijam.")
        else:
            print(f"⚠️  Błąd przy tworzeniu admina: {e.detail}")
    except Exception as e:
        print(f"⚠️  Nieoczekiwany błąd admina: {e}")
    finally:
        await session.close()