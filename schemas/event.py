from typing import Optional
from datetime import datetime
import uuid
from pydantic import BaseModel
from models.event import EventCategory
from schemas.user import UserReadPublic

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_date: datetime
    category: EventCategory = EventCategory.OTHER
    latitude: float
    longitude: float

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    category: Optional[EventCategory] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class EventRead(EventBase):
    id: uuid.UUID
    created_at: datetime
    creator_id: uuid.UUID
    creator: Optional[UserReadPublic]

    class Config:
        from_attributes = True