from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid

class SyncStatus(str, Enum):
    PENDING = "Pending"
    CONFIRMED = "Confirmed"
    REFUSED = "Refused"
    MAYBE = "Maybe"

class Client(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

class SyncState(BaseModel):
    google_event_id: Optional[str] = None
    status: SyncStatus = SyncStatus.PENDING
    last_synced: Optional[datetime] = None

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client: Client
    service: str
    start_time: datetime
    duration_minutes: int
    sync_state: SyncState = Field(default_factory=SyncState)

    @property
    def end_time(self) -> datetime:
        from datetime import timedelta
        return self.start_time + timedelta(minutes=self.duration_minutes)
