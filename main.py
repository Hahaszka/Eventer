import os
import yaml
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth.config import (
    fastapi_users,
    auth_backend_jwt,
    auth_backend_google,
    google_oauth_client,
    SECRET
)

from schemas.user import UserCreate, UserRead
from database.setup import create_db_and_tables
from routers import users as users_router
from routers import admin as admin_router 
from routers import events as events_router
from create_admin import create_admin_user
from rdg import generate_random_events

load_dotenv()

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- LIFESPAN: Start aplikacji ---")
    
    await create_db_and_tables()
    
    if os.path.exists("config.yaml"):
        try:
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            
            if config.get("setup", {}).get("create_admin", False):
                admin_data = config.get("admin", {})
                await create_admin_user(
                    email=admin_data.get("email"),
                    password=admin_data.get("password"),
                    username=admin_data.get("username"),
                    first_name=admin_data.get("first_name"),
                    last_name=admin_data.get("last_name")
                )

            if config.get("setup", {}).get("generate_dummy_data", False):
                count = config.get("setup", {}).get("dummy_data_count", 50)
                await generate_random_events(count)
                
        except Exception as e:
            print(f"⚠️  Błąd podczas przetwarzania config.yaml: {e}")
    else:
        print("ℹ️  Brak pliku config.yaml - pomijam inicjalizację danych.")

    yield
    print("--- LIFESPAN: Zamykanie aplikacji ---")


app = FastAPI(title="Eventer API", lifespan=lifespan)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if "/auth/google/callback" in request.url.path:
        return RedirectResponse(url="/auth.html?error=access_denied", status_code=302)

    if exc.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return RedirectResponse(url="/auth.html", status_code=302)
    
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

@app.post("/auth/logout")
async def logout():
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("fastapiusersauth")
    return response

current_superuser = fastapi_users.current_user(active=True, superuser=True)

@app.get("/admin")
async def admin_panel():
    return FileResponse("secure/admin.html")

@app.get("/admin/js/admin.js")
async def get_admin_js():
    return FileResponse("secure/js/admin.js", media_type="application/javascript")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("public/img/logo.png")

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
app.include_router(admin_router.router, prefix="/admin", tags=["Admin API"])
app.include_router(events_router.router, prefix="/events", tags=["Events"])

if os.path.isdir("public"):
    app.mount("/", StaticFiles(directory="public", html=True), name="public")