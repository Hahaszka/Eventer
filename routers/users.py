import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from auth.manager import UserManager, get_user_manager
from models.user import User
from schemas.user import UserRead, UserUpdate

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.setup import get_async_session
from schemas.user import UserReadPublic
from auth.config import fastapi_users

router = APIRouter()

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="",
    tags=["Users"],
)

@router.get("/public/{user_id}", response_model=UserReadPublic)
async def get_public_user_profile(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
        
    return user

@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(
    user: User = Depends(fastapi_users.current_user(active=True)),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Oznacza konto zalogowanego użytkownika jako usunięte (soft delete).
    """
    if user.deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto zostało już usunięte.",
        )

    user.deleted = True
    user.is_active = False
    await user_manager.update(user, safe=True)
    return None