import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from schemas.user import UserRead

class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    event_date: datetime

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[datetime] = None

class EventRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    latitude: float
    longitude: float
    event_date: datetime
    created_at: datetime
    creator_id: uuid.UUID
    is_deleted: bool
    creator: Optional[UserRead] 
    
    class Config:
        from_attributes = True