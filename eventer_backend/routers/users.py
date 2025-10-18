import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from auth.manager import UserManager, get_user_manager
from models.user import User

from main import fastapi_users
from schemas.user import UserRead, UserUpdate

router = APIRouter()

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="",
    tags=["Users"],
)


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
