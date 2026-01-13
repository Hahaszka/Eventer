import asyncio
import os
import enum
import uuid
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from sqlalchemy import (
    Column, String, Boolean, Date, Enum, Text, Float, 
    ForeignKey, DateTime, Integer
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.dialects.postgresql import UUID

from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyBaseOAuthAccountTableUUID

# --- 1. KONFIGURACJA ---
print("--- 1. Wczytywanie konfiguracji... ---")
load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Nie znaleziono DATABASE_URL w pliku .env")

engine = create_async_engine(DATABASE_URL)
Base = declarative_base()


# --- 2. DEFINICJE ENUM ---
class GenderEnum(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"


# --- 3. DEFINICJE MODELI ---
class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    """
    Tabela: public.oauth_accounts
    Przechowuje tokeny Google/Facebook itp.
    """
    __tablename__ = "oauth_accounts"
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="cascade"), nullable=False)
    user = relationship("User", back_populates="oauth_accounts")


class User(SQLAlchemyBaseUserTableUUID, Base):
    """
    Tabela: public.users
    Główna tabela użytkownika.
    Dziedziczy podstawowe pola (email, hashed_password, is_active itp.) z SQLAlchemyBaseUserTableUUID.
    """
    __tablename__ = "users"

    username = Column(String(50), unique=True, index=True, nullable=True)
    first_name = Column(String(150), nullable=True)
    last_name = Column(String(150), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    
    gender = Column(Enum(GenderEnum, name="gender_enum"), nullable=True)
    
    bio = Column(String(500), nullable=True)
    deleted = Column(Boolean, default=False, nullable=False)

    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="creator")


class Event(Base):
    """
    Tabela: public.events
    Tabela wydarzeń tworzonych przez użytkowników.
    """
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    event_date = Column(DateTime(timezone=False), nullable=False)
    created_at = Column(DateTime(timezone=False), default=datetime.utcnow)
    
    creator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    creator = relationship("User", back_populates="events")


# --- 4. FUNKCJA TWORZĄCA TABELE ---
async def create_tables():
    print(f"--- 2. Łączenie z bazą: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else '...'} ---")
    
    async with engine.begin() as conn:
        
        print("--- 3. Tworzenie tabel w bazie danych... ---")
        await conn.run_sync(Base.metadata.create_all)
    
    print("--- SUKCES: Tabele (events, users, oauth_accounts) zostały utworzone/zaktualizowane. ---")
    
    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(create_tables())
    except Exception as e:
        print(f"\n!!! BŁĄD !!!: {e}")