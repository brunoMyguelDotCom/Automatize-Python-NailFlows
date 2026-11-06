from abc import ABC, abstractmethod

from app.domain.models import Appointment, SyncStatus


class BaseCalendar(ABC):
    @abstractmethod
    def create_event(self, appointment: Appointment) -> str | None:
        """Returns the Google Event ID"""

    @abstractmethod
    def update_event(self, event_id: str, appointment: Appointment) -> bool:
        pass

    @abstractmethod
    def delete_event(self, event_id: str) -> bool:
        pass

    @abstractmethod
    def get_event_status(self, event_id: str) -> SyncStatus | None:
        pass
