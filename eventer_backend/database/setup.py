# database/setup.py

import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import Depends

from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

Base = declarative_base()

from models.oauth import OAuthAccount

print("--- 2. database/setup.py: Moduł zaimportowany ---")

engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db_and_tables():
    from models.user import User

    async with engine.begin() as conn:
        print("--- 4. create_db_and_tables: Nawiązywanie połączenia z silnikiem bazy... ---")
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    from models.user import User

    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)