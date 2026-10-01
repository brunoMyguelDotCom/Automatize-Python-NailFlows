from abc import ABC, abstractmethod
from typing import Optional
from app.domain.models import Appointment, SyncStatus

class BaseCalendar(ABC):
    @abstractmethod
    def create_event(self, appointment: Appointment) -> Optional[str]:
        """Returns the Google Event ID"""
        pass

    @abstractmethod
    def update_event(self, event_id: str, appointment: Appointment) -> bool:
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        pass

    @abstractmethod
    def get_event_status(self, event_id: str) -> Optional[SyncStatus]:
        pass
