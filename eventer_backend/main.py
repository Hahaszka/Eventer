import os
import uuid

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)
from httpx_oauth.clients.google import GoogleOAuth2

from auth.manager import get_user_manager
from models.user import User
from schemas.user import UserCreate, UserRead, UserUpdate

print("--- 1. main.py: Start importu modułów ---")
load_dotenv()


# --- KONFIGURACJA Z PLIKU .ENV ---
SECRET = os.environ.get("SECRET")
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

# --- MODUŁY AUTENTYKACJI ---
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


auth_backend_jwt = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

cookie_transport = CookieTransport(cookie_max_age=3600)

google_oauth_client = GoogleOAuth2(GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)

auth_backend_google = AuthenticationBackend(
    name="google-oauth",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# --- GŁÓWNY OBIEKT FASTAPI-USERS ---
fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend_jwt, auth_backend_google],
)

# Teraz importujemy routery
from database.setup import create_db_and_tables
from routers import users as users_router

# --- APLIKACJA FASTAPI ---
app = FastAPI(title="Eventer API")

# --- PODPIĘCIE GOTOWYCH ROUTERÓW ---
app.include_router(
    fastapi_users.get_auth_router(auth_backend_jwt), prefix="/auth/jwt", tags=["Auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["Auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(), prefix="/auth", tags=["Auth"]
)
app.include_router(
    fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["Auth"]
)
app.include_router(
    fastapi_users.get_oauth_router(
        oauth_client=google_oauth_client,
        backend=auth_backend_google,
        state_secret=SECRET,
        redirect_url="http://127.0.0.1:8000/auth/google/callback",
        associate_by_email=True,
        is_verified_by_default=True,
    ),
    prefix="/auth/google",
    tags=["Auth"],
)
app.include_router(users_router.router, prefix="/users", tags=["Users"])


# --- EVENT STARTOWY (TWORZENIE BAZY) ---
@app.on_event("startup")
async def on_startup():
    print("--- 3. on_startup: Próba utworzenia tabel w bazie ---")
    await create_db_and_tables()
    print("--- 5. on_startup: Tworzenie tabel ZAKOŃCZONE ---")


# --- PRZYKŁADOWY ENDPOINT ---
@app.get("/")
def read_root():
    return {"Hello": "Welcome to Eventer API"}
