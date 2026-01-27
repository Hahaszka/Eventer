from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.orm import selectinload

from database.setup import get_async_session
from models.event import Event, EventCategory
from models.user import User
from schemas.event import EventCreate, EventRead, EventUpdate
from auth.config import fastapi_users

router = APIRouter()
current_user = fastapi_users.current_user(active=True)

# 1. READ ALL
@router.get("/", response_model=List[EventRead])
async def get_events(
    search: Optional[str] = Query(None),
    category: Optional[EventCategory] = Query(None),
    min_lat: Optional[float] = Query(None),
    max_lat: Optional[float] = Query(None),
    min_lng: Optional[float] = Query(None),
    max_lng: Optional[float] = Query(None),
    limit: int = 200,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user) 
):
    query = select(Event).options(selectinload(Event.creator)).where(Event.is_deleted == False)

    if category:
        query = query.where(Event.category == category.value)

    if search:
        query = query.where(
            or_(
                Event.title.ilike(f"%{search}%"),
                Event.description.ilike(f"%{search}%")
            )
        )

    if min_lat is not None and max_lat is not None and min_lng is not None and max_lng is not None:
        query = query.where(
            and_(
                Event.latitude >= min_lat,
                Event.latitude <= max_lat,
                Event.longitude >= min_lng,
                Event.longitude <= max_lng
            )
        )
    
    query = query.order_by(Event.event_date.asc()).limit(limit)
    
    result = await session.execute(query)
    return result.scalars().all()

# 2. MOJE WYDARZENIA 
@router.get("/me", response_model=List[EventRead])
async def get_my_events(
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user)
):
    query = select(Event).options(selectinload(Event.creator)).where(
        Event.creator_id == user.id, 
        Event.is_deleted == False
    ).order_by(desc(Event.event_date))
    
    result = await session.execute(query)
    return result.scalars().all()

# 3. POJEDYNCZE WYDARZENIE
@router.get("/{event_id}", response_model=EventRead)
async def get_event(
    event_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user)
):
    query = select(Event).options(selectinload(Event.creator)).where(Event.id == event_id, Event.is_deleted == False)
    result = await session.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Wydarzenie nie zostało znalezione")
    
    return event

# 4. WYDARZENIA KONKRETNEGO UŻYTKOWNIKA
@router.get("/user/{user_id}", response_model=List[EventRead])
async def get_user_events(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session)
):
    query = select(Event).options(selectinload(Event.creator)).where(
        Event.creator_id == user_id, 
        Event.is_deleted == False
    ).order_by(desc(Event.event_date))
    
    result = await session.execute(query)
    return result.scalars().all()

# 5. TWORZENIE WYDARZENIA
@router.post("/", response_model=EventRead)
async def create_event(
    event_in: EventCreate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):  
    event_data = event_in.dict()
    if event_data.get("event_date") and event_data["event_date"].tzinfo:
        event_data["event_date"] = event_data["event_date"].replace(tzinfo=None)

    new_event = Event(
        **event_data,
        creator_id=user.id,
        is_deleted=False
    )
    session.add(new_event)
    await session.commit()
    await session.refresh(new_event)

    new_event.creator = user
    return new_event

# 6. AKTUALIZACJA
@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: uuid.UUID,
    event_update: EventUpdate,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    query = select(Event).options(selectinload(Event.creator)).where(Event.id == event_id, Event.is_deleted == False)
    result = await session.execute(query)
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Wydarzenie nie istnieje")

    if event.creator_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Brak uprawnień do edycji")

    update_data = event_update.dict(exclude_unset=True)
    if "event_date" in update_data and update_data["event_date"] and update_data["event_date"].tzinfo:
        update_data["event_date"] = update_data["event_date"].replace(tzinfo=None)

    for key, value in update_data.items():
        setattr(event, key, value)

    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event

# 7. USUWANIE
@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: uuid.UUID,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Wydarzenie nie istnieje")
        
    if event.creator_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=403, detail="Brak uprawnień do usunięcia")

    event.is_deleted = True
    session.add(event)
    await session.commit()
    return None