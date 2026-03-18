import os
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import User, ApiKey

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1200))

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password[:72], hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password[:72])

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def generate_api_key():
    return secrets.token_urlsafe(32)

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db)
):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nie udało się zweryfikować uprawnień")

    if api_key and isinstance(api_key, str):
        result = await db.execute(select(ApiKey).filter(ApiKey.key == api_key))
        db_api_key = result.scalars().first()
        if db_api_key:
            user_res = await db.execute(select(User).filter(User.id == db_api_key.user_id))
            return user_res.scalars().first()
        raise HTTPException(status_code=403, detail="Nieprawidłowy API Key")

    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None: raise credentials_exception
        except jwt.PyJWTError: raise credentials_exception
        
        result = await db.execute(select(User).filter(User.username == username))
        user = result.scalars().first()
        if user is None: raise credentials_exception
        return user

    raise credentials_exception