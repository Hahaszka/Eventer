import os
import uuid
from dotenv import load_dotenv
from fastapi import Response
from fastapi.responses import RedirectResponse
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

load_dotenv()

SECRET = os.environ.get("SECRET")
GOOGLE_OAUTH_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

auth_backend_jwt = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

class GoogleRedirectTransport(CookieTransport):
    async def get_login_response(self, token: str) -> Response:
        response = RedirectResponse(url="/dashboard.html", status_code=302)
        return self._set_login_cookie(response, token)

cookie_transport = GoogleRedirectTransport(
    cookie_max_age=3600,
    cookie_secure=False,
    cookie_httponly=True,
    cookie_samesite="lax"
)

google_oauth_client = GoogleOAuth2(GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET)

auth_backend_google = AuthenticationBackend(
    name="google-oauth",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend_jwt, auth_backend_google],
)