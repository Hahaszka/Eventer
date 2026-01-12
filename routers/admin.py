import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from auth.config import fastapi_users
from auth.manager import UserManager, get_user_manager
from database.setup import get_async_session
from models.user import User
from schemas.user import UserRead, UserCreate, UserAdminUpdate

router = APIRouter()

current_superuser = fastapi_users.current_user(active=True, superuser=True)

# 1. LISTA UŻYTKOWNIKÓW 
@router.get("/users", response_model=List[UserRead], dependencies=[Depends(current_superuser)])
async def get_all_users(
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(User).order_by(User.email))
    users = result.scalars().all()
    return users

# 2. STWÓRZ UŻYTKOWNIKA
@router.post("/users", response_model=UserRead, dependencies=[Depends(current_superuser)])
async def create_user(
    user_create: UserCreate,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.create(user_create, safe=True)
        return user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 3. AKTUALIZUJ UŻYTKOWNIKA
@router.patch("/users/{user_id}", response_model=UserRead, dependencies=[Depends(current_superuser)])
async def update_user(
    user_id: uuid.UUID,
    user_update: UserAdminUpdate,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.get(user_id)
        updated_user = await user_manager.update(user_update, user, safe=False)
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 4. USUŃ UŻYTKOWNIKA
@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(current_superuser)])
async def delete_user(
    user_id: uuid.UUID,
    user_manager: UserManager = Depends(get_user_manager),
):
    try:
        user = await user_manager.get(user_id)
        await user_manager.delete(user)
        return None
    except Exception as e:
        raise HTTPException(status_code=404, detail="Użytkownik nie istnieje.")